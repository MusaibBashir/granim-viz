"""Dijkstra — a weighted road network with tempting shortcuts and cheaper
multi-hop alternatives. Nodes turn frontier when queued, visited when popped,
done when finalized. Distances live in the panel."""
import heapq

import granim as ga

g = ga.graph(directed=False)
S, A, B, C, D, E, F, G, T = (g.add_node(x) for x in "SABCDEFGT")

roads = [
    (S, A, 4), (S, B, 2), (S, C, 9),
    (A, B, 1), (A, D, 5), (A, E, 12),
    (B, C, 3), (B, D, 8),
    (C, E, 4),
    (D, E, 2), (D, F, 6),
    (E, F, 1), (F, G, 3), (G, T, 2),
    (E, T, 8),
]

for u, v, w in roads:
    g.add_edge(u, v, weight=w)


@ga.animate(debug=True, show=False)
def dijkstra(start):
    dist = {start.value: 0}
    pq = [(0, 0, start)]
    counter = 1
    start.state = "frontier"
    while pq:
        d, _, u = heapq.heappop(pq)
        if d > dist.get(u.value, float("inf")):
            continue
        u.state = "visited"
        for v in g.neighbors(u):
            nd = d + g.weight(u, v)
            if nd < dist.get(v.value, float("inf")):
                dist[v.value] = nd
                v.state = "frontier"
                heapq.heappush(pq, (nd, counter, v))
                counter += 1
        u.state = "done"
    return dist


if __name__ == "__main__":
    print(dijkstra(S))
