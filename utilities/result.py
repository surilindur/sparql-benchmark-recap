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
    results_min: int
    results_max: int
    time: float
    time_min: float
    time_max: float
    error: bool
    timestamps: List[float]
    timestamps_max: List[float]
    timestamps_min: List[float]
    http_requests: int
    http_requests_min: int
    http_requests_max: int

    def __init__(self, experiment: str, row: Dict[str, str | int | float]) -> None:
        # helper functions
        get_float = lambda k: float(row[k]) if len(row.get(k, "")) else 0
        get_ts_values = lambda k: (
            sorted(float(t) / TIME_DIVISOR for t in row[k].split(LIST_SEPARATOR))
            if len(row.get(k, ""))
            else []
        )
        # actually assigning the data
        self.experiment = experiment
        self.name = row["name"]
        self.id = row["id"]
        self.results = round(get_float("results"))
        self.results_min = round(get_float("resultsMin"))
        self.results_max = round(get_float("resultsMax"))
        self.time = get_float("time") / TIME_DIVISOR
        self.time_min = get_float("timeMin") / TIME_DIVISOR
        self.time_max = get_float("timeMax") / TIME_DIVISOR
        self.error = row["error"] == "true"
        self.timestamps = get_ts_values("timestamps")
        self.timestamps_min = get_ts_values("timestampsMin")
        self.timestamps_max = get_ts_values("timestampsMax")
        self.http_requests = round(get_float("httpRequests"))
        self.http_requests_min = round(get_float("httpRequestsMin"))
        self.http_requests_max = round(get_float("httpRequestsMax"))

    def diefficiency(self, linear: bool = False) -> float:
        previous_timestamp = 0
        diefficiency_total = 0
        result_count = 0
        for t in self.timestamps:
            x = t - previous_timestamp
            y = result_count + (0.5 if linear else 0)
            diefficiency_total += x * y
            previous_timestamp = t
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
