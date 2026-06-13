"""Recorder — collects events, owns the StepBuilder, exposes Tier-2 controls."""
from __future__ import annotations

import contextlib
from pathlib import Path

from .events import Event, safe_repr
from .steps import StepBuilder

MAX_EVENTS = 20_000
MAX_NODES = 500
MAX_STEPS = 3_000


class GranimError(ValueError):
    pass


# -- identity ------------------------------------------------------------------

_counters = {"n": 0, "s": 0}


def next_id(prefix: str) -> str:
    _counters[prefix] += 1
    return f"{prefix}{_counters[prefix]}"


def reset_ids() -> None:  # tests only
    _counters["n"] = _counters["s"] = 0


# -- active recorder routing ----------------------------------------------------

_ACTIVE: "Recorder | None" = None
_pending_structs: list = []  # built before a recording starts
_pending_nodes: list = []    # standalone nodes built before a recording starts


def active() -> "Recorder | None":
    return _ACTIVE


def register_struct(struct) -> None:
    if _ACTIVE is not None:
        _ACTIVE.structs.append(struct)
    else:
        _pending_structs.append(struct)


def register_node(node) -> None:
    if _ACTIVE is None:
        _pending_nodes.append(node)


def emit(kind: str, **payload) -> None:
    """Module-level emission used by structures. No recorder -> no-op."""
    if _ACTIVE is not None:
        _ACTIVE.emit(kind, payload)


class Index:
    """Explicit index binding for rec.watch(i=ga.index(arr, i))."""

    __slots__ = ("array", "value")

    def __init__(self, array, value: int):
        self.array, self.value = array, int(value)


