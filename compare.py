"""One sequential comparison: 12 scenarios, four controls, ten GRASP seeds."""
import argparse
import csv
import json
import platform
import statistics
import subprocess
from pathlib import Path
from experiment import run_native, verify
from prepare import CASES, ROOT, digest

METHODS = ("briggs", "mis", "tabu", "adg", "grasp")

def summarize(rows, directory):
    summaries = []
    comparisons = []
    for name in CASES:
        for regime in ("unit", "weighted"):
            scenario = {}
            for method in METHODS:
                group = [r for r in rows if (r["name"], r["regime"], r["method"]) ==
                         (name, regime, method)]
                valid = [r for r in group if r["status"] == "ok"]
                weights = [r["weight"] for r in valid]
                summary = dict(graph=name, regime=regime, method=method,
                               valid=len(valid), failures=len(group)-len(valid),
                               expected=10 if method=="grasp" else 1,
                               mean=statistics.mean(weights) if weights else "",
                               best=max(weights) if weights else "",
                               sd=statistics.stdev(weights) if len(weights)>1 else "",
                               seconds=statistics.mean(r["elapsed"] for r in valid) if valid else "")
                summaries.append(summary)
                scenario[method] = summary
            complete = all(s["valid"] == s["expected"] for s in scenario.values())
            baseline = max((scenario[m]["best"] for m in METHODS[:-1]
                            if scenario[m]["valid"]), default=None)
            mean = scenario["grasp"]["mean"]
            gain = ""
            if complete:
                gain = 100*(mean-baseline)/baseline if baseline else mean-baseline
            comparisons.append(dict(graph=name, regime=regime, complete=complete,
                                    grasp_mean=mean, best_control=baseline,
                                    gain_percent=gain if baseline else "",
                                    gain_absolute=mean-baseline if complete else ""))
    for filename, data in [("summary.csv", summaries), ("comparison.csv", comparisons)]:
        with (directory/filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    complete = all(r["complete"] for r in comparisons)
    wins = sum(r["complete"] and
               (r["gain_percent"] >= 1 if r["best_control"] else r["gain_absolute"] > 0)
               for r in comparisons)
    losses = sum(r["complete"] and
                 (r["gain_percent"] < -1 if r["best_control"] else r["gain_absolute"] < 0)
                 for r in comparisons)
    status = "inconclusiva" if not complete else "atendida" if wins>=8 and losses<=2 else "não atendida"
    text = [
        "# Comparação das heurísticas a 30 segundos", "",
        "Uma execução por controle determinístico e dez sementes por cenário do GRASP. "
        "O limite da busca tabu também é de 100.000 iterações, com duração tabu 7. "
        "As construtivas terminam após uma passagem completa. Os tempos incluem preparação e inicialização.",
        "", "| Grafo | Pesos | Média GRASP | Melhor controle | Ganho (%) | Completo |",
        "|---|---|---:|---:|---:|---|"]
    for r in comparisons:
        gain = f"{r['gain_percent']:.3f}" if r["gain_percent"]!="" else "—"
        text.append(f"| {r['graph']} | {r['regime']} | {r['grasp_mean']} | "
                    f"{r['best_control']} | {gain} | {r['complete']} |")
    text += ["", f"Hipótese operacional {status}. Ganho de pelo menos 1% em {wins}/12 cenários "
             f"e perda superior a 1% em {losses}/12. "
             "O critério é descritivo. Controles sem resultado válido tornam a comparação incompleta."]
    (directory/"RELATORIO.md").write_text("\n".join(text)+"\n", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("comparacao_30s"))
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    for spec in json.loads((ROOT/"instances"/"manifest.json").read_text()):
        for ext, key in [(".col","graph_sha256"), (".weights","weights_sha256")]:
            if digest(ROOT/"instances"/(spec["name"]+ext))!=spec[key]:
                raise ValueError("Instance hash mismatch")
    args.out.mkdir(parents=True, exist_ok=False)
    sources = ["grasp.cpp", "controls.hpp", "experiment.py", "compare.py"]
    metadata = dict(platform=platform.platform(), python=platform.python_version(),
                    binary_sha256=digest(binary), budget=30, seeds=list(range(1,11)),
                    source_sha256={s:digest(ROOT/s) for s in sources})
    (args.out/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    rows = []
    for name in CASES:
        for regime in ("unit","weighted"):
            for method in METHODS:
                seeds = range(1,11) if method=="grasp" else [1]
                for seed in seeds:
                    graph = ROOT/"instances"/(name+".col")
                    weights = "-" if regime=="unit" else str(ROOT/"instances"/(name+".weights"))
                    command = [str(binary),str(graph),weights,str(CASES[name][2]),str(seed),"30"]
                    row = dict(name=name,regime=regime,method=method,seed=seed,budget=30)
                    try:
                        result = run_native(command,30,method)
                        if len(result)!=1 or result[0]["budget"]!=30:
                            raise ValueError("invalid result")
                        row.update(result[0])
                        verify(name,regime,row)
                        row["status"]="ok"
                    except (AssertionError,ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
                        row = dict(name=name,regime=regime,method=method,seed=seed,
                                   budget=30,status="failed",error=str(error))
                    rows.append(row)
                    with (args.out/"runs.jsonl").open("a",encoding="utf-8") as stream:
                        stream.write(json.dumps(row)+"\n")
                    summarize(rows,args.out)
                    print(f"{len(rows)}/168 {name} {regime} {method} seed={seed} "
                          f"{row['status']} weight={row.get('weight','—')}",flush=True)

if __name__ == "__main__":
    main()
