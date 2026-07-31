#!/usr/bin/env bash
#
# 01 - Quick start: the simplest laser-init workflow.
#
# Downloads administrative boundaries, population, and demographic data for
# Nigeria (NGA) at admin level 2 for 2010-2020, generates a SEIR model in
# ./NGA/2010, and runs it.
#
# Learning objectives:
#   - Understand the basic command syntax
#   - See what files laser-init generates
#   - Run a generated simulation
#
# Note: requires a network connection; the first run downloads several data
# files into the cache (see ../../docs/configuration.md for the cache location).

set -euo pipefail

# Generate the model. With no --output-dir, output goes to ./<ISO>/<start-year>,
# i.e. ./NGA/2010.
laser-init NGA 2 2010 2020

# Inspect the generated files, then run the model.
cd NGA/2010
ls -1   # NGA_admin2.gpkg, config.yaml, seir.py, plot.py, *.csv, report.pdf, ...
python3 ./seir.py
