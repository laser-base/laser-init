# `laser-init` User Guide

A comprehensive guide to using `laser-init` to bootstrap spatial epidemiological modeling with LASER.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Workflow](#understanding-the-workflow)
3. [Working with Output Files](#working-with-output-files)
4. [Common Workflows](#common-workflows)
5. [Interpreting Results](#interpreting-results)
6. [Customizing Models](#customizing-models)
7. [Best Practices](#best-practices)

## Getting Started

### Installation

See the [Installation Guide](installation.md) for installation instructions.

### Your First Model

Let's create a model for Kenya at the district level (admin level 2) for years 2010-2020:

```shell
laser-init KEN 2 2010 2020
```

This command will:

1. Download administrative boundary shapefiles for Kenya
2. Download population raster data for 2010
3. Aggregate population to district boundaries
4. Download demographic data (birth rates, death rates, age distribution, life expectancy)
5. Generate a ready-to-run SEIR model
6. Create validation plots

**Expected time**: 30 seconds - 10 minutes (first run with UNOCHA source downloads ~1-2GB global database)

### What You'll See

During execution, `laser-init` displays progress information:

```text
Starting laser-init CLI
Received arguments: country=Kenya, level=2, start_year=2000, end_year=2025, output_dir=None, shape_source=None, raster_source=None, stats_source=None
Country: Kenya → ISO-3: KEN
level_from_string(): Parsed level number 2 from input '2'.
Administrative Level: 2 → ADM2
Base year: 2010
End year: 2020
Output directory: <cwd>/KEN/2010
Using shape source: unocha (Extracts data from the United Nations Office for the Coordination of Humanitarian Affairs (UNOCHA) at https://data.humdata.org)
Using raster source: worldpop (Extracts data from WorldPop at https://www.worldpop.org)
Using demographic stats source: UNWPP (Extracts data from the UN World Population Prospects (UNWPP) at https://population.un.org/wpp/)
Using shape transformer: unocha (Transform UNOCHA shape data to GeoPackage format, filtered by country and administrative level.)
Clipping raster_file=<user>/.laser/cache/WorldPop/ken_ppp_2000_1km_Aggregated_UNadj.tif with shapefile=/var/folders/fl/_ns4br_j2qxd92vjrgl3t4n00000gn/T/tmp75axlidm/KEN_admin2.shp, shape_attr=adm2_pcode...
Clipped raster_file=<user>/.laser/cache/WorldPop/ken_ppp_2000_1km_Aggregated_UNadj.tif.
Saved GeoPackage: <user>/KEN/2000/KEN_admin2.gpkg
UNOCHA transform complete: <user>/KEN/2000/KEN_admin2.gpkg
Using demographic stats transformer: unwpp (Transform UNWPP demographic data to a usable format, filtered by country and year range.)
Saved CBR/CDR data to <user>/KEN/2000/cxr.csv
Loading population data from <user>/.laser/cache/UNWPP/WPP2024_Population1JanuaryByAge5GroupSex_Medium.csv.gz
Saved age distribution data to <user>/KEN/2000/age_dist.csv
Loading life expectancy data from <user>/.laser/cache/UNWPP/WPP2024_Life_Table_Complete_Medium_Both_1950-2023.csv.gz
Loading additional life expectancy data from <user>/.laser/cache/UNWPP/WPP2024_Life_Table_Complete_Medium_Both_2024-2100.csv.gz
WPP2024_Life_Table_Complete_Medium_Both_2024-2100.csv.gz
Saved life expectancy data to <user>/KEN/2000/life_exp.csv
Finished loading demographics stats.
Emitting model script for ABM/SEIR with data files:
Shape file:                       '<user>/KEN/2000/KEN_admin2.gpkg'
CBR/CDR file:                     '<user>/KEN/2000/cxr.csv'
Population age distribution file: '<user>/KEN/2000/age_dist.csv'
Life expectancy file:             '<user>/KEN/2000/life_exp.csv'
Writing plots of the transformed data...
Choropleth PNG written to <user>/KEN/2000/choropleth.png
CBR/CDR plot PNG written to <user>/KEN/2000/cbr_cdr.png
Age distribution plot PNG written to <user>/KEN/2000/age_distribution.png
Life expectancy plot PNG written to <user>/KEN/2000/life_expectancy.png
PDF report written to <user>/KEN/2000/report.pdf
```

### Running Your First Simulation

After `laser-init` completes:

```shell
cd KEN/2010
python3 ./seir.py
```

The simulation will run and generate output plots showing disease spread across Kenya's districts.

## Understanding the Workflow

### The `laser-init` Pipeline

```
┌─────────────────┐
│ Country & Level │
│   Selection     │
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌──────────────┐
│  Download       │     │   UNOCHA     │
│  Shapefiles     │────>│ geoBoundaries│
└────────┬────────┘     │   GADM       │
         │              └──────────────┘
         v
┌─────────────────┐     ┌──────────────┐
│  Download       │     │  WorldPop    │
│  Population     │────>│   Rasters    │
└────────┬────────┘     └──────────────┘
         │
         v
┌─────────────────┐     ┌────────────┐
│   Aggregate     │     │   country  │
│   Population    │────>│ geoPackage │
│  to Boundaries  │     └────────────┘
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌─────────────────┐
│  Download       │     │   UN WPP        │
│  Demographics   │────>│ CBR, CDR, age,  │
└────────┬────────┘     │ life expectancy │
         │              └─────────────────┘
         v
┌─────────────────┐
│   Generate      │
│  Model Script   │
│  & Config       │
└────────┬────────┘
         │
         v
┌─────────────────┐
│   Validation    │
│     Plots       │
└─────────────────┘
```

### Data Flow

1. **Input**: Country code + administrative level + time period
2. **Extraction**: Download raw geospatial and demographic data
3. **Transformation**: Aggregate, clean, and format data
4. **Loading**: Generate model-ready files and scripts
5. **Validation**: Create plots to verify data quality

## Working with Output Files

### Directory Structure

```
KEN/
└── 2010/
    ├── KEN_admin2.gpkg          # Geospatial data (main input)
    ├── config.yaml              # Model configuration
    ├── seir.py                  # SEIR model script
    ├── plot.py                  # Plotting utilities
    ├── age_dist.csv             # Age distribution
    ├── cxr.csv                  # Crude birth/death rates
    ├── life_exp.csv             # Life expectancy curve
    ├── provenance.json          # Data source metadata
    ├── age_distribution.png     # Age pyramid plot
    ├── cbr_cdr.png              # Birth/death rates plot
    ├── choropleth.png           # Population map
    ├── life_expectancy.png      # Survival curve plot
    └── report.pdf               # Combined PDF report
```

### Understanding the GeoPackage

The `.gpkg` file is the core data product. Load it with GeoPandas:

```python
import geopandas as gpd

# Load the GeoPackage
gdf = gpd.read_file("KEN_admin2.gpkg")

# Inspect the data
print(gdf.head())
print(f"Number of districts: {len(gdf)}")
print(f"Total population: {gdf.population.sum():,.0f}")
print(f"Columns: {gdf.columns.tolist()}")
```

**Expected columns**:

- `nodeid`: Unique integer identifier for each administrative unit (0, 1, 2, ...)
- `name`: Name of the administrative unit
- `population`: Population count for the administrative unit
- `geometry`: Polygon geometry (boundaries)

### Understanding Demographic Files

#### age_dist.csv - Age Distribution

Population by age group for the start year:

```csv
AgeGrpStart,PopTotal
0,9313.250
5,7315.490
...
```

**Note:** PopTotal does not have to be an absolute number as long as the PopTotal counts, relative to each other, correctly represent the distribution of population by age groups.

**Use case**: Initialize age-structured models, calculate age-specific rates

#### cxr.csv - Crude Rates

Crude Birth Rate (CBR) and Crude Death Rate (CDR) for each year in the simulation period:

```csv
Time,CBR,CDR
2010,43.920,11.654
2011,43.981,11.367
...
```

**Units**: Per 1,000 people per-year (43.920 = 42.92 births per 1,000 population, each year)

**Use case**: Vital dynamics (births and deaths) in the model

#### life_exp.csv - Life Expectancy

Survival curve (probability of surviving to each age):

```csv
cumulative_deaths
9668.0
11889.0
13570.0
14853.0
...
98313.0
```

**Note 1:** UN WPP data omits the final cumulative count which is assumed to be 100,000 and is added in the model script to correctly initialize the Kaplan-Meier estimator.

**Note 2:** Like `age_dist.csv`, cumulative deaths does not have to be an absolute number as long as each entry represents the correct fraction of the total population.

**Use case**: Age-specific mortality rates in the model

### Understanding Provenance

`provenance.json` tracks data sources and timestamps:

```json
{
    "KEN_admin2.gpkg": {
        "global_admin_boundaries_matched_latest.gdb.zip": {
            "source_url": "https://data.humdata.org/...",
            "timestamp": "2026-03-10T00:17:53.292892"
        },
        "ken_ppp_2010_1km_Aggregated_UNadj.tif": {
            "source_url": "https://data.worldpop.org/...",
            "timestamp": "2026-03-10T00:18:32.339863"
        }
    }
}
```

**Use case**: Citation, reproducibility, data lineage tracking

### Validation Plots

Review these plots to verify data quality:

1. **choropleth.png**: Population distribution map
   - Check for missing regions
   - Verify population concentrations match expectations
   - Look for outliers or anomalies

2. **age_distribution.png**: Population pyramid
   - Verify age structure matches country profile
   - Check for missing age groups
   - Compare to known demographics

3. **cbr_cdr.png**: Birth and death rates over time
   - Verify trends match known patterns
   - Check for unrealistic jumps or gaps
   - Compare to official statistics if available

4. **life_expectancy.png**: Survival curve
   - Verify life expectancy matches country profile
   - Check for realistic shape (exponential decline with age)
   - Compare to WHO or other sources

## Common Workflows

### Workflow 1: Quick Model Setup

Generate and run a model in minutes:

```shell
# Generate model files
laser-init ETH 2 2010 2020

# Navigate to output
cd ETH/2010

# Run the model
python3 ./seir.py

# Results are saved as PNG files in the current directory
```

### Workflow 2: Comparing Data Sources

Test different shapefile sources to find the best coverage:

```shell
# Try UNOCHA (default)
laser-init MWI 2 2015 2020 --shape-source unocha --output-dir MWI_unocha

# Try geoBoundaries
laser-init MWI 2 2015 2020 --shape-source geoboundaries --output-dir MWI_geoboundaries

# Try GADM
laser-init MWI 2 2015 2020 --shape-source gadm --output-dir MWI_gadm

# Compare the population maps
open MWI_unocha/2015/choropleth.png
open MWI_geoboundaries/2015/choropleth.png
open MWI_gadm/2015/choropleth.png
```

### Workflow 3: Multi-Country Analysis

Generate models for multiple countries:

```shell
#!/bin/bash
# analyze_west_africa.sh

countries=("NGA" "GHA" "SEN" "CIV" "BFA")

for country in "${countries[@]}"; do
    echo "Processing $country..."
    laser-init "$country" 2 2010 2020 --output-dir "west_africa/$country/2010"
done

echo "All countries processed!"
```

### Workflow 4: Time Series Analysis

Generate models for different time periods:

```shell
# Historical period
laser-init PAK 2 2000 2010 --output-dir PAK/historical

# Recent period
laser-init PAK 2 2010 2020 --output-dir PAK/recent

# Compare population growth
python3 -c "
import geopandas as gpd
hist = gpd.read_file('PAK/historical/2000/PAK_admin2.gpkg')
recent = gpd.read_file('PAK/recent/2010/PAK_admin2.gpkg')
print(f'2000 population: {hist.population.sum():,.0f}')
print(f'2010 population: {recent.population.sum():,.0f}')
print(f'Growth: {(recent.population.sum() / hist.population.sum() - 1) * 100:.1f}%')
"
```

### Workflow 5: Custom Model Parameters

Generate baseline, then create parameter variations:

```shell
# Generate baseline
laser-init BRA 2 2015 2020

cd BRA/2015

# Create parameter sweep
for r0 in 1.5 2.0 2.5 3.0 4.0; do
    mkdir -p runs/r0_${r0}

    # Copy base files
    cp seir.py plot.py *.csv *.gpkg runs/r0_${r0}/

    # Modify config
    sed "s/r0: 2.5/r0: ${r0}/" config.yaml > runs/r0_${r0}/config.yaml

    # Run simulation
    (cd runs/r0_${r0} && python3 ./seir.py)
done

echo "Parameter sweep complete!"
```

### Workflow 6: Integration with Custom Analysis

Use `laser-init` data in custom scripts:

```python
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load `laser-init` outputs
data_dir = Path("KEN/2010")
gdf = gpd.read_file(data_dir / "KEN_admin2.gpkg")
cbr_cdr = pd.read_csv(data_dir / "cxr.csv")

# Custom analysis: Calculate population density
gdf["area_km2"] = gdf.geometry.area / 1e6  # Convert to km^2
gdf["density"] = gdf.population / gdf.area_km2

# Custom visualization
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Population map
gdf.plot(column="population", ax=ax1, legend=True, cmap="YlOrRd")
ax1.set_title("Population Distribution")
ax1.axis("off")

# Density map
gdf.plot(column="density", ax=ax2, legend=True, cmap="Blues")
ax2.set_title("Population Density (per km�)")
ax2.axis("off")

plt.tight_layout()
plt.savefig("custom_analysis.png", dpi=300, bbox_inches="tight")
print("Custom analysis saved to custom_analysis.png")
```

## Interpreting Results

### Understanding Model Outputs

After running the generated model script (e.g., `seir.py`), you'll find several output plots:

1. **Stacked Compartments**: Shows S, E, I, R populations over time
   - Look for epidemic peak timing
   - Assess attack rate (final R population)
   - Verify all compartments sum to total population

2. **Effective Reproduction Number (R<sub>t</sub>)**: Time-varying reproduction number
   - R<sub>t</sub> > 1: Epidemic growing
   - R<sub>t</sub> = 1: Steady state
   - R<sub>t</sub> < 1: Epidemic declining
   - Useful for assessing intervention effectiveness

3. **Choropleth Snapshots**: Spatial distribution at key timepoints
   - Identify outbreak origins
   - Track spatial spread patterns
   - Find high-burden regions

4. **Arrival Time Map**: When disease first reaches each location
   - Visualize wave patterns
   - Identify connectivity effects
   - Plan intervention timing

5. **Individual Node Trajectories**: Time series for selected regions
   - Compare urban vs rural patterns
   - Assess heterogeneity in outbreak dynamics
   - Identify outliers

6. **Import Pressure**: Local vs imported cases
   - Understand role of spatial coupling
   - Assess local transmission vs importation
   - Guide travel restriction policies

7. **Peak Timing vs Peak Size**: Scatter plot analysis
   - Identify early-hit vs late-hit regions
   - Correlate peak timing with severity
   - Inform resource allocation

8. **Cumulative Incidence**: Total attack rates by region
   - Final burden assessment
   - Identify high-impact regions
   - Calculate summary statistics

### Validation Checklist

Before trusting simulation results, verify:

- [ ] Population totals match expected values
- [ ] Age distribution matches country demographics
- [ ] Birth/death rates are reasonable
- [ ] No missing or zero-population regions
- [ ] Spatial connectivity looks realistic
- [ ] Model parameters are appropriate for the disease
- [ ] Simulation duration is sufficient to capture full outbreak

## Customizing Models

### Modifying config.yaml

Simple parameter changes:

```yaml
simulation:
    nyears: 20                        # Extend simulation to 20 years
    r0: 3.5                           # Increase transmissibility
    infectious_duration_mean: 5.0     # Shorter infectious period
    naive_population: false           # Add prior immunity
```

Then rerun:
```shell
python3 ./seir.py --config config.yaml
```

### Editing Model Scripts

The generated Python3 ./scripts are fully editable. Common modifications:

#### Change Initial Seeding

In `seir.py`, find the seeding logic:

```python
# Default: Seed largest population center
imax = np.argmax(scenario.population)
scenario.at[imax, "I"] = 50
```

Change to multiple seeds:

```python
# Seed top 3 population centers
top3 = scenario.nlargest(3, "population").index
for idx in top3:
    scenario.at[idx, "I"] = 20
```

Or seed a specific region:

```python
# Seed a specific district by name
seed_district = "Nairobi"
seed_idx = scenario[scenario.name == seed_district].index[0]
scenario.at[seed_idx, "I"] = 100
```

#### Modify Transmission Parameters

```python
# Location in seir.py
params = PropertySet(config["simulation"])

# Add custom parameters
params += {
    "nticks": params.nyears * 365,
    "beta": params.r0 / params.infectious_duration_mean,
    "seasonality_amplitude": 0.2,  # Custom parameter
}
```

#### Add Seasonally Varying Transmission

See [this example notebook](https://laser.idmod.org/laser-generic/tutorials/notebooks/seasonality/#seasonality).

#### Add Interventions

Insert intervention logic into the model:

```python
class Vaccination(Intervention):
    # TODO - implement SIA/vaccination intervention
    pass

# Add to model components
vaccination = Vaccination(model, start_day=365, coverage=0.7)
model.components.append(vaccination)
```

### Customizing Plots

Modify `plot.py` or create custom plotting scripts:

```python
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

# Load results (assuming model saves to CSV/HDF5)
results = pd.read_csv("results.csv")
gdf = gpd.read_file("KEN_admin2.gpkg")

# Custom plot: Attack rate by region
attack_rates = results.groupby("nodeid")["cumulative_incidence"].max()
gdf["attack_rate"] = gdf.nodeid.map(attack_rates)

fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(column="attack_rate", ax=ax, legend=True, cmap="RdYlGn_r",
         vmin=0, vmax=1, legend_kwds={"label": "Attack Rate"})
ax.set_title("Final Attack Rate by District")
ax.axis("off")
plt.savefig("custom_attack_rate.png", dpi=300, bbox_inches="tight")
```

## Best Practices

### Data Selection

1. **Use ISO-3 codes** for country selection to avoid ambiguity
2. **Start with admin level 2** for best data availability
3. **Use UNOCHA** for crisis regions, GADM for comprehensive global coverage
4. **Check validation plots** before running expensive simulations
5. **Compare data sources** if results seem unexpected

### Model Selection

1. **SI**: Use for diseases with permanent infectiousness (e.g., HIV without treatment)
2. **SIR**: Use for immunizing diseases (e.g., measles, chickenpox)
3. **SEIR**: Use for diseases with incubation period (e.g., influenza, COVID-19)
4. **Consider extensions**: Modify scripts for SEIRS (waning immunity), age structure, etc.

### Parameter Selection

1. **R<sub>0</sub>**: Research disease-specific values (literature, WHO reports)
2. **Duration parameters**: Use evidence-based distributions
3. **Start conservative**: Use well-established parameter ranges
4. **Sensitivity analysis**: Test parameter uncertainty with multiple runs
5. **Validate**: Compare aggregate outputs to known outbreak data if available

### Computational Efficiency

1. **Use lower admin levels** (0-2) for faster computation
2. **Cache data sources**: First run is slowest (downloads large files)
3. **Parallel runs**: Generate data once, run multiple parameter sets in parallel
4. **Profile custom code**: Use Python3 profilers to identify bottlenecks

### Reproducibility

1. **Save provenance.json**: Track data sources and versions
2. **Version control**: Git-track custom model modifications
3. **Document parameters**: Keep notes on parameter choices and rationale
4. **Archive outputs**: Save simulation results with metadata
5. **Share config files**: Enable others to reproduce your exact setup

### Troubleshooting

1. **Check validation plots first**: Catch data issues before simulation
2. **Verify population totals**: Compare to official statistics
3. **Test with small regions**: Debug with admin level 0-1 before scaling up
4. **Consult data sources**: When in doubt, check original data provider documentation
5. **Report issues**: File GitHub issues for bugs or unexpected behavior

## Next Steps

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Data Sources](datasources.md) - In-depth data source comparison
- [Models](models.md) - Epidemiological model theory and implementation
- [Architecture](architecture.md) - Developer documentation for extending `laser-init`
- [Contributing](contributing.md) - Contribute improvements to `laser-init`

## Additional Resources

### LASER Documentation

- [LASER Core](https://github.com/laser-base/laser-core) - Core modeling framework
- [LASER Generic](https://github.com/laser-base/laser-generic) - Generic disease models

### Data Source Documentation

- [UNOCHA COD-AB](https://knowledge.base.unocha.org/wiki/spaces/imtoolbox/pages/2557378679/Administrative+Boundaries+COD-AB)
- [geoBoundaries](https://www.geoboundaries.org/)
- [GADM](https://gadm.org/data.html)
- [WorldPop](https://www.worldpop.org/)
- [UN World Population Prospects](https://population.un.org/wpp/)

### Epidemiological Modeling

- [Basic Reproduction Number](https://en.wikipedia.org/wiki/Basic_reproduction_number)
- [Spatial Epidemic Models](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5348083/)

## Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/laser-base/laser-init/issues)
- **Documentation**: Check all docs in the `docs/` directory
- **Examples**: See the [Quick Start](quickstart.md) and the workflows above for common use cases.
