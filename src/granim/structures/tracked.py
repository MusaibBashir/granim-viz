"""Value proxy for array/matrix cells: comparisons emit events, arithmetic
returns plain values."""
from __future__ import annotations

import operator

from ..core.events import safe_repr
from ..core.recorder import emit

_SCALARS = (int, float, str, bool, type(None))


def _unwrap(x):
    return x._v if isinstance(x, Tracked) else x


class Tracked:
    __slots__ = ("_v", "_cid")

    def __init__(self, value, cell_id: str):
        object.__setattr__(self, "_v", value)
        object.__setattr__(self, "_cid", cell_id)

    def __setattr__(self, name, value):
        if name == "state":  # cell coloring: a[i].state = "visited"
            from .base import STATES
            if value not in STATES:
                from ..core.recorder import GranimError
                raise GranimError(f"unknown state {value!r}; one of {STATES}")
            emit("state_set", id=self._cid, state=value)
        else:
            object.__setattr__(self, name, value)

    def _cmp(self, other, op, sym):
        o = _unwrap(other)
        result = op(self._v, o)
        if isinstance(other, Tracked) or isinstance(other, _SCALARS):
            emit("compare",
                 a=self._cid, b=other._cid if isinstance(other, Tracked) else None,
                 a_repr=safe_repr(self._v), b_repr=safe_repr(o), op=sym, result=bool(result))
        return result

    def __lt__(self, o): return self._cmp(o, operator.lt, "<")
    def __le__(self, o): return self._cmp(o, operator.le, "<=")
    def __gt__(self, o): return self._cmp(o, operator.gt, ">")
    def __ge__(self, o): return self._cmp(o, operator.ge, ">=")
    def __eq__(self, o): return self._cmp(o, operator.eq, "==")
    def __ne__(self, o): return self._cmp(o, operator.ne, "!=")

    def __add__(self, o): return self._v + _unwrap(o)
    def __radd__(self, o): return _unwrap(o) + self._v
    def __sub__(self, o): return self._v - _unwrap(o)
    def __rsub__(self, o): return _unwrap(o) - self._v
    def __mul__(self, o): return self._v * _unwrap(o)
    def __rmul__(self, o): return _unwrap(o) * self._v
    def __truediv__(self, o): return self._v / _unwrap(o)
    def __floordiv__(self, o): return self._v // _unwrap(o)
    def __mod__(self, o): return self._v % _unwrap(o)
    def __neg__(self): return -self._v

    def __hash__(self): return hash(self._v)
    def __bool__(self): return bool(self._v)
    def __int__(self): return int(self._v)
    def __float__(self): return float(self._v)
    def __index__(self): return operator.index(self._v)
    def __str__(self): return str(self._v)
    def __repr__(self): return repr(self._v)
