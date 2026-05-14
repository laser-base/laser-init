# Troubleshooting Guide

Common issues and solutions when using `laser-init`.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Country Name Resolution](#country-name-resolution)
3. [Data Download Problems](#data-download-problems)
4. [Administrative Level Issues](#administrative-level-issues)
5. [Memory and Performance](#memory-and-performance)
6. [Model Execution Issues](#model-execution-issues)
7. [Data Quality Issues](#data-quality-issues)
8. [Configuration Problems](#configuration-problems)

## Installation Issues

### Command not found: `laser-init`

**Problem**: After installation, running `laser-init` returns "command not found"

**Solutions**:

1. Ensure you're in the virtual environment:
   ```shell
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows
   ```

2. Check if the package is installed:
   ```shell
   pip list | grep laser-init
   ```

3. Try running directly:
   ```shell
   python -m laser.init.cli --help
   ```

4. Reinstall the package:
   ```shell
   uv sync --refresh
   # or
   pip install -e . --force-reinstall
   ```

### ImportError: No module named 'laser.init'

**Problem**: Python cannot find the `laser-init` module

**Solutions**:

1. Verify you're in the correct directory:
   ```shell
   pwd  # Should be in laser-init project directory
   ```

2. Ensure installation completed successfully:
   ```shell
   pip show laser-init
   ```

3. Check your PYTHONPATH:
   ```shell
   python -c "import sys; print('\n'.join(sys.path))"
   ```

4. Reinstall in development mode:
   ```shell
   pip install -e .
   ```

### GDAL/Geospatial Library Errors

**Problem**: Errors related to GDAL, GEOS, or other geospatial libraries

**Solutions**:

=== "macOS"
    ```shell
    brew install gdal
    pip install --upgrade gdal pyogrio geopandas
    ```

=== "Ubuntu/Debian"
    ```shell
    sudo apt-get update
    sudo apt-get install gdal-bin libgdal-dev
    pip install --upgrade gdal pyogrio geopandas
    ```

=== "Windows"
    Use pre-built wheels from PyPI (usually installed automatically)

## Country Name Resolution

### Could not determine ISO code for country

**Problem**: Error message: "Could not determine ISO code for country: XYZ"

**Solutions**:

1. **Use ISO-3 code directly** (most reliable):
   ```shell
   laser-init NGA 2 2000 2025  # Instead of "Nigeria"
   ```

2. **Check spelling**:
   - Correct: "Kenya" not "Kenia"
   - Correct: "Côte d'Ivoire" or "CIV"

3. **Try the French name**:
   ```shell
   laser-init "Chine" 2 2000 2025  # For China
   ```

4. **Look up ISO-3 code**:
   - Visit [ISO Online Browsing Platform](https://www.iso.org/obp/ui/)
   - Or use: `python -c "import pycountry; print([c for c in pycountry.countries if 'pak' in c.name.lower()])"`

5. **Configure LLM API** (future enhancement):
   ```yaml
   # ~/.laser/laser_config.yaml
   openai_api_key: sk-your-key-here
   # or
   anthropic_api_key: sk-ant-your-key-here
   ```

### Ambiguous Country Names

**Problem**: Multiple countries have similar names

**Examples and solutions**:

- **Congo** → Use "COD" (DRC) or "COG" (Republic of Congo)
- **Korea** → Use "KOR" (South Korea) or "PRK" (North Korea)
- **China** → Use "CHN" (mainland) or "TWN" (Taiwan) or "HKG" (Hong Kong)

## Data Download Problems

### Large Download Size / Slow First Run

**Problem**: First run takes a long time downloading 1-2GB database

**Explanation**: UNOCHA downloads a global database (~1-2GB) on first use

**Solutions**:

1. **Be patient**: This is a one-time download that gets cached
   ```shell
   # Check cache location
   ls -lh ~/.laser/cache/UNOCHA/
   ```

2. **Use alternative source** with smaller downloads:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source geoboundaries
   # or
   laser-init NGA 2 2000 2025 --shape-source gadm
   ```

3. **Monitor progress**: Watch the terminal for download status

4. **Check disk space**:
   ```shell
   df -h ~  # Ensure you have 2-3GB free
   ```

### Download Interrupted / Partial Files

**Problem**: Download fails midway or connection times out

**Solutions**:

1. **Remove partial downloads**:
   ```shell
   rm -rf ~/.laser/cache/UNOCHA/*.partial
   ```

2. **Retry the command**: `laser-init` will resume or restart the download

3. **Check internet connection**:
   ```shell
   ping data.humdata.org
   ```

4. **Use a more stable data source**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source geoboundaries
   ```

### 404 Not Found / URL Errors

**Problem**: Data source URL returns 404 or is unavailable

**Solutions**:

1. **Try a different data source**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source gadm
   ```

2. **Check data source websites**:
   - [UNOCHA HDX](https://data.humdata.org/)
   - [geoBoundaries](https://www.geoboundaries.org/)
   - [GADM](https://gadm.org/)

3. **Clear cache and retry**:
   ```shell
   rm -rf ~/.laser/cache/
   laser-init NGA 2 2000 2025
   ```

4. **Report the issue**: File a GitHub issue with the error message

## Administrative Level Issues

### No Data Available for Administrative Level

**Problem**: "Data source has no data for level 3" or "level 4"

**Solutions**:

1. **Use a lower administrative level**:
   ```shell
   laser-init NGA 2 2000 2025  # Level 2 usually available
   laser-init NGA 1 2000 2025  # Level 1 almost always available
   laser-init NGA 0 2000 2025  # Level 0 (national) always available
   ```

2. **Try a different data source**:
   ```shell
   laser-init NGA 3 2000 2025 --shape-source gadm
   ```

3. **Check data source coverage**:
   - Visit the data source website
   - Look for country-specific documentation

### Missing or Empty Regions

**Problem**: Some administrative regions appear empty or have zero population

**Solutions**:

1. **Check the validation plots**:
   - Open `choropleth.png`
   - Look for gaps or anomalies

2. **Verify with data source**:
   - Check if regions exist in the original data
   - Compare with official statistics

3. **Try a different data source**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source unocha
   ```

4. **Check provenance.json**:
   ```shell
   cat provenance.json  # See data source details
   ```

## Memory and Performance

### Out of Memory Errors

**Problem**: Process crashes with "MemoryError" or "Killed"

**Solutions**:

1. **Use lower administrative level**:
   ```shell
   laser-init NGA 1 2000 2025  # Fewer polygons = less memory
   ```

2. **Close other applications**: Free up RAM

3. **Try a different shape source** with simpler geometries:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source geoboundaries
   ```

4. **Increase swap space** (Linux):
   ```shell
   # Create 4GB swap file
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

5. **Use a machine with more RAM**: Consider cloud resources

### Very Slow Processing

**Problem**: Processing takes an unusually long time

**Solutions**:

1. **Check if download is still in progress**: Look at terminal output

2. **For first run with UNOCHA**: Be patient during initial download

3. **Check system resources**:
   ```shell
   top  # or htop to see CPU/memory usage
   ```

4. **Use a faster data source**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source geoboundaries
   ```

5. **Simplify the task**:
   - Use level 0 or 1 instead of 2+
   - Use shorter time period

## Model Execution Issues

### No module named 'laser.generic'

**Problem**: Generated model fails with "ModuleNotFoundError: No module named 'laser.generic'"

**Solutions**:

1. **Ensure you're in the correct environment**:
   ```shell
   which python  # Should show .venv/bin/python
   ```

2. **Install laser.generic**:
   ```shell
   uv pip install laser.generic
   # or
   pip install laser.generic
   ```

3. **Verify installation**:
   ```shell
   python -c "import laser.generic; print(laser.generic.__version__)"
   ```

### Model Fails to Run / Python Errors

**Problem**: Generated model script fails with various errors

**Solutions**:

1. **Check all data files exist**:
   ```shell
   ls -l *.gpkg *.csv config.yaml
   ```

2. **Validate config.yaml**:
   ```shell
   cat config.yaml  # Check for correct file paths
   ```

3. **Run with verbose output**:
   ```shell
   python seir.py --help  # See available options for the default model script
   python seir.py --config config.yaml  # Explicit config
   ```

   If you generated a different model, replace `seir.py` with `si.py` or `sir.py`.

4. **Check Python version**:
   ```shell
   python --version  # Should be 3.10+
   ```

5. **Review the traceback**: Look for specific error messages

### Simulation Produces Unrealistic Results

**Problem**: Model outputs don't match expectations

**Solutions**:

1. **Check validation plots first**:
   - `choropleth.png` - Population distribution
   - `age_distribution.png` - Age structure
   - `cbr_cdr.png` - Birth/death rates

2. **Verify model parameters**:
   ```yaml
   # config.yaml
   r0: 2.5  # Is this appropriate for your disease?
   infectious_duration_mean: 7.0  # Realistic?
   ```

3. **Check seeding**:
   - Look at initial infection seeding in model script
   - Verify it's in a reasonable location

4. **Compare with literature**:
   - Use published R0 values
   - Verify duration parameters

## Data Quality Issues

### Population Totals Don't Match Official Statistics

**Problem**: Aggregated population differs from known values

**Solutions**:

1. **Check provenance.json**: See what data sources were used

2. **Verify year**:
   - WorldPop data is for specific years
   - Ensure you're using the correct year

3. **Check validation plot**:
   - Open `choropleth.png`
   - Look for obviously wrong values

4. **Try different raster year** (if available):
   ```shell
   # Future enhancement - currently uses closest available year
   ```

5. **Compare with UN WPP**:
   ```python
   import pandas as pd
   gdf = gpd.read_file("NGA_admin2.gpkg")
   print(f"Total population: {gdf.population.sum():,.0f}")
   ```

### Misaligned Boundaries / Geometry Issues

**Problem**: Administrative boundaries look wrong or overlap incorrectly

**Solutions**:

1. **Try a different shape source**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source gadm
   ```

2. **Visualize in QGIS**:
   - Load the .gpkg file
   - Inspect geometry visually

3. **Check for topology issues**:
   ```python
   import geopandas as gpd
   gdf = gpd.read_file("NGA_admin2.gpkg")
   print(gdf.is_valid.all())  # Should be True
   ```

4. **Report to data source**: If boundaries are clearly wrong

## Configuration Problems

### Config File Not Found

**Problem**: `laser-init` doesn't find your configuration file

**Solutions**:

1. **Check filename and location**:
   ```shell
   ls ~/.laser/laser_config.yaml
   # or
   ls ./laser_config.yaml
   ```

2. **Verify file format** (YAML or JSON):
   ```yaml
   # Correct YAML format
   shape_source: unocha

   # NOT like this (incorrect)
   {shape_source: unocha}
   ```

3. **Check file permissions**:
   ```shell
   chmod 644 ~/.laser/laser_config.yaml
   ```

4. **Use command-line options instead**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source unocha
   ```

### Invalid Configuration Values

**Problem**: Config file has invalid values

**Solutions**:

1. **Validate YAML syntax**:
   ```shell
   python -c "import yaml; yaml.safe_load(open('~/.laser/laser_config.yaml'))"
   ```

2. **Check valid options**:
   - `shape_source`: unocha, geoboundaries, gadm
   - `raster_source`: worldpop
   - `stats_source`: unwpp

3. **Use defaults**: Remove config file temporarily to use defaults

## Getting More Help

### Enable Debug Logging

```shell
# Future enhancement - verbose mode
laser-init NGA 2 2000 2025 --verbose
```

### Check Log Files

```shell
# Check for log files
ls ~/.laser/logs/

# View most recent log
tail -f ~/.laser/logs/laser-init.log
```

### Gather Information for Bug Reports

When reporting issues, include:

1. **Command used**:
   ```shell
   laser-init NGA 2 2000 2025 --shape-source unocha
   ```

2. **Error message**: Full traceback

3. **Environment**:
   ```shell
   python --version
   pip list | grep laser
   uname -a  # OS information
   ```

4. **Provenance file** (if generated):
   ```shell
   cat provenance.json
   ```

## Common Error Messages

### "HTTP Error 403: Forbidden"

**Cause**: Data source blocked your IP or requires authentication

**Solution**: Try a different data source or wait and retry later

### "SSL Certificate Verify Failed"

**Cause**: SSL certificate issues

**Solution**:
```shell
pip install --upgrade certifi
# or temporarily (not recommended)
export PYTHONHTTPSVERIFY=0
```

### "Permission Denied" when writing files

**Cause**: No write permission to output directory

**Solution**:
```shell
# Check permissions
ls -ld .

# Use --output-dir with writable location
laser-init NGA 2 2000 2025 --output-dir ~/my-models/NGA
```

### "Raster clip failed"

**Cause**: Raster and shapefile don't overlap properly

**Solution**: Try a different shape source or verify your country code is correct

## Still Having Issues?

1. **Search existing issues**: [GitHub Issues](https://github.com/laser-base/laser-init/issues)
2. **Ask a question**: [GitHub Discussions](https://github.com/laser-base/laser-init/discussions)
3. **File a bug report**: [New Issue](https://github.com/laser-base/laser-init/issues/new)

When filing an issue, include:
- Operating system and version
- Python version
- Full command used
- Complete error message
- Steps to reproduce

## Related Resources

- [Installation Guide](installation.md)
- [Quick Start](quickstart.md)
- [User Guide](userguide.md)
- [Configuration Guide](configuration.md)
- [Data Sources](datasources.md)
