from typing import Dict
from pathlib import Path
from rdflib import Graph
from yaml import dump
from logging import info, debug
from argparse import ArgumentParser


def register_args(parser: ArgumentParser) -> None:
    parser.description = "Calculate metrics about a SolidBench RDF dataset on disk"
    parser.add_argument(
        "--pods",
        help="Path to the SolidBench dataset pods",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        help="Path to serialize results to",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--extensions",
        help="Comma-separated list of extensions to parse as RDF",
        default=".nq",
    )


def run_script(pods: Path, output: Path, extensions: str) -> None:
    info(f"Calculating metrics for {pods}")

    rdf_ext = set(extensions.split(","))
    pod_metrics: Dict[Path, Dict[str, int]] = {}
    total_triples = 0
    total_files = 0

    for pod in pods.iterdir():
        info(f"Processing pod {pod}")
        path_queue = set(pod.iterdir())
        file_count = 0
        triple_count = 0
        while path_queue:
            path = path_queue.pop()
            if path.is_dir():
                path_queue.update(path.iterdir())
            elif path.is_file() and any(path.name.endswith(ext) for ext in rdf_ext):
                data = Graph()
                data.parse(path)
                triple_count += len(data)
                file_count += 1
            else:
                debug(f"Skipping: {path}")
        total_files += file_count
        total_triples += triple_count
        pod_metrics[pod.as_posix()] = {
            "files": file_count,
            "triples": triple_count,
        }

    info(f"Dumping metrics to {output}")

    with open(output, "w") as output_file:
        dump(
            {
                pods.as_posix(): {
                    "pods": len(pod_metrics),
                    "files": total_files,
                    "triples": total_triples,
                },
                **pod_metrics,
            },
            stream=output_file,
            allow_unicode=True,
        )
