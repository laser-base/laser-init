"""Shared helpers for the model-customization examples.

These helpers reproduce the model setup from the generated ``seir.py`` (loading
the config and data, building the scenario and parameters, and creating the
vital-dynamics components) so each example only has to express the part it
customizes.

Running a model-customization example regenerates the base dataset with
``laser-init`` if needed, then builds and runs a LASER model — so these examples
require a network connection on first use and are compute-heavy.
"""

import importlib.util
import subprocess
from pathlib import Path

import geopandas as gpd
import laser.core.distributions as dists
import numpy as np
import pandas as pd
import yaml
from laser.core import PropertySet
from laser.core.demographics import AliasedDistribution, KaplanMeierEstimator
from laser.generic import Model
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


def load_base(base: Path, nyears: int | None = None) -> dict:
    """Build a Model plus vital dynamics from a laser-init output directory.

    Mirrors the generated ``seir.py`` setup but stops short of adding the disease
    (compartment/transmission) components, so each example can supply those.

    Args:
        base: A laser-init output directory containing config.yaml and data files.
        nyears: Optional override for the simulated number of years (useful for
            quick runs); defaults to the value in config.yaml.

    Returns:
        A dict with keys: ``model``, ``scenario``, ``params``, ``expdist``,
        ``infdist``, ``births``, ``mortality``.
    """
    config = yaml.safe_load((base / "config.yaml").read_text())
    if nyears is not None:
        config["simulation"]["nyears"] = nyears

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
    # Seed the largest population center with some initial infections.
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

    return {
        "model": model,
        "scenario": scenario,
        "params": params,
        "expdist": expdist,
        "infdist": infdist,
        "births": births,
        "mortality": mortality,
    }


def show(model, base: Path, name: str):
    """Render the standard plots using the plot.py copied into ``base``."""
    spec = importlib.util.spec_from_file_location("generated_plot", base / "plot.py")
    plot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plot)
    return plot.show_plots(model, output_dir=base, name=name)
