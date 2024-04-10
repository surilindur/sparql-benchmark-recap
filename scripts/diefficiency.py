from csv import DictWriter
from argparse import ArgumentParser
from typing import Dict, List
from pathlib import Path
from logging import info

from utilities.result import load_results
from utilities.sorting import natural_sort_key


def register_args(parser: ArgumentParser) -> None:
    parser.description = (
        "Calculate diefficiency at k "
        "when k is set to the total number of expected results"
    )
    parser.add_argument(
        "--experiments",
        help="Path containing the experiments to consider",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        help="Path to serialize the metrics file to",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--baseline",
        help="Output diefficiency multipliers relative to the chosen experiment",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--delimiter",
        help="Use the chosen delimiter",
        default="\t",
    )
    parser.add_argument(
        "--linear",
        help="Whether to use linear interpolation for answer distribution",
        default=False,
    )


def relative_to_baseline(
    results: Dict[str, Dict[str, float | None]],
    baseline: str,
) -> Dict[str, Dict[str, float | None]]:
    relative_results: Dict[str, Dict[str, float | None]] = {}
    for query, query_results in results.items():
        relative_query_results = {}
        for config, diefficiency in query_results.items():
            relative_query_results[config] = (
                diefficiency / query_results[baseline]
                if diefficiency and query_results[baseline]
                else None
            )
        relative_results[query] = relative_query_results
    return relative_results


def run_script(
    experiments: Path,
    output: Path,
    delimiter: str,
    linear: bool,
    baseline: str | None = None,
) -> None:

    info(f"Calculating diefficiency for output in {experiments.absolute()}")

    configs: List[str] = []
    queries: List[str] = []

    results: Dict[str, Dict[str, float | None]] = {}

    for result in load_results(experiments):
        query = result.query()
        if query not in results:
            results[query] = {}
        results[query][result.experiment] = (
            result.diefficiency(linear=linear) if not result.error else None
        )
        if query not in queries:
            queries.append(query)
        if result.experiment not in configs:
            configs.append(result.experiment)

    # if baseline is selected, convert all results to be relative to that one
    if baseline:
        results = relative_to_baseline(results, baseline)

    configs.sort(key=natural_sort_key)
    queries.sort(key=natural_sort_key)
    configs.insert(0, "query")

    with open(output, "w") as output_file:
        writer = DictWriter(output_file, fieldnames=configs, delimiter=delimiter)
        writer.writeheader()
        for query, experiment_results in results.items():
            writer.writerow({"query": query, **experiment_results})

    info(f"Wrote diefficiency to {output.absolute()}")
