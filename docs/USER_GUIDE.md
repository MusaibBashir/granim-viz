# granim — User Guide

granim turns the algorithm you already wrote into an interactive animation. You
write normal Python against granim's data structures (or your own classes,
decorated); running the function produces a single self-contained HTML file
with a player: nodes appear, arrows flip, cells change color, variables hop
between nodes, the line of source you're on stays highlighted, and you can
drag nodes apart and scrub through every step.

```
pip install granim-viz
```

```python
import granim as ga
```

The PyPI name is `granim-viz`; the import name is `granim`. Zero dependencies,
Python ≥ 3.10. Every snippet in this guide is runnable as-is.

---

## 1. The one decorator: `@ga.animate`

```python
import granim as ga

@ga.animate(debug=True)
def reverse(head):
    prev, cur = None, head
    while cur is not None:
        nxt = cur.next
        cur.next = prev
        prev, cur = cur, nxt
    return prev

reverse(ga.linked_list([1, 2, 3, 4, 5]).head)
```

Run it. A `reverse.html` appears next to your script (named after the
*function*) and opens in your browser. Each loop iteration is one animation
beat; `cur.next = prev` renders as the arrow visibly reversing; `prev`/`cur`/
`nxt` badges hop from node to node.

All parameters (every one optional):

| parameter | default | meaning |
|---|---|---|
| `debug`   | `False` | show the side panel (variables, call stack) and on-canvas badges |
| `theme`   | `"dark"` | `"dark"` (manim-style black), `"light"`, `"contrast"`, or a dict overlay like `{"base": "dark", "--node-stroke": "#ff5577"}` |
| `out`     | `<funcname>.html` | output path |
| `show`    | auto | open in browser (scripts) / render inline (Jupyter); `False` to just write the file |
| `speed`   | `1.0` | initial playback speed |
| `title`   | function name | header title |

Useful facts: the decorated function's return value is passed through
unchanged; recursion through the decorated name records as one animation; if
the function **raises**, the partial animation is still saved with the
exception as the final step label — animating a crash is a feature. In
Jupyter, the animation renders inline automatically.

## 2. Built-in structures

All five work as plain Python with no recording active — your algorithm stays
unit-testable. They only emit animation events inside a recorded call.

### `ga.array(values)`

```python
arr = ga.array([2, 5, 8, 12, 16, 23, 38, 56, 72, 91])

@ga.animate(debug=True)
def binary_search(a, x):
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

binary_search(arr, 23)
```

`a[i]` pulses the cell; comparisons (`a[mid] < x`) animate with a floating
`8 < 23 ✓` glyph; `a[i] = v` animates the value swap; `a.swap(i, j)` swaps two
cells in one beat; `a[i].state = "done"` colors a cell. **Index badges are
automatic**: any int local in range (here `lo`, `hi`, `mid`) renders as a
pointer under the cells — no annotation needed. Elements must be scalars
(int/float/str/bool/None).

### `ga.linked_list(values, doubly=False)`

```python
ll = ga.linked_list([1, 2, 3], doubly=True)
node = ll.head          # tracked: a "head" badge floats over this node
node.next               # read -> pulse
node.next = other       # edge_set -> arrow redraws (or flips, see below)
node.value, node.value = ...  # reads/writes animate
list(ll), ll.to_list()  # plain iteration helpers
```

Notes for doubly lists: `prev` edges render as arcs above the chain;
`node.next = x` does **not** auto-set `x.prev` — set both explicitly, exactly
like LeetCode code does. **The flip animation** is automatic: when you point an
edge back along a channel that just carried the reverse edge (`cur.next =
prev`, or recursive `node.next.next = node`), granim classifies it as a flip
and animates the arrow turning around instead of delete+add.

Unlinked nodes **dim out** automatically once nothing points to them and no
variable holds them (try the dedup example) — see §6.

### `ga.tree(adj=None)` and `ga.TreeNode`

```python
t = ga.tree()                       # empty; or ga.tree({"A": ["B","C"], "B": ["D"]})

@ga.animate(debug=True)
def insert(t, values):
    for v in values:
        node = ga.TreeNode(v)
        if t.root is None:
            t.root = node
            continue
        cur = t.root
        while True:
            if v < cur.value:
                if cur.left is None:
                    cur.left = node; break
                cur = cur.left
            else:
                if cur.right is None:
                    cur.right = node; break
                cur = cur.right

insert(t, [50, 30, 70, 20, 40, 60, 80])
```

Tidy-tree layout (Buchheim) re-flows as nodes attach. `left`/`right` are sugar
over a children list; `node.add_child(c)` for n-ary trees.

### `ga.graph(directed=True, title=None)`

