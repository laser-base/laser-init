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
from fastapi.responses import JSONResponse, StreamingResponse
from shapely.geometry import mapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".laser" / "cache" / "worldpop"))
_YEAR_DEFAULT = 2020
_MAX_RASTER_MB = 2000  # on-demand size limit; larger rasters must use generate.py

# 512 MB GDAL block cache — default is 64 MB which is too small when reading many
# per-polygon windows from a large compressed GeoTIFF (constant cache thrash).
os.environ.setdefault("GDAL_CACHEMAX", "512")

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

        # Pre-flight: check file size before committing to a long download.
        # If Content-Length is unavailable, proceed and let the download run.
        try:
            head = httpx.head(url, follow_redirects=True, timeout=30)
            if head.status_code == 404:
                raise HTTPException(404, f"No WorldPop data for ISO {iso!r} year={year}")
            cl = head.headers.get("content-length")
            if cl:
                mb = int(cl) // (1024 * 1024)
                if mb > _MAX_RASTER_MB:
                    raise HTTPException(
                        422,
                        f"{iso} raster is {mb} MB — too large for on-demand download "
                        f"(limit {_MAX_RASTER_MB} MB). "
                        f"Pre-warm it first: POST /prewarm/{iso}?year={year} "
                        f"(runs in the background; may take 30+ min for large countries)."
                    )
                logger.info("Pre-flight: %s year=%d is %d MB — proceeding", iso, year, mb)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Pre-flight HEAD failed (%s) — proceeding with download", exc)

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


# Maximum pixels read from disk per strip in windowed mode. Each strip is one
# horizontal band of a polygon's bounding-box window. Keeping this at 8 M pixels
# caps per-strip peak memory at ~64 MB (float32 data + bool mask).
_MAX_STRIP_PIXELS = 8_000_000


def _sum_polygon_windowed(src, win, transform, geom, nodata) -> float:
    """Sum raster pixels inside geom using horizontal strips to bound memory.

    Used when the polygon's bounding-box window is too large to read at once
    (e.g. Amazonian states in BRA). Reads _MAX_STRIP_PIXELS pixels at a time.
    """
    height = int(win.height)
    width  = int(win.width)
    strip_rows = max(1, _MAX_STRIP_PIXELS // max(width, 1))
    total = 0.0
    for row_start in range(0, height, strip_rows):
        strip_h = min(strip_rows, height - row_start)
        strip_win = rasterio.windows.Window(
            int(win.col_off), int(win.row_off) + row_start, width, strip_h
        )
        strip_data = src.read(1, window=strip_win)
        strip_transform = rasterio.windows.transform(strip_win, transform)
        strip_mask = rasterio.features.geometry_mask(
            [mapping(geom)],
            out_shape=(strip_h, width),
            transform=strip_transform,
            invert=True,
        )
        vals = strip_data[strip_mask].astype(np.float64)
        if nodata is not None:
            vals = vals[vals != nodata]
        total += float(np.sum(vals))
    return total


def _aggregate_stream(iso: str, year: int, features: list, gdf):
    """Generator that yields a JSON object one key:value at a time.

    Streaming keeps data flowing to the client throughout computation so the
    Azure Load Balancer (4-min idle timeout) never sees a silent connection,
    even when aggregating large-country rasters like BRA or IDN.
    """
    raster_path = _raster_path(iso, year)
    _2GB = 2 * 1024 ** 3

    with rasterio.open(str(raster_path)) as src:
        nodata    = src.nodata
        transform = src.transform
        src_win   = rasterio.windows.Window(0, 0, src.width, src.height)
        uncompressed = src.width * src.height * 4  # float32 bytes

        if uncompressed < _2GB:
            data = src.read(1)
            logger.info("In-memory mode (%.0f MB uncompressed)", uncompressed / 1e6)
            ordered = list(zip(features, gdf.geometry))
        else:
            data = None
            logger.info("Windowed mode (%.0f MB uncompressed — too large for in-memory)",
                        uncompressed / 1e6)
            # Sort by raster row then column so consecutive polygons share GDAL
            # tile-cache entries — critical for level-2 queries with hundreds of
            # small polygons spread across a large compressed raster.
            def _scan_key(feat_geom):
                _, geom = feat_geom
                win = rasterio.windows.from_bounds(
                    *geom.bounds, transform=transform
                ).round_offsets()
                return (int(win.row_off), int(win.col_off))
            ordered = sorted(zip(features, gdf.geometry), key=_scan_key)
            logger.info("Sorted %d features by raster scan order", len(ordered))

        first = True
        for feat, geom in ordered:
            nodeid = int(feat["properties"]["nodeid"])
            try:
                win = rasterio.windows.from_bounds(
                    *geom.bounds, transform=transform
                ).round_lengths().round_offsets()
                win = win.intersection(src_win)

                height = int(win.height)
                width  = int(win.width)
                if height <= 0 or width <= 0:
                    pop = 0.0
                elif data is not None:
                    row_off = int(win.row_off)
                    col_off = int(win.col_off)
                    window_data = data[row_off:row_off + height, col_off:col_off + width]
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
                    pop = float(np.sum(vals))
                else:
                    # Windowed mode: read in strips to bound peak memory.
                    pop = _sum_polygon_windowed(src, win, transform, geom, nodata)
            except Exception:
                logger.exception("Error aggregating nodeid=%d for %s", nodeid, iso)
                pop = 0.0

            prefix = b"{" if first else b","
            first = False
            yield prefix + f'"{nodeid}":{pop}'.encode()

    yield b"}" if not first else b"{}"
    logger.info("Aggregated %d features for %s/%d", len(features), iso, year)


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

    _download_raster(iso.upper(), year)

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    logger.info("Aggregating %s/%d over %d features ...", iso.upper(), year, len(gdf))

    return StreamingResponse(
        _aggregate_stream(iso.upper(), year, features, gdf),
        media_type="application/json",
    )
