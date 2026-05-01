"""
geoboundaries-service — serves geoBoundaries v6.0.0 admin boundary GeoJSON.

GET /health
GET /boundaries/{ISO}/{admin_level}  →  GeoJSON FeatureCollection

Each (ISO, level) combination is a separate zip on GitHub. Downloads on first
request and caches. Same endpoint contract as gadm-service.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".laser" / "cache" / "geoboundaries"))

_GB_BASE = "https://github.com/wmgeolab/geoBoundaries/raw/refs/tags/v6.0.0/releaseData/gbOpen"


def _zip_path(iso: str, level: int) -> Path:
    return CACHE_DIR / iso / f"ADM{level}" / f"geoBoundaries-{iso}-ADM{level}-all.zip"


def _download(iso: str, level: int) -> Path:
    dest = _zip_path(iso, level)
    if dest.exists():
        logger.info("Cache hit: %s", dest)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{_GB_BASE}/{iso}/ADM{level}/geoBoundaries-{iso}-ADM{level}-all.zip"
    logger.info("Downloading %s ...", url)

    tmp = Path(tempfile.mktemp(dir=dest.parent, suffix=".tmp"))
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
            if r.status_code == 404:
                raise HTTPException(404, f"geoBoundaries has no data for {iso!r} ADM{level}")
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(chunk_size=65_536):
                    f.write(chunk)
        shutil.move(str(tmp), str(dest))
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    logger.info("Saved %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
    return dest


def _read(iso: str, level: int) -> gpd.GeoDataFrame:
    zip_path = _download(iso, level)
    shp_name = f"geoBoundaries-{iso}-ADM{level}.shp"
    logger.info("Reading %s ...", shp_name)

    try:
        gdf = gpd.read_file(f"zip://{zip_path}!{shp_name}", engine="pyogrio")
    except Exception as exc:
        raise HTTPException(404, f"Could not read {shp_name} from zip: {exc}") from exc

    gdf["nodeid"] = range(len(gdf))
    gdf["name"] = gdf["shapeName"]
    return gdf[["nodeid", "name", "shapeID", "geometry"]].rename(columns={"shapeID": "gid"})


app = FastAPI(title="geoboundaries-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/boundaries/{iso}/{level}")
def boundaries(iso: str, level: int):
    if not 0 <= level <= 5:
        raise HTTPException(400, f"admin_level must be 0–5, got {level}")
    gdf = _read(iso.upper(), level)
    return JSONResponse(content=gdf.to_crs("EPSG:4326").__geo_interface__)
