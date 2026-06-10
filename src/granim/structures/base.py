"""Shared node and structure machinery."""
from __future__ import annotations

from ..core.recorder import GranimError, MAX_NODES, active, emit, next_id, register_struct

STATES = ("default", "active", "visited", "frontier", "done", "detached")

# Custom slot names ever assigned, per node class. Assigned names default to
# None on other instances; unknown names still raise.
_CUSTOM_NAMES: dict[type, set] = {}


def is_node(v) -> bool:
    """True for granim nodes AND @ga.node-decorated user classes."""
    return isinstance(v, NodeBase) or getattr(type(v), "_ga_node", False)


def new_node_id() -> str:
    rec = active()
    if rec is not None:
        rec._node_count = getattr(rec, "_node_count", 0) + 1
        if rec._node_count > MAX_NODES:
            raise GranimError(f"more than {MAX_NODES} nodes; animation would be unwatchable")
    return next_id("n")


def custom_edges(node):
    """(slot, target) pairs for a node's custom pointers."""
    extra = getattr(node, "_extra", None)
    if extra:
        for slot, v in extra.items():
            if is_node(v):
                yield slot, v


class NodeBase:
    __slots__ = ("_id", "_value", "_state", "_extra")
    _shape = "circle"

    def _snapshot_node(self):
        """Emit this standalone node and its edges at recording start."""
        from ..core.events import safe_repr
        emit("node_add", id=self._id, struct=None,
             value=safe_repr(self._value), shape=type(self)._shape)
        for slot in ("_next", "_prev"):
            t = getattr(self, slot, None)
            if t is not None:
                emit("edge_set", src=self._id, slot=slot[1:], old=None, new=t._id)
        for i, c in enumerate(getattr(self, "_children", None) or ()):
            if c is not None:
                emit("edge_set", src=self._id, slot=f"child:{i}", old=None, new=c._id)
        for slot, v in custom_edges(self):
            emit("edge_set", src=self._id, slot=slot, old=None, new=v._id)

    @property
    def value(self):
        emit("read", id=self._id)
        return self._value

    @value.setter
    def value(self, v):
        from ..core.events import safe_repr
        old = self._value
        self._value = v
        emit("value_set", id=self._id, old=safe_repr(old), new=safe_repr(v))

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, s: str):
        if s not in STATES:
            raise GranimError(f"unknown state {s!r}; one of {STATES}")
        self._state = s
        emit("state_set", id=self._id, state=s)

    # -- custom pointer slots ------------------------------------------------

    def __setattr__(self, name, value):
        try:
            object.__setattr__(self, name, value)  # known fields win
            return
        except AttributeError:
            pass
        if name.startswith("_"):
            raise AttributeError(f"cannot set {name!r} on {type(self).__name__}")
        _CUSTOM_NAMES.setdefault(type(self), set()).add(name)
        try:
            extra = object.__getattribute__(self, "_extra")
        except AttributeError:
            extra = {}
            object.__setattr__(self, "_extra", extra)
        old = extra.get(name)
        extra[name] = value
        if is_node(value) or is_node(old):
            emit("edge_set", src=self._id, slot=name,
                 old=old._id if is_node(old) else None,
                 new=value._id if is_node(value) else None)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            extra = object.__getattribute__(self, "_extra")
        except AttributeError:
            extra = None
        if extra is not None and name in extra:
            v = extra[name]
            if is_node(v):
                emit("read", id=self._id)
            return v
        if name in _CUSTOM_NAMES.get(type(self), ()):
            return None
        raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")

    def __repr__(self):
        return f"Node({self._value!r})"


class Struct:
    """Base for built-in structures; registers with the active or next recorder."""

    type_name = "struct"

    def __init__(self):
        self._id = next_id("s")
        register_struct(self)

    def _snapshot(self) -> None:
        raise NotImplementedError
