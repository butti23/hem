import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from time import monotonic
from prepare import CASES, ROOT, digest, load_graph

def run_native(cmd, limit, method="grasp"):
    # Ubuntu/POSIX. Only GO..DONE is charged; parse and output have separate guards.
    import select
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          bufsize=0,env={**os.environ,"HEM_SUPERVISED":"1","HEM_METHOD":method}) as proc:
        def signal(expected, timeout):
            if not select.select([proc.stdout],[],[],max(0,timeout))[0]:
                raise subprocess.TimeoutExpired(cmd,timeout)
            if proc.stdout.readline().strip()!=expected:
                raise ValueError("unexpected worker signal")
        try:
            signal(b"READY",10)
            start = monotonic()
            proc.stdin.write(b"GO\n")
            signal(b"DONE",limit-(monotonic()-start))
            elapsed = monotonic()-start
            if elapsed>limit:
                raise subprocess.TimeoutExpired(cmd,limit)
            payload,_ = proc.communicate(timeout=10)
            if proc.returncode:
                raise subprocess.CalledProcessError(proc.returncode,cmd)
            data = json.loads(payload)
            for row in data:
                row["external_run_elapsed"] = elapsed
            return data
        finally:
            if proc.poll() is None:
                proc.kill()

def verify(name, regime, row):
    n, edges = load_graph(name)
    colors = row["colors"]
    weights = [1]*n if regime=="unit" else list(map(int,(ROOT/"instances"/(name+".weights")).read_text().split()))
    assert len(colors)==len(weights)==n and all(type(c) is int and 0<=c<=CASES[name][2] for c in colors)
    assert all(colors[u]==0 or colors[u]!=colors[v] for u,v in edges)
    weight = sum(w for w,c in zip(weights,colors) if c)
    assert weight==row["weight"]
    row.update(discard=sum(weights)-weight, kept=sum(bool(c) for c in colors))

def summarize(rows, out):
    groups = defaultdict(list)
    for row in rows:
        groups[row["name"],row["regime"],row["budget"]].append(row)
    with (out/"summary.csv").open("w",newline="") as f:
        writer = csv.writer(f)
        writer.writerow("graph regime budget valid failures mean best sd mean_discard mean_kept mean_restarts mean_moves mean_elapsed unit_optimum".split())
        for (name,regime,budget), group in sorted(groups.items()):
            valid = [r for r in group if r["status"]=="ok"]
            weights = [r["weight"] for r in valid]
            avg = lambda key: round(statistics.mean(r[key] for r in valid),4) if valid else ""
            writer.writerow([name,regime,budget,len(valid),len(group)-len(valid),avg("weight"),
                max(weights,default=""),round(statistics.stdev(weights),4) if len(weights)>1 else "",
                *(avg(k) for k in ("discard","kept","restarts","moves","elapsed")),
                CASES[name][3] if regime=="unit" else ""])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--binary",type=Path)
    p.add_argument("--seeds",type=int,default=10)
    p.add_argument("--paired",action="store_true",help="record four deadlines along one trajectory")
    p.add_argument("--out",type=Path,required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for spec in json.loads((ROOT/"instances"/"manifest.json").read_text()):
        for ext,key in [(".col","graph_sha256"),(".weights","weights_sha256")]:
            assert digest(ROOT/"instances"/(spec["name"]+ext))==spec[key]
    rows = []
    groups = [[5,10,15,30]] if args.paired else [[t] for t in (5,10,15,30)]
    for seed in range(1,args.seeds+1):
        for name in CASES:
            for regime in ("unit","weighted"):
                for limits in groups:
                    if args.binary:
                        graph = ROOT/"instances"/(name+".col")
                        weights = "-" if regime=="unit" else str(graph.with_suffix(".weights"))
                        cmd = [str(args.binary.resolve()),str(graph),weights,str(CASES[name][2]),str(seed)]
                    else:
                        cmd = [sys.executable,str(ROOT/"reference.py"),name,regime,str(seed)]
                    try:
                        cmd += list(map(str,limits))
                        if args.binary:
                            data = run_native(cmd,max(limits))
                        else:
                            proc = subprocess.run(cmd,capture_output=True,text=True,
                                                  timeout=max(limits)+1,check=True)
                            data = json.loads(proc.stdout)
                        assert [r["budget"] for r in data]==limits
                        for r in data:
                            verify(name,regime,r)
                            r["status"]="ok"
                    except (AssertionError,ValueError,subprocess.SubprocessError) as exc:
                        data = [dict(budget=t,status="failed",error=str(exc)) for t in limits]
                    with (args.out/"runs.jsonl").open("a") as f:
                        for r in data:
                            r.update(name=name,regime=regime,seed=seed)
                            print(json.dumps(r),file=f)
                            rows.append(r)
                    summarize(rows,args.out)
