#!/usr/bin/env bash
#
# Multi-country analysis: batch-generate models for several countries, run each,
# then summarize population across them.
#
# Learning objectives:
#   - Batch processing across countries
#   - Regional/comparative analysis
#   - Aggregating across generated GeoPackages
#
# Note: requires network access. Generating and running several countries is
# time-consuming; trim the `countries` list to try it quickly. The population
# summary at the end only needs the GeoPackages (it does not require the model
# runs).

set -euo pipefail

countries=(NGA GHA SEN CIV MLI)   # West Africa
level=2
start_year=2010
end_year=2015
outroot=west_africa

for country in "${countries[@]}"; do
    echo "=== Processing ${country} ==="
    # With --output-dir, output is written directly into the given directory.
    laser-init "$country" "$level" "$start_year" "$end_year" --output-dir "$outroot/$country"

    # Run the generated model for this country.
    ( cd "$outroot/$country" && python3 ./seir.py )
done

# Summarize total population per country from the generated GeoPackages.
echo
echo "=== Regional population summary ==="
python3 - "$outroot" "$level" <<'PY'
import sys
from pathlib import Path

import geopandas as gpd

outroot, level = Path(sys.argv[1]), sys.argv[2]
print(f"{'country':10} {'units':>6} {'population':>15}")
for country_dir in sorted(p for p in outroot.iterdir() if p.is_dir()):
    gpkg = next(country_dir.glob(f"*_admin{level}.gpkg"), None)
    if gpkg is None:
        continue
    gdf = gpd.read_file(gpkg)
    print(f"{country_dir.name:10} {len(gdf):6d} {gdf.population.sum():15,.0f}")
PY
