"""Directed/undirected graph with tracked nodes and weighted edges."""
from __future__ import annotations

from ..core.events import safe_repr
from ..core.recorder import active, emit
from .base import NodeBase, Struct, custom_edges, new_node_id


class GraphNode(NodeBase):
    __slots__ = ("_graph",)

    def __init__(self, value, graph):
        self._id = new_node_id()
        self._value = value
        self._state = "default"
        self._graph = graph


class Graph(Struct):
    type_name = "graph"

    def __init__(self, directed: bool = True, title: str | None = None):
        super().__init__()
        self.directed = directed
        self.title = title
        self._nodes: list[GraphNode] = []
        self._adj: dict[str, list[GraphNode]] = {}
        self._edges: dict[tuple[str, str], object] = {}

    def _key(self, u, v):
        if self.directed:
            return (u._id, v._id)
        return (u._id, v._id) if u._id <= v._id else (v._id, u._id)

    def add_node(self, value) -> GraphNode:
        n = GraphNode(value, self)
        self._nodes.append(n)
        self._adj[n._id] = []
        emit("node_add", id=n._id, struct=self._id, value=safe_repr(value), shape="circle")
        return n

    def add_edge(self, u: GraphNode, v: GraphNode, weight=None) -> None:
        self._edges[self._key(u, v)] = weight
        self._adj[u._id].append(v)
        if not self.directed:
            self._adj[v._id].append(u)
        a, b = self._key(u, v)
        emit("edge_set", src=a, slot="edge", old=None, new=b, weight=weight)

    def remove_edge(self, u: GraphNode, v: GraphNode) -> None:
        self._edges.pop(self._key(u, v), None)
        self._adj[u._id] = [n for n in self._adj[u._id] if n is not v]
        if not self.directed:
            self._adj[v._id] = [n for n in self._adj[v._id] if n is not u]
        a, b = self._key(u, v)
        emit("edge_set", src=a, slot="edge", old=b, new=None)

    def remove_node(self, u: GraphNode) -> None:
        for (a, b) in [k for k in self._edges if u._id in k]:
            del self._edges[(a, b)]
            emit("edge_set", src=a, slot="edge", old=b, new=None)
        self._nodes.remove(u)
        self._adj.pop(u._id, None)
        for k in self._adj:
            self._adj[k] = [n for n in self._adj[k] if n is not u]
        emit("node_remove", id=u._id)

    def weight(self, u: GraphNode, v: GraphNode):
        return self._edges.get(self._key(u, v))

    def neighbors(self, u: GraphNode):
        emit("read", id=u._id)
        return list(self._adj[u._id])

    @property
    def nodes(self):
        return list(self._nodes)

    def _snapshot(self):
        for n in self._nodes:
            emit("node_add", id=n._id, struct=self._id, value=safe_repr(n._value), shape="circle")
        for (a, b), w in self._edges.items():
            emit("edge_set", src=a, slot="edge", old=None, new=b, weight=w)
        for n in self._nodes:
            for slot, v in custom_edges(n):
                emit("edge_set", src=n._id, slot=slot, old=None, new=v._id)
