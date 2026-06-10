"""Per-structure layout with stable composition across keyframes."""
from __future__ import annotations

from .force import force_layout
from .layered import is_dag, layered_layout
from .linear import array_layout, list_layout, matrix_layout
from .tidy import tidy_layout

STRUCT_GAP = 3.0


def compose(structs: list[dict], floating: list[str], prev: dict | None, seed: int) -> dict:
    """Lay out each structure, then floating nodes, into one coordinate space."""
    pos: dict[str, tuple[float, float]] = {}
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
            y_off = max((y for _, y in pos.values()), default=-STRUCT_GAP) + STRUCT_GAP
            p = {n: (x - min(xs), y - min(ys) + y_off) for n, (x, y) in p.items()}
        pos.update(p)

    if floating:
        # structless nodes: chain by creation order below everything
        y_off = max((y for _, y in pos.values()), default=-STRUCT_GAP) + STRUCT_GAP
        chain = list_layout(floating)
        for n, (x, y) in chain.items():
            pos[n] = prev[n] if prev and n in prev else (x, y + y_off)
    return pos


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
