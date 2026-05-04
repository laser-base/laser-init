"""
worldpop-service — aggregates WorldPop population raster into polygon areas.

GET  /health
POST /prewarm/{iso}?year=2020   → {"status": "ok", "iso": "...", "year": ...}
POST /aggregate/{iso}?year=2020 → {nodeid: population, ...}
     body: GeoJSON FeatureCollection; each feature must have "nodeid" in properties

Rasters are downloaded on demand and cached on disk. The WorldPop UN-adjusted
dataset (Global_2000_2020) is used. Per-(iso,year) locks prevent duplicate
concurrent downloads.
"""

import logging
import os
import shutil
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import geopandas as gpd
import httpx
import rasterio
import rasterio.features
import rasterio.mask
import rasterio.windows
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shapely.geometry import mapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".laser" / "cache" / "worldpop"))
_YEAR_DEFAULT = 2020

# Per-(iso, year) lock prevents duplicate concurrent downloads of the same raster.
_lock_registry_mu: threading.Lock = threading.Lock()
_download_locks: dict[tuple[str, int], threading.Lock] = {}


def _raster_path(iso: str, year: int) -> Path:
    return CACHE_DIR / f"{iso.lower()}_ppp_{year}_UNadj.tif"


def _worldpop_url(iso: str, year: int) -> str:
    return (
        f"https://data.worldpop.org/GIS/Population/"
        f"Global_2000_2020/{year}/{iso.upper()}/"
        f"{iso.lower()}_ppp_{year}_UNadj.tif"
    )


def _download_raster(iso: str, year: int) -> Path:
    dest = _raster_path(iso, year)
    if dest.exists():
        logger.info("Cache hit: %s", dest)
        return dest

    # Acquire a per-(iso, year) lock so concurrent requests wait rather than
    # each downloading the same raster simultaneously.
    key = (iso, year)
    with _lock_registry_mu:
        if key not in _download_locks:
            _download_locks[key] = threading.Lock()
    lock = _download_locks[key]

    with lock:
        if dest.exists():  # another thread finished while we waited
            logger.info("Cache hit (post-lock): %s", dest)
            return dest

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = _worldpop_url(iso, year)
        logger.info("Downloading WorldPop raster for %s year=%d ...", iso, year)
        tmp = Path(tempfile.mktemp(dir=CACHE_DIR, suffix=".tmp"))
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
                if r.status_code == 404:
                    raise HTTPException(404, f"No WorldPop data for ISO {iso!r} year={year}")
                r.raise_for_status()
                with tmp.open("wb") as f:
                    downloaded = 0
                    for chunk in r.iter_bytes(chunk_size=1_048_576):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % (50 * 1_048_576) == 0:
                            logger.info("  ... %.0f MB downloaded", downloaded / 1e6)
            shutil.move(str(tmp), str(dest))
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        logger.info("Saved %s (%.0f MB)", dest, dest.stat().st_size / 1e6)
    return dest


@asynccontextmanager
async def lifespan(app: FastAPI):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("worldpop-service ready — rasters downloaded on demand via /prewarm or /aggregate.")
    yield


app = FastAPI(title="worldpop-service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/prewarm/{iso}")
def prewarm(
    iso: str,
    year: int = Query(_YEAR_DEFAULT, ge=2000, le=2020),
):
    _download_raster(iso.upper(), year)
    return {"status": "ok", "iso": iso.upper(), "year": year}


@app.post("/aggregate/{iso}")
def aggregate(
    iso: str,
    year: int = Query(_YEAR_DEFAULT, ge=2000, le=2020),
    body: dict = Body(...),
):
    if body.get("type") != "FeatureCollection":
        raise HTTPException(400, "Body must be a GeoJSON FeatureCollection")
    features = body.get("features", [])
    if not features:
        raise HTTPException(400, "FeatureCollection has no features")

    raster_path = _download_raster(iso.upper(), year)

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    logger.info("Aggregating %s/%d over %d features ...", iso.upper(), year, len(gdf))

    # For countries whose raster fits in memory (< 2 GB uncompressed float32),
    # read the whole array once and slice per polygon — fast, one disk read.
    # For very large countries (CAN ~21 GB, RUS, AUS, …) read only each
    # polygon's bounding-box window from disk to avoid OOM.
    _2GB = 2 * 1024 ** 3

    result = {}
    with rasterio.open(str(raster_path)) as src:
        nodata    = src.nodata
        transform = src.transform
        src_win   = rasterio.windows.Window(0, 0, src.width, src.height)
        uncompressed = src.width * src.height * 4  # float32 bytes

        if uncompressed < _2GB:
            data = src.read(1)  # float32 — read entire raster once
            logger.info("In-memory mode (%.0f MB uncompressed)", uncompressed / 1e6)
        else:
            data = None
            logger.info("Windowed mode (%.0f MB uncompressed — too large for in-memory)",
                        uncompressed / 1e6)

        for feat, geom in zip(features, gdf.geometry):
            nodeid = int(feat["properties"]["nodeid"])
            try:
                win = rasterio.windows.from_bounds(
                    *geom.bounds, transform=transform
                ).round_lengths().round_offsets()
                win = win.intersection(src_win)

                height = int(win.height)
                width  = int(win.width)
                if height <= 0 or width <= 0:
                    result[nodeid] = 0.0
                    continue

                if data is not None:
                    row_off = int(win.row_off)
                    col_off = int(win.col_off)
                    window_data = data[row_off:row_off + height, col_off:col_off + width]
                else:
                    window_data = src.read(1, window=win)

                window_transform = rasterio.windows.transform(win, transform)
                geom_mask = rasterio.features.geometry_mask(
                    [mapping(geom)],
                    out_shape=(height, width),
                    transform=window_transform,
                    invert=True,
                )

                vals = window_data[geom_mask].astype(np.float64)
                if nodata is not None:
                    vals = vals[vals != nodata]
                result[nodeid] = float(np.sum(vals))
            except Exception:
                result[nodeid] = 0.0

    logger.info("Aggregated %d features for %s/%d", len(result), iso.upper(), year)
    return JSONResponse(content=result)
