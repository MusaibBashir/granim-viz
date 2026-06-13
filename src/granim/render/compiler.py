"""Compiles the event stream into deterministic timeline JSON: world replay,
edge-flip classification, orphan detection, layout keyframes."""
from __future__ import annotations

from ..layout import compose
from ..themes import resolve_theme

FLIP_WINDOW = 3
LIST_SLOTS = ("next", "prev", "head")


def compile_timeline(rec) -> dict:
    nodes: dict[str, dict] = {}
    struct_types = {s._id: s.type_name for s in rec.structs}
    struct_meta = {s._id: {"cols": getattr(s, "cols", None),
                           "title": getattr(s, "title", None)} for s in rec.structs}
    members: dict[str, list[str]] = {sid: [] for sid in struct_types}
    slots: dict[tuple[str, str], str] = {}       # (src, slot) -> dst, non-graph
    gedges: dict[str, set] = {sid: set() for sid in struct_types}  # graph edges
    alive: dict[tuple, str] = {}                 # (src, dst, cls) -> element key
    removed: dict[tuple, tuple] = {}             # (src, dst, cls) -> (step, op)
    consumed: dict[tuple, int] = {}
    out_steps = []
    keyframes = []
    prev_pos: dict | None = None
    var_state: dict[str, dict] = {}
    detached: set[str] = set()
    alive_nodes: set[str] = set()
    candidates: set[str] = set()  # lost a rooted incoming edge
    root_reach: set[str] = set()
    ext_roots = set(getattr(rec, "ext_roots", ()))

    def adopt(nid: str, sid: str | None):
        if sid and nid in nodes and nodes[nid]["struct"] is None:
            nodes[nid]["struct"] = sid
            members[sid].append(nid)

    for step in rec.sb.steps:
        ops = []
        structural = False
        for e in step.ops:
            p = e.payload
            if e.kind == "node_add":
                structural = True
                if p["id"] not in nodes:
                    nodes[p["id"]] = {"label": p["value"], "struct": p["struct"],
                                      "shape": p["shape"]}
                    if p["struct"]:
                        members[p["struct"]].append(p["id"])
                alive_nodes.add(p["id"])
                ops.append({"op": "node_add", "id": p["id"], "label": p["value"]})
            elif e.kind == "node_remove":
                structural = True
                alive_nodes.discard(p["id"])
                ops.append({"op": "node_remove", "id": p["id"]})
                sid = nodes[p["id"]]["struct"]
                if sid:
                    members[sid].remove(p["id"])
            elif e.kind == "edge_set":
                structural = True
                if p["old"] and (p["src"] in struct_types or p["src"] in root_reach):
                    candidates.add(p["old"])
                ops += _edge_ops(step.i, p, nodes, struct_types, slots, gedges,
                                 alive, removed, consumed, adopt)
            elif e.kind == "read":
                ops.append({"op": "read", "id": p["id"]})
            elif e.kind == "compare":
                ops.append({"op": "compare", "a": p["a"], "b": p["b"],
                            "a_repr": p["a_repr"], "b_repr": p["b_repr"],
                            "sym": p["op"], "result": p["result"]})
            elif e.kind == "value_set":
                ops.append({"op": "value_set", "id": p["id"], "old": p["old"],
                            "new": p["new"]})
            elif e.kind == "state_set":
                ops.append({"op": "state_set", "id": p["id"], "state": p["state"]})
            elif e.kind == "note":
                ops.append({"op": "note", "text": p["text"]})

        changed = []
        for e in step.vars:
            v = dict(e.payload)
            v["fid"] = e.frame
            name = v.pop("name")
            changed.append(name)
            var_state[name] = v
        # variables expire with their stack frame (fid 0 persists)
        live_fids = {f.get("fid", 0) for f in step.stack}
        var_state = {k: v for k, v in var_state.items()
                     if v["fid"] == 0 or v["fid"] in live_fids}

        # orphan pass: a candidate dims when unreachable from all roots
        # (struct/container slots, live vars, node args, return value)
        root_reach = _reach(alive_nodes, struct_types, slots,
                            ext_roots & alive_nodes)
        held = {v["target"] for v in var_state.values()
                if v.get("kind") == "ref" and v.get("target")}
        full_reach = _reach(alive_nodes, struct_types, slots,
                            (ext_roots | held) & alive_nodes)
        now_detached = {n for n in candidates & alive_nodes
                        if n not in full_reach
                        and struct_types.get(nodes[n]["struct"]) in DIMMABLE}
        for nid in sorted(now_detached - detached):
            ops.append({"op": "state_set", "id": nid, "state": "detached"})
        for nid in sorted(detached - now_detached):
            ops.append({"op": "state_set", "id": nid, "state": "default"})
        detached = now_detached

        if structural:
            keyframes.append({"step": step.i, "pos": _positions(
                struct_types, struct_meta, members, slots, gedges, nodes, prev_pos)})
            prev_pos = keyframes[-1]["pos"]

        out_steps.append({
            "i": step.i, "line": step.line, "depth": step.depth,
            "label": step.label, "kf": len(keyframes) - 1, "ops": ops,
            "chg": changed,
            "via": list(step.via),
            "vars": [{"name": k, **{kk: vv for kk, vv in v.items() if kk != "fid"}}
                     for k, v in var_state.items()],
            "stack": step.stack,
        })

    for s in out_steps:  # drop draw-offs consumed by flips
        s["ops"] = [o for o in s["ops"] if not o.get("suppress")]
    if rec.error and out_steps:
        out_steps[-1]["label"] = rec.error

    src_lines = getattr(rec, "src_lines", None) or []
    used = {s["line"] for s in out_steps if s["line"]}
    used |= {l for s in out_steps for l in s["via"]}
    src = {str(l): src_lines[l - 1].rstrip()[:90]
           for l in used if 0 < l <= len(src_lines)}
    code = _code_block(src_lines, used, getattr(rec, "func_first_line", None))

    return {
        "granim": "1",
        "meta": {"title": rec.title or "granim", "debug": rec.debug,
                 "speed": rec.speed, "error": rec.error, "src": src, "code": code},
        "theme": resolve_theme(rec.theme),
        "nodes": nodes,
        "structs": {sid: {"type": t, **{k: v for k, v in struct_meta[sid].items()
                                        if v is not None}}
                    for sid, t in struct_types.items()},
        "keyframes": [{"step": k["step"],
                       "pos": {n: [round(x, 2), round(y, 2)]
                               for n, (x, y) in sorted(k["pos"].items())}}
                      for k in keyframes],
        "steps": out_steps,
    }


