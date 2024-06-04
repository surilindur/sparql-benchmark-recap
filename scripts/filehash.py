from typing import List, Dict
from logging import info, warn
from pathlib import Path
from hashlib import md5
from json import dump
from argparse import ArgumentParser


def register_args(parser: ArgumentParser) -> None:
    parser.description = "Calculate metrics about a SolidBench RDF dataset on disk"
    parser.add_argument(
        "--path",
        help="Path to the directory or file to calculate hashes for",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        help="Path to serialize results to",
        required=True,
        type=Path,
    )


def run_script(path: Path, output: Path) -> None:
    info(f"Calculating file hashes for {path}")

    hashes: Dict[str, str] = {}
    queue: List[Path] = list(path.iterdir()) if path.is_dir() else [path]

    while queue:
        path = queue.pop(0)
        if path.is_file():
            with path.open("rb") as fp:
                hashes[path.absolute().as_posix()] = md5(
                    fp.read(), usedforsecurity=False
                ).hexdigest()
        elif path.is_dir():
            for fp in path.iterdir():
                queue.append(fp)
        else:
            warn(f"Skipping {path}")

    info(f"Dumping hashes to {output}")

    with output.open("w", encoding="utf-8") as fp:
        dump(obj=hashes, fp=fp, sort_keys=True, ensure_ascii=False, indent=2)

    info("Hash calculation finished")
