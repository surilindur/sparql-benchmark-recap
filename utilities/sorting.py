from re import split

# https://stackoverflow.com/questions/4836710/is-there-a-built-in-function-for-string-natural-sort
natural_sort_key = lambda s: [
    int(t) if t.isdigit() else t.lower() for t in split(r"(\d+)", s)
]
