"""Layered DAG layout: longest-path layering + barycenter ordering."""
from __future__ import annotations

LAYER_GAP = 2.0
NODE_GAP = 1.6
SWEEPS = 4


def is_dag(nodes: list[str], edges: set[tuple[str, str]]) -> bool:
    indeg = {n: 0 for n in nodes}
    for a, b in edges:
        indeg[b] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    seen = 0
    out = {n: [] for n in nodes}
    for a, b in edges:
        out[a].append(b)
    while queue:
        n = queue.pop()
        seen += 1
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return seen == len(nodes)


def layered_layout(nodes: list[str], edges: set[tuple[str, str]]) -> dict:
    preds = {n: [] for n in nodes}
    succs = {n: [] for n in nodes}
    for a, b in edges:
        succs[a].append(b)
        preds[b].append(a)

    layer: dict[str, int] = {}

    def depth(n):
        if n not in layer:
            layer[n] = max((depth(p) + 1 for p in preds[n]), default=0)
        return layer[n]

    for n in nodes:
        depth(n)

    layers: dict[int, list[str]] = {}
    for n in nodes:
        layers.setdefault(layer[n], []).append(n)
    order = [layers[k] for k in sorted(layers)]

    idx = {n: i for row in order for i, n in enumerate(row)}
    for s in range(SWEEPS):
        rows = order if s % 2 == 0 else order[::-1]
        ref = preds if s % 2 == 0 else succs
        for row in rows:
            row.sort(key=lambda n: sum(idx[r] for r in ref[n]) / len(ref[n])
                     if ref[n] else idx[n])
            for i, n in enumerate(row):
                idx[n] = i

    pos = {}
    for li, row in enumerate(order):
        width = (len(row) - 1) * NODE_GAP
        for i, n in enumerate(row):
            pos[n] = (i * NODE_GAP - width / 2, li * LAYER_GAP)
    return pos
