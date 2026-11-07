"""Normalize the canonical graphs and freeze the two weight regimes."""
from pathlib import Path
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parent
CASES = {
    "myciel5": (47, 236, 4, 44), "myciel6": (95, 755, 3, 83),
    "1-Insertions_4": (67, 232, 3, 63), "1-FullIns_4": (93, 593, 3, 87),
    "queen6_6": (36, 290, 6, 32), "DSJC125.9": (125, 6961, 4, 16),
}

def load_graph(name):
    path = ROOT / "instances" / (name + ".col")
    header, *records = path.read_text().splitlines()
    n, m, _, _ = CASES[name]
    assert header.split() == ["p", "edge", str(n), str(m)]
    edges = []
    for record in records:
        tag, u, v = record.split()
        u, v = int(u)-1, int(v)-1
        assert tag == "e" and 0 <= u < v < n
        edges.append((u, v))
    assert len(set(edges)) == len(edges) == m
    return n, edges

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__ == "__main__":
    manifest = []
    for name, (n, m, k, optimum) in CASES.items():
        load_graph(name)
        rng = random.Random(42)
        directory = ROOT / "instances"
        weights = directory / (name + ".weights")
        weights.write_bytes((" ".join(str(rng.randint(1, 100)) for _ in range(n)) + "\n").encode())
        source = ("https://github.com/dynaroars/npbench/blob/master/instances/coloring/graph_color/"+name+".col"
                  if name != "DSJC125.9" else
                  "https://www2.informatik.hu-berlin.de/~wwwmaks/dimacs10/walshaw/graphs-colouring/DSJC125.9.graph")
        manifest.append(dict(name=name, n=n, edges=m, k=k, unit_optimum=optimum, source=source,
                             graph_sha256=digest(directory/(name+".col")), weights_sha256=digest(weights),
                             weights_generator="CPython random.Random(42).randint(1,100), restarted per graph"))
    (ROOT/"instances"/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
