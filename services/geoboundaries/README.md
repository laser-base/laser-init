# geoboundaries-service

A microservice that serves [geoBoundaries v6.0.0](https://www.geoboundaries.org) administrative boundary GeoJSON. It implements the same API contract as `gadm-service` and is interchangeable with it in `laser-generate` via `--shape-source geoboundaries`.

## Why it exists

geoBoundaries is a fully open, CC-BY licensed boundary dataset maintained by the College of William & Mary. It is an alternative to GADM for contexts where license terms matter or where geoBoundaries' boundary definitions better match operational humanitarian usage. This service provides:

- On-demand download and caching of per-(ISO, level) boundary zips from GitHub.
- The same GeoJSON `FeatureCollection` response format as `gadm-service`, so the caller doesn't need to know which source was used.

## API

### `GET /health`

Returns `{"status": "ok"}`.

### `GET /boundaries/{ISO}/{level}`

Returns a GeoJSON `FeatureCollection` of administrative boundaries.

| Parameter | Description |
|-----------|-------------|
| `ISO` | ISO 3166-1 alpha-3 country code (e.g. `ETH`) |
| `level` | Admin level 0–5 |

**Feature properties:**

| Property | Description |
|----------|-------------|
| `nodeid` | Zero-based integer index |
| `name` | Region name (`shapeName` from geoBoundaries) |
| `gid` | geoBoundaries shape ID (`shapeID`) |

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | `level` outside 0–5 |
| 404 | geoBoundaries has no data for the requested ISO / level |

## How it differs from gadm-service

| | gadm-service | geoboundaries-service |
|---|---|---|
| Source | GADM 4.1 | geoBoundaries v6.0.0 |
| License | Non-commercial | CC-BY (open) |
| Coverage | ~250 countries, up to level 5 | ~200+ countries, typically 0–3 |
| Cache unit | One zip per country (all levels) | One zip per (ISO, level) |
| Geometry simplification | Yes — 0.001° for level ≥ 1 | No |
| Boundary definitions | Academic/statistical | Humanitarian (COD-AB aligned) |

geoBoundaries uses P-codes (`shapeID`) consistent with OCHA's Common Operational Datasets, making it the preferred source when integrating with humanitarian data pipelines.

## Caching

Each `(ISO, level)` combination is a separate zip file on GitHub. The service downloads and caches each on first request at `$CACHE_DIR/{ISO}/ADM{level}/geoBoundaries-{ISO}-ADM{level}-all.zip`. Subsequent requests for the same (ISO, level) are served from the cached zip.

The cache directory defaults to `/cache` in the container (backed by a 10 Gi Kubernetes PVC in AKS) and `~/.laser/cache/geoboundaries` locally.

## Running locally

```bash
pip install -r requirements.txt

CACHE_DIR=~/.laser/cache/geoboundaries uvicorn main:app --host 0.0.0.0 --port 8102

# Test
curl http://localhost:8102/boundaries/ETH/1
```

## Docker

```bash
docker build -t laser-geoboundaries-service .
docker run -p 8102:8000 -v geoboundaries-cache:/cache laser-geoboundaries-service
```

## AKS deployment

Deployed as part of `services/AKS/geodata-services.yaml`. Uses a 10 Gi PVC (`laser-geoboundaries-cache`) and a `LoadBalancer` service on port 80.

```bash
kubectl apply -f services/AKS/geodata-services.yaml --kubeconfig services/AKS/kube.conf
kubectl get pods -n laser-ai -l app=laser-geoboundaries-svc --kubeconfig services/AKS/kube.conf
```

## Known limitations

- **No geometry simplification**: Unlike `gadm-service`, geometries are served at full resolution. For countries with very detailed coastlines or borders, responses can be large (tens of MB).
- **Level availability varies**: geoBoundaries only includes levels for which data has been validated. Many countries have data only at levels 0–2.
- **GitHub rate limits**: Downloads come from `github.com/wmgeolab/geoBoundaries`. Repeated cold-start requests from many clients could hit GitHub's unauthenticated rate limit.
