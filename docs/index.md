# `laser-init`

**laser-init** prepares geospatial, population, and demographic data for epidemiological modeling with [LASER](https://github.com/laser-base/laser-generic). It downloads administrative boundary shapefiles, population raster data, and demographic statistics, then generates a ready-to-run spatial disease model.

## Overview

`laser-init` is a command-line tool that bootstraps spatial epidemiological modeling by automating the process of:

1. Downloading administrative boundary shapefiles from multiple sources
2. Acquiring population raster data
3. Aggregating population to administrative units
4. Obtaining demographic statistics (birth rates, death rates, age distributions)
5. Generating ready-to-run disease transmission models (SI, SIR, or SEIR)
6. Creating validation plots and reports

## Key Features

- **Multiple data sources**: Support for UNOCHA, geoBoundaries, and GADM administrative boundaries
- **Population data**: Integration with WorldPop for high-resolution population distributions
- **Demographics**: UN World Population Prospects data for birth rates, death rates, and age distributions
- **Model generation**: Automatic creation of SI, SIR, or SEIR models with spatial connectivity
- **Validation**: Built-in visualization and reporting of input data
- **Flexible**: Customizable output and configurable data sources

## Prerequisites

- Python 3.10 or higher
- Recommended: [uv](https://docs.astral.sh/uv/) for fast dependency management
- Internet connection for downloading data sources
- ~500MB-2GB of disk space for cached data (varies by country and data source)

## Quick Example

```shell
# Generate model data for Nigeria, admin level 2, years 2000-2025
laser-init NGA 2 2000 2025
```

This creates a complete modeling environment in `NGA/2000/` with:

- GeoPackage with administrative boundaries and population
- Demographic data files (birth rates, death rates, age distribution)
- Ready-to-run model script (`seir.py` by default, or `si.py` / `sir.py` with `--model`)
- Validation plots and PDF report
- Configuration file for easy customization

## Getting Started

New to `laser-init`? Follow these guides:

- [Installation](installation.md) - Install `laser-init` on your system
- [Quick Start](quickstart.md) - Run your first model in minutes
- [User Guide](userguide.md) - Comprehensive usage tutorial

## Documentation

- **[User Guide](userguide.md)** - Complete tutorial and workflows
- **[Configuration](configuration.md)** - Configure data sources and preferences
- **[Data Sources](datasources.md)** - Detailed comparison of data sources
- **[Models](models.md)** - Epidemiological model documentation
- **[Architecture](architecture.md)** - Developer documentation
- **[API Reference](api/cli.md)** - API documentation for all modules
- **[Contributing](contributing.md)** - Development setup and guidelines

## Use Cases

`laser-init` is ideal for:

- **Rapid prototyping**: Quickly set up spatial disease models for any country
- **Scenario analysis**: Generate models for different administrative levels and time periods
- **Research**: Consistent, reproducible data preparation for epidemiological studies
- **Education**: Teaching spatial modeling with real-world data
- **Public health**: Emergency preparedness and outbreak response planning

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/laser-base/laser-init).

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/laser-base/laser-init/blob/main/LICENSE) file for details.
