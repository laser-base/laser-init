"""
generate.py — service-based equivalent of the laser-init Extract + Transform phases.

Calls the geodata microservices to produce the same data files as `laser-init`,
without downloading anything directly. The Load phase (config.yaml, model scripts,
validation plots) can then be run by passing the output directory to the existing
laser-init CLI once it supports a --data-dir option, or by running the loader
directly.

Produces (equivalent to laser-init output):
    {ISO}_admin{level}.gpkg   — GeoPackage (nodeid, name, population, geometry)
    cxr.csv                   — Crude birth/death rates (Time, CBR, CDR)
    age_dist.csv              — Age distribution (AgeGrpStart, PopTotal)
    life_exp.csv              — Life expectancy curve (cumulative_deaths)
    config.yaml               — Model configuration (default parameters)
    provenance.json           — Data sources and timestamps

Usage:
    python generate.py ETH 2 2010 2020 --shape-source gadm
    python generate.py NGA 1 2015 2025 --shape-source unocha --output-dir NGA/2015

Service URLs (in precedence order):
    1. --shapes-url / --worldpop-url / --unwpp-url CLI flags
    2. laser_config.yaml keys: gadm_url, geoboundaries_url, unocha_url, worldpop_url, unwpp_url
    3. localhost fallbacks (8101/8102/8103/8104/8100)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import httpx
import pandas as pd
import yaml
from shapely.geometry import shape

from laser.init.config import configuration as _cfg

# Localhost fallbacks (used only when neither laser_config.yaml nor --*-url flags supply a URL).
_SHAPE_SOURCE_LOCALHOST = {
    "gadm":          "http://127.0.0.1:8101",
    "geoboundaries": "http://127.0.0.1:8102",
    "unocha":        "http://127.0.0.1:8103",
}

# Config-file keys for each shape source.
_SHAPE_SOURCE_CFG_KEY = {
    "gadm":          "gadm_url",
    "geoboundaries": "geoboundaries_url",
    "unocha":        "unocha_url",
}


def _default_shapes_url(source: str) -> str:
    return _cfg.get(_SHAPE_SOURCE_CFG_KEY[source], _SHAPE_SOURCE_LOCALHOST[source])


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _get(url: str, timeout: float = 60) -> dict:
    r = httpx.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _post(url: str, body: dict, timeout: float = 1800) -> dict:
    r = httpx.post(url, json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ── Service calls ──────────────────────────────────────────────────────────────

def fetch_shapes(shapes_url: str, iso: str, level: int) -> dict:
    url = f"{shapes_url}/boundaries/{iso}/{level}"
    print(f"  shapes  ← {url}")
    fc = _get(url)
    print(f"           {len(fc['features'])} features")
    return fc


def _truncate_coords(coords, dp: int):
    """Recursively round GeoJSON coordinates to `dp` decimal places.

    3 dp ≈ 100 m at the equator; WorldPop rasters are ~1 km resolution, so
    this loses nothing meaningful but cuts payload size 5–10× for detailed
    borders (e.g. BRA/1 dropped from ~38 MB to a few MB). Matches the
    behaviour of services/worldpop/client.html.
    """
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return [round(v, dp) for v in coords]
    return [_truncate_coords(c, dp) for c in coords]


def fetch_population(wp_url: str, iso: str, year: int, fc: dict) -> dict:
    url = f"{wp_url}/aggregate/{iso}?year={year}"
    print(f"  worldpop← {url}  (first run downloads raster — may take minutes)")
    # Truncate coordinates before POSTing (see _truncate_coords).
    slim_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                **f,
                "geometry": {
                    **f["geometry"],
                    "coordinates": _truncate_coords(f["geometry"]["coordinates"], 3),
                },
            }
            for f in fc["features"]
        ],
    }
    # The Azure LB has a 4-min idle timeout; a slow raster download causes a
    # connection reset mid-request. Retry: the download continues server-side
    # and subsequent calls hit the cache quickly.
    for attempt in range(1, 11):
        try:
            pop = _post(url, slim_fc)
            break
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError):
            if attempt == 10:
                raise
            wait = 60
            print(f"  worldpop  connection reset (raster download in progress) "
                  f"— retry {attempt}/10 in {wait}s ...")
            time.sleep(wait)
    total = sum(pop.values())
    print(f"           {len(pop)} features, total pop {total:,.0f}")
    return pop


def fetch_demographics(unwpp_url: str, iso: str, start_year: int, end_year: int) -> dict:
    url = f"{unwpp_url}/demographics/{iso}?start_year={start_year}&end_year={end_year}"
    print(f"  unwpp   ← {url}")
    demo = _get(url)
    print(f"           {len(demo['cxr'])} years CBR/CDR, "
          f"{len(demo['age_dist'])} age groups, "
          f"{len(demo['life_exp'])} life-exp rows")
    return demo


# ── Build outputs ──────────────────────────────────────────────────────────────

def build_gdf(fc: dict, pop: dict) -> gpd.GeoDataFrame:
    rows = []
    for f in fc["features"]:
        p = f["properties"]
        nodeid = int(p["nodeid"])
        rows.append({
            "nodeid":     nodeid,
            "name":       p.get("name", ""),
            "population": round(float(pop.get(str(nodeid), 0.0))),
            "geometry":   shape(f["geometry"]),
        })
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    return gdf.sort_values("nodeid").reset_index(drop=True)


def write_gpkg(gdf: gpd.GeoDataFrame, output_dir: Path, iso: str, level: int) -> Path:
    dest = output_dir / f"{iso}_admin{level}.gpkg"
    gdf.to_file(dest, driver="GPKG")
    print(f"  → {dest.name}  ({len(gdf)} features, total pop {gdf.population.sum():,.0f})")
    return dest


def write_cxr(demo: dict, output_dir: Path) -> Path:
    dest = output_dir / "cxr.csv"
    pd.DataFrame(
        [{"Time": r["year"], "CBR": r["CBR"], "CDR": r["CDR"]} for r in demo["cxr"]]
    ).to_csv(dest, index=False)
    print(f"  → {dest.name}  ({len(demo['cxr'])} rows)")
    return dest


def write_age_dist(demo: dict, output_dir: Path) -> Path:
    dest = output_dir / "age_dist.csv"
    pd.DataFrame(
        [{"AgeGrpStart": r["age_start"], "PopTotal": r["pop_total"]} for r in demo["age_dist"]]
    ).to_csv(dest, index=False)
    print(f"  → {dest.name}  ({len(demo['age_dist'])} rows)")
    return dest


def write_life_exp(demo: dict, output_dir: Path) -> Path:
    dest = output_dir / "life_exp.csv"
    pd.DataFrame(
        [{"cumulative_deaths": r["cumulative_deaths"]} for r in demo["life_exp"]]
    ).to_csv(dest, index=False)
    print(f"  → {dest.name}  ({len(demo['life_exp'])} rows)")
    return dest


def write_config(output_dir: Path, iso: str, level: int) -> Path:
    """Write a standalone config.yaml (used when --emit-scripts is not set)."""
    dest = output_dir / "config.yaml"
    # Key names match what AbmLoader and the model scripts expect (underscores).
    cfg = {
        "data_dir": str(output_dir.resolve()),
        "datafiles": {
            "shape_data": f"{iso}_admin{level}.gpkg",
            "cxr_data":   "cxr.csv",
            "pop_data":   "age_dist.csv",
            "exp_data":   "life_exp.csv",
        },
        "simulation": {
            "nyears":                   10,
            "r0":                       2.5,
            "exposed_duration_shape":   4.5,
            "exposed_duration_scale":   1.0,
            "infectious_duration_mean": 7.0,
            "naive_population":         True,
            "gravity_k":                500,
            "gravity_a":                1,
            "gravity_b":                1,
            "gravity_c":                2,
        },
    }
    with dest.open("w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"  → {dest.name}")
    return dest


def _emit_scripts(
    output_dir: Path,
    iso: str,
    level: int,
    gpkg: Path,
    cxr: Path,
    age_dist: Path,
    life_exp: Path,
    model: str,
) -> None:
    """Call the laser-init Load phase to emit model scripts and validation plots."""
    from laser.init.cli import write_plots
    from laser.init.loaders.abm import AbmLoader

    print("\nEmitting model scripts via laser-init Load phase ...")
    AbmLoader().emit_script(
        mode="ABM",
        model=model,
        shape_filename=gpkg,
        cxr_filename=cxr,
        pop_filename=age_dist,
        exp_filename=life_exp,
        output_dir=output_dir,
    )
    print(f"  → config.yaml, {model.lower()}.py, plot.py")

    print("Writing validation plots ...")
    write_plots(gpkg, cxr, age_dist, life_exp, output_dir)
    print("  → choropleth.png, cbr_cdr.png, age_distribution.png, life_expectancy.png, report.pdf")


def write_provenance(
    output_dir: Path, iso: str, level: int,
    shapes_url: str, wp_url: str, unwpp_url: str,
    shape_source: str, raster_year: int,
) -> Path:
    dest = output_dir / "provenance.json"
    ts = datetime.now(timezone.utc).isoformat()
    prov = {
        f"{iso}_admin{level}.gpkg": {
            "shape_source":    shape_source,
            "shapes_service":  shapes_url,
            "worldpop_service": wp_url,
            "worldpop_year":   raster_year,
            "timestamp":       ts,
        },
        "cxr.csv":      {"unwpp_service": unwpp_url, "timestamp": ts},
        "age_dist.csv": {"unwpp_service": unwpp_url, "timestamp": ts},
        "life_exp.csv": {"unwpp_service": unwpp_url, "timestamp": ts},
    }
    dest.write_text(json.dumps(prov, indent=2))
    print(f"  → {dest.name}")
    return dest


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate laser-init data files via geodata microservices.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("country",    help="ISO-3 country code (e.g. ETH)")
    parser.add_argument("level",      type=int, help="Admin level (0–3)")
    parser.add_argument("start_year", type=int, help="Start year (e.g. 2010)")
    parser.add_argument("end_year",   type=int, help="End year (e.g. 2020)")
    parser.add_argument("--shape-source",
                        choices=["gadm", "geoboundaries", "unocha"], default="unocha",
                        help="Boundary data source (default: unocha)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory (default: ./{ISO}/{start_year})")
    parser.add_argument("--shapes-url", default=None,
                        help="Shape service base URL (auto-selected from --shape-source; "
                             "falls back to laser_config.yaml then localhost)")
    parser.add_argument("--worldpop-url",
                        default=_cfg.get("worldpop_url", "http://127.0.0.1:8104"))
    parser.add_argument("--unwpp-url",
                        default=_cfg.get("unwpp_url", "http://127.0.0.1:8100"))
    parser.add_argument("--raster-year",  type=int, default=None,
                        help="WorldPop raster year (default: start_year clamped to 2020)")
    parser.add_argument("--model", choices=["SI", "SIR", "SEIR"], default="SEIR",
                        help="Model type for emitted script (default: SEIR)")
    parser.add_argument("--emit-scripts", action="store_true",
                        help="Also emit model scripts and validation plots via laser-init "
                             "Load phase (requires laser-init to be installed)")
    args = parser.parse_args()

    iso         = args.country.upper()
    level       = args.level
    start_year  = args.start_year
    end_year    = args.end_year
    shape_src   = args.shape_source
    raster_year = args.raster_year or min(start_year, 2020)
    output_dir  = args.output_dir or (Path(iso) / str(start_year))

    shapes_url  = (args.shapes_url or _default_shapes_url(shape_src)).rstrip("/")
    wp_url      = args.worldpop_url.rstrip("/")
    unwpp_url   = args.unwpp_url.rstrip("/")

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nlaser-init (services) — {iso} admin{level} {start_year}–{end_year}"
          f"  shape-source={shape_src}")
    print()

    try:
        fc   = fetch_shapes(shapes_url, iso, level)
        pop  = fetch_population(wp_url, iso, raster_year, fc)
        demo = fetch_demographics(unwpp_url, iso, start_year, end_year)
    except httpx.HTTPStatusError as exc:
        print(f"\nHTTP {exc.response.status_code} from {exc.request.url}")
        print(exc.response.text[:300])
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}")
        sys.exit(1)

    print()
    gdf      = build_gdf(fc, pop)
    gpkg     = write_gpkg(gdf, output_dir, iso, level)
    cxr      = write_cxr(demo, output_dir)
    age_dist = write_age_dist(demo, output_dir)
    life_exp = write_life_exp(demo, output_dir)
    write_provenance(output_dir, iso, level,
                     shapes_url, wp_url, unwpp_url, shape_src, raster_year)

    if args.emit_scripts:
        _emit_scripts(output_dir, iso, level, gpkg, cxr, age_dist, life_exp, args.model)
    else:
        write_config(output_dir, iso, level)
        print(f"\nDone — {output_dir}/")
        print(f"Run with --emit-scripts to also generate {args.model.lower()}.py, "
              f"plot.py, config.yaml, and validation plots.")
        return

    print(f"\nDone — {output_dir}/")
    print(f"To run the model:\n  cd {output_dir} && python {args.model.lower()}.py")


if __name__ == "__main__":
    main()
