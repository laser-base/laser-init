"""Shared helpers for the advanced examples.

Builds and runs a SEIR model from a laser-init output directory with optional
simulation-parameter overrides, and extracts scalar summary metrics (peak timing,
peak size, attack rate) from the model after the run. The generated ``seir.py``
only produces plots, so these helpers compute metrics directly from the model's
per-tick compartment arrays (``model.nodes.S/E/I/R``).

``run_scenario`` is a top-level function that rebuilds everything from a directory
path, so it is safe to call from worker processes (see parallel_scenarios.py).
"""

import subprocess
from pathlib import Path

import geopandas as gpd
import laser.core.distributions as dists
import numpy as np
import pandas as pd
import yaml
from laser.core import PropertySet
from laser.core.demographics import AliasedDistribution, KaplanMeierEstimator
from laser.generic import SEIR, Model
from laser.generic.utils import ValuesMap
from laser.generic.vitaldynamics import BirthsByCBR, MortalityByEstimator


def ensure_data(country: str, level: int, start_year: int, end_year: int) -> Path:
    """Generate the base dataset with laser-init if it does not already exist.

    Returns the output directory (``./<COUNTRY>/<start_year>``).
    """
    base = Path(country) / str(start_year)
    if not (base / "config.yaml").exists():
        subprocess.run(
            ["laser-init", country, str(level), str(start_year), str(end_year)],
            check=True,
        )
    return base


def metrics(model, total_population: int) -> dict:
    """Compute summary metrics from a finished model run.

    Returns a dict with ``peak_day``, ``peak_infectious``, ``attack_rate``, and
    ``total_population``.
    """
    s = np.asarray(model.nodes.S)
    i = np.asarray(model.nodes.I)
    infectious_over_time = i.sum(axis=1)
    infected = int(s[0].sum() - s[-1].sum())
    return {
        "peak_day": int(infectious_over_time.argmax()),
        "peak_infectious": int(infectious_over_time.max()),
        "attack_rate": (infected / total_population) if total_population else 0.0,
        "total_population": total_population,
    }


def run_scenario(base, overrides: dict | None = None, nyears: int | None = None) -> dict:
    """Build a SEIR model from ``base``, run it, and return summary metrics.

    Args:
        base: A laser-init output directory (path or str) with config.yaml + data.
        overrides: Optional simulation-parameter overrides, e.g. ``{"r0": 3.0}``.
        nyears: Optional override for the number of simulated years.

    Returns:
        The metrics dict from :func:`metrics`.
    """
    base = Path(base)
    config = yaml.safe_load((base / "config.yaml").read_text())
    if nyears is not None:
        config["simulation"]["nyears"] = nyears
    if overrides:
        config["simulation"].update(overrides)

    data_dir = Path(config["data_dir"])
    datafiles = config["datafiles"]
    scenario = gpd.read_file(data_dir / datafiles["shape_data"])
    cxr_df = pd.read_csv(data_dir / datafiles["cxr_data"])
    pop_df = pd.read_csv(data_dir / datafiles["pop_data"])
    exp_df = pd.read_csv(data_dir / datafiles["exp_data"])

    params = PropertySet(config["simulation"])
    params += {
        "nticks": params.nyears * 365,
        "beta": params.r0 / params.infectious_duration_mean,
    }

    scenario["nodeid"] = np.arange(len(scenario), dtype=np.int32)
    scenario["S"] = scenario.population
    scenario["E"] = 0
    scenario["I"] = 0
    imax = np.argmax(scenario.population)
    scenario.at[imax, "I"] = 50
    if params.naive_population:
        scenario["R"] = 0
    else:
        scenario["R"] = ((1 - 1 / params.r0) * scenario.population).astype(np.int32)
    scenario.S -= scenario.I + scenario.R

    cbr = cxr_df.CBR.to_numpy()
    if len(cbr) < params.nyears:
        cbr = np.pad(cbr, (0, params.nyears - len(cbr)), mode="edge")
    daily_cbr = np.repeat(cbr[0 : params.nyears], 365)
    birthrates = ValuesMap.from_timeseries(daily_cbr, len(scenario))

    model = Model(scenario, params, birthrates=birthrates)
    expdist = dists.gamma(shape=params.exposed_duration_shape, scale=params.exposed_duration_scale)
    infdist = dists.normal(loc=params.infectious_duration_mean, scale=2)
    pyramid = AliasedDistribution(pop_df.PopTotal.to_numpy())
    survival = KaplanMeierEstimator(exp_df.cumulative_deaths.to_numpy())
    births = BirthsByCBR(model, birthrates, pyramid)
    mortality = MortalityByEstimator(model, survival)
    model.components = [
        SEIR.Susceptible(model),
        SEIR.Exposed(model, expdist, infdist),
        SEIR.Infectious(model, infdist),
        SEIR.Recovered(model),
        SEIR.Transmission(model, expdist),
        births,
        mortality,
    ]
    model.run()

    return metrics(model, int(scenario.population.sum()))
