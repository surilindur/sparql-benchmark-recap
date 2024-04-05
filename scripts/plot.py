from pathlib import Path
from csv import DictReader
from sys import argv
from typing import Tuple, Dict, List, Set, Any, Callable
from math import sqrt, ceil, floor
from numpy import arange
from matplotlib import rcParams
from matplotlib.axes import Axes
from matplotlib.ticker import MaxNLocator
from matplotlib.figure import Figure
from matplotlib.pyplot import figure, get_cmap


ROW_INCHES: int = 4
COLUMN_INCHES: int = 6
COLORMAP: str = "nipy_spectral"
IMAGE_EXTENSION: str = "svg"

rcParams["font.family"] = "serif"
rcParams["mathtext.fontset"] = "dejavuserif"


def get_colors(
    timestamps: Dict[str, Dict[str, List[float]]]
) -> Dict[str, Tuple[float, float, float, float]]:
    configs: Set[str] = set()
    for query_data in timestamps.values():
        configs.update(query_data.keys())
    configs_list: List[str] = list(sorted(configs))
    cmap = get_cmap(COLORMAP).resampled(len(configs_list))
    colors = cmap(arange(0, cmap.N))
    return {configs_list[i]: colors[i] for i in range(0, len(configs_list))}


def get_column(
    result_directory: Path, column: str, converter: Callable, error_value: Any
) -> Dict[str, Dict[str, Any | None]]:
    query_config_column: Dict[str, Dict[str, Any]] = {}
    for config_directory in result_directory.iterdir():
        if not config_directory.is_dir():
            continue
        config_name: str = config_directory.name.replace("-", " ")
        config_results: Path = config_directory.joinpath("query-times.csv")
        if not config_results.exists():
            print(f"Results not found: {config_results}")
            continue
        with open(config_results, "r") as result_file:
            reader: DictReader = DictReader(result_file, delimiter=";")
            for row in reader:
                query: str = row["name"].replace("-", " ") + "." + row["id"]
                if query not in query_config_column:
                    query_config_column[query] = {}
                if row["error"] == "false":
                    try:
                        query_config_column[query][config_name] = converter(row[column])
                    except KeyError:
                        query_config_column[query][config_name] = error_value
                else:
                    query_config_column[query][config_name] = error_value
    # for query in list(query_config_column.keys()):
    #    if all(v == error_value for v in query_config_column[query].values()):
    #        print("Remove query with no results", query)
    #        del query_config_column[query]
    return query_config_column


def get_timestamps(result_directory: Path) -> Dict[str, Dict[str, List[float]]]:
    def converter(column: str) -> List[float]:
        return list(int(i) / 1000 for i in column.split(" ") if i)

    timestamps = get_column(result_directory, "timestamps", converter, [])
    for data in timestamps.values():
        for timestamp_values in data.values():
            timestamp_values.sort()
    return timestamps


def get_http_requests(result_directory: Path) -> Dict[str, Dict[str, int]]:
    def converter(column: str) -> int:
        return int(column)

    return get_column(result_directory, "httpRequests", converter, 0)


def get_query_errors(result_directory: Path) -> Dict[str, Dict[str, bool]]:
    def converter(column: str) -> bool:
        return column == "true"

    return get_column(result_directory, "error", converter, True)


def get_join_restarts(result_directory: Path) -> Dict[str, Dict[str, int]]:
    def converter(column: str) -> int:
        return int(column)

    return get_column(result_directory, "restarts", converter, 0)


def get_query_times(result_directory: Path) -> Dict[str, Dict[str, float]]:
    def converter(column: str) -> float:
        return int(column) / 1000

    return get_column(result_directory, "time", converter, 0)


def dief_k_full(timestamps: List[float]) -> float:
    integral: float = 0
    previous_result_count: int = 0
    previous_timestamp: float = 0
    for timestamp in timestamps:
        integral += (timestamp - previous_timestamp) * (previous_result_count + 0.5)
        previous_result_count += 1
        previous_timestamp = timestamp
    return round(integral, 3)


