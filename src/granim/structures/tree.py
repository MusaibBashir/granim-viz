"""Tree with tracked children; left/right are sugar over the children list."""
from __future__ import annotations

from ..core.events import safe_repr
from ..core.recorder import GranimError, active, emit, register_node
from .base import NodeBase, Struct, custom_edges, new_node_id


class TreeNode(NodeBase):
    __slots__ = ("_children",)

    def __init__(self, value):
        self._id = new_node_id()
        self._value = value
        self._state = "default"
        self._children: list[TreeNode | None] = []
        if active() is not None:
            emit("node_add", id=self._id, struct=None, value=safe_repr(value), shape="circle")
        else:
            register_node(self)

    def _set_child(self, i: int, node):
        while len(self._children) <= i:
            self._children.append(None)
        old = self._children[i]
        self._children[i] = node
        emit("edge_set", src=self._id, slot=f"child:{i}",
             old=old._id if old else None, new=node._id if node else None)

    def _get_child(self, i: int):
        emit("read", id=self._id)
        return self._children[i] if i < len(self._children) else None

    @property
    def left(self):
        return self._get_child(0)

    @left.setter
    def left(self, node):
        self._set_child(0, node)

    @property
    def right(self):
        return self._get_child(1)

    @right.setter
    def right(self, node):
        self._set_child(1, node)

    @property
    def children(self):
        emit("read", id=self._id)
        return [c for c in self._children if c is not None]

    def add_child(self, node):
        self._set_child(len(self._children), node)
        return node


class Tree(Struct):
    type_name = "tree"

    def __init__(self, adj: dict | None = None):
        super().__init__()
        self._root: TreeNode | None = None
        self._built: list[TreeNode] = []
        if adj:
            nodes = {}
            children_labels = {c for cs in adj.values() for c in cs}
            roots = [k for k in adj if k not in children_labels]
            if len(roots) != 1:
                raise GranimError("tree adjacency must have exactly one root")

            def build(label):
                n = nodes.get(label)
                if n is None:
                    n = nodes[label] = TreeNode.__new__(TreeNode)
                    n._id, n._value, n._state = new_node_id(), label, "default"
                    n._children = []
                    self._built.append(n)
                return n

            for label, kids in adj.items():
                p = build(label)
                for k in kids:
                    p._children.append(build(k))
            self._root = nodes[roots[0]]
        if active() is not None and self._built:
            self._snapshot()

    def _snapshot(self):
        for n in self._built:
            emit("node_add", id=n._id, struct=self._id, value=safe_repr(n._value), shape="circle")
        for n in self._built:
            for i, c in enumerate(n._children):
                if c is not None:
                    emit("edge_set", src=n._id, slot=f"child:{i}", old=None, new=c._id)
        for n in self._built:
            for slot, v in custom_edges(n):
                emit("edge_set", src=n._id, slot=slot, old=None, new=v._id)
        if self._root is not None:
            emit("edge_set", src=self._id, slot="root", old=None, new=self._root._id)

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, node):
        old = self._root
        self._root = node
        emit("edge_set", src=self._id, slot="root",
             old=old._id if old else None, new=node._id if node else None)
