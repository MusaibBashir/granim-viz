"""Singly/doubly linked list with tracked next/prev pointers."""
from __future__ import annotations

from ..core.events import safe_repr
from ..core.recorder import active, emit, register_node
from .base import NodeBase, Struct, custom_edges, new_node_id


class ListNode(NodeBase):
    __slots__ = ("_next", "_prev", "_list")
    _shape = "pill"

    def __init__(self, value):
        self._id = new_node_id()
        self._value = value
        self._state = "default"
        self._next = None
        self._prev = None
        self._list = None
        if active() is not None:
            emit("node_add", id=self._id, struct=None, value=safe_repr(value), shape="pill")
        else:
            register_node(self)

    @property
    def next(self):
        emit("read", id=self._id)
        return self._next

    @next.setter
    def next(self, node):
        old = self._next
        self._next = node
        emit("edge_set", src=self._id, slot="next",
             old=old._id if old else None, new=node._id if node else None)

    @property
    def prev(self):
        emit("read", id=self._id)
        return self._prev

    @prev.setter
    def prev(self, node):
        old = self._prev
        self._prev = node
        emit("edge_set", src=self._id, slot="prev",
             old=old._id if old else None, new=node._id if node else None)


class LinkedList(Struct):
    type_name = "linked_list"

    def __init__(self, values, doubly: bool = False):
        super().__init__()
        self.doubly = doubly
        self._nodes: list[ListNode] = []
        self._head: ListNode | None = None
        prev = None
        for v in values:
            n = ListNode.__new__(ListNode)
            n._id, n._value, n._state = new_node_id(), v, "default"
            n._next = n._prev = None
            n._list = self
            self._nodes.append(n)
            if prev is None:
                self._head = n
            else:
                prev._next = n
                if doubly:
                    n._prev = prev
            prev = n
        if active() is not None:
            self._snapshot()

    def _snapshot(self):
        for n in self._nodes:
            emit("node_add", id=n._id, struct=self._id, value=safe_repr(n._value), shape="pill")
        for n in self._nodes:
            if n._next is not None:
                emit("edge_set", src=n._id, slot="next", old=None, new=n._next._id)
            if self.doubly and n._prev is not None:
                emit("edge_set", src=n._id, slot="prev", old=None, new=n._prev._id)
        for n in self._nodes:
            for slot, v in custom_edges(n):
                emit("edge_set", src=n._id, slot=slot, old=None, new=v._id)
        if self._head is not None:
            emit("edge_set", src=self._id, slot="head", old=None, new=self._head._id)

    @property
    def head(self):
        return self._head

    @head.setter
    def head(self, node):
        old = self._head
        self._head = node
        emit("edge_set", src=self._id, slot="head",
             old=old._id if old else None, new=node._id if node else None)

    def __iter__(self):
        n = self._head
        while n is not None:
            yield n
            n = n.next

    def to_list(self):
        out, n = [], self._head
        while n is not None:
            out.append(n._value)
            n = n._next
        return out

    def __repr__(self):
        return f"LinkedList({self.to_list()!r})"
