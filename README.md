# granim

Write the algorithm. Get the animation.

granim instruments its data structures so that running your *normal* Python code
produces an interactive, self-contained HTML animation. Nodes appear as you
build, arrows flip as you reverse, frontiers light up in parallel, and debug mode
shows every variable hopping between nodes.

```python
import granim as ga

@ga.animate(debug=True)
def reverse(node):
    if node is None or node.next is None:
        return node
    new_head = reverse(node.next)
    node.next.next = node
    node.next = None
    return new_head

reverse(ga.linked_list([1, 2, 3, 4, 5]).head)   # -> reverse.html, opens in browser
```

That's the entire integration: one decorator, one constructor. The recursion walks
to null while the call stack panel fills; on the way back, each arrow visibly
reverses (granim classifies `node.next.next = node` as an *edge flip*, not a
delete+add).

## What you get

- **Automatic steps** — each loop iteration is one animation beat; same-line
  mutations (a BFS frontier) merge into one *parallel* beat. No annotations.
- **Debug mode** (`debug=True`) — all locals in a side panel, plus on-canvas
  badges: node-valued variables dock to their node, ints near an array become
  index pointers (`lo`/`hi`/`mid` under the cells).
- **Five structures** — `ga.array`, `ga.matrix`, `ga.linked_list`, `ga.tree`,
  `ga.graph`, all usable (and unit-testable) without recording. Matrix cells
  animate values (`m[i][j] = v`) and colors (`m[i][j].state = "visited"`).
- **Your own classes** — `@ga.node(value="val")` instruments any class without
  inheritance: node-valued fields become labeled edges, the value field animates,
  everything else is plain storage. Ad-hoc fields on granim nodes work too
  (`node.random`, `node.child` arc underneath with their name on them).
  `@ga.container` does the same for wrappers (queues, custom lists): `head`/
  `tail`-style fields render as floating badges and root the garbage pass, so
  dropped nodes dim out.
- **Auto layout** : tidy trees (Buchheim), layered DAGs, force-directed graphs,
  snake-wrapped lists; positions stay stable between steps instead of jumping.
- **One file out** : interactive player (play/pause/step/scrub/speed) in a single
  offline HTML file. Jupyter renders inline automatically.
- **Zero dependencies.**

## Examples

`examples/` doubles as the acceptance suite:

| file | shows off |
|---|---|
| `binary_search.py` | auto index badges, comparison pulses |
| `reverse_recursive.py` | call stack + arrows flipping on unwind |
| `reverse_iterative.py` | `prev`/`cur`/`nxt` badges hopping |
| `bst.py` | tidy tree re-flowing as nodes attach |
| `bfs.py` | parallel frontier steps, state coloring |
| `dedup.py` | unlinked nodes dim out (reachability pass) |
| `floyd.py` | tortoise/hare badges meeting; cycle arc |
| `flood_fill.py` | matrix: values + colors spreading, deep recursion |
| `dijkstra.py` | weighted edges, frontier/visited/done coloring |
| `quicksort.py` | pivot glow, swaps, sorted cells locking in |
| `edit_distance.py` | DP table filling, dependency-cell pulses |
| `custom_node.py` | `@ga.node` on a user-owned class (LeetCode 138) |
| `queue.py` | `@ga.container`: head/tail badges, dequeued nodes dim |

Run any of them: `PYTHONPATH=src python examples/bfs.py` → open the HTML next to it.

## Tests

```
python tests/run_tests.py        # pure-python pipeline tests (pytest also works)
node tests/verify_html.js        # replays each example's timeline, checks end state
```

## Design

`docs/PLAN.md` holds the rationale, `docs/SPEC.md` the contracts. The short version:
structures emit a small vocabulary of semantic events; a step builder groups them
into beats (line-scoped via a trace limited to your function); a pure compiler
classifies edge flips, computes layout keyframes, and serializes a timeline that
a dependency-free JS player animates. The trace can only ever coarsen steps
animation truth comes from the structures.
