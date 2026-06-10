"""Buchheim–Walker tidy tree layout (Buchheim, Jünger, Leipert 2002)."""
from __future__ import annotations

SIB_GAP = 1.0
LEVEL_GAP = 1.8


class _T:
    __slots__ = ("node", "children", "parent", "x", "y", "thread", "mod",
                 "ancestor", "change", "shift", "number", "_lms")

    def __init__(self, node, children_of, parent=None, depth=0, number=1):
        self.node = node
        self.parent = parent
        self.x, self.y = -1.0, float(depth)
        self.thread = None
        self.mod = self.change = self.shift = 0.0
        self.ancestor = self
        self.number = number
        self._lms = None
        self.children = [
            _T(c, children_of, self, depth + 1, i + 1)
            for i, c in enumerate(children_of(node))
        ]

    def left(self):
        return self.thread or (self.children[0] if self.children else None)

    def right(self):
        return self.thread or (self.children[-1] if self.children else None)

    def left_brother(self):
        n = None
        if self.parent:
            for c in self.parent.children:
                if c is self:
                    return n
                n = c
        return n

    def lmost_sibling(self):
        if self._lms is None and self.parent and self is not self.parent.children[0]:
            self._lms = self.parent.children[0]
        return self._lms


def tidy_layout(root, children_of) -> dict:
    t = _T(root, children_of)
    _first_walk(t)
    _second_walk(t, -t.x)
    out = {}
    _collect(t, out)
    return out


def _collect(t, out):
    out[t.node] = (t.x, t.y * LEVEL_GAP)
    for c in t.children:
        _collect(c, out)


def _first_walk(v):
    if not v.children:
        v.x = v.left_brother().x + SIB_GAP if v.left_brother() else 0.0
        return v
    default_ancestor = v.children[0]
    for w in v.children:
        _first_walk(w)
        default_ancestor = _apportion(w, default_ancestor)
    _execute_shifts(v)
    midpoint = (v.children[0].x + v.children[-1].x) / 2
    w = v.left_brother()
    if w:
        v.x = w.x + SIB_GAP
        v.mod = v.x - midpoint
    else:
        v.x = midpoint
    return v


def _apportion(v, default_ancestor):
    w = v.left_brother()
    if w is None:
        return default_ancestor
    vir = vor = v
    vil = w
    vol = v.lmost_sibling()
    sir = sor = v.mod
    sil, sol = vil.mod, vol.mod
    while vil.right() and vir.left():
        vil, vir = vil.right(), vir.left()
        vol, vor = vol.left(), vor.right()
        vor.ancestor = v
        shift = (vil.x + sil) - (vir.x + sir) + SIB_GAP
        if shift > 0:
            _move_subtree(_ancestor(vil, v, default_ancestor), v, shift)
            sir += shift
            sor += shift
        sil += vil.mod
        sir += vir.mod
        sol += vol.mod
        sor += vor.mod
    if vil.right() and not vor.right():
        vor.thread = vil.right()
        vor.mod += sil - sor
    elif vir.left() and not vol.left():
        vol.thread = vir.left()
        vol.mod += sir - sol
        default_ancestor = v
    return default_ancestor


def _move_subtree(wl, wr, shift):
    subtrees = wr.number - wl.number
    wr.change -= shift / subtrees
    wr.shift += shift
    wl.change += shift / subtrees
    wr.x += shift
    wr.mod += shift


def _execute_shifts(v):
    shift = change = 0.0
    for w in reversed(v.children):
        w.x += shift
        w.mod += shift
        change += w.change
        shift += w.shift + change


def _ancestor(vil, v, default_ancestor):
    return vil.ancestor if vil.ancestor.parent is v.parent else default_ancestor


def _second_walk(v, m=0.0):
    v.x += m
    for w in v.children:
        _second_walk(w, m + v.mod)
