# unocha-service

A microservice that serves [UNOCHA](https://www.unocha.org) global administrative boundary GeoJSON from the [Humanitarian Data Exchange (HDX)](https://data.humdata.org). It is the **default shape source** for `laser-generate` because OCHA boundaries are the standard reference for humanitarian response operations.

## Why it exists

UNOCHA's Common Operational Dataset (COD) administrative boundaries are the authoritative reference used by humanitarian organisations worldwide. They are designed to be consistent across UN agencies, NGOs, and government partners, making them the natural default for disease modelling work that feeds into response planning. This service provides:

- A one-time download and extraction of the full global GDB (~1–2 GB) at startup.
- Per-(ISO, level) in-memory caching so each country/level combination is read from disk only once.
- The same GeoJSON `FeatureCollection` response format as the other shape services.

## API

### `GET /health`

Returns `{"status": "ok", "gdb_ready": true}` once startup is complete, or `{"status": "warming", "gdb_ready": false}` while the GDB is still being downloaded or extracted.

### `GET /boundaries/{ISO}/{level}`

Returns a GeoJSON `FeatureCollection` of administrative boundaries.

| Parameter | Description |
|-----------|-------------|
| `ISO` | ISO 3166-1 alpha-3 country code (e.g. `NGA`) |
| `level` | Admin level 0–3 (UNOCHA does not provide levels 4–5) |

**Feature properties:**

| Property | Description |
|----------|-------------|
| `nodeid` | Zero-based integer index |
| `name` | Admin unit name (from `adm{level}_name` column) |
| `gid` | P-code (from `adm{level}_pcode` column) — consistent with OCHA COD-AB |

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | `level` outside 0–3 |
| 404 | No UNOCHA data for the requested ISO / level |
| 503 | GDB not yet ready — startup download/extraction still in progress |

## How it differs from the other shape services

| | unocha-service | gadm-service | geoboundaries-service |
|---|---|---|---|
| Source | UNOCHA HDX global GDB | GADM 4.1 | geoBoundaries v6.0.0 |
| License | CC-BY-IGO | Non-commercial | CC-BY |
| Levels | 0–3 | 0–5 | 0–3 (varies) |
| Cache unit | Single global GDB | Per-country zip | Per-(ISO, level) zip |
| Startup download | Yes (~1–2 GB at boot) | No (on-demand) | No (on-demand) |
| In-memory cache | Yes, per (ISO, level) | No | No |
| P-codes | Yes (COD-AB) | No (GADM GIDs) | Yes (shapeID) |
| Default in laser-generate | **Yes** | No | No |

UNOCHA boundaries use P-codes that align with other humanitarian datasets (population figures, health facility lists, incident reports), which is why they are the default.

## Startup behaviour

On first boot the service:
1. Downloads the global GDB zip from HDX (~1–2 GB, 5–15 minutes depending on connectivity).
2. Extracts the `.gdb` directory from the zip.
3. Sets `_gdb_ready = True` and begins accepting requests.

With a warm cache (zip already in `$CACHE_DIR`) extraction takes ~30 seconds. Kubernetes readiness probe on `/health` prevents traffic from reaching the pod until `gdb_ready` is `true`.

## In-memory layer cache

The first request for any `(ISO, level)` pair reads the relevant GDB layer, filters to the requested country, and stores the result in a process-level dictionary. All subsequent requests for that pair are served directly from memory with no disk I/O.

## Running locally

```bash
pip install -r requirements.txt

CACHE_DIR=~/.laser/cache/unocha uvicorn main:app --host 0.0.0.0 --port 8103
```

Wait for `UNOCHA GDB ready — accepting requests.` in the log before sending requests. Test:

```bash
curl http://localhost:8103/boundaries/NGA/1
```

## Docker

```bash
docker build -t laser-unocha-service .
docker run -p 8103:8000 -v unocha-cache:/cache laser-unocha-service
```

## AKS deployment

Deployed as part of `services/AKS/geodata-services.yaml`. Uses a 5 Gi PVC (`laser-unocha-cache`) for the GDB, and 2 CPU / 3 Gi memory limit. The `LoadBalancer` service exposes port 80.

```bash
kubectl apply -f services/AKS/geodata-services.yaml --kubeconfig services/AKS/kube.conf

# Watch startup progress (GDB download takes several minutes on a cold pod)
kubectl logs -f deployment/laser-unocha-svc -n laser-ai --kubeconfig services/AKS/kube.conf
```

## Known limitations

- **Startup latency**: A cold pod is unavailable for several minutes during the HDX download. Plan for this after initial deployment or after pod restarts.
- **Levels 0–3 only**: UNOCHA does not provide sub-district (level 4+) boundaries globally. Use `gadm-service` for finer administrative detail.
- **HDX URL stability**: The download URL is a direct link to a specific HDX resource ID. If UNOCHA publishes a new version, the URL in `main.py` must be updated.
- **Single replica**: The PVC is `ReadWriteOnce`; scaling requires a shared file store or an alternative caching strategy.
