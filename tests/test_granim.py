"""Pipeline tests: emission, step rules, flip classification, determinism,
and the no-recorder contract (SPEC §13)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import granim as ga
from granim.core import recorder as rcore


@pytest.fixture(autouse=True)
def fresh():
    rcore.reset_ids()
    rcore._pending_structs.clear()
    rcore._pending_nodes.clear()
    assert rcore.active() is None
    yield
    rcore._pending_structs.clear()
    rcore._pending_nodes.clear()


def compile_of(fn, *args, **dec):
    rec_holder = {}
    wrapped = ga.animate(fn, show=False, out="__tmp__.html", **dec)
    orig_save = rcore.Recorder.save
    def save(self, path):
        rec_holder["tl"] = self.compile()
        return Path(path)
    rcore.Recorder.save = save
    try:
        result = wrapped(*args)
    finally:
        rcore.Recorder.save = orig_save
    return rec_holder["tl"], result


# -- no-recorder contract ------------------------------------------------------

def test_structures_work_unrecorded():
    a = ga.array([3, 1, 2])
    a.swap(0, 1)
    assert a.to_list() == [1, 3, 2]
    ll = ga.linked_list([1, 2, 3])
    assert ll.to_list() == [1, 2, 3]
    g = ga.graph()
    u, v = g.add_node("u"), g.add_node("v")
    g.add_edge(u, v)
    assert v in g.neighbors(u)


def test_algorithms_correct_with_recording():
    def rev(node, prev=None):
        while node is not None:
            node.next, prev, node = prev, node, node.next
        return prev

    tl, head = compile_of(lambda h: rev(h), ga.linked_list([1, 2, 3]).head)
    out = []
    while head is not None:
        out.append(head._value)
        head = head._next
    assert out == [3, 2, 1]


# -- flip classification --------------------------------------------------------

def _flip_count(tl):
    return sum(1 for s in tl["steps"] for op in s["ops"] if op["op"] == "edge_flip")


def test_iterative_reversal_flips():
    def rev(head):
        prev, cur = None, head
        while cur is not None:
            nxt = cur.next
            cur.next = prev
            prev, cur = cur, nxt
        return prev

    tl, _ = compile_of(rev, ga.linked_list([1, 2, 3, 4]).head)
    assert _flip_count(tl) == 3  # n-1 flips; first set is next=None, not a flip


def test_recursive_reversal_flips():
    def rev(node):
        if node is None or node.next is None:
            return node
        new_head = rev(node.next)
        node.next.next = node
        node.next = None
        return new_head

    tl, _ = compile_of(rev, ga.linked_list([1, 2, 3, 4]).head)
    assert _flip_count(tl) == 3
    unsets = [op for s in tl["steps"] for op in s["ops"] if op["op"] == "edge_unset"]
    flipped_keys = {op["from_key"] for s in tl["steps"] for op in s["ops"]
                    if op["op"] == "edge_flip"}
    assert not [u for u in unsets if u["key"] in flipped_keys]


def test_readding_same_direction_is_not_flip():
    def f(ll):
        n1 = ll.head
        n2 = n1.next
        n1.next = None
        n1.next = n2  # same direction re-add: must NOT be a flip
        return ll

    tl, _ = compile_of(f, ga.linked_list([1, 2]))
    assert _flip_count(tl) == 0


# -- step grouping ----------------------------------------------------------------

def test_bfs_frontier_batches():
    g = ga.graph(directed=False)
    hub = g.add_node("hub")
    spokes = [g.add_node(i) for i in range(4)]
    for s in spokes:
        g.add_edge(hub, s)

    def mark(g, hub):
        for v in g.neighbors(hub):
            v.state = "frontier"

    tl, _ = compile_of(mark, g, hub)
    batched = [s for s in tl["steps"]
               if sum(1 for op in s["ops"] if op["op"] == "state_set"
                      and op["state"] == "frontier") == 4]
    assert batched, "4 same-line state_sets should merge into one parallel step"


def test_traversal_reads_stay_separate():
    def walk(head):
        cur = head
        while cur is not None:
            cur = cur.next
        return True

    tl, _ = compile_of(walk, ga.linked_list([1, 2, 3]).head)
    read_steps = [s for s in tl["steps"]
                  if s["ops"] and all(op["op"] == "read" for op in s["ops"])]
    assert len(read_steps) >= 3  # one pulse per hop — the walk must stay visible


# -- debug vars --------------------------------------------------------------------

def test_index_vars_classified():
    def bsearch(a, x):
        lo, hi = 0, len(a) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if a[mid] == x:
                return mid
            if a[mid] < x:
                lo = mid + 1
            else:
                hi = mid - 1
        return -1

    tl, found = compile_of(bsearch, ga.array([1, 3, 5, 7, 9]), 7, debug=True)
    assert found == 3
    kinds = {v["name"]: v["kind"] for s in tl["steps"] for v in s["vars"]}
    assert kinds.get("lo") == "index" and kinds.get("mid") == "index"


def test_ref_vars_classified():
    def walk(head):
        cur = head
        cur = cur.next
        return cur

    tl, _ = compile_of(walk, ga.linked_list([1, 2]).head, debug=True)
    refs = [v for s in tl["steps"] for v in s["vars"] if v["kind"] == "ref"]
    assert refs and all(v["target"].startswith("n") for v in refs)


# -- reachability (orphan dimming) ---------------------------------------------

def test_dedup_orphans_detach():
    def dedup(head):
        cur = head
        while cur is not None and cur.next is not None:
            if cur.next.value == cur.value:
                cur.next = cur.next.next
            else:
                cur = cur.next
        return head

    tl, head = compile_of(dedup, ga.linked_list([1, 1, 2, 2, 3]).head)
    out = []
    while head is not None:
        out.append(head._value)
        head = head._next
    assert out == [1, 2, 3]
    detached = {op["id"] for s in tl["steps"] for op in s["ops"]
                if op["op"] == "state_set" and op["state"] == "detached"}
    assert len(detached) == 2  # the two duplicate nodes dim out


def test_reversal_never_detaches():
    def rev(head):
        prev, cur = None, head
        while cur is not None:
            nxt = cur.next
            cur.next = prev
            prev, cur = cur, nxt
        return prev

    tl, _ = compile_of(rev, ga.linked_list([1, 2, 3, 4]).head)
    assert not [op for s in tl["steps"] for op in s["ops"]
                if op["op"] == "state_set" and op["state"] == "detached"]


def test_floyd_badges_meet():
    ll = ga.linked_list([1, 2, 3, 4, 5, 6])
    nodes = list(ll)
    nodes[-1]._next = nodes[2]  # silent cycle (no recorder yet anyway)

    def has_cycle(head):
        slow = fast = head
        while fast is not None and fast.next is not None:
            slow = slow.next
            fast = fast.next.next
            if slow is fast:
                return True
        return False

    tl, found = compile_of(has_cycle, ll.head, debug=True)
    assert found is True
    assert _meet(tl), "slow and fast must point at the same node at the end"


def _meet(tl):
    for s in tl["steps"]:
        refs = {v["name"]: v.get("target") for v in s["vars"] if v.get("kind") == "ref"}
        if "slow" in refs and "fast" in refs and refs["slow"] == refs["fast"] \
                and refs["slow"] is not None:
            return True
    return False


# -- determinism & output -------------------------------------------------------------

def test_compile_deterministic():
    def f(a):
        a.swap(0, 2)
        return a

    tl1, _ = compile_of(f, ga.array([3, 2, 1]))
    rcore.reset_ids()
    tl2, _ = compile_of(f, ga.array([3, 2, 1]))
    assert json.dumps(tl1, sort_keys=True) == json.dumps(tl2, sort_keys=True)


def test_html_is_self_contained(tmp_path):
    def f(a):
        a.swap(0, 1)
        return a

    out = tmp_path / "x.html"
    ga.animate(f, show=False, out=out)(ga.array([2, 1]))
    html = out.read_text(encoding="utf-8")
    assert "granim-data" in html and "<script src=" not in html


def test_exception_still_saves(tmp_path):
    out = tmp_path / "boom.html"

    def f(a):
        a[0] = 9
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        ga.animate(f, show=False, out=out)(ga.array([1, 2]))
    assert out.exists() and "boom" in out.read_text(encoding="utf-8")


# -- matrix ------------------------------------------------------------------------

def test_matrix_unrecorded():
    m = ga.matrix([[1, 2], [3, 4]])
    assert m[0][1] == 2 and m[1, 0] == 3
    m[0][0] = 9
    m[1, 1] = 8
    assert m.to_lists() == [[9, 2], [3, 8]]
    assert len(m) == 2 and m.cols == 2


def test_matrix_flood_fill():
    m = ga.matrix([[1, 1, 0], [0, 1, 0], [0, 1, 1]])

    def flood(m, i, j, old, new):
        if not (0 <= i < len(m) and 0 <= j < m.cols):
            return
        if m[i][j] != old:
            return
        m[i][j] = new
        m[i][j].state = "visited"
        flood(m, i + 1, j, old, new)
        flood(m, i - 1, j, old, new)
        flood(m, i, j + 1, old, new)
        flood(m, i, j - 1, old, new)

    tl, _ = compile_of(flood, m, 0, 0, 1, 7)
    assert m.to_lists() == [[7, 7, 0], [0, 7, 0], [0, 7, 7]]
    vsets = [op for s in tl["steps"] for op in s["ops"] if op["op"] == "value_set"]
    states = [op for s in tl["steps"] for op in s["ops"]
              if op["op"] == "state_set" and op["state"] == "visited"]
    assert len(vsets) == 5 and len(states) == 5  # the connected region
    # grid layout: 9 cells at 3 distinct x and 3 distinct y positions
    pos = tl["keyframes"][0]["pos"]
    assert len(pos) == 9
    assert len({xy[0] for xy in pos.values()}) == 3
    assert len({xy[1] for xy in pos.values()}) == 3


# -- custom pointer slots (random, child, ...) -----------------------------------

def test_custom_pointer_becomes_edge():
    def copy_random(first, second):
        first.random = None
        second.random = first
        return first

    ll = ga.linked_list([7, 13])
    a, b = list(ll)
    tl, _ = compile_of(copy_random, a, b)
    edges = [op for s in tl["steps"] for op in s["ops"]
             if op["op"] == "edge_set" and op["slot"] == "random"]
    assert len(edges) == 1 and edges[0]["src"] == b._id and edges[0]["dst"] == a._id


def test_custom_slot_defaults_none_after_first_use():
    n1, n2 = ga.ListNode(1), ga.ListNode(2)
    n1.child = n2
    assert n2.child is None          # registered name -> default None
    with pytest.raises(AttributeError):
        _ = n1.nxet                  # never-assigned name -> typo, raises


def test_plain_custom_value_attr_no_edge():
    def f(head):
        head.weight = 42             # not a node: stored, not animated
        return head.weight

    tl, w = compile_of(f, ga.linked_list([1]).head)
    assert w == 42
    assert not [op for s in tl["steps"] for op in s["ops"]
                if op["op"] == "edge_set" and op["slot"] == "weight"]


def test_flatten_multilevel():
    def flatten(head):
        cur = head
        while cur is not None:
            if cur.child is not None:
                nxt = cur.next
                cur.next = cur.child
                cur.child.prev = cur
                cur.child = None
                tail = cur.next
                while tail.next is not None:
                    tail = tail.next
                tail.next = nxt
                if nxt is not None:
                    nxt.prev = tail
            cur = cur.next
        return head

    h, s2, c = ga.ListNode(1), ga.ListNode(2), ga.ListNode(7)
    h.next = s2
    h.child = c
    tl, head = compile_of(flatten, h)
    out = []
    while head is not None:
        out.append(head._value)
        head = head._next
    assert out == [1, 7, 2]
    # standalone nodes (no ga.linked_list) still get real chain positions
    pos = tl["keyframes"][-1]["pos"]
    assert len(pos) == 3 and len({xy[0] for xy in pos.values()}) == 3


# -- @ga.node: user-owned classes ---------------------------------------------------

def test_node_decorator_instruments_user_class():
    @ga.node(value="val", shape="pill")
    class N:
        def __init__(self, val):
            self.val = val
            self.next = None
            self.random = None

    def weave(a):
        b = N(a.val * 10)
        b.next = a.next
        a.next = b
        a.random = b
        b.val = 99
        return a

    n1, n2 = N(1), N(2)
    n1.next = n2  # pre-recording: stored silently, snapshot picks it up
    tl, head = compile_of(weave, n1)
    ops = [op for s in tl["steps"] for op in s["ops"]]
    assert sum(1 for o in ops if o["op"] == "node_add") == 3
    assert [o for o in ops if o["op"] == "edge_set" and o["slot"] == "random"]
    assert [o for o in ops if o["op"] == "value_set" and o["new"] == "99"]
    refs = [v for s in tl["steps"] for v in s["vars"] if v["kind"] == "ref"]
    assert refs and all(v["target"].startswith("n") for v in refs)
    # algorithm output intact
    assert head.val == 1 and head.next.val == 99 and head.random is head.next


def test_node_decorator_unrecorded_contract():
    @ga.node(value="v")
    class P:
        def __init__(self, v):
            self.v = v
            self.next = None

    a, b = P(1), P(2)
    a.next = b
    assert a.next is b and a.v == 1  # plain Python semantics, zero events


def test_tier2_record_context():
    with ga.record() as rec:
        ll = ga.linked_list([1, 2])
        n = ll.head
        rec.step("flip head")
        n.next = None
    tl = rec.compile()
    assert any(s["label"] == "flip head" for s in tl["steps"])
    assert any(op["op"] == "edge_unset" for s in tl["steps"] for op in s["ops"])


# -- @ga.container + custom-node orphan dimming -------------------------------------

def _queue_classes():
    @ga.node(value="val", shape="pill")
    class QNode:
        def __init__(self, val):
            self.val = val
            self.next = None

    class PlainQueue:
        def __init__(self):
            self.head = None
            self.tail = None
        def enqueue(self, v):
            n = QNode(v)
            if self.tail is not None:
                self.tail.next = n
            else:
                self.head = n
            self.tail = n
        def dequeue(self):
            n = self.head
            self.head = n.next
            n.next = None
            return n.val

    return QNode, PlainQueue


def test_container_badges_and_dequeue_dims():
    QNode, PlainQueue = _queue_classes()
    Queue = ga.container(type("Queue", (PlainQueue,), {}))

    def demo():
        q = Queue()
        for v in (1, 2, 3):
            q.enqueue(v)
        return q.dequeue()

    tl, first = compile_of(demo)
    assert first == 1
    ops = [op for s in tl["steps"] for op in s["ops"]]
    badge_slots = {o["slot"] for o in ops if o["op"] == "badge_set"}
    assert {"head", "tail"} <= badge_slots
    dimmed = [o["id"] for o in ops if o["op"] == "state_set" and o["state"] == "detached"]
    assert len(dimmed) == 1  # exactly the dequeued node


def test_plain_container_never_dims():
    QNode, PlainQueue = _queue_classes()

    def demo():
        q = PlainQueue()  # untracked container: granim can't see q.head
        for v in (1, 2, 3):
            q.enqueue(v)
        return q.dequeue()

    tl, first = compile_of(demo)
    assert first == 1
    # never-rooted nodes must NOT dim — granim has no visibility into q.head,
    # so claiming the chain is garbage would be a lie
    assert not [o for s in tl["steps"] for o in s["ops"]
                if o["op"] == "state_set" and o["state"] == "detached"]


def test_vars_die_with_their_frame():
    def helper(head):
        probe = head.next
        return probe

    def main(head):
        helper(head)
        x = head
        return x

    tl, _ = compile_of(main, ga.linked_list([1, 2]).head)
    steps_with_probe = [s["i"] for s in tl["steps"]
                        for v in s["vars"] if v["name"] == "probe"]
    last_step = tl["steps"][-1]["i"]
    assert steps_with_probe and max(steps_with_probe) < last_step, \
        "helper's local must vanish from the panel after helper returns"


# -- execution trace data --------------------------------------------------------

def test_timeline_carries_source_and_changes():
    def walk(head):
        cur = head
        while cur is not None:
            cur = cur.next
        return True

    tl, _ = compile_of(walk, ga.linked_list([1, 2]).head, debug=True)
    src = tl["meta"]["src"]
    assert src, "traced source lines must ship in meta.src"
    assert any("cur = cur.next" in line for line in src.values())
    assert any("while cur is not None" in line for line in src.values()), \
        "silent condition lines must ship via the `via` path"
    via_lines = [l for s in tl["steps"] for l in s.get("via", [])]
    assert via_lines, "silent lines between beats must be recorded"
    changed = [n for s in tl["steps"] for n in s.get("chg", [])]
    assert "cur" in changed


def test_via_lines_appear_once_per_execution():
    def rev(node):
        if node is None or node.next is None:
            return node
        new_head = rev(node.next)
        node.next.next = node
        node.next = None
        return new_head

    tl, _ = compile_of(rev, ga.linked_list([1, 2, 3, 4, 5]).head, debug=True)
    src = tl["meta"]["src"]
    ret_line = next(int(l) for l, t in src.items() if "return new_head" in t)
    count = sum(s.get("via", []).count(ret_line) for s in tl["steps"])
    assert count == 4, f"'return new_head' runs 4 times for 5 nodes, traced {count}"
    base_line = next(int(l) for l, t in src.items() if "return node" in t)
    count = sum(s.get("via", []).count(base_line) for s in tl["steps"])
    assert count == 1, f"base-case return runs once, traced {count}"


def test_struct_groups_never_overlap():
    # a graph that grows across keyframes must push the matrix out of its way
    g = ga.graph(directed=True)
    m = ga.matrix([[0] * 4, [0] * 4])

    def grow(g, m):
        prev = g.add_node("n0")
        for i in range(1, 7):
            cur = g.add_node(f"n{i}")
            g.add_edge(prev, cur)
            m[i % 2][i % 4] = i
            prev = cur
        return prev

    tl, _ = compile_of(grow, g, m)
    groups = {}
    for nid, meta in tl["nodes"].items():
        groups.setdefault(meta["struct"], set()).add(nid)
    (ga_ids, mb_ids) = [v for k, v in sorted(groups.items())]
    for kf in tl["keyframes"]:
        boxes = []
        for ids in (ga_ids, mb_ids):
            pts = [kf["pos"][n] for n in ids if n in kf["pos"]]
            if not pts:
                boxes.append(None)
                continue
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
        a, b = boxes
        if a and b:
            x_overlap = a[0] <= b[2] and a[2] >= b[0]
            y_overlap = a[1] < b[3] - 0.1 and a[3] > b[1] + 0.1
            assert not (x_overlap and y_overlap), \
                f"kf@step{kf['step']}: graph box {a} intersects matrix box {b}"
