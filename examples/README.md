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

## More examples

Additional workflow, data-integration, and model-customization examples are
planned. Contributions are welcome — see the
[contributing guide](../docs/contributing.md).
