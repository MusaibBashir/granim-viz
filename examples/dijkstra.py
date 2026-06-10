"""Dijkstra — weighted edges show their weights; nodes turn frontier when
queued, visited when popped, done when finalized. Distances live in the panel."""
import heapq

import granim as ga

g = ga.graph(directed=False)
A, B, C, D, E, F = (g.add_node(x) for x in "ABCDEF")
for u, v, w in [(A, B, 4), (A, C, 2), (B, C, 1), (B, D, 5),
                (C, D, 8), (C, E, 10), (D, E, 2), (D, F, 6), (E, F, 3)]:
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
    print(dijkstra(A))
