"""Event model: a small, closed set of semantic events."""
from __future__ import annotations

from dataclasses import dataclass

KINDS = frozenset({
    "node_add", "node_remove", "edge_set", "read", "compare",
    "value_set", "state_set", "var_set",
})

# Kinds that trigger layout keyframes. edge_flip is assigned by the compiler.
STRUCTURAL = frozenset({"node_add", "node_remove", "edge_set"})
# Kinds eligible for parallel batch-merging.
BATCHABLE = frozenset({"state_set", "node_add"})
PASSIVE = frozenset({"read", "compare"})

REPR_MAX = 60


@dataclass(frozen=True, slots=True)
class Event:
    seq: int
    kind: str
    payload: dict
    depth: int
    line: int | None
    frame: int


def safe_repr(value) -> str:
    from ..structures.base import NodeBase
    from ..structures.tracked import Tracked

    if isinstance(value, Tracked):
        value = value._v
    if isinstance(value, NodeBase):
        r = f"Node({value._value!r})"
    else:
        try:
            r = repr(value)
        except Exception:
            r = f"<{type(value).__name__}>"
    return r if len(r) <= REPR_MAX else r[: REPR_MAX - 1] + "…"
