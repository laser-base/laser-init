# laser-init - a tool to bootstrap spatial modeling with LASER

[![Documentation](https://github.com/laser-base/laser-init/actions/workflows/docs.yml/badge.svg)](https://laser-base.github.io/laser-init)

**laser-init** prepares geospatial, population, and demographic data for epidemiological modeling with [LASER](https://github.com/laser-base/laser-generic). It downloads administrative boundary shapefiles, population raster data, and demographic statistics, then generates a ready-to-run spatial disease model.

## Prerequisites

- Python 3.10 or higher
- Recommended: [uv](https://docs.astral.sh/uv/) for fast dependency management
- Internet connection for downloading data sources
- ~500MB-2GB of disk space for cached data (varies by country and data source)

## Installation

### Using uv (recommended)

```shell
# Clone the repository
git clone https://github.com/laser-base/laser-init.git
cd laser-init

# Install with uv
uv sync
```

### Using pip

```shell
# Clone the repository
git clone https://github.com/laser-base/laser-init.git
cd laser-init

# Install the package
pip install -e .
```

## Quick Start

Once installed, you can run `laser-init` from the command line:

```shell
# Generate model data for Nigeria, admin level 2, years 2000-2025
laser-init NGA 2 2000 2025
```

This will create a directory `NGA/2000/` with all necessary data files and a ready-to-run SEIR model script.

## Basic Usage

```shell
laser-init <country> <level> <start-year> <end-year>
```

### Arguments

- **`country`**: Country name or ISO-3 code (e.g., "PAK", "Nigeria", "Pakistan")
  - ISO-3 codes are preferred for precision
  - Country names support fuzzy matching, including common misspellings and French names
  - Optionally configure OpenAI or Anthropic API for enhanced country name resolution (see [Configuration](#configuration))

- **`level`**: Administrative level (0-4)
  - 0 = country level
  - 1 = state/province
  - 2 = district/county
  - 3-4 = sub-district (availability varies by country and data source)
  - Note: Data beyond level 2 may not be available or reliable for all countries

- **`start-year`**: Starting year for demographic data (1950-2050)

- **`end-year`**: Ending year for demographic data (1950-2050, inclusive)

### What laser-init Does

1. **Downloads shapefile data** for the specified country at the selected administrative level
2. **Downloads population raster data** (e.g., from WorldPop)
3. **Aggregates population** from raster to administrative boundaries using [RasterToolkit](https://github.com/InstituteforDiseaseModeling/RasterToolkit)
4. **Downloads demographic statistics** from UN World Population Prospects:
   - Crude Birth Rate (CBR) and Crude Death Rate (CDR)
   - Population age distribution
   - Life expectancy/survival curves
5. **Generates a GeoPackage** with administrative boundaries, population, and geometry
6. **Creates a ready-to-run model script** (SI, SIR, or SEIR)
7. **Generates validation plots** and a combined PDF report

## Example

```shell
laser-init NGA 2 2000 2025
```

End result:

```text
% ls -l NGA/2000
total 12440
-rw-r--r--  1 user  staff  3170304 Mar 10 00:18 NGA_admin2.gpkg
-rw-r--r--  1 user  staff      265 Mar 10 00:18 age_dist.csv
-rw-r--r--  1 user  staff    73694 Mar 10 00:18 age_distribution.png
-rw-r--r--  1 user  staff    95107 Mar 10 00:18 cbr_cdr.png
-rw-r--r--  1 user  staff   628305 Mar 10 00:18 choropleth.png
-rw-r--r--  1 user  staff      328 Mar 10 00:18 config.yaml
-rw-r--r--  1 user  staff      500 Mar 10 00:18 cxr.csv
-rw-r--r--  1 user  staff      827 Mar 10 00:18 life_exp.csv
-rw-r--r--  1 user  staff    86740 Mar 10 00:18 life_expectancy.png
-rw-r--r--  1 user  staff    19152 Mar 10 00:18 plot.py
-rw-r--r--@ 1 user  staff     1898 Mar 10 00:18 provenance.json
-rw-r--r--@ 1 user  staff  1387855 Mar 10 00:18 report.pdf
-rw-r--r--  1 user  staff     3301 Mar 10 00:18 seir.py
```

### Output Files

- **`NGA_admin2.gpkg`**: GeoPackage with administrative boundaries, population, and geometry
  - Can be loaded with GeoPandas: `gpd.read_file("NGA_admin2.gpkg")`
  - Contains columns: `nodeid`, `name`, `population`, `geometry`

- **`config.yaml`**: Configuration file referencing data files and model parameters

- **`seir.py`**: Ready-to-run SEIR model script
  - Run with: `python3 ./seir.py` or `python3 ./seir.py --config config.yaml`
  - Requires `laser.generic` package

- **`plot.py`**: Supporting script, called from `seir.py`, for generating simulation result plots

- **Demographic data files**:
  - `age_dist.csv`: Population age distribution for the start year
  - `cxr.csv`: Crude Birth Rate (CBR) and Crude Death Rate (CDR) time series
  - `life_exp.csv`: Life expectancy/survival curve for the start year

- **Validation plots**:
  - `age_distribution.png`: Age pyramid for the start year
  - `cbr_cdr.png`: Birth and death rates over the simulation period
  - `choropleth.png`: Population density map
  - `life_expectancy.png`: Survival curve
  - `report.pdf`: Combined PDF with all validation plots

- **`provenance.json`**: Metadata tracking data sources and download timestamps

## Options

### `--model` (Model Type)

Choose which epidemiological model to generate (default: `SEIR`):

```shell
laser-init NGA 2 2000 2025 --model SI    # Susceptible-Infectious
laser-init NGA 2 2000 2025 --model SIR   # Susceptible-Infectious-Recovered
laser-init NGA 2 2000 2025 --model SEIR  # Susceptible-Exposed-Infectious-Recovered
```

- **SI**: Simple model with susceptible and infectious states
- **SIR**: Adds recovery (immunity) to the model
- **SEIR**: Includes an exposed (latent) period before infectiousness

### `--mode` (Modeling Mode)

Select the modeling approach (default: `ABM`):

```shell
laser-init NGA 2 2000 2025 --mode ABM  # Agent-Based Model
laser-init NGA 2 2000 2025 --mode MPM  # Metapopulation Model
```

### `--shape-source` (Administrative Boundaries)

Choose the source for administrative boundary shapefiles:

```shell
laser-init NGA 2 2000 2025 --shape-source unocha         # Default
laser-init NGA 2 2000 2025 --shape-source geoboundaries
laser-init NGA 2 2000 2025 --shape-source gadm
```

Supported sources:
- **[UNOCHA COD-AB](https://knowledge.base.unocha.org/wiki/spaces/imtoolbox/pages/2557378679/Administrative+Boundaries+COD-AB)** (default): UN Office for Coordination of Humanitarian Affairs
  - High quality, humanitarian-focused
  - World-wide geodatabase (~1-2GB, cached locally)
  - Best coverage for crisis-affected regions

- **[geoBoundaries](https://github.com/wmgeolab/geoBoundaries/)**: Open geospatial boundary database
  - Academic research quality
  - Good global coverage

- **[GADM](https://gadm.org/)**: Database of Global Administrative Areas
  - Comprehensive global coverage
  - Frequent updates

See [docs/datasources.md](docs/datasources.md) for detailed comparison.

### `--raster-source` (Population Data)

Choose the population raster data source:

```shell
laser-init NGA 2 2000 2025 --raster-source worldpop  # Default and only option
```

Currently supported:
- **[WorldPop](https://hub.worldpop.org/)** (default): High-resolution population distribution

### `--stats-source` (Demographics Statistics)

Choose the demographic statistics source:

```shell
laser-init NGA 2 2000 2025 --stats-source unwpp  # Default and only option
```

Currently supported:
- **[UN World Population Prospects](https://population.un.org/wpp/)** (default): Comprehensive demographic indicators

### `--output-dir` (Output Directory)

Specify a custom output directory:

```shell
laser-init NGA 2 2000 2025 --output-dir /path/to/output
```

Default: `./<ISOCODE>/<start_year>` (e.g., `./NGA/2000`)

## Configuration

You can create an optional configuration file to set default preferences and API keys for enhanced country name resolution.

Create `~/.laser/laser_config.yaml` or `laser_config.yaml` in your current directory:

```yaml
# Default data source preferences
shape_source: unocha      # or geoboundaries, gadm
raster_source: worldpop
stats_source: unwpp

# Optional: API keys for LLM-enhanced country name matching
# If provided, laser-init can use AI to resolve ambiguous country names
openai_api_key: sk-your-key-here
anthropic_api_key: sk-ant-your-key-here
```

Alternatively, use JSON format (`laser_config.json`):

```json
{
  "shape_source": "unocha",
  "raster_source": "worldpop",
  "stats_source": "unwpp",
  "openai_api_key": "sk-your-key-here",
  "anthropic_api_key": "sk-ant-your-key-here"
}
```

## Running the Generated Model

After running `laser-init`, you'll have a complete model setup:

```shell
cd NGA/2000
python3 ./seir.py
```

The model will:
1. Load configuration and data from `config.yaml`
2. Initialize the population across administrative units
3. Simulate disease transmission using a spatial gravity model
4. Generate output plots in the same directory

### Customizing Model Parameters

Edit `config.yaml` to adjust model behavior:

```yaml
data-dir: /path/to/NGA/2000

datafiles:
    shape-data: NGA_admin2.gpkg
    cxr-data: cxr.csv
    pop-data: age_dist.csv
    exp-data: life_exp.csv

simulation:
    nyears: 10                        # Simulation duration in years
    r0: 2.5                           # Basic reproduction number
    exposed-duration-shape: 4.5       # Exposed period gamma distribution shape (SEIR only)
    exposed-duration-scale: 1.0       # Exposed period gamma distribution scale (SEIR only)
    infectious-duration-mean: 7.0     # Mean infectious period in days
    naive-population: true            # If false, initialize with (1-1/R0)×S in R compartment
    gravity_k: 500                    # connection factor constant
    gravity_a: 1                      # source population power
    gravity_b: 1                      # destination population power
    gravity_c: 2                      # distance power
```

**Note**: Spatial connectivity is determined by a gravity model.

$connection_{ij} = k \frac {P_{src}^a \times P_{dst}^b} {D_{ij}^c}$

## Troubleshooting

### Country Not Found

**Error**: "Could not determine ISO code for country: XYZ"

**Solutions**:
- Use the ISO-3 code instead (e.g., "PAK" instead of "Pakistan")
- Check spelling and try common variants
- Try the French name (e.g., "Chine" for China)
- Configure OpenAI or Anthropic API key for enhanced matching (not currently implemented)

### No Data Available for Administrative Level

**Error**: Data source has no data for level 3 or 4

**Solutions**:
- Try a lower administrative level (0, 1, or 2)
- Try a different `--shape-source` (coverage varies by source and country)
- Check the data source websites for country-specific coverage

### Large Download Size

**Issue**: First run downloads large files (e.g., UNOCHA's 1-2GB global database)

**Solutions**:
- Files are cached locally in `~/.laser/cache/` for future use
- Subsequent runs will be much faster
- Consider using `--shape-source geoboundaries` or `gadm` for smaller downloads

### Missing Dependencies

**Error**: "No module named 'laser.generic'" when running model

**Solutions**:

Run in the environment with `laser-init` installed (`laser-init` installs `laser.generic` as a dependency).

Or, install `laser.generic` into the current environment:

```shell
uv pip install laser.generic
# or
pip install laser.generic
```

## Advanced Usage

### Batch Processing Multiple Countries

```shell
for country in NGA KEN ETH; do
  laser-init $country 2 2000 2025
done
```

### Custom Model Modifications

The generated model scripts are fully editable Python files. Common modifications:

1. **Change initial seed locations**: Edit the seeding logic in `seir.py`
2. **Modify transmission parameters**: Adjust `r0`, `beta`, or duration parameters
3. **Add interventions**: Insert intervention logic into the model components (see [LASER documentation](https://laser.idmod.org/laser-generic))
4. **Customize plots**: Modify `plot.py` or import it and call specific plot functions

### Using Output Data in Other Tools

The GeoPackage can be used in any GIS tool:

```python
import geopandas as gpd
import matplotlib.pyplot as plt

# Load the data
gdf = gpd.read_file("NGA/2000/NGA_admin2.gpkg")

# Plot population density
gdf.plot(column="population", legend=True, figsize=(10, 10))
plt.title("Population Distribution")
plt.show()
```

## Documentation

- [User Guide](docs/userguide.md) - Comprehensive tutorial and workflows
- [Data Sources](docs/datasources.md) - Detailed comparison of data sources
- [Models](docs/models.md) - Epidemiological model documentation
- [Architecture](docs/architecture.md) - Developer documentation
- [Contributing](docs/contributing.md) - Development setup and guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/laser-base/laser-init).
