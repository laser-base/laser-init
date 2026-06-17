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

## Advanced examples

Techniques that run the model many times and extract scalar outcomes (peak
timing, peak size, attack rate) from `model.nodes.S/E/I/R`. They share
`_common.py`, whose `run_scenario(base, overrides, nyears)` builds and runs a SEIR
model with parameter overrides and returns summary metrics.

| Script | What it shows |
| --- | --- |
| [`advanced/uncertainty_quantification.py`](advanced/uncertainty_quantification.py) | Monte Carlo: sample R0, run the model per draw, summarize the attack-rate / peak distribution. |
| [`advanced/calibration_example.py`](advanced/calibration_example.py) | Calibrate R0 to a target attack rate with a bounded (bisection) search — numpy only, no scipy. |
| [`advanced/parallel_scenarios.py`](advanced/parallel_scenarios.py) | Run a grid of scenarios across worker processes with `ProcessPoolExecutor`. |

Each of these runs the full LASER model multiple times, so they are the
heaviest examples here. Reduce the sample count / grid / `NYEARS` (or choose a
smaller country) to try them quickly, and keep `MAX_WORKERS` small in the
parallel example since each worker holds a full model in memory.

## Notebooks

Interactive Jupyter notebooks that walk through the same material:

| Notebook | What it covers |
| --- | --- |
| [`notebooks/01_getting_started.ipynb`](notebooks/01_getting_started.ipynb) | Generate a dataset, inspect the outputs, and run the model. |
| [`notebooks/02_data_exploration.ipynb`](notebooks/02_data_exploration.ipynb) | Explore the GeoPackage and demographic CSVs with maps and plots. |
| [`notebooks/03_model_comparison.ipynb`](notebooks/03_model_comparison.ipynb) | Build and run SI / SIR / SEIR on the same data and overlay the infectious curves. |
| [`notebooks/04_custom_analysis.ipynb`](notebooks/04_custom_analysis.ipynb) | End-to-end: generate, sweep R0 with `run_scenario`, and compare outcomes. |

Jupyter isn't a project dependency. Run the notebooks with, e.g.:

```shell
uv run --with jupyter jupyter lab examples/notebooks
```

Run them from the `examples/notebooks/` directory (notebook 04 imports the shared
helper from `../advanced/`). Like the scripts, they generate data on first run and
the model-running notebooks (01, 03, 04) are compute-heavy — pick a smaller
`COUNTRY` or fewer years to try them quickly.

## More examples

Contributions are welcome — see the [contributing guide](../docs/contributing.md).
