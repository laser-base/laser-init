#!/usr/bin/env bash
#
# 02 - Compare administrative-boundary sources for the same country.
#
# laser-init can pull boundaries from three sources. This generates the same
# country and level from each into its own directory so you can compare them.
#
# Learning objectives:
#   - Understand that the boundary source is configurable (--shape-source)
#   - See how the choice affects the boundaries and population aggregation
#   - Learn the trade-offs between sources (see ../../docs/datasources.md)
#
# Note: requires network access and downloads data for each source.

set -euo pipefail

country=MWI   # Malawi
level=2

# With --output-dir the output is written directly into the given directory
# (the GeoPackage is named <ISO>_admin<level>.gpkg).
laser-init "$country" "$level" 2015 2020 --shape-source unocha        --output-dir compare/unocha
laser-init "$country" "$level" 2015 2020 --shape-source geoboundaries --output-dir compare/geoboundaries
laser-init "$country" "$level" 2015 2020 --shape-source gadm          --output-dir compare/gadm

echo "Generated GeoPackages:"
ls -1 compare/*/"${country}_admin${level}.gpkg"
