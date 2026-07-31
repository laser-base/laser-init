import importlib.util
from pathlib import Path

import click
import geopandas as gpd
import numpy as np
import pandas as pd
import polars as pl
import yaml
from laser.measles.abm import ABMModel, ABMParams, components
from laser.measles.components import create_component

spec = importlib.util.spec_from_file_location(
    "module_name", Path(__file__).parent / "measles_plot.py"
)
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)


@click.command()
@click.option(
    "-c",
    "--config",
    "config_file",
    type=click.Path(exists=True),
    default=Path(__file__).parent / "config.yaml",
    help="Path to the configuration YAML file.",
)
@click.option(
    "-d",
    "--data-dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to the data directory.",
)
def main(config_file: Path, data_dir: Path) -> None:
    """Run a measles ABM (Agent-Based Model) epidemiological simulation.

    Loads configuration and data files, constructs a spatial scenario from
    administrative boundaries, sets up the ABM with vital dynamics, disease
    transmission, and state tracking components, then runs the simulation
    and generates output plots.

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
    config = yaml.safe_load(Path(config_file).read_text())

    data_dir = Path(data_dir or config["data_dir"])
    datafiles = config["datafiles"]
    gdf = gpd.read_file(data_dir / datafiles["shape_data"])
    cxr_df = pd.read_csv(data_dir / datafiles["cxr_data"])

    # Build the scenario Polars DataFrame from the GeoPackage
    centroids = gdf.geometry.centroid
    scenario = pl.DataFrame(
        {
            "id": [f"patch_{i}" for i in range(len(gdf))],
            "lat": centroids.y.to_numpy(),
            "lon": centroids.x.to_numpy(),
            "pop": gdf["population"].to_numpy().astype(np.int64),
            "mcv1": np.zeros(len(gdf)),
        }
    )

    sim = config["simulation"]

    # Configure model parameters
    params = ABMParams(
        num_ticks=sim["nyears"] * 365,
        seed=sim.get("seed", 42),
        start_time=sim.get("start_time", "2000-01"),
    )

    model = ABMModel(scenario=scenario, params=params)

    # Vital dynamics
    cbr = cxr_df["CBR"].iloc[0] if "CBR" in cxr_df.columns else 30.0
    cdr = cxr_df["CDR"].iloc[0] if "CDR" in cxr_df.columns else 10.0
    vd_params = components.VitalDynamicsParams(
        crude_birth_rate=float(cbr),
        crude_death_rate=float(cdr),
    )

    # Infection seeding — seed the largest population patch
    largest_patch = scenario.sort("pop", descending=True)["id"][0]
    seeding_params = components.InfectionSeedingParams(
        target_patches=[largest_patch],
        infections_per_patch=sim.get("initial_infections", 50),
    )

    # Infection process
    infection_params = components.InfectionParams(
        beta=sim.get("beta", 20.0),
        seasonality=sim.get("seasonality", 0.0),
        distance_exponent=sim.get("distance_exponent", 2.0),
        mixing_scale=sim.get("mixing_scale", 0.01),
    )

    # Initialize equilibrium states if not a naive population
    if not sim.get("naive_population", True):
        model.add_component(components.InitializeEquilibriumStatesProcess)

    # Assemble components
    model.components = [
        create_component(components.VitalDynamicsProcess, vd_params),
        create_component(components.InfectionSeedingProcess, seeding_params),
        create_component(components.InfectionProcess, infection_params),
        components.StateTracker,
        create_component(
            components.StateTracker,
            components.StateTrackerParams(aggregation_level=0),
        ),
    ]

    model.run()

    plot.show_plots(model, scenario, output_dir=Path(__file__).parent, name="measles")

    return


if __name__ == "__main__":
    main()
