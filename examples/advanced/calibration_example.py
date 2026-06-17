#!/usr/bin/env python3
"""Calibrate R0 to a target attack rate via a bounded (bisection) search.

To stay self-contained, the "observed" target attack rate is generated from a
known R0 (``TRUE_R0``); calibration then tries to recover it. Attack rate increases
monotonically with R0, so a bisection search converges. Uses only numpy + the model
(no scipy), keeping to the project's own dependencies.

Learning objectives:
    - Calibrating a parameter to a target output
    - Exploiting monotonicity for a robust 1-D search
    - The "model as a function" pattern

Compute-heavy: each search step runs the model once (so ~ITERATIONS + 1 runs). The
model is stochastic, so the recovered value is approximate. Requires ``laser-init``
on ``PATH`` (network on first run).
"""

import _common  # sibling helper module (examples/advanced/_common.py)

COUNTRY = "ETH"
LEVEL = 2
START_YEAR = 2015
END_YEAR = 2017
NYEARS = 1
TRUE_R0 = 3.0
R0_LOW = 1.2
R0_HIGH = 6.0
ITERATIONS = 7


def attack_rate(base, r0: float) -> float:
    """Run the model at the given R0 and return the attack rate."""
    return _common.run_scenario(base, overrides={"r0": r0}, nyears=NYEARS)["attack_rate"]


def main() -> None:
    base = _common.ensure_data(COUNTRY, LEVEL, START_YEAR, END_YEAR)

    # Synthetic "observation": the attack rate produced by the (unknown) true R0.
    target = attack_rate(base, TRUE_R0)
    print(f"Target attack rate (from true R0={TRUE_R0}): {target:.3f}\n")

    lo, hi = R0_LOW, R0_HIGH
    mid = (lo + hi) / 2
    for iteration in range(1, ITERATIONS + 1):
        mid = (lo + hi) / 2
        ar = attack_rate(base, mid)
        print(f"  iter {iteration}: R0={mid:.3f} -> attack_rate={ar:.3f}")
        if ar < target:
            lo = mid  # attack rate too low -> need a higher R0
        else:
            hi = mid

    print(
        f"\nRecovered R0 ~= {mid:.3f} (true value {TRUE_R0}); "
        f"final search interval [{lo:.3f}, {hi:.3f}]"
    )


if __name__ == "__main__":
    main()
