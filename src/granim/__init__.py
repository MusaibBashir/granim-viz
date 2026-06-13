"""granim — write the algorithm, get the animation.

    import granim as ga

    @ga.animate(debug=True)
    def rev(node, prev=None):
        if node is None:
            return prev
        nxt = node.next
        node.next = prev
        return rev(nxt, node)

    rev(ga.linked_list([1, 2, 3, 4, 5]).head)   # -> rev.html
"""
from __future__ import annotations

import functools
import linecache
import sys
import webbrowser
from pathlib import Path

from .core.recorder import GranimError, Index, Recorder, active
from .core.trace import Trace
from .structures.array import Array
from .structures.graph import Graph, GraphNode
from .structures.linked_list import LinkedList, ListNode
from .structures.custom import container, node
from .structures.matrix import Matrix
from .structures.tracked import Tracked
from .structures.tree import Tree, TreeNode

__version__ = "2.0.0"
__all__ = [
    "animate", "record", "array", "matrix", "linked_list", "tree", "graph",
    "node", "container", "index", "note", "GranimError", "ListNode",
    "TreeNode", "GraphNode",
]

array = Array
matrix = Matrix
linked_list = LinkedList
tree = Tree
graph = Graph
index = Index
record = Recorder


def note(text=None) -> None:
    """Drop an explanatory caption onto the canvas at this point in the run.
    Persists across steps until the next note; pass None or "" to clear it.
    A no-op outside a recording, so it never disturbs the plain algorithm."""
    rec = active()
    if rec is not None:
        rec.emit("note", {"text": str(text) if text else None})


def animate(fn=None, *, debug=False, theme="dark", out=None, show=None,
            speed=1.0, title=None):
    """Decorate a function; calling it records, compiles, and saves the
    animation. Returns the function's result unchanged."""
    if fn is None:
        return functools.partial(animate, debug=debug, theme=theme, out=out,
                                 show=show, speed=speed, title=title)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        rec = active()
        if rec is not None:
            if rec._owner is wrapper:  # recursive call into the same recording
                return fn(*args, **kwargs)
            raise GranimError("nested recording: another @animate function is running")

        rec = Recorder(debug=debug, theme=theme, title=title or fn.__name__,
                       speed=speed, owner=wrapper)
        rec.src_lines = linecache.getlines(fn.__code__.co_filename)
        rec.func_first_line = fn.__code__.co_firstlineno
        from .structures.base import is_node
        rec.ext_roots = [a._id for a in (*args, *kwargs.values()) if is_node(a)]
        result, err = None, None
        with rec:
            try:
                with Trace(rec, fn.__code__):
                    result = fn(*args, **kwargs)
            except Exception as e:  # save the partial recording, then re-raise
                err = e
                rec.error = f"{type(e).__name__}: {e}"
            if is_node(result):
                rec.ext_roots.append(result._id)

        path = _out_path(out, fn)
        rec.save(path)
        if err is not None:
            sys.stderr.write(f"granim: saved partial animation to {path}\n")
            raise err
        _present(rec, path, show, out)
        return result._v if isinstance(result, Tracked) else result

    return wrapper


def _out_path(out, fn) -> Path:
    if out is not None:
        return Path(out)
    src = Path(fn.__code__.co_filename)
    base = src.parent if src.is_file() else Path.cwd()
    return base / f"{fn.__name__}.html"


def _present(rec, path, show, out) -> None:
    in_jupyter = "ipykernel" in sys.modules
    if show is None:
        show = out is None
    if not show:
        return
    if in_jupyter:
        rec.show()
    else:
        webbrowser.open(path.resolve().as_uri())
