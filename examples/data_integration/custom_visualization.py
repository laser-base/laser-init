#!/usr/bin/env python3
"""Create a publication-quality population choropleth.

Demonstrates a styled choropleth with a logarithmic color scale, district edges,
and a high-DPI export — using only the project's existing dependencies
(geopandas, matplotlib). To overlay a web basemap, install the optional
``contextily`` package; see the note at the bottom of the file.

Learning objectives:
    - Publication-quality matplotlib figures from a GeoPackage
    - Log-scaled choropleths (and why the minimum must be positive)
    - High-DPI export

Requires ``laser-init`` on ``PATH`` and a network connection for the initial
download (the data is generated once into ./NGA/2010 and reused afterwards).
"""

import subprocess
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

COUNTRY = "NGA"
LEVEL = 2
START_YEAR = 2010
END_YEAR = 2015

BASE = Path(COUNTRY) / str(START_YEAR)
GPKG = BASE / f"{COUNTRY}_admin{LEVEL}.gpkg"


def main() -> None:
    if not GPKG.exists():
        subprocess.run(
            ["laser-init", COUNTRY, str(LEVEL), str(START_YEAR), str(END_YEAR)],
            check=True,
        )
    gdf = gpd.read_file(GPKG)

    # A log color scale needs a strictly positive minimum.
    positive = gdf.population[gdf.population > 0]
    vmin = max(1, int(positive.min()))
    vmax = int(gdf.population.max())

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(
        column="population",
        ax=ax,
        legend=True,
        cmap="YlOrRd",
        edgecolor="black",
        linewidth=0.4,
        norm=LogNorm(vmin=vmin, vmax=vmax),
        legend_kwds={"label": "Population (log scale)", "shrink": 0.6},
    )
    ax.set_title(
        f"{COUNTRY} population distribution ({START_YEAR})", fontsize=15, fontweight="bold"
    )
    ax.axis("off")
    plt.tight_layout()
    out = BASE / f"{COUNTRY}_population_publication.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"Saved {out}")

    # Optional: overlay a web basemap with contextily (`pip install contextily`):
    #
    #   import contextily as cx
    #   gdf_web = gdf.to_crs(epsg=3857)            # Web Mercator for tile basemaps
    #   ax = gdf_web.plot(column="population", alpha=0.7, ...)
    #   cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)


if __name__ == "__main__":
    main()
