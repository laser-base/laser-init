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

## More examples

Additional data-integration and model-customization examples are planned.
Contributions are welcome — see the [contributing guide](../docs/contributing.md).
