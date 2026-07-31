#!/usr/bin/env python3
"""Propagate parameter uncertainty through the model (Monte Carlo).

Samples R0 from a distribution, runs the SEIR model once per draw, and summarizes
the resulting attack-rate and peak-timing distributions, saving a scatter plus a
histogram.

Learning objectives:
    - Monte Carlo propagation of input uncertainty
    - Extracting scalar outcomes from a model run (see _common.metrics)
    - Summarizing an output distribution

Compute-heavy: runs the model once per sample. Reduce ``N_SAMPLES`` / ``NYEARS``
(or pick a smaller country) to try it quickly. Requires ``laser-init`` on ``PATH``
(network on first run). The model is stochastic, so results vary between runs.
"""

import _common  # sibling helper module (examples/advanced/_common.py)
import matplotlib.pyplot as plt
import numpy as np

COUNTRY = "ETH"
LEVEL = 2
START_YEAR = 2015
END_YEAR = 2017
NYEARS = 1
N_SAMPLES = 6
R0_MEAN = 2.5
R0_SD = 0.5
SEED = 20240617


def main() -> None:
    base = _common.ensure_data(COUNTRY, LEVEL, START_YEAR, END_YEAR)

    rng = np.random.default_rng(SEED)
    r0_samples = rng.normal(R0_MEAN, R0_SD, size=N_SAMPLES).clip(1.1, 6.0)

    results = []
    for k, r0 in enumerate(r0_samples, start=1):
        print(f"[{k}/{N_SAMPLES}] R0={r0:.2f} ...")
        result = _common.run_scenario(base, overrides={"r0": float(r0)}, nyears=NYEARS)
        result["r0"] = float(r0)
        results.append(result)

    attack = np.array([r["attack_rate"] for r in results])
    peak_day = np.array([r["peak_day"] for r in results])
    print(
        f"\nAttack rate: mean={attack.mean():.3f}, "
        f"90% interval=[{np.percentile(attack, 5):.3f}, {np.percentile(attack, 95):.3f}]"
    )
    print(f"Peak day:    mean={peak_day.mean():.0f}, range=[{peak_day.min()}, {peak_day.max()}]")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.scatter([r["r0"] for r in results], attack)
    ax1.set_xlabel("R0")
    ax1.set_ylabel("attack rate")
    ax1.set_title("Attack rate vs sampled R0")
    ax2.hist(attack, bins=min(10, N_SAMPLES))
    ax2.set_xlabel("attack rate")
    ax2.set_ylabel("count")
    ax2.set_title("Attack-rate distribution")
    fig.tight_layout()
    out = base / "uncertainty_quantification.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
