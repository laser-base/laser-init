# Examples Directory Plan (#10)

Comprehensive plan for creating an `examples/` directory with practical, educational examples for laser-init users.

## Overview

The examples directory will provide ready-to-run scripts and notebooks demonstrating common workflows, best practices, and advanced usage patterns.

## Directory Structure

```
examples/
├── README.md                          # Index of all examples
├── basic/                             # Basic usage examples
│   ├── 01_quick_start.sh             # Simplest possible use case
│   ├── 02_data_source_comparison.sh  # Compare UNOCHA vs GADM vs geoBoundaries
│   └── 03_custom_parameters.sh       # Modify model parameters
├── workflows/                         # Complete workflows
│   ├── multi_country_analysis.sh     # Batch process multiple countries
│   ├── time_series_comparison.py     # Compare different time periods
│   └── sensitivity_analysis.py       # Parameter sensitivity sweep
├── data_integration/                  # Working with output data
│   ├── geopackage_analysis.py        # Load and analyze GeoPackage
│   ├── custom_visualization.py       # Custom plots and maps
│   └── export_to_qgis.py            # Prepare data for QGIS
├── model_customization/               # Extending models
│   ├── add_vaccination.py            # Add vaccination intervention
│   ├── social_distancing.py          # Model social distancing
│   ├── age_structured_seir.py        # Age-stratified model
│   └── seirs_waning_immunity.py      # SEIRS with waning immunity
├── advanced/                          # Advanced techniques
│   ├── calibration_example.py        # Calibrate to historical data
│   ├── uncertainty_quantification.py # Parameter uncertainty analysis
│   └── parallel_scenarios.py         # Run multiple scenarios in parallel
└── notebooks/                         # Jupyter notebooks
    ├── 01_getting_started.ipynb      # Interactive tutorial
    ├── 02_data_exploration.ipynb     # Explore output data
    ├── 03_model_comparison.ipynb     # Compare SI/SIR/SEIR
    └── 04_custom_analysis.ipynb      # End-to-end custom analysis
```

## Example Descriptions

### Basic Examples

#### 01_quick_start.sh
```shell
#!/bin/bash
# Simplest possible laser-init workflow
# Downloads data for Nigeria at district level and runs model

laser-init NGA 2 2010 2020
cd NGA/2010
python3 ./seir.py
```

**Learning objectives**:
- Understand basic command syntax
- See what files are generated
- Run a simulation

#### 02_data_source_comparison.sh
```shell
#!/bin/bash
# Compare different shapefile sources for the same country

# UNOCHA (humanitarian focus)
laser-init MWI 2 2015 2020 --shape-source unocha --output-dir MWI/unocha

# geoBoundaries (academic)
laser-init MWI 2 2015 2020 --shape-source geoboundaries --output-dir MWI/geoboundaries

# GADM (comprehensive)
laser-init MWI 2 2015 2020 --shape-source gadm --output-dir MWI/gadm

# Compare population maps
echo "Comparing population distributions..."
python3 compare_sources.py MWI/*/2015/*.gpkg
```

**Learning objectives**:
- Understand data source differences
- See impact of source choice on results
- Learn when to use each source

#### 03_custom_parameters.sh
```shell
#!/bin/bash
# Generate model with custom parameters

laser-init KEN 2 2015 2020

# Edit parameters
cd KEN/2015
sed -i 's/r0: 2.5/r0: 4.0/' config.yaml
sed -i 's/infectious-duration-mean: 7.0/infectious-duration-mean: 5.0/' config.yaml

# Run with custom parameters
python3 ./seir.py

echo "Simulation complete with R0=4.0, duration=5 days"
```

**Learning objectives**:
- Modify model parameters
- Understand parameter effects
- Iterate on model runs

### Workflows

#### multi_country_analysis.sh
```shell
#!/bin/bash
# Analyze multiple countries in West Africa

countries=("NGA" "GHA" "SEN" "CIV" "MLI")
level=2
start_year=2010
end_year=2020

for country in "${countries[@]}"; do
    echo "Processing $country..."
    laser-init "$country" "$level" "$start_year" "$end_year" \
        --output-dir "west_africa/$country/$start_year"

    # Run model
    cd "west_africa/$country/$start_year"
    python3 ./seir.py
    cd -
done

# Generate comparative report
python3 generate_regional_report.py west_africa/
```

**Learning objectives**:
- Batch processing
- Regional analysis
- Comparative epidemiology

