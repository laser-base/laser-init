#!/usr/bin/env python3
"""Run a grid of scenarios in parallel processes.

Each worker process builds and runs a full SEIR model for one parameter set and
returns summary metrics, demonstrating an embarrassingly-parallel scenario sweep.

Learning objectives:
    - Parallelizing independent model runs with ``ProcessPoolExecutor``
    - A picklable, top-level worker that rebuilds from a directory path
    - Aggregating parallel results

Resource note: each worker builds a full LASER model (itself multithreaded and
memory-heavy), so process parallelism multiplies memory use. Keep ``MAX_WORKERS``
small (2 is a safe default). Compute-heavy; requires ``laser-init`` on ``PATH``
(network on first run).
"""

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import _common  # sibling helper module (examples/advanced/_common.py)

COUNTRY = "ETH"
LEVEL = 2
START_YEAR = 2015
END_YEAR = 2017
NYEARS = 1
R0_GRID = [1.5, 2.0, 2.5, 3.0]
MAX_WORKERS = 2

BASE = Path(COUNTRY) / str(START_YEAR)


def run_one(r0: float) -> dict:
    """Worker: run one scenario and return its metrics.

    Must be a top-level function so it is picklable for the process pool; it
    rebuilds everything from the (already-generated) BASE directory.
    """
    result = _common.run_scenario(BASE, overrides={"r0": r0}, nyears=NYEARS)
    result["r0"] = r0
    return result


def main() -> None:
    # Generate the base dataset once, before fanning out to workers.
    _common.ensure_data(COUNTRY, LEVEL, START_YEAR, END_YEAR)

    workers = min(MAX_WORKERS, len(R0_GRID), os.cpu_count() or 1)
    print(f"Running {len(R0_GRID)} scenarios with {workers} worker process(es)...")
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(run_one, R0_GRID))

    print(f"\n{'R0':>5} {'attack_rate':>12} {'peak_day':>9} {'peak_infectious':>16}")
    for r in sorted(results, key=lambda x: x["r0"]):
        print(
            f"{r['r0']:5.1f} {r['attack_rate']:12.3f} "
            f"{r['peak_day']:9d} {r['peak_infectious']:16,d}"
        )


if __name__ == "__main__":
    main()
