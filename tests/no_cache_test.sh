# 1. Create an isolated workspace with an empty cache
TESTROOT="$(mktemp -d /tmp/laser-init-test.XXXXXX)"
mkdir -p "$TESTROOT/cache" "$TESTROOT/logs" "$TESTROOT/output"

# 2. Write a config pointing cache_dir/log_dir at the temp location
cat > "$TESTROOT/laser_config.yaml" <<EOF
shape_source: unocha
raster_source: worldpop
stats_source: unwpp
cache_dir: $TESTROOT/cache
log_dir: $TESTROOT/logs
EOF

# 3. Run from inside $TESTROOT so the config is picked up
source .venv/bin/activate
( cd "$TESTROOT" && laser-init SEN ADM1 2020 2025 --shape-source unocha -o "$TESTROOT/output" )

# 4. Inspect, then clean up when done
ls -l "$TESTROOT/output"
cat "$TESTROOT/cache/provenance.json"
rm -rf "$TESTROOT"