#### time_series_comparison.py
```python
"""Compare population and demographics across time periods."""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load data from different time periods
periods = [2000, 2010, 2020]
data = {}

for year in periods:
    gdf = gpd.read_file(f"PAK/{year}/PAK_admin2.gpkg")
    data[year] = gdf

# Calculate population growth
growth = pd.DataFrame({
    year: data[year].groupby("name")["population"].sum()
    for year in periods
})

# Plot growth rates
growth_pct = growth.pct_change(axis=1) * 100
growth_pct.plot(kind="box", title="Population Growth by District (%)")
plt.ylabel("Growth Rate (%)")
plt.savefig("population_growth_analysis.png")

print(f"National population growth 2000-2020: {growth.sum().pct_change().iloc[-1]*100:.1f}%")
```

**Learning objectives**:
- Temporal analysis
- Population growth patterns
- Long-term demographic changes

#### sensitivity_analysis.py
```python
"""Run sensitivity analysis on key model parameters."""

import subprocess
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Generate base model
subprocess.run(["laser-init", "ETH", "2", "2015", "2020"])

# Parameter ranges to test
r0_values = [1.5, 2.0, 2.5, 3.0, 4.0]
duration_values = [5, 7, 10, 14]

results = []

for r0 in r0_values:
    for duration in duration_values:
        # Create scenario directory
        scenario_dir = Path(f"ETH/2015/scenarios/r0_{r0}_dur_{duration}")
        scenario_dir.mkdir(parents=True, exist_ok=True)

        # Copy files and modify config
        # ... (implementation details)

        # Run model
        subprocess.run(["python", "seir.py"], cwd=scenario_dir)

        # Extract results
        # ... (parse output)

        results.append({
            "r0": r0,
            "duration": duration,
            "peak_day": peak_day,
            "attack_rate": attack_rate
        })

# Visualize sensitivity
results_df = pd.DataFrame(results)
pivot = results_df.pivot(index="r0", columns="duration", values="attack_rate")
plt.figure(figsize=(10, 6))
plt.imshow(pivot, cmap="RdYlGn_r", aspect="auto")
plt.colorbar(label="Attack Rate")
plt.title("Sensitivity Analysis: Attack Rate by R0 and Duration")
plt.xlabel("Infectious Duration (days)")
plt.ylabel("R0")
plt.savefig("sensitivity_analysis.png")
```

**Learning objectives**:
- Parameter uncertainty
- Sensitivity analysis
- Scenario planning

### Data Integration

#### geopackage_analysis.py
```python
"""Detailed analysis of GeoPackage output."""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# Load GeoPackage
gdf = gpd.read_file("NGA/2010/NGA_admin2.gpkg")

# Summary statistics
print(f"Total districts: {len(gdf)}")
print(f"Total population: {gdf.population.sum():,.0f}")
print(f"Population density (per km²): {gdf.population.sum() / (gdf.geometry.area.sum() / 1e6):,.1f}")

# Find population extremes
print(f"\nMost populous: {gdf.nlargest(5, 'population')[['name', 'population']]}")
print(f"\nLeast populous: {gdf.nsmallest(5, 'population')[['name', 'population']]}")

# Calculate density
gdf["area_km2"] = gdf.geometry.area / 1e6
gdf["density"] = gdf.population / gdf.area_km2

# Plot distribution
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

gdf.plot(column="population", ax=axes[0], legend=True, cmap="YlOrRd")
axes[0].set_title("Population")
axes[0].axis("off")

gdf.plot(column="density", ax=axes[1], legend=True, cmap="plasma")
axes[1].set_title("Density (per km²)")
axes[1].axis("off")

gdf.plot(column="area_km2", ax=axes[2], legend=True, cmap="viridis")
axes[2].set_title("Area (km²)")
axes[2].axis("off")

plt.tight_layout()
plt.savefig("geospatial_analysis.png")
```

**Learning objectives**:
- Load and analyze GeoPackage
- Spatial statistics
- Custom visualizations

