"""
Command-line interface for laser-init.
Using the Click library to create a simple CLI entry point. This can be expanded with subcommands and options as needed.
"""

from pathlib import Path

import click
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from laser.init.extractors import gadm as gadmex
from laser.init.extractors import geoboundaries as geoboundariesex
from laser.init.extractors import unocha as unochaex
from laser.init.extractors import unwpp as unwppex
from laser.init.extractors import worldpop as worldpopex
from laser.init.loaders import abm, mpm
from laser.init.transformers import gadm as gadmtx
from laser.init.transformers import geoboundaries as geoboundariestx
from laser.init.transformers import unocha as unochatx
from laser.init.transformers import unwpp as unwpptx

from .config import VERSION
from .config import configuration as config
from .utils import error, inform, iso_from_country_string, level_from_string

help = """
Download spatial data for modeling diseases across populations and prepare for use with a LASER model.
E.g., laser-init NGA ADM2 2010 2025
"""
__MIN_YEAR__ = 1950
__MAX_YEAR__ = 2100


@click.command(help=help)
@click.version_option(version=VERSION, prog_name="laser-init")
@click.argument("country", required=True)
@click.argument("level", required=True)
@click.argument("start-year", required=True, type=click.IntRange(__MIN_YEAR__, __MAX_YEAR__))
@click.argument("end-year", required=True, type=click.IntRange(__MIN_YEAR__, __MAX_YEAR__))
@click.option(
    "-o",
    "--output-dir",
    type=Path,
    default=None,
    help="Output directory for transformed data (default: ./ISOCODE/start_year)",
)
@click.option(
    "--mode",
    type=click.Choice(["ABM", "MPM"], case_sensitive=False),
    default="ABM",
    help="Select the modeling mode - ABM or MPM (default: ABM)",
)
@click.option(
    "--model",
    type=click.Choice(["SI", "SIR", "SEIR", "MEASLES"], case_sensitive=False),
    default="SEIR",
    help="Select the type of epidemiological model to prepare data for (default: SEIR)",
)
@click.option(
    "--shape-source",
    type=click.Choice(["unocha", "geoboundaries", "gadm"], case_sensitive=False),
    default=None,
    help="Select the shape file source (default: laser_config value or 'UNOCHA')",
)
@click.option(
    "--raster-source",
    type=click.Choice(["worldpop"], case_sensitive=False),
    default=None,
    help="Select the population raster file source (default: laser_config value or 'WorldPop')",
)
@click.option(
    "--stats-source",
    type=click.Choice(["unwpp"], case_sensitive=False),
    default=None,
    help="Select the demographic stats source (default: laser_config value or 'UNWPP')",
)
def cli(
    country: str,
    level: str,
    start_year: int,
    end_year: int,
    output_dir: Path | None,
    mode: str,
    model: str,
    shape_source: str | None,
    raster_source: str | None,
    stats_source: str | None,
) -> None:
    """Main CLI entry point to download, transform, and prepare spatial data for LASER models.

    This function orchestrates the complete data pipeline for LASER model initialization:
    1. Validates and normalizes input parameters
    2. Downloads administrative boundaries, population rasters, and demographic statistics
    3. Transforms raw data into model-ready formats
    4. Generates model-specific initialization scripts
    5. Creates visualization reports

    Args:
        country: Country name or ISO 3166-1 alpha-3 code (e.g., "Nigeria" or "NGA").
        level: Administrative level as string (e.g., "ADM1", "admin2", "3").
        start_year: Base year for simulation (1950-2100, must be <= end_year).
        end_year: End year for simulation (1950-2100, must be >= start_year).
        output_dir: Output directory path. If None, defaults to "./ISOCODE/start_year".
        mode: Modeling mode, either "ABM" (agent-based model) or "MPM" (metapopulation model).
        model: Epidemiological model type - "SI", "SIR", "SEIR", or "MEASLES".
        shape_source: Administrative boundary data source - "unocha", "geoboundaries", or "gadm".
            If None, uses config value or defaults to "unocha".
        raster_source: Population raster data source - currently only "worldpop" supported.
            If None, uses config value or defaults to "worldpop".
        stats_source: Demographic statistics source - currently only "unwpp" supported.
            If None, uses config value or defaults to "unwpp".

    Returns:
        None. Outputs are written to the specified output_dir:
            - Transformed GeoPackage with administrative boundaries and population
            - CSV files with CBR/CDR, age distribution, and life expectancy data
            - Model initialization script (ABM or MPM)
            - PDF report with visualization plots

    Raises:
        click.exceptions.Exit: If any validation fails:
            - Invalid country code or ISO-3 code cannot be determined
            - Invalid administrative level format
            - Start year out of range (< 1900 or > current year)
            - End year out of range (< start_year or > current year)
            - Invalid shape_source, raster_source, or stats_source
        RuntimeError: If data extraction or transformation fails:
            - Shape file cannot be read during plotting
            - CSV files cannot be read during plotting
        AssertionError: If output_dir cannot be created or is not a valid directory.

    Example:
        ```bash
        # Initialize SEIR ABM model for Nigeria at ADM2 level for years 2010-2025
        laser-init NGA ADM2 2010 2025

        # Use MPM mode with custom output directory
        laser-init "Nigeria" ADM1 2015 2020 --mode MPM --output-dir ./my_output

        # Specify data sources explicitly
        laser-init NGA ADM2 2010 2025 --shape-source gadm --stats-source unwpp
        ```
    """
    inform("Starting laser-init CLI")
    inform(
        f"Received arguments: country={country}, level={level}, start_year={start_year}, end_year={end_year}, output_dir={output_dir}, shape_source={shape_source}, raster_source={raster_source}, stats_source={stats_source}"
    )

    iso_code, adm_level, output_dir = validate_arguments(
        country, level, start_year, end_year, output_dir
    )

    # Extract (download)
    shape_data = download_shape_data(iso_code, adm_level, start_year, shape_source)
    raster_data = download_raster_data(iso_code, start_year, raster_source)
    stats_data = download_demographic_stats(iso_code, start_year, end_year, stats_source)

    # Transform
    shapes_filename = transform_shape_and_raster_data(
        shape_source, shape_data, iso_code, adm_level, raster_data, output_dir
    )
    (cxr_filename, pop_filename, exp_filename) = transform_stats_data(
        stats_source, stats_data, iso_code, start_year, end_year, output_dir
    )

    # Load (emit data loading script)
    emit_model_script(
        mode, model, shapes_filename, cxr_filename, pop_filename, exp_filename, output_dir
    )

    write_plots(shapes_filename, cxr_filename, pop_filename, exp_filename, output_dir)

    return


