"""
gadm-service — serves GADM 4.1 admin boundary GeoJSON.

GET /health
GET /boundaries/{ISO}/{admin_level}  →  GeoJSON FeatureCollection

Downloads gadm41_{ISO}_shp.zip on first request for a country, caches it.
All admin levels for that country are then served from the single cached zip.
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

CACHE_DIR = Path(os.environ.get("CACHE_DIR", Path.home() / ".laser" / "cache" / "gadm"))

_GADM_BASE = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp"


def _zip_path(iso: str) -> Path:
    return CACHE_DIR / iso / f"gadm41_{iso}_shp.zip"


def _download(iso: str) -> Path:
    dest = _zip_path(iso)
    if dest.exists():
        logger.info("Cache hit: %s", dest)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{_GADM_BASE}/gadm41_{iso}_shp.zip"
    logger.info("Downloading %s ...", url)

    # Write to a temp file first — avoids a partial file being treated as cached
    tmp_fd, tmp_name = tempfile.mkstemp(dir=dest.parent, suffix=".tmp")
    os.close(tmp_fd)
    tmp = Path(tmp_name)
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
            if r.status_code == 404:
                raise HTTPException(404, f"GADM has no data for ISO {iso!r}")
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
    zip_path = _download(iso)
    layer = f"gadm41_{iso}_{level}"
    logger.info("Reading %s from %s ...", layer, zip_path.name)

    try:
        gdf = gpd.read_file(f"zip://{zip_path}!{layer}.shp", engine="pyogrio")
    except Exception as exc:
        raise HTTPException(404, f"Admin level {level} not available for {iso}: {exc}") from exc

    gdf["nodeid"] = range(len(gdf))

    if level == 0:
        gdf["name"] = gdf["GID_0"]
    elif level <= 3:
        gdf["name"] = gdf[f"NAME_{level}"]
    else:
        gdf["name"] = gdf["NAME_3"].astype(str) + ":" + gdf["NAME_4"].astype(str)

    gid_col = f"GID_{level}"
    gdf = gdf[["nodeid", "name", gid_col, "geometry"]].rename(columns={gid_col: "gid"})

    # Simplify to ~100 m (0.001°). Matches WorldPop raster resolution, removes
    # the coordinate bloat that OOMkills the pod on large level-2+ countries.
    if level >= 1:
        gdf.geometry = gdf.geometry.simplify(0.001, preserve_topology=True)

    return gdf


app = FastAPI(title="gadm-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/boundaries/{iso}/{level}")
def boundaries(iso: str, level: int):
    if not 0 <= level <= 5:
        raise HTTPException(400, f"admin_level must be 0–5, got {level}")
    gdf = _read(iso.upper(), level)
    # to_crs ensures WGS-84; set_crs first if the shapefile has no CRS metadata.
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return JSONResponse(content=gdf.to_crs("EPSG:4326").__geo_interface__)