class Recorder:
    def __init__(self, *, debug=False, theme="dark", title=None, speed=1.0, owner=None):
        self.debug = debug
        self.theme = theme
        self.title = title
        self.speed = speed
        self._owner = owner
        self.structs: list = []
        self.sb = StepBuilder(self._stack_snapshot)
        self._seq = 0
        self._quiet = 0
        self._stack: list[dict] = []
        self._frame_serial = 0
        self._locals: dict[int, dict] = {}
        self.ext_roots: list[str] = []  # node-valued args and return value
        self.error: str | None = None

    # -- lifecycle ---------------------------------------------------------------

    def __enter__(self):
        global _ACTIVE
        if _ACTIVE is not None:
            raise GranimError("nested recording: a recorder is already active")
        _ACTIVE = self
        if _pending_structs:
            self.structs += _pending_structs
            _pending_structs.clear()
        pending_nodes, _pending_nodes[:] = list(_pending_nodes), []
        self.sb.boundary(label="initial state")
        self.sb.begin_batch()
        for n in pending_nodes:  # nodes first so struct edges can adopt them
            n._snapshot_node()
        for s in self.structs:
            s._snapshot()
        self.sb.end_batch()
        return self

    def __exit__(self, etype, exc, tb):
        global _ACTIVE
        _ACTIVE = None
        if exc is not None:
            self.error = f"{etype.__name__}: {exc}"
        self.sb.finish()
        return False

    # -- emission ----------------------------------------------------------------

    def emit(self, kind: str, payload: dict) -> None:
        if self._quiet and kind in ("read", "compare"):
            return
        self._seq += 1
        if self._seq > MAX_EVENTS:
            raise GranimError(
                f"recording exceeded {MAX_EVENTS} events (last at line "
                f"{self._cur_line()}); use a smaller input or rec.quiet()"
            )
        self.sb.add(Event(
            seq=self._seq, kind=kind, payload=payload,
            depth=max(len(self._stack) - 1, 0), line=self._cur_line(),
            frame=self._stack[-1]["frame"] if self._stack else 0,
        ))

    def _cur_line(self) -> int | None:
        return self._stack[-1].get("line") if self._stack else None

    def _stack_snapshot(self) -> list[dict]:
        return [{"fn": f["fn"], "args": f["args"], "fid": f["frame"]}
                for f in self._stack]

    # -- trace hooks (core/trace.py calls these) ----------------------------------

    def on_call(self, frame) -> None:
        self.sb.boundary(self._cur_line(), max(len(self._stack) - 1, 0), mode="call")
        self._frame_serial += 1
        code = frame.f_code
        args = ", ".join(
            safe_repr(frame.f_locals[n])
            for n in code.co_varnames[: code.co_argcount]
            if n in frame.f_locals
        )
        self._stack.append({
            "frame": self._frame_serial, "fn": code.co_name,
            "args": f"({args})", "line": frame.f_lineno,
        })
        self._locals[self._frame_serial] = {}

    def on_line(self, frame) -> None:
        # locals are always diffed; debug only controls display
        self._diff_locals(frame)
        self._stack[-1]["line"] = frame.f_lineno
        self.sb.boundary(frame.f_lineno, max(len(self._stack) - 1, 0), mode="line")

    def on_return(self, frame) -> None:
        self._diff_locals(frame)
        self.sb.boundary(self._cur_line(), max(len(self._stack) - 1, 0))
        if self._stack:
            self._locals.pop(self._stack[-1]["frame"], None)
            self._stack.pop()
        if self._stack:
            # caller locals re-emit on its next line (badges snap back on unwind)
            self._locals[self._stack[-1]["frame"]] = {}

    # -- locals diffing ------------------------------------------------------------

    def _diff_locals(self, frame) -> None:
        from ..structures.array import Array
        from ..structures.base import Struct

        serial = self._stack[-1]["frame"] if self._stack else 0
        prev = self._locals.setdefault(serial, {})
        arrays = [v for v in frame.f_locals.values() if isinstance(v, Array)]
        for name, val in frame.f_locals.items():
            if name.startswith("_") or isinstance(val, Struct) or callable(val) \
                    or getattr(type(val), "_ga_container", False):
                continue
            r = safe_repr(val)
            if prev.get(name) == r:
                continue
            prev[name] = r
            self._emit_var(name, val, r, arrays)

    def _emit_var(self, name, val, r, arrays) -> None:
        from ..structures.base import is_node
        from ..structures.tracked import Tracked

        kind, target, struct = "scalar", None, None
        if isinstance(val, Tracked):
            val = val._v
        if is_node(val):
            kind, target = "ref", val._id
        elif isinstance(val, Index):
            kind, struct, r = "index", val.array._id, str(val.value)
        elif isinstance(val, int) and not isinstance(val, bool) and len(arrays) == 1 \
                and 0 <= val <= len(arrays[0]):
            kind, struct = "index", arrays[0]._id
        self.emit("var_set", {"name": name, "kind": kind, "repr": r,
                              "target": target, "struct": struct})

    # -- Tier 2 --------------------------------------------------------------------

    def step(self, label: str = "") -> None:
        self.sb.boundary(self._cur_line(), max(len(self._stack) - 1, 0), label=label or None)

    @contextlib.contextmanager
    def batch(self):
        self.sb.begin_batch()
        try:
            yield
        finally:
            self.sb.end_batch()

    @contextlib.contextmanager
    def quiet(self):
        self._quiet += 1
        try:
            yield
        finally:
            self._quiet -= 1

    def watch(self, **vars) -> None:
        for name, val in vars.items():
            self._emit_var(name, val, safe_repr(val), [])

    # -- output ---------------------------------------------------------------------

    def compile(self) -> dict:
        from ..render.compiler import compile_timeline

        if not self.sb.steps:
            raise GranimError("empty recording: nothing was animated")
        if len(self.sb.steps) > MAX_STEPS:
            raise GranimError(f"recording produced {len(self.sb.steps)} steps (max {MAX_STEPS})")
        return compile_timeline(self)

    def to_html(self) -> str:
        from ..render.html import render_html

        return render_html(self.compile())

    def save(self, path) -> Path:
        path = Path(path)
        path.write_text(self.to_html(), encoding="utf-8")
        return path

    def show(self) -> None:
        from ..render.html import display_inline

        display_inline(self.to_html())
