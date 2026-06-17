#!/usr/bin/env python3
"""Analyze a laser-init GeoPackage: summary statistics, density, and maps.

Loads the GeoPackage produced by laser-init and computes population statistics
and density, then saves a three-panel map of population, density, and area.

Learning objectives:
    - Load and inspect a laser-init GeoPackage with GeoPandas
    - Compute spatial statistics correctly
    - Produce quick multi-panel choropleths

Important: the GeoPackage is in EPSG:4326 (longitude/latitude degrees), where a
raw ``.area`` is in square degrees and is *not* meaningful in km². Areas here are
computed after reprojecting to an equal-area CRS (EPSG:6933).

Requires ``laser-init`` on ``PATH`` and a network connection for the initial
download (the data is generated once into ./NGA/2010 and reused afterwards).
"""

import subprocess
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

COUNTRY = "NGA"
LEVEL = 2
START_YEAR = 2010
END_YEAR = 2015
EQUAL_AREA_EPSG = 6933  # World Cylindrical Equal Area (meters)

BASE = Path(COUNTRY) / str(START_YEAR)
GPKG = BASE / f"{COUNTRY}_admin{LEVEL}.gpkg"


def ensure_data() -> None:
    """Generate the GeoPackage with laser-init if it does not already exist."""
    if not GPKG.exists():
        subprocess.run(
            ["laser-init", COUNTRY, str(LEVEL), str(START_YEAR), str(END_YEAR)],
            check=True,
        )


def main() -> None:
    ensure_data()
    gdf = gpd.read_file(GPKG)

    # Area in km² via an equal-area projection (the data is EPSG:4326 / degrees).
    gdf["area_km2"] = gdf.to_crs(EQUAL_AREA_EPSG).geometry.area / 1e6
    gdf["density"] = gdf.population / gdf.area_km2

    print(f"Administrative units: {len(gdf)}")
    print(f"Total population:     {gdf.population.sum():,.0f}")
    print(f"Total area:           {gdf.area_km2.sum():,.0f} km^2")
    print(f"Mean density:         {gdf.population.sum() / gdf.area_km2.sum():,.1f} per km^2")
    print("\nMost populous units:")
    print(gdf.nlargest(5, "population")[["name", "population"]].to_string(index=False))
    print("\nLeast populous units:")
    print(gdf.nsmallest(5, "population")[["name", "population"]].to_string(index=False))

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, column, cmap, title in [
        (axes[0], "population", "YlOrRd", "Population"),
        (axes[1], "density", "plasma", "Density (per km^2)"),
        (axes[2], "area_km2", "viridis", "Area (km^2)"),
    ]:
        gdf.plot(column=column, ax=ax, legend=True, cmap=cmap)
        ax.set_title(title)
        ax.axis("off")
    plt.tight_layout()
    out = BASE / "geopackage_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
