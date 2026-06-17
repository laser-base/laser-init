# laser-init examples

Ready-to-run examples demonstrating common `laser-init` workflows.

## Prerequisites

- `laser-init` installed and on your `PATH` (see the project
  [README](../README.md) or [installation guide](../docs/installation.md)).
- A network connection — the examples download administrative boundary,
  population, and demographic data on first run. Data is cached afterwards; see
  the [configuration docs](../docs/configuration.md) for the cache location.
- Run the scripts from a directory where you're happy to have output
  directories created (the examples write into the current working directory).

## Basic examples

| Script | What it shows |
| --- | --- |
| [`basic/01_quick_start.sh`](basic/01_quick_start.sh) | The simplest end-to-end workflow: generate a SEIR model for Nigeria and run it. |
| [`basic/02_data_source_comparison.sh`](basic/02_data_source_comparison.sh) | Generate the same country/level from each boundary source (UNOCHA, geoBoundaries, GADM) for comparison. |
| [`basic/03_custom_parameters.sh`](basic/03_custom_parameters.sh) | Edit the generated `config.yaml` (R0, infectious duration) and re-run. |

Run an example from the repository root, for example:

```shell
bash examples/basic/01_quick_start.sh
```

## Workflow examples

Longer, end-to-end workflows that drive `laser-init` across multiple runs:

| Script | What it shows |
| --- | --- |
| [`workflows/multi_country_analysis.sh`](workflows/multi_country_analysis.sh) | Batch-generate and run models for several countries, then summarize population across them. |
| [`workflows/time_series_comparison.py`](workflows/time_series_comparison.py) | Generate the same country across multiple snapshot years and compare district/national population over time. |
| [`workflows/sensitivity_analysis.py`](workflows/sensitivity_analysis.py) | Sweep R0 and infectious duration over one dataset, collecting each scenario's output. |

The `.py` workflows are run with `python3`, e.g.:

```shell
python3 examples/workflows/time_series_comparison.py
```

These workflows generate (and, in some cases, run) models for multiple
countries/years/parameter sets, so they download more data and take longer than
the basic examples. Each script notes how to trim its scope to try it quickly.

## Data integration examples

Working with the GeoPackage output in Python and other GIS tools:

| Script | What it shows |
| --- | --- |
| [`data_integration/geopackage_analysis.py`](data_integration/geopackage_analysis.py) | Load a GeoPackage, compute population statistics and density (with correct equal-area area calculation), and save multi-panel maps. |
| [`data_integration/custom_visualization.py`](data_integration/custom_visualization.py) | Produce a publication-quality, log-scaled population choropleth with matplotlib only. |
| [`data_integration/export_to_qgis.py`](data_integration/export_to_qgis.py) | Enrich the GeoPackage with area/density/rank attributes and write a QGIS-ready layer. |

These read the GeoPackage that `laser-init` produces (generating it once into
`./NGA/2010` if needed); they do not run the epidemiological model. Note that the
GeoPackage is in EPSG:4326, so area and density are computed after reprojecting to
an equal-area CRS.

## Model customization examples

Change the generated model's structure or dynamics using laser-generic
components. These build and run a full LASER simulation, so they are
compute-heavy; they share `_common.py`, which reproduces the generated `seir.py`
setup (data loading, scenario, vital dynamics) so each example only expresses its
customization.

| Script | What it shows |
| --- | --- |
| [`model_customization/social_distancing.py`](model_customization/social_distancing.py) | Reduce transmission during a window using the `Transmission` component's `seasonality` multiplier. |
| [`model_customization/seirs_waning_immunity.py`](model_customization/seirs_waning_immunity.py) | Switch SEIR → SEIRS so immunity wanes (R → S) after a drawn duration. |

> **Note on vaccination:** laser-generic ships `ImmunizationCampaign` /
> `RoutineImmunization` components, but they target a model formulation with a
> per-agent `susceptibility` property and use the classic `__call__(model, tick)`
> component protocol, whereas the generated S/E/I/R model uses compartment
> components driven by `step(tick)`. They therefore don't drop into the generated
> model without changes, so a vaccination example is intentionally omitted rather
> than shipped in a form that doesn't run. Initial/standing immunity can instead be
> set at setup via the scenario's `R` column (see `naive_population` in the config).

## More examples

Advanced examples (calibration, uncertainty quantification, parallel scenarios)
and notebooks are planned. Contributions are welcome — see the
[contributing guide](../docs/contributing.md).
