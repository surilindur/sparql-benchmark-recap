from os import scandir
from sys import argv
from pathlib import Path
from typing import Dict, Tuple, Set, List
from csv import DictReader
from statistics import mean

from scripts.utilities import get_config_format_string


def run_script() -> None:

    results: Path = Path(argv[1]).resolve()
    requests_by_config_and_query: Dict[Tuple[str, str], int] = {}
    first_result_by_config_and_query: Dict[Tuple[str, str], int] = {}
    last_result_by_config_and_query: Dict[Tuple[str, str], int] = {}
    finished_queries_by_config: Dict[str, int] = {}

    all_queries: Set[str] = set()
    failed_queries: Set[str] = set()

    print(f"Loading results from {results}")

    for fp in scandir(results):
        query_times: Path = Path(fp.path).joinpath("query-times.csv")
        print(f"Parsing {query_times}")
        with open(query_times, "r") as csv_file:
            reader: DictReader = DictReader(csv_file, delimiter=";")
            for row in reader:
                query_name: str = row["name"]
                query_id: str = row["id"]
                query: str = f"{query_name}-{query_id}"
                all_queries.add(query)
                if row["error"] == "true" or row["results"] == "0":
                    failed_queries.add(query)
                else:
                    if fp.name in finished_queries_by_config:
                        finished_queries_by_config[fp.name] += 1
                    else:
                        finished_queries_by_config[fp.name] = 1
                    result_times = row["timestamps"].split(" ")
                    first_result = int(result_times[0])
                    last_result = int(result_times[-1])
                    first_result_by_config_and_query[(fp.name, query)] = first_result
                    last_result_by_config_and_query[(fp.name, query)] = last_result
                    requests_by_config_and_query[(fp.name, query)] = int(
                        row["httpRequests"]
                    )

    print(f"Failed {len(failed_queries)} / {len(all_queries)} queries")

    requests_by_config: Dict[str, int] = {}
    first_result_by_config: Dict[str, List[int]] = {}
    last_result_by_config: Dict[str, List[int]] = {}

    for (config, query), requests in requests_by_config_and_query.items():
        if query not in failed_queries:
            if config not in requests_by_config:
                requests_by_config[config] = requests
                first_result_by_config[config] = [
                    first_result_by_config_and_query[(config, query)]
                ]
                last_result_by_config[config] = [
                    last_result_by_config_and_query[(config, query)]
                ]
            else:
                requests_by_config[config] += requests
                first_result_by_config[config].append(
                    first_result_by_config_and_query[(config, query)]
                )
                last_result_by_config[config].append(
                    last_result_by_config_and_query[(config, query)]
                )

    avg_first = {
        config: round(mean(times) / 1000, 2)
        for config, times in first_result_by_config.items()
    }
    avg_last = {
        config: round(mean(times) / 1000, 2)
        for config, times in last_result_by_config.items()
    }

    config_fmt = get_config_format_string(requests_by_config.keys())

    print(
        "\t".join(
            (config_fmt.format("config"), "done", "total", "#req", "first", "last")
        )
    )

    for config, requests in requests_by_config.items():
        print(
            "\t".join(
                (
                    config_fmt.format(config),
                    str(finished_queries_by_config[config]),
                    str(len(all_queries)),
                    str(requests),
                    str(avg_first[config]),
                    str(avg_last[config]),
                )
            )
        )
