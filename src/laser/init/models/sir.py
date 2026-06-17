import importlib.util
from pathlib import Path

import click
import geopandas as gpd
import laser.core.distributions as dists
import numpy as np
import pandas as pd
import yaml
from laser.core import PropertySet
from laser.core.demographics import AliasedDistribution, KaplanMeierEstimator
from laser.generic import SIR, Model
from laser.generic.utils import ValuesMap
from laser.generic.vitaldynamics import BirthsByCBR, MortalityByEstimator

spec = importlib.util.spec_from_file_location("module_name", Path(__file__).parent / "plot.py")
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)


@click.command()
@click.option(
    "-c",
    "--config",
    "config_file",
    type=click.Path(exists=True, path_type=Path),
    default=Path(__file__).parent / "config.yaml",
    help="Path to the configuration YAML file.",
)
@click.option(
    "-d",
    "--data-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to the data directory.",
)
def main(config_file: Path, data_dir: Path) -> None:
    """Run an SIR (Susceptible-Infectious-Recovered) epidemiological model.

    Loads configuration and data files, sets up the model with vital dynamics
    (births and mortality), runs the simulation, and generates output plots.

    Args:
        config_file: Path to the YAML configuration file.
        data_dir: Path to the data directory, or None to use config value.

    Returns:
        None

    Raises:
        click.exceptions.ClickException: If config_file or data_dir paths are invalid.
        KeyError: If required configuration keys are missing.
        FileNotFoundError: If data files specified in config cannot be found.
    """
    config = yaml.safe_load(config_file.read_text())

    data_dir = Path(data_dir or config["data_dir"])
    datafiles = config["datafiles"]
    scenario = gpd.read_file(data_dir / datafiles["shape_data"])
    cxr_df = pd.read_csv(data_dir / datafiles["cxr_data"])  # "cxr.csv")
    pop_df = pd.read_csv(data_dir / datafiles["pop_data"])  # "age_dist.csv")
    exp_df = pd.read_csv(data_dir / datafiles["exp_data"])  # "life_exp.csv")

    params = PropertySet(config["simulation"])
    params += {"nticks": params.nyears * 365, "beta": params.r0 / params.infectious_duration_mean}

    scenario["nodeid"] = np.arange(len(scenario), dtype=np.int32)
    scenario["S"] = scenario.population
    scenario["I"] = 0
    # seed the largest population center with some initial infections
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

    infdist = dists.normal(loc=params.infectious_duration_mean, scale=2)

    s = SIR.Susceptible(model)
    i = SIR.Infectious(model, infdist)
    r = SIR.Recovered(model)
    tx = SIR.Transmission(model, infdist)

    pyramid = AliasedDistribution(pop_df.PopTotal.to_numpy())
    survival = KaplanMeierEstimator(exp_df.cumulative_deaths.to_numpy())

    births = BirthsByCBR(model, birthrates, pyramid)
    mortality = MortalityByEstimator(model, survival)
    model.components = [s, i, r, tx, births, mortality]

    model.run()

    plot.show_plots(model, output_dir=Path(__file__).parent, name="sir")

    return


if __name__ == "__main__":
    main()
