# unwpp-service

A microservice that serves demographic data from the [UN World Population Prospects 2024](https://population.un.org/wpp/) for use by `laser-generate`.

## Why it exists

LASER models require three demographic inputs per country: crude birth and death rates over time (CBR/CDR), the age distribution at the start of the simulation, and a life expectancy curve. The UN WPP is the authoritative global source for all three, but the raw dataset files are large (hundreds of MB each, gzip-compressed CSV). Loading and filtering them on the user's machine on every run is slow and requires a pandas/numpy environment. Running it once in a shared service means:

- The four WPP CSV files are downloaded once at startup and held entirely in memory.
- All subsequent requests are served from in-memory DataFrames — typical response time is under 100 ms.
- `laser-generate` fetches all three demographic tables with a single HTTP call.

## API

### `GET /health`

Returns `{"status": "ok", "loaded": ["age_dist", "indicators", "life_1950", "life_2024"]}` once startup is complete. The `loaded` list shows which datasets are in memory.

### `GET /demographics/{ISO}?start_year=YYYY&end_year=YYYY`

Returns CBR/CDR, age distribution, and life expectancy for the requested country and year range.

| Parameter | Description |
|-----------|-------------|
| `ISO` | ISO 3166-1 alpha-3 country code (e.g. `NGA`) |
| `start_year` | First year of simulation (1950–2100) |
| `end_year` | Last year of simulation (1950–2100) |

**Response:**

```json
{
  "iso": "NGA",
  "start_year": 2020,
  "end_year": 2020,
  "cxr": [
    { "year": 2020, "CBR": 37.2, "CDR": 10.4 }
  ],
  "age_dist": [
    { "age_start": 0,  "pop_total": 18234.5 },
    { "age_start": 5,  "pop_total": 16102.3 },
    ...
  ],
  "life_exp": [
    { "age": 0,  "cumulative_deaths": 4823.0 },
    { "age": 1,  "cumulative_deaths": 5201.0 },
    ...
  ]
}
```

- `cxr`: one row per year between `start_year` and `end_year`
- `age_dist`: 5-year age groups at `start_year` (from WPP medium variant)
- `life_exp`: 101 rows (ages 0–100), cumulative deaths per 100 000 births at `start_year`; uses the 1950–2023 life table for years ≤ 2023 and the 2024–2100 projection for later years

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | `start_year > end_year` |
| 404 | ISO code not found in WPP dataset |

## Data source

Four files downloaded at startup from the UN WPP 2024 CSV release:

| Internal key | File |
|---|---|
| `age_dist` | `WPP2024_Population1JanuaryByAge5GroupSex_Medium.csv.gz` |
| `indicators` | `WPP2024_Demographic_Indicators_Medium.csv.gz` |
| `life_1950` | `WPP2024_Life_Table_Complete_Medium_Both_1950-2023.csv.gz` |
| `life_2024` | `WPP2024_Life_Table_Complete_Medium_Both_2024-2100.csv.gz` |

## Startup behaviour

The service downloads and loads all four files before accepting requests. On a cold start with an empty cache this takes 2–5 minutes (download + CSV parse). With a warm cache (files already in `$CACHE_DIR`) it takes ~30 seconds for the in-memory load. The `/health` endpoint is available throughout startup but returns `"loaded": []` until all datasets are ready.

## Running locally

```bash
pip install -r requirements.txt

CACHE_DIR=~/.laser/cache/unwpp uvicorn main:app --host 0.0.0.0 --port 8100
```

Wait for the log line `Pre-warm complete — ready to serve.` before sending requests. Test:

```bash
curl "http://localhost:8100/demographics/NGA?start_year=2020&end_year=2020"
```

## Docker

```bash
docker build -t laser-unwpp-service .
docker run -p 8100:8000 -v unwpp-cache:/cache laser-unwpp-service
```

## AKS deployment

Deployed as part of `services/AKS/geodata-services.yaml`. Uses a 2 Gi PVC (`laser-unwpp-cache`) for the WPP CSV files, 2 CPU / 6 Gi memory limit (the four in-memory DataFrames total ~2–3 GB).

```bash
kubectl apply -f services/AKS/geodata-services.yaml --kubeconfig services/AKS/kube.conf
kubectl logs -f deployment/laser-unwpp-svc -n laser-ai --kubeconfig services/AKS/kube.conf
```

## Known limitations

- **Startup latency**: A cold-start pod is unavailable for several minutes. Kubernetes readiness probe on `/health` prevents traffic until all datasets are loaded.
- **Memory footprint**: ~2–3 GB resident — size the pod accordingly.
- **WPP 2024 only**: The 2022 and earlier WPP releases are not supported. Country coverage and historical estimates reflect WPP 2024 methodology.
