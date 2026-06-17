#!/usr/bin/env python3
"""Prepare a laser-init GeoPackage for use in QGIS.

A GeoPackage opens directly in QGIS, so "exporting" is mostly about enriching it
with analysis-ready attributes. This example adds area, density, and population
rank columns, writes a new GeoPackage, and prints loading instructions.

Learning objectives:
    - Enrich a GeoPackage with derived attributes
    - Write a new GeoPackage layer with GeoPandas
    - Use laser-init output in a desktop GIS

Areas use an equal-area projection (EPSG:6933) because the source data is in
EPSG:4326 (degrees). Requires ``laser-init`` on ``PATH`` and a network
connection for the initial download (data is generated into ./NGA/2010).
"""

import subprocess
from pathlib import Path

import geopandas as gpd

COUNTRY = "NGA"
LEVEL = 2
START_YEAR = 2010
END_YEAR = 2015
EQUAL_AREA_EPSG = 6933  # World Cylindrical Equal Area (meters)

BASE = Path(COUNTRY) / str(START_YEAR)
GPKG = BASE / f"{COUNTRY}_admin{LEVEL}.gpkg"


def main() -> None:
    if not GPKG.exists():
        subprocess.run(
            ["laser-init", COUNTRY, str(LEVEL), str(START_YEAR), str(END_YEAR)],
            check=True,
        )
    gdf = gpd.read_file(GPKG)

    gdf["area_km2"] = (gdf.to_crs(EQUAL_AREA_EPSG).geometry.area / 1e6).round(2)
    gdf["density"] = (gdf.population / gdf["area_km2"]).round(2)
    gdf["pop_rank"] = gdf.population.rank(ascending=False, method="min").astype(int)

    layer = f"{COUNTRY}_admin{LEVEL}"
    out = BASE / f"{COUNTRY}_admin{LEVEL}_qgis.gpkg"
    gdf.to_file(out, layer=layer, driver="GPKG")

    print(f"Wrote {out} (layer '{layer}')")
    print(f"Columns: {list(gdf.columns)}")
    print(
        "\nLoad in QGIS:\n"
        "  1. Layer > Add Layer > Add Vector Layer...\n"
        f"  2. Select {out}\n"
        "  3. Symbology > Graduated, colour by 'population', 'density', or 'pop_rank'.\n"
        "  (A GeoPackage can also be dragged directly onto the QGIS map canvas.)"
    )


if __name__ == "__main__":
    main()
