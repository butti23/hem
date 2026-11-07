"""Independent exact reference for the small independence number of DSJC125.9."""
from prepare import ROOT, load_graph

def optimum(weights, edges, k):
    n = len(weights)
    all_vertices = (1 << n)-1
    compatible = [all_vertices ^ (1 << v) for v in range(n)]
    for u,v in edges:
        compatible[u] &= ~(1 << v)
        compatible[v] &= ~(1 << u)
    classes = []

    def enumerate_classes(mask, remaining, score):
        while remaining:
            bit = remaining & -remaining
            remaining ^= bit
            v = bit.bit_length()-1
            extended = mask | bit
            value = score + weights[v]
            classes.append((value,extended))
            enumerate_classes(extended,remaining & compatible[v],value)
    enumerate_classes(0,all_vertices,0)
    classes.sort(reverse=True)
    best = 0

    def pack(index, remaining, used, score):
        nonlocal best
        best = max(best,score)
        if remaining == 0:
            return
        for i in range(index,len(classes)):
            value,mask = classes[i]
            if score+remaining*value <= best:
                break
            if not mask & used:
                pack(i+1,remaining-1,used | mask,score+value)
    pack(0,k,0,0)
    return best

if __name__ == "__main__":
    n,edges = load_graph("DSJC125.9")
    weights = list(map(int,(ROOT/"instances"/"DSJC125.9.weights").read_text().split()))
    print("unit",optimum([1]*n,edges,4))
    print("weighted",optimum(weights,edges,4))
