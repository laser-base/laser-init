from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from laser.generic.model import Model
from matplotlib.backends.backend_pdf import PdfPages


def show_plots(model: Model, output_dir: Path | None, name: str = "model") -> Path:
    """Generate all visualization plots for model output.

    Creates a comprehensive set of plots for analyzing epidemic model results,
    including temporal dynamics, spatial patterns, and summary statistics.
    If output_dir is provided, saves all plots to a single PDF file.

    Args:
        model: LASER model instance with completed simulation results.
        output_dir: Directory where output PDF will be saved, or None to skip saving.

    Returns:
        None
    """

    plots = [
        stacked_e_and_i,
        r_effective_t,
        choropleth_snapshots,
        arrival_time_choropleth,
        individual_incidence,
        import_pressure,
        peak_timing_peak_size,
        cumulative_incidence,
    ]
    figs = (plot_func(model, output_dir) for plot_func in plots)
    if output_dir:
        pdf_path = Path(output_dir) / f"{name}_output.pdf"
        with PdfPages(pdf_path) as pdf:
            for fig in figs:
                pdf.savefig(fig)
                plt.close(fig)
    else:
        pdf_path = None

    return pdf_path


def stacked_e_and_i(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot stacked infectious individuals over time for top locations.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Get the indices of the top N nodes with the highest incidence across the simulation
    top_n = 16
    top_nodes = np.argsort(model.nodes.I.sum(axis=0))[-top_n:]

    # Create stacked area plot for E and I values for top nodes plus "others"
    fig, ax = plt.subplots(figsize=(12, 8))

    # Prepare data for stacking
    num_timesteps = model.nodes.I.shape[0]

    # Stack infectious counts
    i_stack = np.zeros((num_timesteps, len(top_nodes) + 1))
    for idx, node in enumerate(top_nodes):
        i_stack[:, idx] = model.nodes.I[:, node]

    # Calculate "other" nodes (all nodes not in top 8)
    all_nodes = np.arange(model.nodes.I.shape[1])
    other_nodes = np.setdiff1d(all_nodes, top_nodes)
    i_stack[:, -1] = model.nodes.I[:, other_nodes].sum(axis=1)

    # Create colors for top nodes + other
    colors_i = plt.cm.tab10(np.linspace(0, 0.9, top_n))
    colors_i = np.vstack([colors_i, [[0.7, 0.7, 0.7, 1]]])  # Gray for "other"

    # Create stacked area plot for Infectious
    # Get node names from the scenario GeoDataFrame
    node_names = [model.scenario.name.iloc[node] for node in top_nodes]
    labels_i = [f"{name} (I)" for name in node_names] + ["Other nodes (I)"]
    ax.stackplot(range(num_timesteps), i_stack.T, labels=labels_i, colors=colors_i, alpha=0.8)

    ax.set_xlabel("Time (days)", fontsize=12)
    ax.set_ylabel("Number of Individuals", fontsize=12)
    ax.set_title("Stacked Infectious Individuals Over Time", fontsize=14)
    ax.legend(loc="upper right", fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output_dir:
        plt.savefig(
            Path(output_dir) / "top_nodes_exposed_infectious.png", dpi=200, bbox_inches="tight"
        )
    plt.show()

    return fig


def r_effective_t(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot effective reproduction number (R_t) over time.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Calculate the effective reproduction number R_t over time
    new_infections = model.nodes.newly_infected
    infectious_individuals = model.nodes.I
    with np.errstate(divide="ignore", invalid="ignore"):
        r_effective = np.where(
            infectious_individuals > 0, new_infections / infectious_individuals, 0
        )
    r_effective = np.nan_to_num(r_effective) * model.params.infectious_duration_mean

    # Plot R_t over time
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(r_effective.mean(axis=1), label="Average R_t")
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Effective Reproduction Number (R_t)")
    ax.set_title("Effective Reproduction Number Over Time")
    ax.axhline(y=1, color="r", linestyle="--", label="R_t = 1")
    ax.legend()
    if output_dir:
        plt.savefig(Path(output_dir) / "effective_reproduction_number.png")
    plt.show()

    return fig


def choropleth_snapshots(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot choropleth maps showing spatial spread over time.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Create choropleth snapshots of the infectious population at specific time points
    # two rows, four columns
    # choose 8 time points between t0 and when incidence hits zero (or the end of the simulation)
    # shapes are in the GeoPandas GeoDataFrame model.scenario

    # Calculate total infectious across all locations at each time point
    total_infectious = model.nodes.I.sum(axis=1)

    # Find when incidence hits zero (or use end of simulation)
    nonzero_times = np.where(total_infectious > 0)[0]
    if len(nonzero_times) > 0:
        end_time = nonzero_times[-1]
    else:
        end_time = len(total_infectious) - 1

    # Select 8 evenly spaced time points from t0 to end_time
    time_points = np.linspace(0, end_time, 8, dtype=int)

    # Create 2x4 subplot grid
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.flatten()

    # Get the scenario GeoDataFrame
    gdf = model.scenario.copy()

    # Find global min/max for consistent color scaling
    vmin = 0
    # vmax = model.nodes.I[time_points, :].max()
    # vmax should be the maximum of (I/population) for all selected time points and locations
    vmax = (
        model.nodes.I[time_points, :] / np.maximum(model.scenario.population.values, 1)[None, :]
    ).max()

    for idx, t in enumerate(time_points):
        ax = axes[idx]

        # Add infectious counts to the GeoDataFrame for this time point
        # gdf["value"] = model.nodes.I[t, :]
        gdf["value"] = model.nodes.I[t, :] / np.maximum(
            model.scenario.population.values, 1
        )  # Normalize by population for better visualization

        # Create choropleth
        gdf.plot(
            column="value",
            ax=ax,
            legend=False,
            cmap="YlOrRd",
            edgecolor="black",
            linewidth=0.5,
            vmin=vmin,
            vmax=vmax,
        )

        ax.set_title(f"Day {t}", fontsize=10)
        ax.axis("off")

    # Add a colorbar to the figure with proper spacing
    sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])

    plt.suptitle("Infectious Population Snapshots Over Time", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])  # Make room for colorbar at bottom

    # Add colorbar below the plots
    cbar = fig.colorbar(sm, ax=axes, orientation="horizontal", pad=0.08, aspect=40, shrink=0.8)
    cbar.set_label("Infectious Individuals (Normalized by Population)", fontsize=10)

    if output_dir:
        plt.savefig(Path(output_dir) / "choropleth_snapshots.png", dpi=200, bbox_inches="tight")
    plt.show()

    return fig


def arrival_time_choropleth(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot time to first infection for each location.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Determine the time to first infection for each node and create a choropleth map of these arrival times
    # shapes are in the GeoPandas GeoDataFrame model.scenario

    # Calculate the time to first infection for each location
    num_locations = model.nodes.I.shape[1]
    arrival_times = np.zeros(num_locations)

    for loc in range(num_locations):
        # Find the first time point where I > 0 for this location
        infected_times = np.where(model.nodes.I[:, loc] > 0)[0]
        if len(infected_times) > 0:
            arrival_times[loc] = infected_times[0]
        else:
            # No infection ever arrived - set to NaN
            arrival_times[loc] = np.nan

    # Create the choropleth map
    fig, ax = plt.subplots(figsize=(12, 10))

    # Get the scenario GeoDataFrame
    gdf = model.scenario.copy()
    gdf["arrival_time"] = arrival_times

    # Plot the choropleth
    gdf.plot(
        column="arrival_time",
        ax=ax,
        legend=True,
        cmap="viridis",
        edgecolor="black",
        linewidth=0.5,
        missing_kwds={
            "color": "lightgrey",
            "edgecolor": "black",
            "hatch": "///",
            "label": "No infection",
        },
    )

    ax.set_title("Time to First Infection by Location", fontsize=14)
    ax.axis("off")

    # Customize the legend
    legend = ax.get_legend()
    if legend:
        legend.set_title("Day", prop={"size": 10})
        legend.set_bbox_to_anchor((1.15, 0.5))
        legend.set_frame_on(True)

    plt.tight_layout()

    if output_dir:
        plt.savefig(
            Path(output_dir) / "arrival_time_choropleth.png",
            dpi=200,
            bbox_inches="tight",
        )
    plt.show()

    return fig


def individual_incidence(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot incidence curves for top locations (log scale).

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Plot the incidence curve (new infections per day), in log space, for a few selected nodes
    # Get the indices of the top N nodes with the highest total incidence across the simulation

    # Calculate total incidence (cumulative infections) for each node
    top_n = 12
    total_incidence = model.nodes.newly_infected.sum(axis=0)

    # Get the indices of the top N nodes
    top_nodes = np.argsort(total_incidence)[-top_n:]
    # Reverse node indices so that the node with the highest cases is plotted first
    top_nodes = top_nodes[::-1]

    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot incidence curves for each top node
    colors = plt.cm.tab10(np.linspace(0, 1, top_n))

    for idx, node in enumerate(top_nodes):
        # Get new infections for this node (add small epsilon to avoid log(0))
        incidence = model.nodes.newly_infected[:, node]
        incidence_safe = np.where(incidence > 0, incidence, np.nan)

        # Get node name from scenario GeoDataFrame
        node_name = model.scenario.name.iloc[node]

        ax.plot(incidence_safe, label=node_name, color=colors[idx], linewidth=2, alpha=0.8)

    ax.set_xlabel("Time (days)", fontsize=12)
    ax.set_ylabel("New Infections per Day (log scale)", fontsize=12)
    ax.set_title(f"Incidence Curves for Top {top_n} Nodes", fontsize=14)
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5, which="both")
    ax.legend(loc="best", frameon=True, fancybox=False, edgecolor="#CCCCCC")

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output_dir:
        plt.savefig(Path(output_dir) / "individual_incidence.png", dpi=200, bbox_inches="tight")
    plt.show()

    return fig


def import_pressure(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot import pressure from top source locations.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Pick the top 6 nodes (2 rows, 3 columns) with the highest total case counts (model.nodes.newly_infected.sum()) and plot the import
    # pressure at the _other_ nodes from these top nodes. Import pressure can be calculated using the total
    # of infectious counts and multiplying by the model.network (@ model.network) to determine the
    # import pressure on other nodes.

    # Calculate total case counts for each node
    total_cases = model.nodes.newly_infected.sum(axis=0)

    # Get the indices of the top 6 nodes
    top_nodes = np.argsort(total_cases)[-6:]

    # Reverse node indices so that the node with the highest cases is plotted first
    top_nodes = top_nodes[::-1]

    # Create 2x3 subplot grid
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    # Get the scenario GeoDataFrame
    gdf = model.scenario.copy()

    # Calculate global max for consistent color scaling
    all_pressures = []

    # For each top node, calculate import pressure
    for source_node in top_nodes:
        # Calculate import pressure from this source node over time
        # Import pressure = infectious individuals at source * connectivity to other nodes
        import_pressure_over_time = (
            model.nodes.I[:, source_node : source_node + 1]
            @ model.network[source_node : source_node + 1, :]
        )

        # Sum import pressure over time for each destination node
        total_import_pressure = import_pressure_over_time.sum(axis=0)
        total_import_pressure[source_node] = 0  # Zero out self-import

        all_pressures.append(np.log1p(total_import_pressure))

    # Find global max for consistent color scaling
    vmin = 0
    vmax = max(p.max() for p in all_pressures)

    # Create choropleth for each source node
    for idx, source_node in enumerate(top_nodes):
        ax = axes[idx]

        # Add import pressure to the GeoDataFrame
        gdf["import_pressure"] = all_pressures[idx]

        # Create choropleth
        gdf.plot(
            column="import_pressure",
            ax=ax,
            legend=False,
            cmap="YlOrRd",
            edgecolor="black",
            linewidth=0.5,
            vmin=vmin,
            vmax=vmax,
        )

        # Get source node name for title
        source_name = model.scenario.name.iloc[source_node]
        ax.set_title(f"Import Pressure from {source_name}", fontsize=11)
        ax.axis("off")

    # Add a shared colorbar
    sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])

    plt.suptitle("Import Pressure from Top 6 Source Nodes", fontsize=16, y=0.98)
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])

    cbar = fig.colorbar(sm, ax=axes, orientation="horizontal", pad=0.08, aspect=40, shrink=0.8)
    cbar.set_label("Total Import Pressure (log space)", fontsize=10)

    if output_dir:
        plt.savefig(Path(output_dir) / "import_pressure.png", dpi=200, bbox_inches="tight")
    plt.show()

    return fig


