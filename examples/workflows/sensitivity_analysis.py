#!/usr/bin/env python3
"""Parameter sweep over R0 and infectious duration for one country.

Generates one base dataset and model, then runs the generated SEIR model for a
grid of ``(r0, infectious_duration_mean)`` values by writing a per-scenario
config and collecting each run's output PDF.

Learning objectives:
    - Parameter sweeps / scenario planning
    - Reusing one dataset across many model runs via ``seir.py --config``
    - Organizing per-scenario outputs

Note: the generated ``seir.py`` produces plots (``seir_output.pdf`` and PNGs),
not summary metrics. Extracting scalar outcomes (attack rate, peak timing) would
require instrumenting the model; this example demonstrates the sweep-and-collect
pattern. Each grid point runs a full simulation, so this is compute-heavy —
shrink ``R0_VALUES`` / ``DURATION_VALUES`` to try it quickly.

Requires ``laser-init`` on ``PATH`` and a network connection for the initial
download.
"""

import shutil
import subprocess
from pathlib import Path

import yaml

COUNTRY = "ETH"
LEVEL = 2
START_YEAR = 2015
END_YEAR = 2017
R0_VALUES = [1.5, 2.5, 4.0]
DURATION_VALUES = [5.0, 10.0]

BASE = Path(COUNTRY) / str(START_YEAR)


def main() -> None:
    # 1. Generate the base dataset + model once (default output dir is ./<ISO>/<start>).
    if not (BASE / "config.yaml").exists():
        subprocess.run(
            ["laser-init", COUNTRY, str(LEVEL), str(START_YEAR), str(END_YEAR)],
            check=True,
        )

    base_config = yaml.safe_load((BASE / "config.yaml").read_text())
    scenarios_dir = BASE / "scenarios"
    scenarios_dir.mkdir(exist_ok=True)

    # 2. Sweep: write a config per combination, run the model, collect its PDF.
    #    The base config's data_dir is absolute, so each scenario reads the same
    #    data; only the simulation parameters change.
    for r0 in R0_VALUES:
        for duration in DURATION_VALUES:
            tag = f"r0_{r0}_dur_{duration}"
            config = dict(base_config)
            config["simulation"] = {
                **base_config["simulation"],
                "r0": r0,
                "infectious_duration_mean": duration,
            }
            cfg_path = scenarios_dir / f"{tag}.yaml"
            cfg_path.write_text(yaml.safe_dump(config))

            print(f"Running scenario {tag} ...")
            subprocess.run(
                ["python3", "./seir.py", "--config", str(cfg_path.resolve())],
                cwd=BASE,
                check=True,
            )

            # seir.py writes seir_output.pdf next to itself; collect it per scenario.
            produced = BASE / "seir_output.pdf"
            if produced.exists():
                shutil.move(str(produced), str(scenarios_dir / f"{tag}.pdf"))

    print(f"\nScenario outputs in: {scenarios_dir}")


if __name__ == "__main__":
    main()
