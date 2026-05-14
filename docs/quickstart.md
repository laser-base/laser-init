# Quick Start

Get started with `laser-init` in minutes. This guide walks you through generating your first spatial disease model.

## Your First Model

Let's create a model for Nigeria at administrative level 2 for years 2000-2025.

### Step 1: Run `laser-init`

```shell
laser-init NGA 2 2000 2025
```

This command:

- **`NGA`** - Nigeria (ISO-3 country code)
- **`2`** - Administrative level 2 (districts/counties)
- **`2000`** - Start year for demographic data
- **`2025`** - End year for demographic data

### Step 2: Wait for Data Download

`laser-init` will:

1. Download administrative boundaries from UNOCHA
2. Download population raster data from WorldPop
3. Aggregate population to administrative units
4. Download demographic statistics from UN WPP
5. Generate model files and validation plots

!!! note "First Run Takes Longer"
    The first run downloads large databases (~1-2GB for UNOCHA) that are cached locally. Subsequent runs for other countries will be much faster.

### Step 3: Explore the Output

Navigate to the output directory:

```shell
cd NGA/2000
ls -l
```

You should see:

```text
NGA_admin2.gpkg          # GeoPackage with boundaries and population
config.yaml              # Model configuration
seir.py                  # Ready-to-run model script (default; use --model for si.py or sir.py)
plot.py                  # Plotting utilities
age_dist.csv             # Age distribution data
cxr.csv                  # Birth and death rates
life_exp.csv             # Life expectancy data
age_distribution.png     # Age pyramid visualization
cbr_cdr.png              # Birth/death rate plots
choropleth.png           # Population map
life_expectancy.png      # Survival curve
report.pdf               # Combined validation report
provenance.json          # Data source metadata
```

### Step 4: Run the Model

Execute the generated model:

```shell
python3 ./seir.py
```

If you generated a different model with `--model`, run `python3 ./si.py` or `python3 ./sir.py` instead.

The model will:

1. Load configuration and data
2. Initialize the population
3. Seed infections in one location
4. Simulate disease transmission for 10 years
5. Generate output plots

!!! tip "Requires laser.generic"
    The model requires the `laser.generic` package, which is automatically installed as a dependency of `laser-init`.

## Understanding the Output

### GeoPackage (NGA_admin2.gpkg)

The GeoPackage contains administrative boundaries with population data:

```python
import geopandas as gpd

# Load the data
gdf = gpd.read_file("NGA_admin2.gpkg")

# Explore the data
print(gdf.head())
print(gdf.columns)  # nodeid, name, population, geometry

# Plot population
gdf.plot(column="population", legend=True, figsize=(10, 10))
```

### Configuration (config.yaml)

The configuration file controls model behavior:

```yaml
data-dir: /path/to/NGA/2000

datafiles:
    shape-data: NGA_admin2.gpkg
    cxr-data: cxr.csv
    pop-data: age_dist.csv
    exp-data: life_exp.csv

simulation:
    nyears: 10                        # Duration in years
    r0: 2.5                           # Basic reproduction number
    exposed-duration-shape: 4.5       # Exposed period (SEIR only)
    exposed-duration-scale: 1.0
    infectious-duration-mean: 7.0     # Mean infectious period (days)
    naive-population: true            # All susceptible initially
    gravity_k: 500                    # Spatial connectivity parameters
    gravity_a: 1
    gravity_b: 1
    gravity_c: 2
```

### Model Script (`si.py`, `sir.py`, or `seir.py`)

The generated Python script is fully editable. Common customizations:

- Change R₀ value in config.yaml
- Modify seeding location in the script
- Adjust simulation duration
- Add interventions

## Try Different Options

### Different Country

```shell
# Pakistan at admin level 1
laser-init PAK 1 2000 2025

# Kenya at admin level 2
laser-init KEN 2 2010 2030
```

### Different Model Type

```shell
# Simple SI model (no recovery)
laser-init NGA 2 2000 2025 --model SI

# SIR model (with recovery)
laser-init NGA 2 2000 2025 --model SIR

# SEIR model (with exposed period, default)
laser-init NGA 2 2000 2025 --model SEIR
```

### Different Data Sources

```shell
# Use geoBoundaries for admin boundaries
laser-init NGA 2 2000 2025 --shape-source geoboundaries

# Use GADM for admin boundaries
laser-init NGA 2 2000 2025 --shape-source gadm
```

See [Data Sources](datasources.md) for detailed comparison.

### Custom Output Directory

```shell
# Specify output location
laser-init NGA 2 2000 2025 --output-dir /path/to/my-models/nigeria
```

## Common Workflows

### Batch Processing Multiple Countries

```shell
# Process multiple countries
for country in NGA KEN ETH TZA; do
    laser-init $country 2 2000 2025
done
```

### Different Administrative Levels

```shell
# Compare national vs district level
laser-init NGA 0 2000 2025  # National level
laser-init NGA 1 2000 2025  # State/province level
laser-init NGA 2 2000 2025  # District level
```

### Different Time Periods

```shell
# Historical analysis
laser-init NGA 2 1990 2000

# Future projections
laser-init NGA 2 2020 2050
```

## Troubleshooting

### Country Not Found

If you get "Could not determine ISO code":

- Use ISO-3 codes (e.g., "PAK" instead of "Pakistan")
- Check spelling
- Try the French name (e.g., "Chine" for China)

See [Configuration](configuration.md) for LLM-enhanced country name resolution.

### No Data for Administrative Level

If data isn't available at level 3 or 4:

- Try level 0, 1, or 2 (most reliable)
- Try a different `--shape-source`
- Check the data source websites for coverage

### Memory Issues

If processing fails with memory errors:

- Use a lower administrative level (fewer polygons)
- Close other applications
- Try a different shape source

### Model Fails to Run

If the generated model script fails:

- Ensure you're in the environment where `laser-init` is installed
- Check that `laser.generic` is installed: `pip list | grep laser`
- Try: `uv pip install laser.generic`

## Next Steps

Now that you've created your first model:

- **[User Guide](userguide.md)** - Learn detailed usage and customization
- **[Configuration](configuration.md)** - Set up config file for preferences
- **[Models](models.md)** - Understand the disease models
- **[Data Sources](datasources.md)** - Compare data source options

## Getting Help

- Check the [troubleshooting section](#troubleshooting)
- Review the [User Guide](userguide.md) for detailed information
- Visit the [GitHub repository](https://github.com/laser-base/laser-init) for issues and discussions
