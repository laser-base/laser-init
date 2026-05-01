"""
unwpp-service — serves filtered UN World Population Prospects demographic data.

GET /health
GET /demographics/{ISO}?start_year=YYYY&end_year=YYYY

On startup, downloads all four WPP dataset files to CACHE_DIR if not already
present (pre-warm), then loads them into memory. Requests are served entirely
from in-memory DataFrames.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".laser" / "cache" / "unwpp"))

_WPP_BASE = (
    "https://population.un.org/wpp/assets/Excel%20Files/"
    "1_Indicator%20(Standard)/CSV_FILES"
)

_FILES = {
    "age_dist":   "WPP2024_Population1JanuaryByAge5GroupSex_Medium.csv.gz",
    "indicators": "WPP2024_Demographic_Indicators_Medium.csv.gz",
    "life_1950":  "WPP2024_Life_Table_Complete_Medium_Both_1950-2023.csv.gz",
    "life_2024":  "WPP2024_Life_Table_Complete_Medium_Both_2024-2100.csv.gz",
}

_CSV_DTYPES = {"Notes": str, "ISO3_code": str, "ISO2_code": str, "LocTypeName": str}

# In-memory DataFrames populated at startup
_data: dict[str, pd.DataFrame] = {}


def _download(key: str) -> Path:
    filename = _FILES[key]
    dest = CACHE_DIR / filename
    if dest.exists():
        logger.info("Cache hit: %s", dest)
        return dest
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{_WPP_BASE}/{filename}"
    logger.info("Downloading %s ...", url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=65_536):
                f.write(chunk)
    logger.info("Saved %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
    return dest


def _load(key: str) -> pd.DataFrame:
    path = _download(key)
    logger.info("Loading %s ...", path.name)
    df = pd.read_csv(path, compression="gzip", dtype=_CSV_DTYPES)
    logger.info("Loaded %s — %d rows", path.name, len(df))
    return df


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Pre-warming: downloading and loading all WPP datasets ...")
    for key in _FILES:
        _data[key] = _load(key)
    logger.info("Pre-warm complete — ready to serve.")
    yield


app = FastAPI(title="unwpp-service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "loaded": list(_data.keys())}


@app.get("/demographics/{iso}")
def demographics(
    iso: str,
    start_year: int = Query(..., ge=1950, le=2100),
    end_year: int = Query(..., ge=1950, le=2100),
):
    if start_year > end_year:
        raise HTTPException(400, "start_year must be <= end_year")
    iso = iso.upper()

    # ── CBR / CDR ──────────────────────────────────────────────────────────────
    country_demo = _data["indicators"][_data["indicators"]["ISO3_code"] == iso]
    if country_demo.empty:
        raise HTTPException(404, f"ISO code not found: {iso!r}")

    cxr = (
        country_demo[country_demo["Time"].between(start_year, end_year)]
        .sort_values("Time")[["Time", "CBR", "CDR"]]
        .rename(columns={"Time": "year"})
        .to_dict(orient="records")
    )

    # ── Age distribution at start_year ─────────────────────────────────────────
    country_pop = _data["age_dist"][
        (_data["age_dist"]["ISO3_code"] == iso) & (_data["age_dist"]["Time"] == start_year)
    ]
    age_dist = (
        country_pop.sort_values("AgeGrpStart")[["AgeGrpStart", "PopTotal"]]
        .rename(columns={"AgeGrpStart": "age_start", "PopTotal": "pop_total"})
        .to_dict(orient="records")
    )

    # ── Life expectancy (cumulative deaths) at start_year ──────────────────────
    life_key = "life_1950" if start_year <= 2023 else "life_2024"
    country_life = _data[life_key][
        (_data[life_key]["ISO3_code"] == iso) & (_data[life_key]["Time"] == start_year)
    ].sort_values("AgeGrpStart").reset_index(drop=True)

    survival = country_life["lx"].to_numpy()
    cumulative = 100_000 - np.round(survival)
    cumulative = np.append(cumulative[1:], 100_000)
    life_exp = [
        {"age": int(age), "cumulative_deaths": float(cd)}
        for age, cd in zip(country_life["AgeGrpStart"].tolist(), cumulative)
    ]

    return {
        "iso": iso,
        "start_year": start_year,
        "end_year": end_year,
        "cxr": cxr,
        "age_dist": age_dist,
        "life_exp": life_exp,
    }
