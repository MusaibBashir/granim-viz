"""2D grid of tracked cells; supports m[i][j] and m[i, j] indexing."""
from __future__ import annotations

import operator

from ..core.events import safe_repr
from ..core.recorder import GranimError, emit
from .base import Struct, new_node_id
from .tracked import Tracked, _SCALARS, _unwrap


class Matrix(Struct):
    type_name = "matrix"

    def __init__(self, rows):
        super().__init__()
        rows = [list(r) for r in rows]
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise GranimError("matrix rows must be non-empty and equal length")
        self.cols = len(rows[0])
        self._values: list[list] = []
        self._cells: list[list[str]] = []
        for r in rows:
            vrow, crow = [], []
            for v in r:
                v = _unwrap(v)
                if not isinstance(v, _SCALARS):
                    raise GranimError(f"matrix elements must be scalars, got {type(v).__name__}")
                vrow.append(v)
                crow.append(new_node_id())
            self._values.append(vrow)
            self._cells.append(crow)
        from ..core.recorder import active
        if active() is not None:
            self._snapshot()

    def _snapshot(self):
        for crow, vrow in zip(self._cells, self._values):
            for cid, v in zip(crow, vrow):
                emit("node_add", id=cid, struct=self._id, value=safe_repr(v), shape="cell")

    def _at(self, i, j):
        i, j = operator.index(i), operator.index(j)
        emit("read", struct=self._id, id=self._cells[i][j])
        return Tracked(self._values[i][j], self._cells[i][j])

    def _put(self, i, j, v):
        i, j = operator.index(i), operator.index(j)
        v = _unwrap(v)
        emit("value_set", id=self._cells[i][j],
             old=safe_repr(self._values[i][j]), new=safe_repr(v))
        self._values[i][j] = v

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self._at(*key)
        return _Row(self, operator.index(key))

    def __setitem__(self, key, v):
        if not isinstance(key, tuple):
            raise GranimError("assign cells via m[i][j] = v or m[i, j] = v")
        self._put(key[0], key[1], v)

    def __len__(self):  # rows, so `0 <= i < len(m)` reads naturally
        return len(self._values)

    def __iter__(self):
        return (_Row(self, i) for i in range(len(self._values)))

    def to_lists(self):
        return [list(r) for r in self._values]

    def __repr__(self):
        return f"Matrix({len(self._values)}x{self.cols})"


class _Row:
    __slots__ = ("_m", "_i")

    def __init__(self, m, i):
        self._m, self._i = m, i

    def __getitem__(self, j):
        return self._m._at(self._i, j)

    def __setitem__(self, j, v):
        self._m._put(self._i, j, v)

    def __len__(self):
        return self._m.cols

    def __iter__(self):
        return (self[j] for j in range(self._m.cols))

    def __repr__(self):
        return f"row {self._i}"
