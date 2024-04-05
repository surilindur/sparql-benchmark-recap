from os import scandir
from sys import argv
from pathlib import Path
from typing import Dict
from argparse import ArgumentParser, _SubParsersAction
from logging import DEBUG, INFO, ERROR, basicConfig, exception
from importlib import import_module

log_levels: Dict[str, int] = {"debug": DEBUG, "info": INFO, "error": ERROR}
scripts_module = "scripts"


def setup_logging(level: str) -> None:
    basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_levels[level],
    )


def load_scripts(subparsers: _SubParsersAction) -> Dict[str, callable]:
    path = Path(__file__).parent.joinpath(scripts_module)
    scripts: Dict[str, callable] = {}
    for fp in scandir(path):
        if fp.name.endswith(".py"):
            module_name = fp.name.removesuffix(".py")
            try:
                module = import_module(f"{scripts_module}.{module_name}")
                if hasattr(module, "register_args") and hasattr(module, "run_script"):
                    parser = subparsers.add_parser(module_name)
                    getattr(module, "register_args")(parser)
                    scripts[module_name] = getattr(module, "run_script")
            except Exception as ex:
                exception(ex)
    return scripts


def run() -> None:
    parser = ArgumentParser(
        description=(
            "Experimental scripts to analyse results "
            "from the SPARQL benchmark runner"
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--logging", choices=log_levels.keys(), default="info")
    subparsers = parser.add_subparsers(dest="script")
    scripts = load_scripts(subparsers)
    args = parser.parse_known_args(argv[1:])[0]
    setup_logging(args.logging)
    scripts[args.script](
        **{k: v for k, v in args._get_kwargs() if k not in ("script", "logging")}
    )


if __name__ == "__main__":
    run()