def validate_arguments(
    country: str, level: str, start_year: int, end_year: int, output_dir: Path | None
) -> tuple[str, int, Path]:
    """Validate and normalize command-line arguments.

    Args:
        country: Country name or ISO code string.
        level: Administrative level string (e.g., "admin1", "ADM2", "3").
        start_year: Starting year for the simulation.
        end_year: Ending year for the simulation.
        output_dir: Output directory path or None for default.

    Returns:
        Tuple of (iso_code, adm_level, output_dir) with validated and normalized values.

    Raises:
        click.exceptions.Exit: If validation fails for any argument.
    """

    iso_code = iso_from_country_string(country)
    if not iso_code:
        error(
            f"Could not determine the ISO-3 code for '{country}'. Please check your input and try again.",
            click.exceptions.Exit(1),
        )
    inform(f"Country: {country} → ISO-3: {iso_code}")

    adm_level = level_from_string(level)
    if adm_level is None:
        error(
            f"Could not determine the administrative level from '{level}'. Please check your input and try again.",
            click.exceptions.Exit(1),
        )
    inform(f"Administrative Level: {level} → ADM{adm_level}")

    # start_year <= end_year
    if start_year > end_year:
        error(
            f"Start year {start_year} cannot be greater than end year {end_year}. Please check your input and try again.",
            click.exceptions.Exit(1),
        )

    if start_year < __MIN_YEAR__ or start_year > __MAX_YEAR__:
        error(
            f"Start year {start_year} is out of range. Please provide a year between {__MIN_YEAR__} and {__MAX_YEAR__}.",
            click.exceptions.Exit(1),
        )
    inform(f"Base year: {start_year}")

    if end_year < __MIN_YEAR__ or end_year > __MAX_YEAR__:
        error(
            f"End year {end_year} is out of range. Please provide a year between {__MIN_YEAR__} and {__MAX_YEAR__}.",
            click.exceptions.Exit(1),
        )
    inform(f"End year: {end_year}")

    output_dir = output_dir or (Path.cwd() / iso_code / str(start_year))
    output_dir.mkdir(parents=True, exist_ok=True)
    assert output_dir.is_dir(), f"Output directory {output_dir} is not a valid directory."
    inform(f"Output directory: {output_dir}")

    return iso_code, adm_level, output_dir


