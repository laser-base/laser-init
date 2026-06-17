#!/usr/bin/env python3
"""SEIRS model with waning immunity.

Swaps the SEIR components for laser-generic's ``SEIRS`` components, where
recovered agents lose immunity after a waning period and return to the
susceptible pool (R -> S). The waning duration is drawn from a distribution.

Learning objectives:
    - Switch model structure (SEIR -> SEIRS) by changing components
    - Supply a waning-duration distribution
    - Reuse the same data and vital-dynamics setup across model variants

Requires ``laser-init`` on ``PATH`` (network access on first run) and runs a full
LASER simulation, so it is compute-heavy.
"""

import _common  # sibling helper module (examples/model_customization/_common.py)
import laser.core.distributions as dists
from laser.generic import SEIRS

COUNTRY = "NGA"
LEVEL = 2
START_YEAR = 2010
END_YEAR = 2015

# Mean duration of immunity before it wanes (ticks/days); ~1 year here.
WANING_MEAN_DAYS = 365
WANING_SD_DAYS = 60


def main() -> None:
    base = _common.ensure_data(COUNTRY, LEVEL, START_YEAR, END_YEAR)
    ctx = _common.load_base(base)
    model = ctx["model"]

    # Distribution of how long immunity lasts before waning (R -> S).
    wandist = dists.normal(loc=WANING_MEAN_DAYS, scale=WANING_SD_DAYS)

    s = SEIRS.Susceptible(model)
    e = SEIRS.Exposed(model, ctx["expdist"], ctx["infdist"])
    i = SEIRS.Infectious(model, ctx["infdist"], wandist)
    r = SEIRS.Recovered(model, wandist)
    tx = SEIRS.Transmission(model, ctx["expdist"])

    model.components = [s, e, i, r, tx, ctx["births"], ctx["mortality"]]
    model.run()

    out = _common.show(model, base, "seirs_waning_immunity")
    print(f"Done. Output written to {out}")


if __name__ == "__main__":
    main()
