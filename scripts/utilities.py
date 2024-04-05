from sys import argv
from csv import DictReader
from typing import Dict, Tuple, Set, List, Iterable
from pathlib import Path
from os import scandir


def load_results(path: Path) -> Dict[Tuple[str, str], Dict[str, any]]:
    output: Dict[Tuple[str, str], Dict[str, str]] = {}
    for fp in scandir(path):
        csv_path = Path(fp.path).joinpath("query-times.csv")
        with open(csv_path, "r") as csv_file:
            reader = DictReader(csv_file, delimiter=";")
            for row in reader:
                query_name = row["name"]
                query_id = row["id"]
                output[(fp.name, f"{query_name}-{query_id}")] = dict(row)
    return output


def load_common_results(path: Path) -> Dict[Tuple[str, str], Dict[str, any]]:
    successful_queries: Dict[str, Set[str]] = {}
    output = load_results(path)
    for (config, query), result in output.items():
        if result["error"] == "true" or result["results"] == "0":
            continue
        if config in successful_queries:
            successful_queries[config].add(query)
        else:
            successful_queries[config] = set((query,))
    query_sets: List[Set[str]] = list(successful_queries.values())
    common_successful: Set[str] = query_sets[0]
    for query_set in query_sets[1:]:
        common_successful = common_successful.intersection(query_set)
    for config, query in list(output.keys()):
        if query not in common_successful:
            del output[(config, query)]
    return output


def get_target_path() -> Path:
    return Path(argv[1]).resolve()


def get_config_format_string(configs: Iterable[str]) -> str:
    max_config_length = max(len(c) for c in configs)
    config_fmt = "{:" + str(max_config_length) + "s}"
    return config_fmt
