"""Decorators that instrument user-owned classes without inheritance."""
from __future__ import annotations

from ..core.events import safe_repr
from ..core.recorder import active, emit, next_id, register_node, register_struct
from .base import is_node, new_node_id


def _node_children(v):
    """Nodes held directly or inside a plain collection field (e.g. a set of
    operands in a computation graph)."""
    if is_node(v):
        return (v,)
    if isinstance(v, (list, tuple, set, frozenset)):
        return tuple(x for x in v if is_node(x))
    return ()


class _CustomGraph:
    """Implicit container that makes @node(graph=...) instances lay out as a
    graph. The nodes emit themselves; this only supplies type, title and
    membership."""
    type_name = "graph"
    cols = None

    def __init__(self, sid, title=None):
        self._id = sid
        self.title = title

    def _snapshot(self):  # nodes snapshot themselves; nothing to root here
        pass


def _graph_sid(key, title):
    """One graph container per group key per recording, created on first use.
    A string key is a named group shared across classes; otherwise per-class."""
    rec = active()
    if rec is None:
        return None
    reg = getattr(rec, "_cgraphs", None)
    if reg is None:
        reg = rec._cgraphs = {}
    sid = reg.get(key)
    if sid is None:
        sid = reg[key] = next_id("s")
        rec.structs.append(_CustomGraph(sid, title))
    return sid


def node(cls=None, *, value: str = "value", shape: str = "circle",
         graph: "bool | str" = False):
    """Instrument a node class: node-valued fields become edges, `value`
    animates label changes, everything else is plain storage.

    graph=True groups every instance into one graph and renders pointer
    fields (single nodes or collections of them) as graph edges, so a web of
    custom nodes lays out like ga.graph instead of a floating chain.
    graph="name" does the same but into a *named* graph, shown with that
    title on the canvas; instances of any class sharing the name join it,
    letting you split e.g. a forward graph from a backward one."""
    if cls is None:
        return lambda c: node(c, value=value, shape=shape, graph=graph)
    if getattr(cls, "_ga_node", False):
        return cls

    is_graph = bool(graph)
    gtitle = graph if isinstance(graph, str) else None
    gkey = ("name", graph) if gtitle else ("cls", cls)

    cls._ga_node = True
    cls._ga_value_attr = value
    cls._ga_shape = shape
    cls._ga_graph = is_graph
    cls._ga_building = False
    orig_init = cls.__init__
    slot_of = (lambda name: "edge") if is_graph else (lambda name: name)

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, "_id", new_node_id())
        object.__setattr__(self, "_ga_building", True)
        try:
            orig_init(self, *args, **kwargs)
        finally:
            object.__setattr__(self, "_ga_building", False)
        if active() is not None:
            self._snapshot_node()
        else:
            register_node(self)

    def _snapshot_node(self):
        emit("node_add", id=self._id, struct=_graph_sid(gkey, gtitle) if is_graph else None,
             value=safe_repr(getattr(self, value, None)), shape=shape)
        for name, v in list(self.__dict__.items()):
            if name.startswith("_"):
                continue
            for child in _node_children(v):
                emit("edge_set", src=self._id, slot=slot_of(name),
                     old=None, new=child._id)

    def __setattr__(self, name, val):
        if name.startswith("_") or self._ga_building or active() is None:
            object.__setattr__(self, name, val)
            return
        old = self.__dict__.get(name)
        object.__setattr__(self, name, val)
        if is_node(val) or is_node(old):
            emit("edge_set", src=self._id, slot=slot_of(name),
                 old=old._id if is_node(old) else None,
                 new=val._id if is_node(val) else None)
        elif name == value:
            emit("value_set", id=self._id, old=safe_repr(old), new=safe_repr(val))

    def __getattribute__(self, name):
        v = object.__getattribute__(self, name)
        if not name.startswith("_") and is_node(v) and active() is not None:
            emit("read", id=object.__getattribute__(self, "_id"))
        return v

    cls.__init__ = __init__
    cls._snapshot_node = _snapshot_node
    cls.__setattr__ = __setattr__
    cls.__getattribute__ = __getattribute__
    if cls.__repr__ is object.__repr__:
        cls.__repr__ = lambda self: f"Node({getattr(self, value, None)!r})"
    return cls


def container(cls):
    """Instrument a container class: node-valued fields render as badges
    and root the reachability pass."""
    if getattr(cls, "_ga_container", False):
        return cls
    cls._ga_container = True
    cls.type_name = "container"
    cls._ga_building = False
    orig_init = cls.__init__

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, "_id", next_id("s"))
        object.__setattr__(self, "_ga_building", True)
        register_struct(self)
        try:
            orig_init(self, *args, **kwargs)
        finally:
            object.__setattr__(self, "_ga_building", False)
        if active() is not None:
            self._snapshot()

    def _snapshot(self):
        for name, v in list(self.__dict__.items()):
            if not name.startswith("_") and is_node(v):
                emit("edge_set", src=self._id, slot=name, old=None, new=v._id)

    def __setattr__(self, name, val):
        if name.startswith("_") or self._ga_building or active() is None:
            object.__setattr__(self, name, val)
            return
        old = self.__dict__.get(name)
        object.__setattr__(self, name, val)
        if is_node(val) or is_node(old):
            emit("edge_set", src=self._id, slot=name,
                 old=old._id if is_node(old) else None,
                 new=val._id if is_node(val) else None)

    cls.__init__ = __init__
    cls._snapshot = _snapshot
    cls.__setattr__ = __setattr__
    return cls
