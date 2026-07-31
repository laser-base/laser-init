#!/usr/bin/env python3
"""Compare district population across snapshot years for one country.

Generates the same country and administrative level for several start years (the
population for each snapshot comes from that year's WorldPop raster), then
compares per-district and national population across the years from the generated
GeoPackages.

Learning objectives:
    - Temporal analysis across multiple laser-init runs
    - Population growth patterns
    - Driving laser-init from Python via subprocess

Note: requires ``laser-init`` on ``PATH`` and a network connection for the first
run. This example only needs the extraction/transform output (the GeoPackages);
it does not run the epidemiological model.
"""

import subprocess
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

COUNTRY = "PAK"
LEVEL = 2
YEARS = [2000, 2010, 2020]
OUTROOT = Path("timeseries")


def generate() -> None:
    """Generate a snapshot for each year (skipping any that already exist)."""
    for year in YEARS:
        outdir = OUTROOT / str(year)
        gpkg = outdir / f"{COUNTRY}_admin{LEVEL}.gpkg"
        if gpkg.exists():
            continue
        subprocess.run(
            [
                "laser-init",
                COUNTRY,
                str(LEVEL),
                str(year),
                str(year + 1),
                "--output-dir",
                str(outdir),
            ],
            check=True,
        )


def main() -> None:
    generate()

    # Population per district (keyed by admin-unit name) for each year.
    pop_by_year = {}
    for year in YEARS:
        gdf = gpd.read_file(OUTROOT / str(year) / f"{COUNTRY}_admin{LEVEL}.gpkg")
        pop_by_year[year] = gdf.groupby("name")["population"].sum()

    pop = pd.DataFrame(pop_by_year)

    totals = pop.sum()
    print("National population by year:")
    print(totals.map(lambda v: f"{v:,.0f}").to_string())
    if len(YEARS) >= 2:
        growth = (totals.iloc[-1] / totals.iloc[0] - 1) * 100
        print(f"\nTotal growth {YEARS[0]}-{YEARS[-1]}: {growth:.1f}%")

    # Distribution of per-district population by year.
    ax = pop.plot(kind="box", logy=True, title=f"{COUNTRY} district population by year")
    ax.set_ylabel("Population (log scale)")
    plt.tight_layout()
    out_png = OUTROOT / "population_by_year.png"
    plt.savefig(out_png, dpi=150)
    print(f"\nSaved {out_png}")


if __name__ == "__main__":
    main()