```python
g = ga.graph(directed=False)
a, b = g.add_node("A"), g.add_node("B")
g.add_edge(a, b, weight=4)     # weights render as edge labels
g.neighbors(a); g.weight(a, b)
a.state = "frontier"           # color: default/active/visited/frontier/done
```

DAGs get layered layout; cyclic graphs get force-directed (deterministic —
same input, same picture). State changes on the same line of a loop body merge
into one **parallel** beat: a BFS frontier lights up all at once, no
annotations needed. Pass `title=` to caption the graph on the canvas; because
each `ga.graph(...)` is its own laid-out structure, making two of them renders
two separate titled graphs — a forward pass and a backward pass, say
(`examples/rnn_bptt.py`).

```python
fwd = ga.graph(directed=True, title="Forward")
bwd = ga.graph(directed=True, title="Backward")

@ga.animate(show=False)
def two_graphs():
    x, h = fwd.add_node("x"), fwd.add_node("h")
    fwd.add_edge(x, h, weight="W")           # built into the Forward graph
    dh, dx = bwd.add_node("dh"), bwd.add_node("dx")
    bwd.add_edge(dh, dx, weight="Wᵀ")        # a second, separately-titled graph

two_graphs()
```

### `ga.matrix(rows)`

```python
m = ga.matrix([[1, 1, 0], [0, 1, 0], [0, 1, 1]])
x = m[0][1]                # read (row-proxy indexing, like normal DP code)
y = m[0, 1]                # tuple indexing also works
m[1][2] = 7                # value animates
m[1][2].state = "visited"  # cell color animates
rows, cols = len(m), m.cols
```

See `examples/flood_fill.py` (colors + values spreading recursively) and
`examples/edit_distance.py` (DP table filling, dependency cells pulsing).

## 3. Your own classes: `@ga.node` and `@ga.container`

You don't have to use granim's structures at all.

```python
@ga.node(value="val", shape="pill")     # shape: "pill" | "circle" | "cell"
class Node:                              # the exact class LeetCode gives you
    def __init__(self, val):
        self.val = val
        self.next = None
        self.random = None
```

No inheritance. Rules: a field assigned a **node** becomes an animated edge
(`next`/`prev` are drawn as list edges and participate in flips; any other
name — `random`, `child`, `down` — arcs underneath with its name as a label).
The field named by `value=` animates label changes. Anything else
(`self.weight = 42`) is plain storage. Reads of node-valued fields pulse.
Iterators work: a generator `__iter__` defined in your file animates step by
step, appears in the call stack panel, and its locals get badges.

Pass `graph=True` to lay a web of these nodes out like `ga.graph` (layered DAG
or force-directed) instead of a chain: every node-valued field — a single node
*or* a list/set of them — becomes a clean graph edge, exactly what a
computation graph needs. `graph="forward"` does the same into a *named*, titled
graph, so instances can be split across, say, a forward and a backward graph
(`examples/expr_graph.py`).

```python
@ga.node(value="label", shape="circle", graph=True)
class Value:                                   # a micrograd-style scalar
    def __init__(self, data, label="", children=()):
        self.data = data
        self.label = label or f"{data:.1f}"
        self.children = list(children)         # node fields -> graph edges
    def __add__(self, o): return Value(self.data + o.data, "+", (self, o))
    def __mul__(self, o): return Value(self.data * o.data, "×", (self, o))

@ga.animate(show=False)
def expr():
    a, b, c = Value(2, "a"), Value(-3, "b"), Value(10, "c")
    return a * b + c        # the result's `children` wire up a DAG, not a chain

expr()
```

```python
@ga.container
class Queue:
    def __init__(self):
        self.head = None
        self.tail = None
    def enqueue(self, v): ...
    def dequeue(self): ...
```

