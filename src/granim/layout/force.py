"""Fruchterman–Reingold force layout, deterministic and warm-startable."""
from __future__ import annotations

import math
import random

COLD_ITERS = 300
WARM_ITERS = 40
K_SCALE = 1.4


def force_layout(nodes: list[str], edges: set[tuple[str, str]],
                 prev: dict | None = None, seed: int = 1) -> dict:
    if not nodes:
        return {}
    if len(nodes) == 1:
        return {nodes[0]: (0.0, 0.0)}

    rng = random.Random(seed)
    area = max(len(nodes) * 4.0, 9.0)
    side = math.sqrt(area)
    k = K_SCALE * math.sqrt(area / len(nodes))

    pos = {}
    warm = prev is not None and any(n in prev for n in nodes)
    for n in nodes:
        if warm and n in prev:
            pos[n] = list(prev[n])
        elif warm:
            # new nodes spawn near a laid-out neighbor
            nb = next((prev[a] if b == n else prev[b]
                       for a, b in edges if n in (a, b) and (a if b == n else b) in prev), None)
            j = random.Random(hash(n)).uniform(-0.5, 0.5)
            pos[n] = [nb[0] + j, nb[1] + 0.7] if nb else [rng.uniform(0, side), rng.uniform(0, side)]
        else:
            pos[n] = [rng.uniform(0, side), rng.uniform(0, side)]

    iters = WARM_ITERS if warm else COLD_ITERS
    temp = side / (8.0 if warm else 4.0)
    cool = temp / iters
    for _ in range(iters):
        disp = {n: [0.0, 0.0] for n in nodes}
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = max(math.hypot(dx, dy), 0.01)
                f = k * k / d
                disp[a][0] += dx / d * f
                disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f
                disp[b][1] -= dy / d * f
        for a, b in edges:
            if a not in pos or b not in pos:
                continue
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = max(math.hypot(dx, dy), 0.01)
            f = d * d / k
            disp[a][0] -= dx / d * f
            disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f
            disp[b][1] += dy / d * f
        for n in nodes:
            dx, dy = disp[n]
            d = max(math.hypot(dx, dy), 0.01)
            pos[n][0] += dx / d * min(d, temp)
            pos[n][1] += dy / d * min(d, temp)
        temp = max(temp - cool, 0.01)

    return {n: (p[0], p[1]) for n, p in pos.items()}
