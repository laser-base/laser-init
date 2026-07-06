# worldpop-service

A microservice that aggregates [WorldPop](https://www.worldpop.org) UN-adjusted population rasters into per-polygon counts for use by `laser-generate` and the browser choropleth client.

## Why it exists

Population data for spatial epidemic models must be attributed to each administrative unit (node). WorldPop provides globally consistent ~1 km rasters, but summing pixel values within arbitrary polygon boundaries requires GDAL/rasterio, significant RAM, and for large countries many minutes of computation. Running this once in a shared service means:

- The raster is downloaded and cached **once** per country/year — subsequent requests are served from the local GeoTIFF.
- No rasterio/GDAL installation is required on the user's machine.
- The browser choropleth client can aggregate population with a single `fetch()` call.

## API

### `GET /health`

Returns `{"status": "ok"}`.

### `POST /aggregate/{ISO}?year=YYYY`

Aggregates population for each polygon in the request body and returns a map of `nodeid → population`.

| Parameter | Description |
|-----------|-------------|
| `ISO` | ISO 3166-1 alpha-3 country code (e.g. `NGA`) |
| `year` | Raster year (2000–2020, default 2020) |

**Request body:** GeoJSON `FeatureCollection`. Each feature must have a `nodeid` integer in its `properties`.

**Response:** JSON object mapping `nodeid` (string key) to population count (float).

```json
{ "0": 4521302.0, "1": 1203847.0, "2": 892100.0, ... }
```

The response is **streamed** — the first bytes arrive quickly and results accumulate as each polygon is processed. This keeps the Azure Load Balancer's 4-minute idle TCP timeout from killing long-running aggregation requests.

### `POST /prewarm/{ISO}?year=YYYY`

Downloads and caches the raster for `ISO`/`year` without performing any aggregation. Use this to pre-populate the cache for large countries (BRA, IND, RUS, …) before the first `/aggregate` call.

Returns `{"status": "ok", "iso": "...", "year": ...}` once the raster is on disk.

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Body is not a GeoJSON FeatureCollection, or has no features |
| 404 | No WorldPop data for the requested ISO / year |
| 422 | Raster exceeds 2 GB and has not been pre-warmed (use `/prewarm` first) |

## Raster source

WorldPop UN-adjusted constrained dataset:
```
https://data.worldpop.org/GIS/Population/Global_2000_2020/{year}/{ISO}/{iso}_ppp_{year}_UNadj.tif
```

Only years 2000–2020 are available. `laser-generate` automatically clamps `start_year` to 2020 for the raster year.

## Memory and performance

| Raster size | Mode | Notes |
|-------------|------|-------|
| < 2 GB uncompressed | In-memory | Entire raster loaded once; polygon reads are fast array slices |
| ≥ 2 GB uncompressed | Windowed strips | 8 M pixels (~64 MB) read per strip per polygon; bounded memory regardless of country size |

In windowed mode, features are sorted by raster scan order (row then column) before aggregation, which maximises GDAL tile-cache reuse across adjacent polygons and is critical for level-2 queries with hundreds of small features (e.g. TZA/2 with 186 districts).

GDAL tile cache is set to 512 MB (`GDAL_CACHEMAX=512`) at startup.

## Caching

Rasters are cached at `$CACHE_DIR/{iso_lower}_ppp_{year}_UNadj.tif`. A per-(ISO, year) mutex prevents duplicate concurrent downloads. The cache directory defaults to `/cache` in the container (backed by a 100 Gi Kubernetes PVC in AKS) and `~/.laser/cache/worldpop` locally.

## Running locally

```bash
pip install -r requirements.txt

CACHE_DIR=~/.laser/cache/worldpop uvicorn main:app --host 0.0.0.0 --port 8104
```

Test with a small country first — NGA (~200 MB raster) is a reasonable smoke-test:

```bash
python test_client.py --url http://localhost:8104
```

For large countries (BRA, IND), pre-warm before aggregating:

```bash
curl -X POST "http://localhost:8104/prewarm/BRA?year=2020"
```

## Docker

```bash
docker build -t laser-worldpop-service .
docker run -p 8104:8000 -v worldpop-cache:/cache laser-worldpop-service
```

## AKS deployment

Deployed as part of `services/AKS/geodata-services.yaml`. Uses a 100 Gi PVC (`laser-worldpop-cache`), 4 CPU / 4 Gi memory limit. A separate prewarm Job (`worldpop-prewarm-job.yaml`) populates the cache for the default humanitarian country list after initial deployment.

```bash
# Deploy service
kubectl apply -f services/AKS/geodata-services.yaml --kubeconfig services/AKS/kube.conf

# Run prewarm job (once, after service is Ready)
kubectl apply -f services/AKS/worldpop-prewarm-job.yaml --kubeconfig services/AKS/kube.conf

# Monitor prewarm progress
kubectl logs -f job/laser-worldpop-prewarm -n laser-ai --kubeconfig services/AKS/kube.conf
```

## Known limitations

- **Year cap at 2020**: WorldPop's Global_2000_2020 dataset ends at 2020. There is no 2021+ raster.
- **Large country first-run latency**: BRA (~3.7 GB raster, ~30 min download), IND (~1.4 GB) benefit greatly from pre-warming.
- **Level-2 aggregation time**: Even with the raster cached, 500+ small polygons in windowed mode can take several minutes. The browser client warns and falls back to the CLI for known large-raster countries at high admin levels.