`@ga.container` is for the wrapper object: its node-valued fields (`head`,
`tail`, `top`, any name) render as floating badges that follow their node, and
they anchor garbage detection — dequeued nodes dim out. Without the decorator
the container is simply invisible (the chain still animates; nothing dims,
because granim refuses to guess about objects it can't see).

Ad-hoc fields work on built-in nodes too: `node.random = other` on a
`ga.ListNode` animates the same way. Once a field name has been used on a
class, reading it on other instances returns `None` (LeetCode convention);
truly unknown names still raise `AttributeError`, so typos stay loud.

## 4. The HTML player

One file, fully offline, shareable. The canvas sits in the middle; with
`debug=True` a **source** and a **this step** panel appear on the left and a
**state** panel on the right.

**Canvas.** Nodes appear, arrows flip, cells recolor. **Drag any node** to move
it — its edges follow and stay attached, and a dragged node holds its spot as
later steps re-flow everything else (handy when a dense graph overlaps itself).
Double-click a node to send it back to its computed position, or press `r` to
release them all. Scroll to zoom, drag the background to pan, double-click empty
space (or `f`) to fit. `ga.graph(title=…)` / `@ga.node(graph="name")`
structures show their title above them.

**Source (left, top).** The function's source with the executing line
highlighted; it auto-scrolls to follow execution inside its own scroll box.

**This step (left, bottom).** A separate panel — so the source scrolling never
moves it — listing what the current beat did: edges set, value/state changes,
comparisons and their outcome, loop/call/return markers, and any note.

**State (right).** For the current step: **variables** (`→ name`, amber, are
node references), **iterators** (loop indices like `i`/`t`), **node states**
(every node currently active/visited/frontier/done), and the **call stack** with
the active frame highlighted. Values vanish when their function returns.

**Controls.** Play/pause (`Space`), step forward/back (`→` / `←`), `Home`/`End`,
a scrubber, and a speed menu (0.25×–4×, remembered between sessions). The header
chip shows the current source line. Every recording ends on one extra beat
showing the final state.

### Captions: `ga.note()`

`ga.note("forward pass")` drops a caption onto the canvas at that point in your
code. It stays until the next note (`ga.note(None)` clears it) and is a no-op
outside a recording, so it never disturbs the plain algorithm — use it to narrate
phases. Notes also show in the *this step* feed. A note is not a structure: it has
no nodes or edges and doesn't affect layout.

```python
@ga.animate(debug=True, show=False)
def search(a, x):
    ga.note("scanning left to right")
    for i in range(len(a)):
        if a[i] == x:
            ga.note(f"found {x} at index {i}")
            return i
    ga.note(None)                              # clear the caption
    return -1

search(ga.array([4, 8, 15, 16, 23]), 15)
```

## 5. Tier 2: manual control

The decorator covers ~95% of use. For the rest:

```python
with ga.record(debug=True) as rec:
    ll = ga.linked_list([1, 2, 3])
    rec.step("about to break the chain")   # explicit labeled beat
    with rec.batch():                       # everything inside = one beat
        ...
    with rec.quiet():                       # suppress read/compare pulses
        ...
    rec.watch(i=ga.index(arr, i))           # override badge classification
rec.save("out.html")                        # or rec.show() in Jupyter
```

Tier 2 has no tracing: there is no automatic stepping, so use `rec.step()` /
`rec.batch()` to shape beats.

## 6. How granim decides things (so the output never surprises you)

**Steps.** One executed source line = one beat. Repeated executions of the
same line that only color/add nodes merge into a parallel beat. Pointer-walk
reads stay one beat per hop, so traversals are visible.

**Dimming.** A node dims only when (a) it explicitly lost an incoming edge
whose source granim could see was rooted, and (b) nothing reachable holds it —
where "held" means: a struct/container field, a live local variable, a
node-valued argument, or the function's return value. Plain invisible
containers never cause dimming.

**Layout.** Arrays/matrices are grids; lists are chains in creation order
(stable: nodes hold still while arrows flip; long lists snake-wrap); trees are
tidy; graphs are layered (DAG) or force-directed (cyclic, seeded). Positions
never lurch between steps.

**Limits.** 20,000 events / 500 nodes / 3,000 steps — beyond that an animation
is unwatchable, so granim raises a `GranimError` naming the hot source line
instead of producing one.

## 7. Gotchas

- `is` comparisons (`slow is fast`) are invisible to instrumentation — Python
  gives no hook. The meeting still shows: both badges land on the same node.
- Builtins like `deque`/`dict`/`list` are untracked; use them freely for
  bookkeeping, but only granim structures and decorated classes animate.
- Functions must live in the same file as the `@ga.animate` function to get
  per-line steps and stack frames; imported helpers still animate correctly
  but coarser (their events merge into the calling line's beat).
- List layout follows node *creation order* — insert-at-head reads as a
  backward arc rather than a reshuffle.
- Keep inputs teaching-sized (≲ 30 nodes); that's the point of the tool.

## 8. Gallery

The `examples/` folder is the feature tour — each file is a dozen lines:
`binary_search`, `reverse_recursive` (stack panel + flips on unwind),
`reverse_iterative`, `bst`, `bfs` (parallel frontier), `dedup` (orphans dim),
`floyd` (cycle + badges meeting), `flood_fill` (matrix), `dijkstra` (weights),
`quicksort`, `edit_distance` (DP), `custom_node` (`@ga.node`, LeetCode 138),
`queue` (`@ga.container`), `expr_graph` (`@ga.node(graph=…)` computation graph
with `ga.note` captions), `rnn_bptt` (two titled graphs — forward activations and
backward gradients — Karpathy's min-char-RNN with BPTT).