def plot_timestamps(
    timestamps: Dict[str, Dict[str, List[float]]],
    query_times: Dict[str, Dict[str, float]],
    figure_path: Path,
    step_not_line: bool = True,
) -> None:
    fig: Figure = figure(dpi=300)
    rows: int = floor(sqrt(len(timestamps)))
    cols: int = ceil(len(timestamps) / rows)
    print("Plotting into", cols, "x", rows, "grid")
    colors: Dict[str, Tuple[float, float, float, float]] = get_colors(timestamps)
    subplot_index: int = 0
    for query, query_data in sorted(timestamps.items(), key=lambda d: d[0]):
        subplot_index += 1
        ax: Axes = fig.add_subplot(rows, cols, subplot_index)
        ax.set_title(query)
        for config, config_timestamps in sorted(query_data.items(), key=lambda d: d[0]):
            result_count: int = len(config_timestamps)
            # the result count will have (0, 0) added to the beginning
            if step_not_line:
                ax.step(
                    x=[0, *config_timestamps],
                    y=range(0, result_count + 1),
                    lw=1,
                    alpha=0.8,
                    where="post",
                    label=config,
                    color=colors[config],
                )
            else:
                ax.plot(
                    [0, *config_timestamps],
                    range(0, result_count + 1),
                    lw=1,
                    alpha=0.8,
                    label=config,
                    color=colors[config],
                )
            ax.plot(
                query_times[query][config],
                result_count,
                alpha=0.8,
                lw=1,
                marker="x",
                color=colors[config],
            )
            # this adds too much noise to the chart
            # if result_count > 0:
            #    ax.plot(
            #        config_timestamps[-1],
            #        result_count,
            #        alpha=0.8,
            #        lw=1,
            #        marker=".",
            #        color=colors[config],
            #    )
            #    ax.axvline(
            #        query_times[query][config],
            #        alpha=0.4,
            #        linestyle="--",
            #        lw=1,
            #        color=colors[config],
            #    )
        ax_xbound_upper = int(ax.get_xbound()[1] + 1)
        ax_ybound_upper = int(ax.get_ybound()[1] + 1)
        ax.set_xbound(lower=0, upper=ax_xbound_upper)
        ax.set_ybound(lower=0, upper=ax_ybound_upper)
        ax.set_xlabel("time [s]")
        ax.set_ylabel("# results")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        handles, labels = ax.get_legend_handles_labels()
    lgd = fig.legend(
        handles=handles,
        labels=labels,
        # bbox_to_anchor=(0.9, 0.05),
        bbox_to_anchor=(0.5, 0),
        # loc="lower right",
        loc="upper center",
        ncols=int(sqrt(len(labels))),
        frameon=False,
    )
    fig.set_size_inches(cols * COLUMN_INCHES, rows * ROW_INCHES)
    fig.tight_layout(pad=1, h_pad=1, w_pad=1)
    fig.savefig(figure_path, bbox_extra_artists=(lgd,), bbox_inches="tight")


def plot_http_requests(requests: Dict[str, Dict[str, int]], figure_path: Path) -> None:
    fig: Figure = figure(dpi=300)
    rows: int = int(ceil(sqrt(len(requests))))
    cols: int = int(ceil(len(requests) / rows))
    print("Plotting into", cols, "x", rows, "grid")
    colors: Dict[str, Tuple[float, float, float, float]] = get_colors(requests)
    subplot_index: int = 0
    for query, query_data in sorted(requests.items(), key=lambda d: d[0]):
        subplot_index += 1
        ax: Axes = fig.add_subplot(rows, cols, subplot_index)
        ax.set_title(query)
        request_labels: List[str] = []
        request_values: List[int] = []
        for config, config_requests in sorted(query_data.items(), key=lambda d: d[0]):
            request_labels.append(config)
            request_values.append(config_requests)
        request_colors: List[str] = [colors[k] for k in request_labels]
        ax.bar(
            request_labels,
            request_values,
            width=0.2,
            label=request_labels,
            color=request_colors,
            alpha=0.8,
            lw=1,
        )
        ax_ybound_upper = int(ax.get_ybound()[1] + 1)
        ax.set_ybound(lower=0, upper=ax_ybound_upper)
        ax.set_ylabel("# http requests")
        ax.xaxis.set_visible(False)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles=handles,
        labels=labels,
        bbox_to_anchor=(0.9, 0.05),
        loc="lower right",
        ncols=int(sqrt(len(labels))),
        frameon=False,
    )
    fig.set_size_inches(cols * COLUMN_INCHES, rows * ROW_INCHES)
    fig.tight_layout(pad=1, h_pad=1, w_pad=1)
    fig.savefig(figure_path)


