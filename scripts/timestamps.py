from pathlib import Path
from typing import Dict, List
from math import sqrt, ceil, floor
from numpy import arange, ndarray
from argparse import ArgumentParser
from logging import info
from matplotlib import rcParams
from matplotlib.axes import Axes
from matplotlib.ticker import MaxNLocator
from matplotlib.figure import Figure
from matplotlib.pyplot import figure, get_cmap

from utilities.result import load_results, group_by_query, Result
from utilities.sorting import natural_sort_key

COLUMN_INCHES = 4
ROW_INCHES = 3


def register_args(parser: ArgumentParser) -> None:
    parser.description = "Produce a plot of result arrival timestamps per query"
    parser.add_argument(
        "--experiments",
        help="Path containing the experiments to consider",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        help="Path to save the plotted image to",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--serif",
        help="Use serif fonts in the plot",
        action="store_true",
    )
    parser.add_argument(
        "--colormap",
        help="The colour map to use for the plot",
        default="Spectral",
        type=str,
    )
    parser.add_argument(
        "--steps",
        help="Plot steps instead of straight lines",
        action="store_true",
    )
    parser.add_argument(
        "--transparent",
        help="Save the figure with transparent background",
        action="store_true",
    )
    parser.add_argument(
        "--dpi",
        help="Image dpi",
        default=300,
        type=int,
    )


def get_colors(configs: List[str], colormap: str) -> Dict[str, ndarray]:
    cmap = get_cmap(colormap)
    config_count = len(configs)
    cmap = cmap.resampled(config_count)
    colors = cmap(arange(0, config_count, 1))
    return {configs[i]: colors[i] for i in range(0, cmap.N)}


def plot_timestamps(
    results: Dict[str, List[Result]],
    steps: bool,
    colors: Dict[str, ndarray],
    dpi: int,
) -> Figure:
    fig: Figure = figure(dpi=dpi)
    rows: int = floor(sqrt(len(results)))
    cols: int = ceil(len(results) / rows)
    info(f"Plotting into {cols} x {rows} grid")
    subplot_index: int = 0
    # results are grouped by query -> sort them by the query name
    sorted_query_results = sorted(results.items(), key=lambda i: natural_sort_key(i[0]))
    for query, query_results in sorted_query_results:
        subplot_index += 1
        ax: Axes = fig.add_subplot(rows, cols, subplot_index)
        ax.set_title(query)
        # sort the different results by the configuration they used
        for result in sorted(
            query_results, key=lambda r: natural_sort_key(r.experiment)
        ):
            plot_x = [0, *result.timestamps]
            plot_y = range(0, result.results_max + 1)
            # the result count will have (0, 0) added to the beginning
            if steps:
                ax.step(
                    plot_x,
                    plot_y,
                    lw=1,
                    alpha=0.8,
                    label=result.experiment,
                    color=colors[result.experiment],
                    where="post",
                )
            else:
                ax.plot(
                    plot_x,
                    plot_y,
                    lw=1,
                    alpha=0.8,
                    label=result.experiment,
                    color=colors[result.experiment],
                )
                ax.fill_betweenx(
                    plot_y,
                    [0, *result.timestamps_min],
                    [0, *result.timestamps_max],
                    alpha=0.2,
                    color=colors[result.experiment],
                )
            ax.plot(
                result.time,
                result.results_max,
                color=colors[result.experiment],
                marker="x",
            )
        ax_xbound_upper = int(ax.get_xbound()[1] + 1)
        ax_ybound_upper = int(ax.get_ybound()[1] + 1)
        ax.set_xbound(lower=0, upper=ax_xbound_upper)
        ax.set_ybound(lower=0, upper=ax_ybound_upper)
        ax.set_xlabel("time [s]")
        ax.set_ylabel("# results")
        ax.xaxis.grid(visible=True, alpha=0.5)
        ax.yaxis.grid(visible=True, alpha=0.5)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        handles, labels = ax.get_legend_handles_labels()
    lgd = fig.legend(
        handles=handles,
        labels=labels,
        bbox_to_anchor=(0.8, 0.1),
        loc="lower center",
        ncols=cols,
        # frameon=False,
    )
    fig.set_size_inches(cols * COLUMN_INCHES, rows * ROW_INCHES)
    fig.tight_layout(pad=1)
    return fig


def run_script(
    experiments: Path,
    output: Path,
    serif: bool,
    colormap: str,
    steps: bool,
    transparent: bool,
    dpi: int,
) -> None:
    info(f"Loading results from {experiments.absolute()}")
    results = load_results(experiments)
    configs = list(set(r.experiment for r in results))
    results = group_by_query(results)
    colors = get_colors(configs, colormap)
    info(f"Using colormap {colormap} to get {len(colors)} unique colours")
    if serif:
        rcParams["font.family"] = "serif"
        rcParams["mathtext.fontset"] = "dejavuserif"
    info(f"Plotting {len(results)} results at {dpi} dpi")
    fig = plot_timestamps(results, steps, colors, dpi)
    info(f"Saving figure to {output.absolute()}")
    fig.savefig(output, transparent=transparent)
