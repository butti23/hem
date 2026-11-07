"""Single-thread fallback for machines without a C++20 compiler."""
import json
import random
import sys
from time import perf_counter
from prepare import CASES, ROOT, load_graph

def solve(name, regime, seed, limits):
    n, edges = load_graph(name)
    k = CASES[name][2]
    w = [1]*n if regime == "unit" else list(map(int, (ROOT/"instances"/(name+".weights")).read_text().split()))
    start = perf_counter()
    deadline = start + max(limits)
    rng = random.Random(seed)
    adj = [set() for _ in w]
    for v, u in edges:
        adj[v].add(u)
        adj[u].add(v)
    order = sorted(range(n), key=lambda v: -w[v]/(1+len(adj[v])))
    product = []
    for v in range(n):
        for j in range(k):
            neighbors = [u*k+j for u in adj[v]]
            neighbors.extend(v*k+i for i in range(k) if i != j)
            product.append(sum(1 << x for x in neighbors))
    results = []
    best, best_weight = [0]*n, 0
    restarts = moves = 0
    checkpoints = iter(sorted(limits))
    following = next(checkpoints)

    def record(now):
        nonlocal following
        while following is not None and now >= start + following:
            results.append(dict(budget=following, weight=best_weight, colors=best[:],
                                restarts=restarts, moves=moves, elapsed=now-start))
            following = next(checkpoints, None)

    def refill(colors, score):
        for v in order:
            if colors[v] == 0:
                blocked = {colors[u] for u in adj[v]}
                for j in range(1, k+1):
                    if j not in blocked:
                        colors[v] = j
                        score += w[v]
                        break
        return score

    def publish(colors, score):
        nonlocal best, best_weight
        now = perf_counter()
        record(now)
        if now < deadline and score > best_weight:
            best, best_weight = colors[:], score

    while perf_counter() < deadline:
        restarts += 1
        colors, score = [0]*n, 0
        active = (1 << (n*k))-1
        while active and perf_counter() < deadline:
            scan, candidates = active, []
            while scan:
                bit = scan & -scan
                x = bit.bit_length()-1
                candidates.append((x, w[x//k]/(1+(product[x]&active).bit_count())))
                scan ^= bit
            low = min(value for _,value in candidates)
            high = max(value for _,value in candidates)
            threshold = high - 0.2*(high-low)
            x = rng.choice([x for x,value in candidates if value >= threshold])
            v, j = divmod(x, k)
            colors[v] = j+1
            score += w[v]
            active &= ~(product[x] | (1 << x))
            publish(colors, score)
        while perf_counter() < deadline:
            score = refill(colors, score)
            publish(colors, score)
            winner, top = colors, score
            for v in range(n):
                if perf_counter() >= deadline:
                    break
                if colors[v]:
                    trial = colors[:]
                    trial[v] = 0
                    value = refill(trial, score-w[v])
                    if value > top:
                        winner, top = trial, value
                        publish(trial, value)
            if top == score:
                break
            colors, score = winner, top
            moves += 1
    record(perf_counter())
    return results

if __name__ == "__main__":
    name, regime, seed, *limits = sys.argv[1:]
    print(json.dumps(solve(name, regime, int(seed), list(map(float, limits)))))
