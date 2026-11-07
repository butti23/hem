"""Verify the completed independent runs and write their experimental report."""
from collections import Counter
from pathlib import Path
import json
import statistics
import sys
from experiment import verify
from prepare import CASES, ROOT, load_graph
from exact_dense import optimum

def fmt(value):
    return f"{value:.2f}".replace(".",",")

def report(directory):
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    budgets = (5,10,15,30)
    keys = Counter((r["name"],r["regime"],r["seed"],r["budget"]) for r in rows)
    expected = {(name,regime,seed,t) for name in CASES for regime in ("unit","weighted")
                for seed in range(1,11) for t in budgets}
    if set(keys)!=expected or any(n!=1 for n in keys.values()):
        raise ValueError(f"Bateria incompleta ou duplicada: {len(keys)} de {len(expected)} combinações.")
    valid = [r for r in rows if r["status"]=="ok"]
    for row in valid:
        verify(row["name"],row["regime"],row)
        assert row["external_run_elapsed"]<=row["budget"]
    n,edges = load_graph("DSJC125.9")
    weights = list(map(int,(ROOT/"instances"/"DSJC125.9.weights").read_text().split()))
    dense_opt = optimum(weights,edges,4)
    assert optimum([1]*n,edges,4)==CASES["DSJC125.9"][3]
    lines = ["# Qualidade do GRASP por orçamento","",
        f"{len(valid)} de {len(rows)} execuções produziram soluções validadas. "
        "Cada célula de média usa apenas execuções válidas, com até dez sementes por cenário e prazo. "
        "Uma unidade a mais significa um vértice adicional no regime unitário ou uma unidade de peso no heterogêneo.","",
        "| Grafo | Pesos | 5 s | 10 s | 15 s | 30 s | Melhor a 30 s | Referência ótima |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    gains = []
    for name,(_,_,k,unit_opt) in CASES.items():
        for regime,label in [("unit","Unitários"),("weighted","Heterogêneos")]:
            groups = [[r["weight"] for r in valid if (r["name"],r["regime"],r["budget"])==(name,regime,t)]
                      for t in budgets]
            means = [statistics.mean(g) if g else None for g in groups]
            cells = " | ".join(fmt(v) if v is not None else "—" for v in means)
            reference = unit_opt if regime=="unit" else dense_opt if name=="DSJC125.9" else "—"
            if isinstance(reference,int):
                assert all(w<=reference for g in groups for w in g)
            if all(len(g)==10 for g in groups) and means[0]:
                gains.append((100*(means[-1]/means[0]-1),name,label))
            lines.append(f"| {name} (k={k}) | {label} | {cells} | {max(groups[-1],default='—')} | {reference} |")
    lines += ["","## Efeito do tempo","",
              "| Orçamento | Execuções unitárias válidas | Atingiram o ótimo | DSJC ponderado no ótimo / válidas |",
              "|---:|---:|---:|---:|"]
    for t in budgets:
        unit = [r for r in valid if r["regime"]=="unit" and r["budget"]==t]
        dense = [r for r in valid if (r["name"],r["regime"],r["budget"])==("DSJC125.9","weighted",t)]
        hits = sum(r["weight"]==CASES[r["name"]][3] for r in unit)
        lines.append(f"| {t} s | {len(unit)} | {hits} | {sum(r['weight']==dense_opt for r in dense)} / {len(dense)} |")
    if gains:
        gain,name,label = max(gains)
        lines += ["",f"Entre os {len(gains)} cenários com dez sementes válidas em cada prazo, "
            f"{sum(g>0 for g,_,_ in gains)} aumentaram o peso médio de 5 para 30 s, "
            f"{sum(g==0 for g,_,_ in gains)} empataram e {sum(g<0 for g,_,_ in gains)} diminuíram. "
            f"A maior variação relativa foi de {fmt(gain)}% em {name} ({label.lower()}). "
            "Cada prazo corresponde a um processo independente e as médias são descritivas desta bateria."]
    lines += ["","## Interpretação e reprodução","",
        "As referências unitárias são os valores de αk publicados na Tabela 4 de "
        "[Kuryatnikova, Sotirov e Vera](https://arxiv.org/pdf/2001.09644). "
        f"Para DSJC125.9 heterogêneo, a enumeração exata das classes de cor dá {dense_opt}. "
        "O travessão nos demais cenários ponderados indica que o ótimo não foi determinado. "
        "A hipótese sobre os quatro controles exige executar também esses métodos.","",
        "O CSV informa média, melhor peso, desvio-padrão amostral, descarte, contagem mantida, reinícios, "
        "melhorias, tempo e falhas. O JSONL preserva as cores e a medição externa de cada execução. "
        "O README descreve os comandos e o controle de prazo. O registro de ambiente documenta o Linux, "
        "a memória visível à máquina virtual e o compilador usados."]
    (directory/"RELATORIO.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    report(Path(sys.argv[1]))