def dump_interesting_metrics(
    timestamps: Dict[str, Dict[str, List[float]]],
    query_times: Dict[str, Dict[str, float]],
    requests: Dict[str, Dict[str, int]],
    restarts: Dict[str, Dict[str, int]],
    errors: Dict[str, Dict[str, bool]],
    file_path: Path,
) -> None:
    columns: List[str] = [
        "query",
        "config",
        "error",
        "httprequests",
        "firstresult",
        "lastresult",
        "termination",
        "diefficiency",
        "restarts",
    ]
    csv_sep: str = "\t"
    with open(file_path, "w") as metrics_file:
        metrics_file.write(csv_sep.join(columns) + "\n")
        for query, query_data in timestamps.items():
            for config, config_timestamps in query_data.items():
                metrics_file.write(
                    csv_sep.join(
                        str(k)
                        for k in (
                            query,
                            config,
                            (
                                "true"
                                if errors[query][config] or len(config_timestamps) < 1
                                else "false"
                            ),
                            requests[query][config],
                            config_timestamps[0] if len(config_timestamps) else "",
                            config_timestamps[-1] if len(config_timestamps) else "",
                            query_times[query][config],
                            (
                                dief_k_full(config_timestamps)
                                if len(config_timestamps)
                                else ""
                            ),
                            restarts[query][config],
                        )
                    )
                    + "\n"
                )


def filter_data(
    config_prefix: str | None = None,
    query_prefixes: List[str] | None = None,
    dictionary: Dict[str, Dict[str, Any]] = {},
) -> Dict[str, Dict[str, Any]]:
    # if not query_prefixes:
    #    query_prefixes = ["interactive discover 8.0", "interactive discover 2.3"]
    if query_prefixes or config_prefix:
        for query, query_data in list(dictionary.items()):
            if query_prefixes and not any(query.startswith(p) for p in query_prefixes):
                del dictionary[query]
            elif config_prefix:
                for config in list(query_data.keys()):
                    if (
                        not config.startswith("baseline")
                        and not config.startswith("overhead")
                        and not config.startswith(config_prefix)
                    ):
                        del query_data[config]
    return dictionary


def plot_all_results(prefix: str | None) -> None:
    results_path: Path = Path(__file__).parent.parent.joinpath("results")
    for result_directory in results_path.iterdir():
        timestamps = get_timestamps(result_directory)
        query_terminations = get_query_times(result_directory)
        plot_timestamps(
            filter_data(config_prefix=prefix, dictionary=timestamps),
            filter_data(config_prefix=prefix, dictionary=query_terminations),
            result_directory.joinpath(
                f'timestamps-{prefix or "all"}.{IMAGE_EXTENSION}'
            ),
        )
        http_requests = get_http_requests(result_directory)
        join_restarts = get_join_restarts(result_directory)
        plot_http_requests(
            filter_data(config_prefix=prefix, dictionary=http_requests),
            result_directory.joinpath(
                f'httprequests-{prefix or "all"}.{IMAGE_EXTENSION}'
            ),
        )
        query_errors = get_query_errors(result_directory)
        dump_interesting_metrics(
            filter_data(config_prefix=prefix, dictionary=timestamps),
            filter_data(config_prefix=prefix, dictionary=query_terminations),
            filter_data(config_prefix=prefix, dictionary=http_requests),
            filter_data(config_prefix=prefix, dictionary=join_restarts),
            filter_data(config_prefix=prefix, dictionary=query_errors),
            result_directory.joinpath(f'metrics-{prefix or "all"}.tsv'),
        )


def run_script() -> None:
    plot_all_results(argv[1] if len(argv) > 1 else None)
