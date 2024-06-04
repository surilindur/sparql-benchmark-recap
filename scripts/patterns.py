from typing import Dict, Set, List
from pathlib import Path
from rdflib.term import Variable, Literal, URIRef, Node, BNode
from rdflib.graph import Graph
from rdflib.paths import Path as SPARQLPath, AlternativePath, SequencePath, InvPath, NegatedPath, MulPath
from rdflib.plugins.sparql import prepareQuery
from csv import DictWriter
from logging import info, debug
from argparse import ArgumentParser


QUERY_EXCLUSIONS: Set[str] = set(("complex",))
QUERY_EXTENSIONS: Set[str] = set((".sparql", ".rq"))
QUERY_DELIMITER: str = "\n\n"

class TriplePattern(object):
    def __init__(self, s: URIRef | BNode | Variable, p: URIRef | SPARQLPath, o: URIRef | Literal | Variable) -> None:
        # this is super ugly and not correct, but provides some approximation
        if isinstance(s, BNode) or isinstance(s, Variable):
            self.s = Variable("s")
            self.s_var = True
        else:
            self.s = s
            self.s_var = False
        if isinstance(o, BNode) or isinstance(o, Variable):
            self.o = Variable("o")
            self.o_var = True
        else:
            self.o = o
            self.o_var = False
        self.p = p
    
    def __repr__(self) -> str:
        return " ".join(self.stringify_term(t) for t in (self.s, self.p, self.o))
    
    def stringify_term(self, term: URIRef | Variable | SPARQLPath) -> str:
        if isinstance(term, URIRef):
            return f"<{term.toPython()}>"
        elif isinstance(term, Variable) or isinstance(term, BNode):
            return term.toPython()
        elif isinstance(term, NegatedPath):
            return "!" + self.stringify_term(term.args)
        elif isinstance(term, InvPath):
            return "~" + self.stringify_term(term.arg)
        elif isinstance(term, MulPath):
            return self.stringify_term(term.path) + term.mod
        elif isinstance(term, AlternativePath):
            return "|".join(self.stringify_term(p) for p in term.args)
        elif isinstance(term, SequencePath):
            return "/".join(self.stringify_term(p) for p in term.args)
        print("UNKNOWN", type(term), term)
        return "UNKNOWN"

    def __hash__(self) -> int:
        return hash((self.s, self.p, self.o))

    def __eq__(self, value: object) -> bool:
        return isinstance(value, TriplePattern) and value.p == self.p and value.s == self.s and value.o == self.o

    # this is an ugly hack that works for most triples and patterns
    def match(self, s: Node, p: Node, o: Node) -> bool:
        if (self.s_var or self.s == s) and (self.o_var or self.o == o):
            if isinstance(self.p, URIRef):
                return self.p == p
            elif isinstance(self.p, AlternativePath) or isinstance(self.p, SequencePath) or isinstance(self.p, InvPath):
                return any(x == p for x in self.p.args)
            elif isinstance(self.p, NegatedPath):
                return any(x != p for x in self.p.args)
            elif isinstance(self.p, MulPath):
                return self.p.path == p
        return False


def register_args(parser: ArgumentParser) -> None:
    parser.description = "Produce a report of triple patterns and their matches in SolidBench"
    parser.add_argument(
        "--pods",
        help="Path to the SolidBench dataset pods",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--queries",
        help="Path to the SolidBench queries",
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


def extract_patterns(query_strings: Dict[str, str]) -> Dict[str, List[TriplePattern]]:
    output: Dict[str, TriplePattern] = {}
    pattern_count = 0
    for query_id, query_string in query_strings.items():
        query = prepareQuery(query_string)
        queue = [query.algebra]
        query_patterns = []
        while queue:
            item = queue.pop(0)
            if isinstance(item, dict):
                for key, value in item.items():
                    if key == "triples":
                        for pattern in [p for p in value if len(p) == 3]:
                            pattern_count += 1
                            query_patterns.append(TriplePattern(*pattern))
                    else:
                        queue.append(value)
        output[query_id] = query_patterns
    info(f"Extracted {pattern_count} patterns from {len(query_strings)} queries")
    return output


def load_queries(path: Path) -> Dict[str, str]:
    output: Dict[str, str] = {}
    for fp in path.iterdir():
        if any(kw in fp.name for kw in QUERY_EXCLUSIONS):
            info(f"Skipping {fp.name}")
            continue
        if any(fp.name.endswith(ext) for ext in QUERY_EXTENSIONS):
            info(f"Loading {fp.name}")
            with open(fp, "r") as query_file:
                query_name = fp.name.split(".")[0]
                query_strings = query_file.read().split(QUERY_DELIMITER)
                for i in range(0, len(query_strings)):
                    output[f"{query_name}-{i}"] = query_strings[i]
    info(f"Loaded {len(output)} SolidBench queries from {path}")
    return output


def run_script(pods: Path, queries: Path, output: Path, extensions: str) -> None:
    query_strings = load_queries(queries)
    query_patterns = extract_patterns(query_strings)

    info(f"Processing SolidBench dataset from {pods}")

    rdf_ext = set(extensions.split(","))

    pattern_metrics: Dict[TriplePattern, Dict[str, int | Set[str | Path]]] = {}

    for query, patterns in query_patterns.items():
        for pattern in patterns:
            if pattern not in pattern_metrics:
                pattern_metrics[pattern] = {
                    "matching_documents": set(),
                    "matching_triples": 0,
                    "matching_pods": set(),
                    "containing_queries": set([ query ]),
                }
            else:
                pattern_metrics[pattern]["containing_queries"].add(query)

    total_documents = 0
    total_triples = 0
    total_pods = 0

    for pod in pods.iterdir():
        info(f"Processing pod {pod}")
        total_pods += 1
        path_queue = set(pod.iterdir())
        while path_queue:
            path = path_queue.pop()
            if path.is_dir():
                path_queue.update(path.iterdir())
            elif path.is_file() and any(path.name.endswith(ext) for ext in rdf_ext):
                data = Graph()
                data.parse(path)
                total_documents += 1
                for s, p, o in data:
                    total_triples += 1
                    for pattern, metrics in pattern_metrics.items():
                        if pattern.match(s, p, o):
                            metrics["matching_triples"] += 1
                            metrics["matching_pods"].add(pod)
                            metrics["matching_documents"].add(path)
            else:
                debug(f"Skipping: {path}")

    for pattern, metrics in pattern_metrics.items():
        metrics["pattern"] = pattern
        metrics["total_documents"] = total_documents
        metrics["total_pods"] = total_pods
        metrics["total_triples"] = total_triples
        metrics["total_queries"] = len(query_patterns)
        metrics["matching_documents"] = len(metrics["matching_documents"])
        metrics["matching_pods"] = len(metrics["matching_pods"])
        metrics["containing_queries"] = len(metrics["containing_queries"])

    info(f"Dumping metrics to {output}")

    fieldnames = ["pattern", "containing_queries", "total_queries", "matching_pods", "total_pods", "matching_documents", "total_documents", "matching_triples", "total_triples"]
    with open(output, "w") as output_file:
        writer = DictWriter(output_file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(pattern_metrics.values())
