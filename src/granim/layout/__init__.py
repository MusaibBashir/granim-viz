"""Per-structure layout with stable composition across keyframes."""
from __future__ import annotations

from .force import force_layout
from .layered import is_dag, layered_layout
from .linear import array_layout, list_layout, matrix_layout
from .tidy import tidy_layout

STRUCT_GAP = 3.0


def compose(structs: list[dict], floating: list[str], prev: dict | None, seed: int) -> dict:
    """Lay out each structure, then floating nodes, into one coordinate space.
    Groups that grow into an earlier group's box are pushed down (translation
    only, so intra-structure stability is preserved)."""
    pos: dict[str, tuple[float, float]] = {}
    boxes: list[tuple[float, float, float, float]] = []
    for st in structs:
        p = _layout_one(st, prev, seed)
        if not p:
            continue
        if prev and any(n in prev for n in p):
            p = _align(p, prev)  # translate only; never re-normalize survivors
        else:
            # new structure: stack below whatever is already placed
            xs = [xy[0] for xy in p.values()]
            ys = [xy[1] for xy in p.values()]
            y_off = (boxes[-1][3] + STRUCT_GAP) if boxes else 0.0
            p = {n: (x - min(xs), y - min(ys) + y_off) for n, (x, y) in p.items()}
        p = _push_clear(p, boxes)
        pos.update(p)
        boxes.append(_bbox(p))

    if floating:
        chain = _push_clear(list_layout(floating), boxes)
        for n, (x, y) in chain.items():
            pos[n] = prev[n] if prev and n in prev else (x, y)
    return pos


def _bbox(p) -> tuple[float, float, float, float]:
    xs = [xy[0] for xy in p.values()]
    ys = [xy[1] for xy in p.values()]
    return (min(xs), min(ys), max(xs), max(ys))


def _push_clear(p: dict, boxes) -> dict:
    """Translate a group downward until it no longer intersects earlier groups."""
    if not p:
        return p
    x0, y0, x1, y1 = _bbox(p)
    dy = 0.0
    for bx0, by0, bx1, by1 in boxes:
        if x0 <= bx1 + 1.0 and x1 >= bx0 - 1.0 and y0 + dy <= by1 + STRUCT_GAP * 0.5:
            dy = max(dy, by1 + STRUCT_GAP - y0)
    if dy:
        return {n: (x, y + dy) for n, (x, y) in p.items()}
    return p


def _layout_one(st: dict, prev, seed) -> dict:
    t, members = st["type"], st["members"]
    if not members:
        return {}
    if t == "array":
        return array_layout(members)
    if t == "matrix":
        return matrix_layout(members, st["cols"])
    if t == "linked_list":
        return list_layout(members)
    if t == "tree":
        root = st.get("root") or members[0]
        children = st["children"]  # id -> ordered child ids
        laid = tidy_layout(root, lambda n: children.get(n, ()))
        for m in members:  # detached subtree nodes keep their previous spot
            if m not in laid:
                if prev and m in prev:
                    laid[m] = prev[m]
                else:
                    laid[m] = (max(x for x, _ in laid.values()) + 1.6, 0.0)
        return laid
    edges = st["edges"]
    if is_dag(members, edges):
        return layered_layout(members, edges)
    return force_layout(members, edges, prev, seed)


def _align(p: dict, prev) -> dict:
    common = [n for n in p if n in prev]
    if not common:
        return p
    mdx = sum(p[n][0] - prev[n][0] for n in common) / len(common)
    mdy = sum(p[n][1] - prev[n][1] for n in common) / len(common)
    if abs(mdx) < 1e-9 and abs(mdy) < 1e-9:
        return p
    return {n: (x - mdx, y - mdy) for n, (x, y) in p.items()}