def download_shape_data(iso_code: str, adm_level: int, start_year: int, shape_source: str) -> Path:
    """Download administrative boundary shape data.

    Args:
        iso_code: ISO 3166-1 alpha-3 country code.
        adm_level: Administrative level (0-4).
        start_year: Year for the data (for cache organization).
        shape_source: Data source name ("unocha", "geoboundaries", or "gadm").

    Returns:
        Path to the downloaded shape data file.

    Raises:
        click.exceptions.Exit: If invalid shape_source is specified.
    """

    shape_source = (shape_source or config.get("shape_source", "unocha")).lower()
    try:
        shape_extractor = {
            "unocha": unochaex.UnochaExtractor,
            "geoboundaries": geoboundariesex.GeoBoundariesExtractor,
            "gadm": gadmex.GadmExtractor,
        }[shape_source]()
    except KeyError:
        error(
            f"Invalid shape source '{shape_source}'. Valid options are: unocha, geoboundaries, gadm.",
            click.exceptions.Exit(1),
        )

    inform(f"Using shape source: {shape_source} ({shape_extractor.description()})")

    return shape_extractor.extract(iso_code, adm_level, start_year)


def download_raster_data(iso_code: str, start_year: int, raster_source: str) -> Path:
    """Download population raster data.

    Args:
        iso_code: ISO 3166-1 alpha-3 country code.
        start_year: Year for the population data.
        raster_source: Data source name (currently only "worldpop").

    Returns:
        Path to the downloaded raster file.

    Raises:
        click.exceptions.Exit: If invalid raster_source is specified.
    """

    raster_source = (raster_source or config.get("raster_source", "worldpop")).lower()
    try:
        raster_extractor = {
            "worldpop": worldpopex.WorldPopExtractor,
        }[raster_source]()
    except KeyError:
        error(
            f"Invalid raster source '{raster_source}'. Valid options are: worldpop.",
            click.exceptions.Exit(1),
        )

    inform(f"Using raster source: {raster_source} ({raster_extractor.description()})")

    return raster_extractor.extract(iso_code, start_year)


def download_demographic_stats(
    iso_code: str, start_year: int, end_year: int, stats_source: str
) -> tuple[Path, ...]:
    """Download demographic statistics data.

    Args:
        iso_code: ISO 3166-1 alpha-3 country code.
        start_year: Start year for the data range.
        end_year: End year for the data range.
        stats_source: Data source name (currently only "unwpp").

    Returns:
        Tuple of Paths to downloaded demographic data files.

    Raises:
        click.exceptions.Exit: If invalid stats_source is specified.
    """

    stats_source = (stats_source or config.get("stats_source", "unwpp")).lower()

    try:
        stats_extractor = {
            "unwpp": unwppex.UnwppExtractor,
        }[stats_source]()
    except KeyError:
        error(
            f"Invalid demographic stats source '{stats_source}'. Valid options are: unwpp.",
            click.exceptions.Exit(1),
        )

    inform(f"Using demographic stats source: UNWPP ({stats_extractor.description()})")

    return stats_extractor.extract(iso_code, start_year, end_year)


