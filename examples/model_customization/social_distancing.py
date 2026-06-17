#!/usr/bin/env python3
"""Model a temporary "social distancing" reduction in transmission.

The SEIR ``Transmission`` component accepts a ``seasonality`` multiplier applied
to the force of infection each tick. Here it is used as a generic time-varying
transmission modifier: 1.0 normally, reduced during a distancing window.

Learning objectives:
    - Drive time-varying transmission with the ``seasonality`` argument
    - Build a per-tick multiplier with ``ValuesMap.from_timeseries``
    - Apply a non-pharmaceutical intervention without a custom component

Requires ``laser-init`` on ``PATH`` (network access on first run) and runs a full
LASER simulation, so it is compute-heavy.
"""

import _common  # sibling helper module (examples/model_customization/_common.py)
import numpy as np
from laser.generic import SEIR
from laser.generic.utils import ValuesMap

COUNTRY = "NGA"
LEVEL = 2
START_YEAR = 2010
END_YEAR = 2015

# Distancing window (in ticks/days) and the transmission multiplier during it.
DISTANCING_START = 120
DISTANCING_END = 240
DISTANCING_MULTIPLIER = 0.4


def main() -> None:
    base = _common.ensure_data(COUNTRY, LEVEL, START_YEAR, END_YEAR)
    ctx = _common.load_base(base)
    model = ctx["model"]
    nticks = int(ctx["params"].nticks)
    nnodes = len(ctx["scenario"])

    # 1.0 everywhere, reduced during the distancing window.
    multiplier = np.ones(nticks, dtype=np.float32)
    multiplier[DISTANCING_START:DISTANCING_END] = DISTANCING_MULTIPLIER
    seasonality = ValuesMap.from_timeseries(multiplier, nnodes, nticks)

    s = SEIR.Susceptible(model)
    e = SEIR.Exposed(model, ctx["expdist"], ctx["infdist"])
    i = SEIR.Infectious(model, ctx["infdist"])
    r = SEIR.Recovered(model)
    tx = SEIR.Transmission(model, ctx["expdist"], seasonality=seasonality)

    model.components = [s, e, i, r, tx, ctx["births"], ctx["mortality"]]
    model.run()

    out = _common.show(model, base, "seir_social_distancing")
    print(f"Done. Output written to {out}")


if __name__ == "__main__":
    main()
