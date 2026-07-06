# gadm-service

A lightweight HTTP microservice that serves [GADM 4.1](https://gadm.org) administrative boundary GeoJSON for use by `laser-generate` and the browser choropleth client.

## Why it exists

`laser-generate` needs administrative boundary polygons (shapes + names) as a prerequisite for population aggregation and model-grid construction. GADM provides high-quality, globally consistent boundaries at levels 0–4, but the raw shapefiles are large (hundreds of MB per country) and require GDAL/GeoPandas to parse. Running that machinery inside a shared microservice means:

- The shapefile is downloaded and cached **once**, then served instantly to all clients.
- No GDAL installation is required on the user's machine.
- The browser choropleth client can fetch GeoJSON directly with a simple `fetch()` call.

## API

### `GET /health`

Liveness check. Returns `{"status": "ok"}`.

### `GET /boundaries/{ISO}/{level}`

Returns a GeoJSON `FeatureCollection` of administrative boundaries.

| Parameter | Description |
|-----------|-------------|
| `ISO` | ISO 3166-1 alpha-3 country code (case-insensitive, e.g. `NGA`, `nga`) |
| `level` | Admin level 0–5 (0 = country, 1 = province, 2 = district, …) |

**Feature properties:**

| Property | Description |
|----------|-------------|
| `nodeid` | Zero-based integer index (stable within a request, matches WorldPop service) |
| `name` | Human-readable region name |
| `gid` | GADM GID string (e.g. `NGA.1_1`) |

**Geometry:** simplified to ~100 m (0.001°) for levels ≥ 1, which reduces payload size significantly for large countries while preserving topology at WorldPop raster resolution (~1 km).

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | `level` outside 0–5 |
| 404 | GADM has no data for the requested ISO or admin level |

**Example:**

```
GET /boundaries/NGA/1
```

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "nodeid": 0, "name": "Abia", "gid": "NGA.1_1" },
      "geometry": { "type": "MultiPolygon", "coordinates": [...] }
    },
    ...
  ]
}
```

## Caching

On first request for a country, the service downloads `gadm41_{ISO}_shp.zip` from `geodata.ucdavis.edu` (~1–500 MB depending on country) and caches it under `$CACHE_DIR/{ISO}/`. All admin levels for that country are served from the single cached zip — no re-download on subsequent requests or different level queries.

The cache directory defaults to `/cache` in the container (backed by a Kubernetes PVC in AKS) and `~/.laser/cache/gadm` locally.

## Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service on port 8101
CACHE_DIR=~/.laser/cache/gadm uvicorn main:app --host 0.0.0.0 --port 8101

# Run the test suite against it
python test_client.py --url http://localhost:8101
```

First request for a country triggers the shapefile download. Luxembourg (`LUX`, ~1 MB) is used by the test suite for speed.

## Docker

```bash
# Build
docker build -t laser-gadm-service .

# Run
docker run -p 8101:8000 -v gadm-cache:/cache laser-gadm-service
```

## AKS deployment

Deployed as part of `services/AKS/geodata-services.yaml` in the `laser-ai` namespace. The deployment uses a 20 Gi PVC (`laser-gadm-cache`) for the shapefile cache and exposes a `LoadBalancer` service on port 80.

```bash
# Deploy / update
kubectl apply -f services/AKS/geodata-services.yaml --kubeconfig services/AKS/kube.conf

# Check status
kubectl get pods -n laser-ai -l app=laser-gadm-svc --kubeconfig services/AKS/kube.conf
```

## Known limitations

- **BRA admin-2**: 5 572 municipalities. Geometry simplification keeps the response under 50 MB, but the request takes ~20 s on first read from zip. Subsequent requests are equally slow (no in-memory cache between requests).
- **Level 4–5**: Available only for countries where GADM provides sub-district data; most countries stop at level 2 or 3.
- **Single replica**: The deployment uses `strategy: Recreate` because the PVC is `ReadWriteOnce`. Scaling requires switching to a shared file store.
