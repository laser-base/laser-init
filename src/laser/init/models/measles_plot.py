from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.backends.backend_pdf import PdfPages


def show_plots(model, scenario: pl.DataFrame, output_dir: Path | None, name: str = "measles") -> Path:
    """Generate visualization plots for measles ABM model output.

    Creates plots for analyzing measles ABM simulation results including
    global SEIR dynamics, spatial attack rates, and infectious spread.
    If output_dir is provided, saves all plots to a single PDF file.

    Args:
        model: laser-measles ABM model instance with completed simulation results.
        scenario: Polars DataFrame with scenario data (id, lat, lon, pop, mcv1).
        output_dir: Directory where output PDF will be saved, or None to skip saving.
        name: Base name for the output PDF file.

    Returns:
        Path to the saved PDF file, or None if output_dir is None.
    """

    plots = [
        global_seir_fractions,
        spatial_attack_rate,
        infectious_over_time,
    ]
    figs = [plot_func(model, scenario) for plot_func in plots]
    if output_dir:
        pdf_path = Path(output_dir) / f"{name}_output.pdf"
        with PdfPages(pdf_path) as pdf:
            for fig in figs:
                pdf.savefig(fig)
                plt.close(fig)
    else:
        pdf_path = None

    return pdf_path


def global_seir_fractions(model, scenario: pl.DataFrame) -> plt.Figure:
    """Plot global SEIR fractions over time.

    Args:
        model: laser-measles ABM model instance with completed simulation.
        scenario: Polars DataFrame with scenario data.

    Returns:
        Matplotlib Figure with stacked SEIR fraction plot.
    """
    global_tracker = model.get_instance("StateTracker")[0]
    total_pop = scenario["pop"].sum()
    ticks = np.arange(model.params.num_ticks)

    S = np.array(global_tracker.S) / total_pop
    E = np.array(global_tracker.E) / total_pop
    I = np.array(global_tracker.I) / total_pop
    R = np.array(global_tracker.R) / total_pop

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.stackplot(ticks, S, E, I, R, labels=["S", "E", "I", "R"], alpha=0.8)
    ax.set_xlabel("Day")
    ax.set_ylabel("Fraction of Population")
    ax.set_title("Global SEIR Fractions Over Time")
    ax.legend(loc="center right")
    ax.set_xlim(0, len(ticks) - 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()

    return fig


def spatial_attack_rate(model, scenario: pl.DataFrame) -> plt.Figure:
    """Plot spatial attack rate by patch.

    Args:
        model: laser-measles ABM model instance with completed simulation.
        scenario: Polars DataFrame with scenario data.

    Returns:
        Matplotlib Figure with attack rate scatter plot.
    """
    patch_tracker = model.get_instance("StateTracker")[1]
    pops = scenario["pop"].to_numpy()

    # Cumulative recovered at end as proxy for attack rate
    final_R = np.array(patch_tracker.R)[-1]
    attack_rate = final_R / pops

    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        scenario["lon"].to_numpy(),
        scenario["lat"].to_numpy(),
        c=attack_rate,
        s=pops / pops.max() * 200,
        cmap="YlOrRd",
        alpha=0.7,
        edgecolors="black",
    )
    plt.colorbar(scatter, ax=ax, label="Attack Rate")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Spatial Attack Rate")
    fig.tight_layout()

    return fig


def infectious_over_time(model, scenario: pl.DataFrame) -> plt.Figure:
    """Plot infectious count per patch over time as a heatmap.

    Args:
        model: laser-measles ABM model instance with completed simulation.
        scenario: Polars DataFrame with scenario data.

    Returns:
        Matplotlib Figure with infectious heatmap.
    """
    patch_tracker = model.get_instance("StateTracker")[1]
    I_data = np.array(patch_tracker.I)

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(I_data.T, aspect="auto", cmap="hot", interpolation="nearest")
    plt.colorbar(im, ax=ax, label="Infectious Count")
    ax.set_xlabel("Day")
    ax.set_ylabel("Patch Index")
    ax.set_title("Infectious Agents per Patch Over Time")
    fig.tight_layout()

    return fig