#### custom_visualization.py
```python
"""Create publication-quality visualizations."""

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import contextily as cx

# Load data
gdf = gpd.read_file("KEN/2015/KEN_admin2.gpkg")

# Reproject for basemap
gdf_web = gdf.to_crs(epsg=3857)

# Create figure
fig, ax = plt.subplots(figsize=(12, 10))

# Plot population with log scale
gdf_web.plot(
    column="population",
    ax=ax,
    legend=True,
    cmap="YlOrRd",
    edgecolor="black",
    linewidth=0.5,
    norm=LogNorm(vmin=gdf.population.min(), vmax=gdf.population.max()),
    legend_kwds={"label": "Population (log scale)"}
)

# Add basemap
cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, alpha=0.5)

# Styling
ax.set_title("Kenya Population Distribution (2015)", fontsize=16, fontweight="bold")
ax.axis("off")

plt.tight_layout()
plt.savefig("kenya_population_publication.png", dpi=300, bbox_inches="tight")
```

**Learning objectives**:
- Publication-quality figures
- Basemap integration
- Advanced matplotlib

### Model Customization

#### add_vaccination.py
```python
"""Add vaccination campaign to SEIR model."""

# (Copy of SEIR model with vaccination intervention added)
# Full working example with detailed comments

class VaccinationCampaign:
    """Implements a vaccination campaign intervention.

    Args:
        model: LASER model instance
        start_day: Day to begin vaccination
        daily_rate: Fraction of susceptibles vaccinated per day
        efficacy: Vaccine efficacy (0-1)
        target_coverage: Stop when this fraction is vaccinated
    """
    def __init__(self, model, start_day, daily_rate, efficacy, target_coverage):
        self.model = model
        self.start_day = start_day
        self.daily_rate = daily_rate
        self.efficacy = efficacy
        self.target_coverage = target_coverage
        self.total_vaccinated = 0

    def apply(self):
        if self.model.tick < self.start_day:
            return

        current_coverage = self.total_vaccinated / self.model.scenario.population.sum()
        if current_coverage >= self.target_coverage:
            return

        # Vaccinate fraction of remaining susceptibles
        to_vaccinate = (self.model.scenario.S * self.daily_rate).astype(int)
        effective = (to_vaccinate * self.efficacy).astype(int)

        self.model.scenario.S -= effective
        self.model.scenario.R += effective
        self.total_vaccinated += effective.sum()

# Add to model
vaccination = VaccinationCampaign(
    model,
    start_day=180,  # Start at day 180
    daily_rate=0.01,  # Vaccinate 1% of susceptibles per day
    efficacy=0.9,  # 90% effective
    target_coverage=0.7  # Stop at 70% coverage
)
model.components.append(vaccination)
```

**Learning objectives**:
- Intervention modeling
- Custom LASER components
- Vaccination campaigns

### Advanced Examples

#### calibration_example.py
```python
"""Calibrate model parameters to historical outbreak data."""

import numpy as np
from scipy.optimize import minimize
from pathlib import Path

# Load historical data
historical_cases = pd.read_csv("historical_ebola_cases.csv")

def run_model(r0, duration):
    """Run model with given parameters and return simulated cases."""
    # Modify config, run model, extract results
    # ...
    return simulated_cases

def objective(params):
    """Objective function: sum of squared errors."""
    r0, duration = params
    simulated = run_model(r0, duration)

    # Compare to historical data
    error = np.sum((simulated - historical_cases.values) ** 2)
    return error

# Calibrate
initial_guess = [2.5, 10.0]
bounds = [(1.0, 5.0), (5.0, 20.0)]

result = minimize(
    objective,
    initial_guess,
    method="L-BFGS-B",
    bounds=bounds
)

print(f"Calibrated R0: {result.x[0]:.2f}")
print(f"Calibrated duration: {result.x[1]:.1f} days")
print(f"Final error: {result.fun:.2f}")
```

**Learning objectives**:
- Model calibration
- Optimization techniques
- Historical data fitting

## Implementation Plan

> **Status: implemented.** The examples were built and corrected against the real
> CLI and `laser-generic` API (the snippets above are the original plan and may
> differ from what shipped). See **Implementation notes & deviations** below.

### Phase 1: Basic Examples — DONE
- [x] Create examples directory structure
- [x] Write basic/ examples (01-03)
- [x] Test all basic examples (`bash -n`; the CLI path was verified end to end)
- [x] Write examples/README.md

### Phase 2: Workflows — DONE
- [x] Implement multi_country_analysis.sh
- [x] Implement time_series_comparison.py (verified end to end)
- [x] Implement sensitivity_analysis.py
- [x] Add supporting utilities — done inline (replaced the plan's undefined
      `compare_sources.py` / `generate_regional_report.py` with in-script logic)

