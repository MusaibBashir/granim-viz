"""List-backed array; cells are tracked nodes."""
from __future__ import annotations

import operator

from ..core.events import safe_repr
from ..core.recorder import GranimError, emit
from .base import Struct, new_node_id
from .tracked import Tracked, _SCALARS, _unwrap


class Array(Struct):
    type_name = "array"

    def __init__(self, values):
        super().__init__()
        self._values = []
        self._cells = []
        for v in values:
            self._append(v)

    def _append(self, v):
        v = _unwrap(v)
        if not isinstance(v, _SCALARS):
            raise GranimError(f"Array elements must be scalars, got {type(v).__name__}")
        cid = new_node_id()
        self._values.append(v)
        self._cells.append(cid)
        emit("node_add", id=cid, struct=self._id, value=safe_repr(v), shape="cell")

    def _snapshot(self):
        for cid, v in zip(self._cells, self._values):
            emit("node_add", id=cid, struct=self._id, value=safe_repr(v), shape="cell")

    def __len__(self):
        return len(self._values)

    def _idx(self, i):
        i = operator.index(i)
        return i + len(self._values) if i < 0 else i

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self)))]
        i = self._idx(i)
        emit("read", struct=self._id, id=self._cells[i])
        return Tracked(self._values[i], self._cells[i])

    def __setitem__(self, i, v):
        i = self._idx(i)
        v = _unwrap(v)
        emit("value_set", id=self._cells[i], old=safe_repr(self._values[i]), new=safe_repr(v))
        self._values[i] = v

    def swap(self, i, j):
        i, j = self._idx(i), self._idx(j)
        a, b = self._values[i], self._values[j]
        emit("value_set", id=self._cells[i], old=safe_repr(a), new=safe_repr(b))
        emit("value_set", id=self._cells[j], old=safe_repr(b), new=safe_repr(a))
        self._values[i], self._values[j] = b, a

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def to_list(self):
        return list(self._values)

    def __repr__(self):
        return f"Array({self._values!r})"