def transform_shape_and_raster_data(
    shape_source: str,
    shape_data: Path,
    iso_code: str,
    adm_level: int,
    raster_data: Path,
    output_dir: Path,
) -> Path:
    """Transform shape and raster data using the specified shape transformer.
    This function selects and instantiates the appropriate shape transformer based on
    the provided shape_source, then uses it to transform the input shape and raster data.

    Args:
        shape_source: The source of shape data (e.g., "unocha"). If not provided,
            defaults to the value from config. Case-insensitive.
        shape_data: Path to the input shape data file.
        iso_code: ISO country code for the region to process.
        adm_level: Administrative level (e.g., 0 for country, 1 for regions).
        raster_data: Path to the input raster data file.
        output_dir: Path to the output directory where transformed data will be saved.

    Returns:
        The result of the shape transformer's transform method.

    Raises:
        KeyError: If the specified shape_source is not found in the available transformers.
    """

    shape_source = (shape_source or config.get("shape_source", "unocha")).lower()
    shape_transformer = {
        "unocha": unochatx.UnochaTransformer,
        "geoboundaries": geoboundariestx.GeoBoundariesTransformer,
        "gadm": gadmtx.GadmTransformer,
    }[shape_source]()

    inform(f"Using shape transformer: {shape_source} ({shape_transformer.description()})")

    return shape_transformer.transform(shape_data, iso_code, adm_level, raster_data, output_dir)


