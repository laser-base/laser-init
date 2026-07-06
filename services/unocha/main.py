"""
unocha-service — serves UNOCHA global admin boundary GeoJSON.

GET /health
GET /boundaries/{ISO}/{admin_level}  →  GeoJSON FeatureCollection

On startup, downloads the single ~1-2 GB global GDB zip from HDX (if not
already cached) and extracts it. All country/level requests are served by
reading the appropriate GDB layer, filtering by iso3, and caching the result
in memory so each (ISO, level) pair is only loaded from disk once.
"""

import logging
import os
import shutil
import tempfile
import warnings
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

import geopandas as gpd
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".laser" / "cache" / "unocha"))

_ZIP_NAME = "global_admin_boundaries_matched_latest.gdb.zip"
_GDB_NAME = "global_admin_boundaries_matched_latest.gdb"
_HDX_URL = (
    "https://data.humdata.org/dataset/70f1cb54-a30c-43b2-a751-44e77d8f5ade"
    "/resource/733a9d4c-4e70-4f67-a5af-4138922cf43f/download/"
    + _ZIP_NAME
)

# In-memory cache: (iso, level) → GeoDataFrame
_cache: dict[tuple[str, int], gpd.GeoDataFrame] = {}
_gdb_ready = False


def _zip_path() -> Path:
    return CACHE_DIR / _ZIP_NAME


def _gdb_path() -> Path:
    return CACHE_DIR / _GDB_NAME


def _download_zip() -> None:
    dest = _zip_path()
    if dest.exists():
        logger.info("Cache hit: %s", dest)
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading UNOCHA global GDB (~1-2 GB) — this takes a few minutes ...")
    tmp_fd, tmp_name = tempfile.mkstemp(dir=CACHE_DIR, suffix=".tmp")
    os.close(tmp_fd)
    tmp = Path(tmp_name)
    try:
        with httpx.stream("GET", _HDX_URL, follow_redirects=True, timeout=1800) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                downloaded = 0
                for chunk in r.iter_bytes(chunk_size=1_048_576):  # 1 MB chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (100 * 1_048_576) == 0:
                        logger.info("  ... %.0f MB downloaded", downloaded / 1e6)
        shutil.move(str(tmp), str(dest))
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    logger.info("Saved %s (%.0f MB)", dest, dest.stat().st_size / 1e6)


def _extract_gdb() -> None:
    gdb = _gdb_path()
    if gdb.exists():
        logger.info("GDB already extracted: %s", gdb)
        return
    logger.info("Extracting GDB from zip (may take a minute) ...")
    with zipfile.ZipFile(_zip_path(), "r") as zf:
        zf.extractall(CACHE_DIR)
    logger.info("Extraction complete: %s", gdb)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _gdb_ready
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _download_zip()
    _extract_gdb()
    _gdb_ready = True
    logger.info("UNOCHA GDB ready — accepting requests.")
    yield


def _read(iso: str, level: int) -> gpd.GeoDataFrame:
    key = (iso, level)
    if key in _cache:
        return _cache[key]

    layer = f"admin{level}"
    logger.info("Reading GDB layer %r for %s ...", layer, iso)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        full = gpd.read_file(_gdb_path(), layer=layer, engine="pyogrio")

    country = full[full["iso3"] == iso].copy()
    if country.empty:
        raise HTTPException(404, f"No UNOCHA data for ISO {iso!r} at admin level {level}")

    pcode_col = f"adm{level}_pcode"
    name_col = f"adm{level}_name"

    country["nodeid"] = range(len(country))
    country["name"] = country[name_col] if level < 4 else country["adm3_name"] + country["adm4_name"]
    country = country[["nodeid", "name", pcode_col, "geometry"]].rename(
        columns={pcode_col: "gid"}
    )
    _cache[key] = country
    logger.info("Cached %s / admin%d — %d features", iso, level, len(country))
    return country


app = FastAPI(title="unocha-service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok" if _gdb_ready else "warming", "gdb_ready": _gdb_ready}


@app.get("/boundaries/{iso}/{level}")
def boundaries(iso: str, level: int):
    if not _gdb_ready:
        raise HTTPException(503, "GDB not ready yet — startup download/extraction in progress")
    if not 0 <= level <= 3:
        raise HTTPException(400, f"UNOCHA supports admin levels 0–3, got {level}")
    gdf = _read(iso.upper(), level)
    return JSONResponse(content=gdf.to_crs("EPSG:4326").__geo_interface__)