### Phase 3: Data Integration — DONE
- [x] Implement geopackage_analysis.py
- [x] Implement custom_visualization.py (matplotlib only; `contextily` shown as an
      optional snippet rather than a dependency)
- [x] Implement export_to_qgis.py
- [x] Add sample data if needed — decided **against** bundling; examples generate
      data on demand via `laser-init` (documented in the examples README)

### Phase 4: Model Customization — PARTIAL (2 of 4)
- [ ] Implement add_vaccination.py — **omitted**: `laser-generic`'s
      `ImmunizationCampaign`/`RoutineImmunization` use the legacy `__call__(model, tick)`
      protocol and a per-agent `susceptibility` model, so they don't run with the
      generated S/E/I/R model. Upstream issue drafted in `tmp/lg-issue.md`; revisit
      when fixed.
- [x] Implement social_distancing.py (verified end to end; uses the `Transmission`
      seasonality multiplier)
- [ ] Implement age_structured_seir.py — **omitted**: laser-generic is already
      per-agent/age-based and exposes no contact-matrix/age-stratified construct, so no
      non-speculative example was possible.
- [x] Implement seirs_waning_immunity.py (verified end to end)

### Phase 5: Advanced Examples — DONE
- [x] Implement calibration_example.py (numpy bisection — no scipy; `scipy` is not a
      project dependency)
- [x] Implement uncertainty_quantification.py
- [x] Implement parallel_scenarios.py (verified end to end)
- [x] Performance optimization — kept runs tractable via `nyears`, small grids/samples,
      and a `ProcessPoolExecutor`; added a shared `_common.run_scenario` that extracts
      metrics directly from `model.nodes` (the generated `seir.py` emits only plots)

### Phase 6: Notebooks — DONE
- [x] Create Jupyter notebooks (01-04)
- [ ] Add interactive widgets — skipped (out of scope; kept notebooks dependency-light)
- [x] Test notebooks — verified by code (all cells compile; notebook 02 and the model
      builder in 03 run), since Jupyter is not installed in this environment
- [ ] Add binder/colab links — skipped (see Future Enhancements)

### Phase 7: Documentation & Polish — DONE
- [x] Write comprehensive examples/README.md (learning progression + per-section tables)
- [x] Add comments and docstrings (module docstrings + learning objectives; notebook markdown)
- [x] Create example data directory — reframed as an "Example data" note: data is
      generated on demand, not bundled (keeps examples in sync with the data sources)
- [x] Update main README to link to examples
- [x] CI/CD for testing examples — the CI lint job runs `ruff` over `examples/`,
      compiles every script, and validates notebooks as nbformat-v4 JSON (static only;
      full execution is too heavy/network-dependent for CI)

## Implementation notes & deviations

- **Corrected against reality:** the original snippets had bugs (hyphenated config keys,
  `--output-dir` path assumptions, `.area` on EPSG:4326, a `seir.py --config` crash that
  was fixed in the package, and speculative model/optimizer APIs). The shipped examples
  use the real CLI behavior, the verified `laser-generic` API, and only the project's own
  dependencies (no `contextily`, no `scipy`).
- **Two examples omitted** (`add_vaccination.py`, `age_structured_seir.py`) — see Phase 4.
- **Shared helpers:** `model_customization/_common.py` and `advanced/_common.py` reproduce
  the generated `seir.py` setup so examples express only what they customize.

## Success Criteria

- [~] All examples run without errors — verified by representative end-to-end runs
      (parallel_scenarios, time_series_comparison, social_distancing, seirs_waning,
      notebook 02 + the 03 model builder, `run_scenario`) plus static checks on the rest;
      not every example was exhaustively executed (full runs are large downloads + long
      LASER simulations)
- [x] Clear learning progression (basic → advanced)
- [x] Well-commented code
- [x] Comprehensive README with learning objectives
- [x] Examples tested in CI (static: lint + compile + notebook validity)
- [x] Notebooks render correctly on GitHub (valid nbformat-v4 JSON)
- [x] Example data included or downloadable (downloadable/generated on demand)

## Future Enhancements

- Interactive web demos (Streamlit/Dash)
- Video tutorials
- Binder integration for notebooks
- Example gallery website
- Community-contributed examples

---

**Created**: March 2026
**Status**: Implemented (2026-06-17) — all phases complete except two intentionally
omitted Phase 4 examples (`add_vaccination.py`, `age_structured_seir.py`); see the
Implementation Plan notes.
**Priority**: Medium (after core documentation complete)