def transform_stats_data(
    stats_source: str,
    stats_data: tuple[Path, ...],
    iso_code: str,
    start_year: int,
    end_year: int,
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Transform demographic statistics data using the specified stats transformer.

    Selects and instantiates the appropriate demographic statistics transformer
    based on the provided stats_source, then uses it to filter and transform
    the input data for the specified country and year range.

    Args:
        stats_source: The source of demographic stats (e.g., "unwpp"). If not provided,
            defaults to the value from config. Case-insensitive.
        stats_data: Tuple of Paths to demographic data files.
        iso_code: ISO 3166-1 alpha-3 country code for filtering.
        start_year: Start year for the data range.
        end_year: End year for the data range.
        output_dir: Path to the output directory where transformed CSV files will be saved.

    Returns:
        Tuple of Paths: (cxr_filename, pop_filename, life_exp_filename).

    Raises:
        KeyError: If the specified stats_source is not found in the available transformers.
    """
    stats_source = (stats_source or config.get("stats_source", "unwpp")).lower()
    stats_transformer = {
        "unwpp": unwpptx.UnwppTransformer,
        # Add other stats transformers here as needed
    }[stats_source]()

    inform(
        f"Using demographic stats transformer: {stats_source} ({stats_transformer.description()})"
    )

    return stats_transformer.transform(stats_data, iso_code, start_year, end_year, output_dir)


def emit_model_script(
    mode: str,
    model: str,
    shapes_filename: Path,
    cxr_filename: Path,
    pop_filename: Path,
    exp_filename: Path,
    output_dir: Path,
) -> None:
    """Generate model script and configuration files.

    Args:
        mode: Model mode ("ABM" or "MPM").
        model: Model type ("SI", "SIR", "SEIR", or "MEASLES").
        shapes_filename: Path to the administrative boundaries GeoPackage.
        cxr_filename: Path to the crude birth/death rate CSV.
        pop_filename: Path to the age distribution CSV.
        exp_filename: Path to the life expectancy CSV.
        output_dir: Directory where model files will be written.

    Returns:
        None
    """
    # For now, just print the paths to the transformed data files. In the future, this could generate
    # a Python script that loads the data and prepares it for use with a LASER model.
    inform(f"Emitting model script for {mode}/{model} with data files:")
    inform(f"Shape file:                       '{shapes_filename}'")
    inform(f"CBR/CDR file:                     '{cxr_filename}'")
    inform(f"Population age distribution file: '{pop_filename}'")
    inform(f"Life expectancy file:             '{exp_filename}'")

    model_loader = {
        "ABM/SI": abm.AbmLoader,
        "ABM/SIR": abm.AbmLoader,
        "ABM/SEIR": abm.AbmLoader,
        "ABM/MEASLES": abm.AbmLoader,
        "MPM/SI": mpm.MpmLoader,
        "MPM/SIR": mpm.MpmLoader,
        "MPM/SEIR": mpm.MpmLoader,
    }[f"{mode.upper()}/{model.upper()}"]()

    model_loader.emit_script(
        mode, model, shapes_filename, cxr_filename, pop_filename, exp_filename, output_dir
    )

    return


def write_plots(
    shapes_filename: Path,
    cxr_filename: Path,
    pop_filename: Path,
    exp_filename: Path,
    output_dir: Path,
) -> None:
    """Generate visualization plots and combine into a PDF report.

    Creates individual plots for population choropleth, birth/death rates,
    age distribution, and life expectancy, then combines them into a single
    PDF report.

    Args:
        shapes_filename: Path to the administrative boundaries GeoPackage.
        cxr_filename: Path to the crude birth/death rate CSV.
        pop_filename: Path to the age distribution CSV.
        exp_filename: Path to the life expectancy CSV.
        output_dir: Directory where plots and PDF will be saved.

    Returns:
        None
    """
    # Generate individual plots and save as PNGs, then combine into a PDF report
    inform("Writing plots of the transformed data...")

    # Create PDF report
    pdf_path = Path(output_dir) / "report.pdf"
    with PdfPages(pdf_path) as pdf:
        # Generate each plot and add to PDF
        for fig in [
            plot_population_choropleth(shapes_filename, output_dir),
            plot_cbr_and_cdr(cxr_filename, output_dir),
            plot_age_distribution(pop_filename, output_dir),
            plot_life_expectancy(exp_filename, output_dir),
        ]:
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    inform(f"PDF report written to {pdf_path}")

    return


def plot_population_choropleth(shapes_filename: Path, output_dir: Path) -> plt.Figure:
    """Generate a population choropleth map.

    Args:
        shapes_filename: Path to the administrative boundaries GeoPackage.
        output_dir: Directory where the PNG image will be saved.

    Returns:
        Matplotlib figure object.

    Raises:
        RuntimeError: If the shape file cannot be read.
    """
    try:
        gdf = gpd.read_file(shapes_filename)
    except Exception as e:
        error(f"Failed to read shape file: {e}", RuntimeError)

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    gdf["log_pop"] = np.log1p(gdf.population) / np.log(10)
    gdf.plot(column="log_pop", ax=ax, legend=True, cmap="viridis", edgecolor="black")
    ax.set_title("Population (log10) Choropleth")
    ax.axis("off")

    output_path = Path(output_dir) / "choropleth.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200)
    inform(f"Choropleth PNG written to {output_path}")

    return fig


def plot_cbr_and_cdr(cxr_filename: Path, output_dir: Path) -> plt.Figure:
    """Generate crude birth and death rate time series plot.

    Args:
        cxr_filename: Path to the CSV file with CBR/CDR data.
        output_dir: Directory where the PNG image will be saved.

    Returns:
        Matplotlib figure object.

    Raises:
        RuntimeError: If the CBR/CDR file cannot be read.
    """
    # Plot CBR and CDR over time and write as a PNG in output_dir
    try:
        cxr_df = pd.read_csv(cxr_filename)
    except Exception as e:
        error(f"Failed to read CBR/CDR file: {e}", RuntimeError)

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot CBR with enhanced styling
    ax.plot(
        cxr_df.Time,
        cxr_df.CBR,
        label="CBR",
        color="#00897B",
        linewidth=2.5,
        marker="o",
        markersize=3,
        markevery=3,
    )

    # Plot CDR with enhanced styling
    ax.plot(
        cxr_df.Time,
        cxr_df.CDR,
        label="CDR",
        color="#E65100",
        linewidth=2.5,
        marker="s",
        markersize=3,
        markevery=3,
    )

    # Fill areas under curves
    ax.fill_between(cxr_df.Time, cxr_df.CBR, alpha=0.15, color="#00897B")
    ax.fill_between(cxr_df.Time, cxr_df.CDR, alpha=0.15, color="#E65100")

    # Fill area between curves to highlight natural growth rate
    ax.fill_between(cxr_df.Time, cxr_df.CBR, cxr_df.CDR, alpha=0.1, color="#FFB300")

    ax.set_title("Crude Birth Rate (CBR) and Crude Death Rate (CDR) Over Time", fontsize=12)
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Rate (per 1000 population)", fontsize=10)

    # Enhanced gridlines
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)
    ax.set_axisbelow(True)

    # Clean up spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    ax.legend(frameon=True, fancybox=False, edgecolor="#CCCCCC", framealpha=0.95)

    output_path = Path(output_dir) / "cbr_cdr.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200, facecolor="white")
    inform(f"CBR/CDR plot PNG written to {output_path}")

    return fig


def plot_age_distribution(pop_filename: Path, output_dir: Path) -> plt.Figure:
    """Generate population pyramid plot showing age distribution.

    Args:
        pop_filename: Path to the CSV file with age distribution data.
        output_dir: Directory where the PNG image will be saved.

    Returns:
        Matplotlib figure object.

    Raises:
        RuntimeError: If the population file cannot be read.
    """
    # Plot the age distribution as a population pyramid (mirrored on the y-axis)
    # Duplicate data to represent both males and females
    try:
        pop_df = pd.read_csv(pop_filename)
    except Exception as e:
        error(f"Failed to read population age distribution file: {e}", RuntimeError)

    # Create age group labels
    age_labels = [f"{start}-{start + 4}" for start in pop_df.AgeGrpStart[:-1]]
    age_labels.append(f"{pop_df.AgeGrpStart.iloc[-1]}+")

    # Calculate population values for each sex (duplicate the data)
    male_pop = pop_df.PopTotal.values
    female_pop = pop_df.PopTotal.values

    # Find the maximum value for symmetric x-axis
    max_pop = max(male_pop.max(), female_pop.max())

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot males (left side, negative values)
    ax.barh(age_labels, -male_pop, height=0.8, color="#6495ED", edgecolor="white", linewidth=0.5)

    # Plot females (right side, positive values)
    ax.barh(age_labels, female_pop, height=0.8, color="#E91E8C", edgecolor="white", linewidth=0.5)

    # Set x-axis limits and labels
    ax.set_xlim(-max_pop * 1.1, max_pop * 1.1)
    ax.set_xlabel("Population", fontsize=10)

    # Format x-axis to show absolute values
    ticks = ax.get_xticks()
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{abs(int(x)):,}" for x in ticks])

    # Add legend
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="#6495ED", label="Male"),
        Patch(facecolor="#E91E8C", label="Female"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", frameon=False)

    # Add gridlines
    ax.grid(True, axis="x", alpha=0.3, linestyle="-", linewidth=0.5)
    ax.set_axisbelow(True)

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    output_path = Path(output_dir) / "age_distribution.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200, facecolor="white")
    inform(f"Age distribution plot PNG written to {output_path}")

    return fig


def plot_life_expectancy(exp_filename: Path, output_dir: Path) -> plt.Figure:
    """Generate Kaplan-Meier survival curve plot.

    Args:
        exp_filename: Path to the CSV file with cumulative deaths data.
        output_dir: Directory where the PNG image will be saved.

    Returns:
        Matplotlib figure object.

    Raises:
        RuntimeError: If the life expectancy file cannot be read.
    """

    # Plot life expectancy as a Kaplan-Meier survival curve
    try:
        exp_df = pd.read_csv(exp_filename)
    except Exception as e:
        error(f"Failed to read life expectancy file: {e}", RuntimeError)

    # Invert cumulative deaths to get survival probability
    survival = exp_df.cumulative_deaths.max() - exp_df.cumulative_deaths

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot as step function (typical for Kaplan-Meier curves)
    ax.step(
        range(len(exp_df)),
        survival,
        where="post",
        color="black",
        linewidth=1,
        label="Survival",
    )

    # Fill area under curve
    ax.fill_between(range(len(exp_df)), survival, step="post", alpha=0.2, color="#2E86AB")

    ax.set_title("Survival Curve (Life Expectancy)")
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Survival Probability (per 100,000 births)")
    ax.set_ylim(0, survival.max() * 1.05)
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    ax.legend(loc="upper right", frameon=False)

    # Remove top and right spines for cleaner look
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    output_path = Path(output_dir) / "life_expectancy.png"
    fig.savefig(output_path, bbox_inches="tight", dpi=200, facecolor="white")
    inform(f"Life expectancy plot PNG written to {output_path}")

    return fig


if __name__ == "__main__":
    cli()
