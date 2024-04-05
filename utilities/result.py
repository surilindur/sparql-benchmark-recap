from os import scandir
from csv import DictReader
from typing import List, Dict
from pathlib import Path


TIME_DIVISOR = 1000
LIST_SEPARATOR = " "
COLUMN_SEPARATOR = ";"


class Result:
    name: str
    id: str
    experiment: str
    results: int
    time: float
    error: bool
    timestamps: List[float]
    http_requests: int

    def __init__(self, experiment: str, row: Dict[str, str | int | float]) -> None:
        self.experiment = experiment
        self.name = row["name"]
        self.id = row["id"]
        self.results = int(row["results"])
        self.time = int(row["time"]) / TIME_DIVISOR
        self.error = row["error"] == "true"
        self.timestamps = (
            list(int(t) / TIME_DIVISOR for t in row["timestamps"].split(LIST_SEPARATOR))
            if len(row["timestamps"]) > 0
            else []
        )
        self.timestamps.sort()
        self.http_requests = (
            int(row["httpRequests"]) if len(row["httpRequests"]) > 0 else 0
        )

    def diefficiency(self) -> float:
        previous_timestamp = 0
        diefficiency_total = 0
        result_count = 0
        for t in self.timestamps:
            diefficiency_total += (t - previous_timestamp) * (result_count + 0.5)
            result_count += 1
        return diefficiency_total

    def query(self) -> str:
        return f"{self.name}-{self.id}"


def load_results_from_file(experiment: str, path: Path) -> List[Result]:
    results: List[Result] = []
    with open(path, "r") as result_file:
        reader = DictReader(result_file, delimiter=COLUMN_SEPARATOR)
        for row in reader:
            results.append(Result(experiment, row))
    return results


def load_results(
    path: Path,
    subpath: List[str] = ["output", "query-times.csv"],
) -> List[Result]:
    results: List[Result] = []
    for fp in scandir(path):
        if fp.is_dir():
            experiment = fp.name
            result_path = path.joinpath(fp.name, *subpath)
            if result_path.is_file():
                results.extend(load_results_from_file(experiment, result_path))
    return results


def group_by_query(results: List[Result]) -> Dict[str, List[Result]]:
    results_by_query: Dict[str, List[Result]] = {}
    for result in results:
        if result.query() not in results_by_query:
            results_by_query[result.query()] = [result]
        else:
            results_by_query[result.query()].append(result)
    return results_by_query