def _edge_ops(step_i, p, nodes, struct_types, slots, gedges,
              alive, removed, consumed, adopt) -> list[dict]:
    src, slot, old, new = p["src"], p["slot"], p["old"], p["new"]
    ops = []

    if src in struct_types:  # head/root/container badge channels
        if slot != "edge":
            if new:
                slots[(src, slot)] = new
            else:
                slots.pop((src, slot), None)
            ops.append({"op": "badge_set", "src": src, "slot": slot, "dst": new})
            return ops

    cls = "list" if slot in LIST_SLOTS else "g"
    if slot == "edge":
        sid = nodes[src]["struct"]
        if new:
            gedges[sid].add((src, new))
        else:
            gedges[sid].discard((src, old))
    else:
        if new:
            slots[(src, slot)] = new
        else:
            slots.pop((src, slot), None)
        if new:
            adopt(new, nodes.get(src, {}).get("struct"))
            adopt(src, nodes.get(new, {}).get("struct"))

    if old is not None:
        ch = (src, old, cls)
        key = alive.pop(ch, _ekey(src, slot, old))
        if ch in consumed and step_i - consumed[ch] <= FLIP_WINDOW:
            consumed.pop(ch)  # already consumed by a flip
        else:
            op = {"op": "edge_unset", "src": src, "dst": old, "slot": slot, "key": key}
            removed[ch] = (step_i, op)
            ops.append(op)

    if new is not None:
        rev = (new, src, cls)
        key = _ekey(src, slot, new)
        if rev in alive:  # reverse edge currently on screen
            from_key = alive.pop(rev)
            consumed[rev] = step_i
            ops.append({"op": "edge_flip", "src": src, "dst": new, "slot": slot,
                        "key": key, "from_key": from_key})
        elif rev in removed and step_i - removed[rev][0] <= FLIP_WINDOW:
            r_step, r_op = removed.pop(rev)
            r_op["suppress"] = True  # its element survives to be flipped
            ops.append({"op": "edge_flip", "src": src, "dst": new, "slot": slot,
                        "key": key, "from_key": r_op["key"]})
        else:
            o = {"op": "edge_set", "src": src, "dst": new, "slot": slot, "key": key}
            if p.get("weight") is not None:
                o["w"] = p["weight"]
            ops.append(o)
        alive[(src, new, cls)] = key

    return ops


def _code_block(src_lines, used, first_line) -> list:
    """The contiguous source span to show in the player: from the function's
    def line (or first executed line) down to the last line that ever ran."""
    used = {l for l in used if 0 < l <= len(src_lines)}
    if not used:
        return []
    start = first_line if first_line and 0 < first_line <= min(used) else min(used)
    end = max(used)
    return [[l, src_lines[l - 1].rstrip("\n")[:200]] for l in range(start, end + 1)]


def _ekey(src, slot, dst) -> str:
    return f"{src}|{slot}|{dst}"


DIMMABLE = (None, "linked_list", "tree", "container")


def _reach(alive_nodes, struct_types, slots, extra_roots) -> set[str]:
    roots = set(extra_roots)
    adj: dict[str, list] = {}
    for (src, _slot), dst in slots.items():
        if not dst:
            continue
        if src in struct_types:
            roots.add(dst)
        else:
            adj.setdefault(src, []).append(dst)
    reach, frontier = set(), [r for r in roots if r in alive_nodes]
    while frontier:
        n = frontier.pop()
        if n in reach:
            continue
        reach.add(n)
        frontier += [d for d in adj.get(n, ()) if d not in reach]
    return reach


def _positions(struct_types, struct_meta, members, slots, gedges, nodes, prev_pos) -> dict:
    structs = []
    placed = set()
    for sid, t in struct_types.items():
        st = {"id": sid, "type": t, "members": list(members[sid]),
              "cols": struct_meta[sid]["cols"]}
        placed.update(st["members"])
        if t == "tree":
            children: dict[str, list] = {}
            for (src, slot), dst in slots.items():
                if slot.startswith("child:") and src in nodes:
                    children.setdefault(src, []).append((int(slot[6:]), dst))
            st["children"] = {s: [d for _, d in sorted(cs)] for s, cs in children.items()}
            st["root"] = slots.get((sid, "root"))
            if st["root"] is None:  # fall back to the member that is nobody's child
                kids = {d for cs in st["children"].values() for d in cs}
                st["root"] = next((m for m in st["members"] if m not in kids), None)
        elif t == "graph":
            st["edges"] = set(gedges[sid])
        structs.append(st)
    floating = [n for n in nodes if n not in placed and nodes[n]["struct"] is None]
    return compose(structs, floating, prev_pos, seed=1)