def peak_timing_peak_size(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot peak timing versus peak size scatter plot.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Find the peak case timing and peak size (fraction of population) for each node, and plot these against each other in a scatter plot. Color the points by the total population of the node (model.scenario.population).
    # Find the peak incidence timing and peak size (fraction) for each node, and plot these against each other in a scatter plot. Color the points by the total population of the node (model.scenario.population).

    num_locations = model.nodes.I.shape[1]
    peak_times = np.zeros(num_locations)
    peak_sizes = np.zeros(num_locations)

    # Get population for each node
    populations = np.maximum(model.scenario.population.values, 1)

    # Find peak timing and peak size for each node
    for loc in range(num_locations):
        incidence = model.nodes.newly_infected[:, loc]

        if incidence.max() > 0:
            # Peak timing: day when incidence is highest
            peak_times[loc] = np.argmax(incidence)

            # Peak size: maximum incidence as fraction of population
            peak_sizes[loc] = incidence.max() / populations[loc]
        else:
            # No infections - set to NaN
            peak_times[loc] = np.nan
            peak_sizes[loc] = np.nan

    # Create scatter plot
    fig, ax = plt.subplots(figsize=(12, 8))

    # Filter out nodes with no infections
    valid_mask = ~np.isnan(peak_times)

    if valid_mask.sum() > 0:
        # Create scatter plot colored by population (log scale)
        scatter = ax.scatter(
            peak_times[valid_mask],
            peak_sizes[valid_mask] * 100,  # Convert to percentage
            c=np.log10(populations[valid_mask]),
            cmap="viridis",
            s=100,
            alpha=0.6,
            edgecolors="black",
            linewidth=0.5,
        )

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Population (log10)", fontsize=10)

        ax.set_xlabel("Peak Timing (days)", fontsize=12)
        ax.set_ylabel("Peak Size (% of population)", fontsize=12)
        ax.set_title("Epidemic Peak Timing vs Peak Size by Location", fontsize=14)
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

        # Remove top and right spines
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output_dir:
        plt.savefig(Path(output_dir) / "peak_timing_peak_size.png", dpi=200, bbox_inches="tight")
    plt.show()

    return fig


def cumulative_incidence(model: Model, output_dir: Path | None) -> plt.Figure:
    """Plot ranked cumulative incidence distribution across locations.

    Args:
        model: LASER model instance with simulation results.
        output_dir: Directory where PNG will be saved, or None to skip saving.

    Returns:
        Matplotlib figure object.
    """

    # Plot the cumulative incidence over time for the entire population and for selected nodes
    # Assume you have:
    # model.nodes.I[t,c] = infectious count at center c time t
    # model.nodes.newly_infected[t,c] = new cases (incidence) at center c time t
    # pop[c] = model.nodes.S[-1,:] + model.nodes.E[-1,:] + model.nodes.I[-1,:] + model.nodes.R[-1,:] population at center c (strongly recommended)
    # A) Cumulative incidence distribution (across centers)
    # 1) Compute cumulative incidence per center
    # Pick the time window [t0, t1] you want to summarize (often the whole sim).
    # Counts
    # cum_cases[c] = sum_t model.nodes.newly_infected[t,c] over t0..t1
    # Rate (recommended)
    # cum_per_100k[c] = 100000 * cum_cases[c] / pop[c]
    # That's the core derived vector: one number per center.
    # 2) Plot it (pick one; ranked curve is my default)
    # Ranked curve (very clear)
    # Sort centers by cum_per_100k descending
    # X: rank (1..n_centers)
    # Y: cum_per_100k
    # This instantly shows whether burden is concentrated in a few centers or spread out.

    # Calculate total population for each center
    # Use final timestep to get total population (S + E + I + R)
    pop = model.nodes.S[-1, :]
    pop += model.nodes.E[-1, :] if hasattr(model.nodes, "E") else 0
    pop += model.nodes.I[-1, :]
    pop += model.nodes.R[-1, :] if hasattr(model.nodes, "R") else 0

    # Calculate cumulative cases per center (sum over all time)
    cum_cases = model.nodes.newly_infected.sum(axis=0)

    # Calculate cumulative incidence rate per 100,000 population
    cum_per_100k = 100000 * cum_cases / pop

    # Sort centers by cumulative incidence (descending)
    sorted_indices = np.argsort(cum_per_100k)[::-1]
    sorted_cum_per_100k = cum_per_100k[sorted_indices]

    # Create ranked curve plot
    fig, ax = plt.subplots(figsize=(12, 8))

    ranks = np.arange(1, len(sorted_cum_per_100k) + 1)

    ax.plot(
        ranks,
        sorted_cum_per_100k,
        color="#2E86AB",
        linewidth=2.5,
        marker="o",
        markersize=4,
        markevery=max(1, len(ranks) // 20),
    )

    # Fill area under curve
    ax.fill_between(ranks, sorted_cum_per_100k, alpha=0.2, color="#2E86AB")

    ax.set_xlabel("Location Rank (by cumulative incidence)", fontsize=12)
    ax.set_ylabel("Cumulative Incidence (per 100,000 population)", fontsize=12)
    ax.set_title("Ranked Cumulative Incidence Distribution Across Locations", fontsize=14)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    ax.set_axisbelow(True)

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add annotation for concentration
    total_cases = cum_cases.sum()
    top_10_pct_cutoff = max(1, int(0.1 * len(cum_cases)))
    top_10_pct_cases = cum_cases[sorted_indices[:top_10_pct_cutoff]].sum()
    concentration_pct = 100 * top_10_pct_cases / total_cases

    ax.text(
        0.98,
        0.98,
        f"Top 10% of locations\naccount for {concentration_pct:.1f}%\nof all cases",
        transform=ax.transAxes,
        verticalalignment="top",
        horizontalalignment="right",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
        fontsize=10,
    )

    plt.tight_layout()

    if output_dir:
        plt.savefig(Path(output_dir) / "cumulative_incidence.png", dpi=200, bbox_inches="tight")
    plt.show()

    return fig
