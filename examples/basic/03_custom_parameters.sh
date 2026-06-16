#!/usr/bin/env bash
#
# 03 - Customize model parameters.
#
# Generates a model, edits the simulation parameters in config.yaml, then runs
# it. The generated config uses underscore_separated keys under "simulation:".
#
# Learning objectives:
#   - Locate and edit the generated config.yaml
#   - Change model parameters (R0, infectious duration)
#   - Re-run with custom parameters
#
# Note: requires network access for the initial data download. Uses perl for the
# in-place edit so it behaves the same on macOS and Linux.

set -euo pipefail

laser-init KEN 2 2015 2020   # output in ./KEN/2015
cd KEN/2015

# Edit parameters in place (they live under the "simulation:" section). The
# patterns keep the leading indentation and replace only the value.
perl -i -pe 's/^(\s*r0:).*/${1} 4.0/' config.yaml
perl -i -pe 's/^(\s*infectious_duration_mean:).*/${1} 5.0/' config.yaml

echo "Updated parameters:"
grep -E 'r0:|infectious_duration_mean:' config.yaml

python3 ./seir.py
echo "Simulation complete with R0=4.0, infectious_duration_mean=5 days"
