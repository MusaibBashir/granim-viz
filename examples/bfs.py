"""BFS — each frontier appears in parallel (auto-batched, no annotations)."""
from collections import deque

import granim as ga

g = ga.graph(directed=False)
a, b, c, d, e, f, h, i = (g.add_node(x) for x in "ABCDEFHI")
for u, v in [(a, b), (a, c), (b, d), (b, e), (c, f), (c, h), (e, i), (f, i)]:
    g.add_edge(u, v)


@ga.animate(debug=True, show=False)
def bfs(start):
    start.state = "frontier"
    q = deque([start])
    order = []
    while q:
        u = q.popleft()
        u.state = "visited"
        order.append(u)
        for v in g.neighbors(u):
            if v.state == "default":
                v.state = "frontier"
                q.append(v)
        u.state = "done"
    return order


if __name__ == "__main__":
    print([n.value for n in bfs(a)])
