from re import split
from typing import Iterable


# https://stackoverflow.com/questions/4836710/is-there-a-built-in-function-for-string-natural-sort
def natural_sort_key(s: str) -> Iterable[str | int]:
    return [int(t) if t.isdigit() else t.lower() for t in split(r"(\d+)", s)]
