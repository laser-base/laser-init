import shutil
from pathlib import Path

from laser.init.logger import logger

__yaml__ = """
data_dir: %%data_dir%%

datafiles:
    shape_data: %%shape_data%%
    cxr_data: %%cxr_data%%
    pop_data: %%pop_data%%
    exp_data: %%exp_data%%

simulation:
    nyears: 2
    r0: 2.5
    exposed_duration_shape: 4.5
    exposed_duration_scale: 1.0
    infectious_duration_mean: 7.0
    gravity_k: 500
    gravity_a: 1
    gravity_b: 1
    gravity_c: 2
    naive_population: true
"""

__measles_yaml__ = """
data_dir: %%data_dir%%

datafiles:
    shape_data: %%shape_data%%
    cxr_data: %%cxr_data%%

simulation:
    nyears: 2
    seed: 42
    start_time: "%%start_time%%"
    beta: 20.0
    seasonality: 0.0
    distance_exponent: 2.0
    mixing_scale: 0.01
    initial_infections: 50
    naive_population: true
"""


class AbmLoader:
    def __init__(self) -> None:
        """Initialize the ABM (Agent-Based Model) loader.

        Returns:
            None
        """
        pass

    @staticmethod
    def description() -> str:
        """Return a brief description of this loader.

        Returns:
            A string describing the model script generation performed by this class.
        """
        return "Write an ABM model script loading data from the downloaded data sources."

    def emit_script(
        self,
        mode: str,
        model: str,
        shape_filename: Path,
        cxr_filename: Path,
        pop_filename: Path,
        exp_filename: Path,
        output_dir: Path,
    ) -> None:
        """Generate ABM model script and configuration files.

        Creates a YAML configuration file with data file paths and simulation parameters,
        then copies the appropriate model script (SI, SIR, SEIR, or MEASLES) and plotting
        utilities to the output directory. The MEASLES model uses laser-measles instead of
        laser-generic and only consumes shape and crude-rate data; ``pop_filename`` and
        ``exp_filename`` are accepted for signature compatibility with the other model
        types but are ignored for MEASLES.

        Args:
            mode: Model mode (must be "ABM").
            model: Model type ("SI", "SIR", "SEIR", or "MEASLES").
            shape_filename: Path to the GeoPackage file with administrative boundaries.
            cxr_filename: Path to the CSV file with crude birth/death rates.
            pop_filename: Path to the CSV file with age distribution. Ignored for MEASLES.
            exp_filename: Path to the CSV file with life expectancy data. Ignored for MEASLES.
            output_dir: Directory where model script and config will be written.

        Raises:
            AssertionError: If mode is not "ABM".
        """

        assert mode.upper() == "ABM", f"AbmLoader only supports ABM mode, got {mode}"

        if model.upper() == "MEASLES":
            self._emit_measles(shape_filename, cxr_filename, output_dir)
        else:
            self._emit_generic(
                model, shape_filename, cxr_filename, pop_filename, exp_filename, output_dir
            )

        return

    def _emit_generic(
        self,
        model: str,
        shape_filename: Path,
        cxr_filename: Path,
        pop_filename: Path,
        exp_filename: Path,
        output_dir: Path,
    ) -> None:
        """Generate a laser-generic model script and configuration.

        Args:
            model: Model type ("SI", "SIR", or "SEIR").
            shape_filename: Path to the GeoPackage file with administrative boundaries.
            cxr_filename: Path to the CSV file with crude birth/death rates.
            pop_filename: Path to the CSV file with age distribution.
            exp_filename: Path to the CSV file with life expectancy data.
            output_dir: Directory where model script and config will be written.
        """
        logger.info("Emitting laser-generic %s model script to %s", model, output_dir)

        yaml = __yaml__.replace("%%data_dir%%", str(output_dir.absolute()))
        yaml = yaml.replace("%%shape_data%%", str(shape_filename.name))
        yaml = yaml.replace("%%cxr_data%%", str(cxr_filename.name))
        yaml = yaml.replace("%%pop_data%%", str(pop_filename.name))
        yaml = yaml.replace("%%exp_data%%", str(exp_filename.name))
        (Path(output_dir) / "config.yaml").write_text(yaml)

        source_dir = Path(__file__).parent.parent / "models"
        shutil.copy2(source_dir / f"{model.lower()}.py", Path(output_dir) / f"{model.lower()}.py")
        shutil.copy2(source_dir / "plot.py", Path(output_dir) / "plot.py")

    def _emit_measles(
        self,
        shape_filename: Path,
        cxr_filename: Path,
        output_dir: Path,
        start_time: str = "2000-01",
    ) -> None:
        """Generate a laser-measles ABM model script and configuration.

        Args:
            shape_filename: Path to the GeoPackage file with administrative boundaries.
            cxr_filename: Path to the CSV file with crude birth/death rates.
            output_dir: Directory where model script and config will be written.
            start_time: Simulation start time in YYYY-MM format.
        """
        logger.info("Emitting laser-measles ABM model script to %s", output_dir)

        yaml = __measles_yaml__.replace("%%data_dir%%", str(output_dir.absolute()))
        yaml = yaml.replace("%%shape_data%%", str(shape_filename.name))
        yaml = yaml.replace("%%cxr_data%%", str(cxr_filename.name))
        yaml = yaml.replace("%%start_time%%", start_time)
        (Path(output_dir) / "config.yaml").write_text(yaml)

        source_dir = Path(__file__).parent.parent / "models"
        shutil.copy2(source_dir / "measles.py", Path(output_dir) / "measles.py")
        shutil.copy2(source_dir / "measles_plot.py", Path(output_dir) / "measles_plot.py")
