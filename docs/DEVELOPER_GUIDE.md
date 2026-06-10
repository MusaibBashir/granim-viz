# granim — Developer Guide

For contributors.
This guide is the codebase walkthrough: how a line of user Python becomes a frame of animation, and where to cut when you extend it.

## 0. The pipeline in one picture

```
user code runs
  │  structures' descriptors / decorator hooks emit Events  (structures/*)
  │  scoped sys.settrace adds line/call/return boundaries   (core/trace.py)
  ▼
Recorder collects Events ──► StepBuilder groups them into Steps   (core/*)
  ▼
compile_timeline(): world replay, flip classification, orphan pass,
layout keyframes ──► timeline JSON                         (render/compiler.py)
  ▼
single HTML file = template + CSS + JS player + embedded JSON   (render/html.py)
browser: player.js replays ops as SVG animations          (render/player/)
```

The load-bearing invariant: **the trace never emits structure events**. Events
come only from instrumented attribute access. A broken or absent trace degrades
step granularity, never correctness of the drawing.

## 1. Event model (`core/events.py`)

Eight event kinds, deliberately closed: `node_add`, `node_remove`, `edge_set`
(with `new=None` as the unset case), `read`, `compare`, `value_set`,
`state_set`, `var_set`. Each `Event` is a frozen dataclass: `(seq, kind,
payload, depth, line, frame)`. Payloads carry only ids and truncated reprs —
never references to user objects, so recordings are serializable and leak-free.
`edge_flip` is **not** an event: it's a classification the compiler assigns.
Resist adding kinds; almost everything is expressible as these eight plus a
compiler pass.

Identity: nodes are `"n<k>"`, structures/containers `"s<k>"` (module-level
counters in `core/recorder.py`; `reset_ids()` for tests). Edges are not
entities — an edge is `(src, slot, dst)`, where slot ∈ `next`, `prev`,
`child:<i>`, `edge` (graphs), `head`/`root`/any container field (badge
channels, src is an `s` id), or any custom name.

## 2. Emission: how structures talk (`structures/`)

`core/recorder.py:emit(kind, **payload)` is a module-level function that
routes to the active recorder or silently no-ops — this is why every structure
works unrecorded.

- **Built-ins** (`array/linked_list/tree/graph/matrix.py`) use property
  descriptors on `__slots__` classes: `ListNode.next` getter emits `read`,
  setter emits `edge_set` with old/new. `Array`/`Matrix` cells are nodes;
  reads return a `Tracked` proxy (`tracked.py`) implementing the number
  protocol so `a[i] < x` emits `compare`; arithmetic results unwrap to plain
  values. `Tracked.__setattr__` intercepts `.state` for cell coloring.
- **Custom slots** (`base.py`): `NodeBase.__setattr__` first tries
  `object.__setattr__` (slots/properties win); on `AttributeError` the name
  becomes a dynamic slot stored in `_extra` — node values emit `edge_set`,
  others store silently. `__getattr__` serves `_extra`, returns `None` for
  names registered on the class (`_CUSTOM_NAMES`), raises otherwise.
- **User classes** (`custom.py`): `@ga.node` injects `__init__` (assign `_id`,
  suppress events during construction via `_ga_building`, then self-snapshot),
  `__setattr__` (edge/value classification), `__getattribute__` (read pulses
  on node-valued fields). Identity is duck-typed: `base.is_node()` checks
  `isinstance NodeBase or type(v)._ga_node` — use it everywhere, never
  isinstance directly. `@ga.container` is the same trick with an `s` id;
  its field writes land in the compiler's badge branch.

Pre-creation: structures and standalone nodes built before recording register
in `_pending_structs`/`_pending_nodes`; `Recorder.__enter__` snapshots them
into step 0 (nodes first, so struct edges can adopt them).

## 3. Recorder + StepBuilder (`core/recorder.py`, `core/steps.py`)

`Trace` (`core/trace.py`) installs `sys.settrace` for the duration of the
decorated call only, and only traces frames whose `co_filename` matches the
decorated function's file — stdlib/import frames cost one comparison.
Generators behave correctly for free: each resume fires `call`, each
yield/return fires `return`, so the stack stays balanced.

On every `line` event the recorder (1) diffs `frame.f_locals` by repr against
the previous reading and emits `var_set` for changes (always — debug only
controls *display*; the compiler's reachability pass needs refs), then (2)
signals a boundary to the StepBuilder. On `return` it pops the stack and
clears the caller's locals cache so the caller's view re-emits (badges snap
back when recursion unwinds).

StepBuilder rules (each has a dedicated test):

1. boundary (new line / call / return / explicit `rec.step`) flushes pending
   events into a Step;
2. a flush merges into the previous step iff same line+depth and both consist
   only of `state_set`/`node_add` mutations — that's BFS-frontier parallelism;
3. read/compare events never block a merge, and a read-only flush is its own
   step (the pointer walk must stay visible);
4. `rec.quiet()` drops reads at emission; `rec.batch()` suspends grouping;
5. var-only flushes don't create beats — they attach to the next real step;
6. `finish()` appends one synthetic ops-free final step so end state (pruned
   vars, final dims) renders.

Steps carry stack snapshots `{fn, args, fid}` — `fid` is the frame serial the
compiler uses to expire variables.

## 4. The compiler (`render/compiler.py`)

Pure function: `(recorder) -> timeline dict`, deterministic to the byte
(sorted keys, fixed float precision, no timestamps) — that's what makes
golden-style tests trivial. It replays events through a world model in one
pass:

- **World state**: `nodes` (id → label/struct/shape), `members` per struct,
  `slots` ((src, slot) → dst), `gedges` per graph, `alive_nodes`.
- **Flip classification** (`_edge_ops`): an `edge_set src=S new=N` becomes
  `edge_flip` if the reverse channel N→S is alive *now* (recursive reversal:
  `node.next.next = node`) or was removed within the last `FLIP_WINDOW=3`
  steps (iterative: the prior `prev.next=` unset). The consumed element's
  draw-off is suppressed retroactively (`suppress` flag, filtered at the end)
  and a `consumed` map keeps its later unset silent. The false-positive guard
  (re-adding the same direction ≠ flip) is pinned by a test.
- **Variable lifetime**: `var_set` events fold into a cumulative `var_state`
  keyed by name, tagged with `fid`; entries whose frame is no longer on the
  step's stack are dropped (fid 0 = Tier-2 watch vars, persist).
- **Orphan pass** (`_unreachable`/`_reach`): candidates = nodes that appeared
  as `old` in an edge whose src was struct-rooted at the previous step (or was
  an `s` id). A candidate dims iff unreachable from {struct/container slots ∪
  live var refs ∪ `rec.ext_roots`} following all node slots. `ext_roots` are
  the decorated call's node-valued arguments and return value — caller-owned.
  Only `None`/`linked_list`/`tree`/`container`-typed nodes can dim. The
  asymmetry is deliberate: plain invisible containers can never produce
  candidates, so granim never claims a chain it can't see is garbage.
- **Keyframes**: steps containing structural ops trigger a layout pass; the
  step records a keyframe index; the player tweens positions between
  keyframes.

## 5. Layout (`layout/`)

`compose()` lays each struct independently and composes: arrays/matrices are
grids (`linear.py`), lists are creation-order chains with snake wrap (the
point: nodes hold still during pointer surgery), trees are Buchheim–Walker
(`tidy.py` — adapted from the canonical reference, don't improvise there),
graphs are layered for DAGs (`layered.py`: longest-path layering + barycenter
sweeps) or seeded Fruchterman–Reingold (`force.py`, warm-startable). Floating
nodes (no struct — raw/decorated nodes) chain in creation order below
everything. **Stability contract**: surviving structures are only translated
(mean-displacement alignment in `_align`), never re-normalized; force layouts
warm-start from previous positions; new nodes spawn near a neighbor.

## 6. Rendering (`render/html.py`, `render/player/`)

`render_html()` inlines `template.html` + `player.css` + `player.js` + the
JSON (with `</` escaped) into one offline file. The player (~450 lines,
dependency-free):

- precomputes per-step world states by replaying ops (powers the scrubber and
  back-stepping — backward = instant `renderState`, forward = animated);
- one animation primitive per op type (`PRIM`): scale-in for `node_add`,
  stroke-dash draw-on/off for edges, simultaneous draw-on/off in flip color
  for `edge_flip`, expanding ring for `read`, floating glyph for `compare`,
  text swap for `value_set`, CSS color transition for `state_set`;
- geometry in `edgePath`: straight for forward list edges/tree/graph,
  arc-above for backward `next`/`prev`, arc-below with a name label for
  custom slots, bezier self-loop;
- badges (var refs, indices, container fields) are SVG groups tweened between
  targets; the panel and stack render from the step's `vars`/`stack`.

Theming is exactly the 17 CSS custom properties in `themes.py` — a theme dict
overlay validates against that token set.

## 7. Testing (`tests/`)

- `test_granim.py` (27 tests) covers: the no-recorder contract, every
  StepBuilder rule, the flip truth table (both reversal shapes + the
  false-positive guard), variable classification, dimming (orphans dim;
  reversal never dims; plain containers never dim), `@ga.node`/`@ga.container`
  behavior, determinism, error-still-saves. `run_tests.py` is a pytest shim so
  the suite runs with zero deps.
- `verify_html.js` replays every example's embedded timeline in Node and
  asserts the *algorithmic end state* (e.g. reversal ends 5→4→3→2→1 with
  exactly 4 flips on screen) — browserless end-to-end coverage.
- A LeetCode harness (20 linked-list problems) lives in the author's test
  folder; it's the source of several features (custom slots, standalone-node
  adoption).

Convention: every bug fix lands with a test pinning it; compiler changes
should keep `test_compile_deterministic` green.

## 8. How to extend

**A new animation effect**: add a compiler op (usually a pass over existing
events, like `edge_flip`) + a `PRIM` entry + CSS. Don't add an event kind
unless emission genuinely can't express it.

**A new structure**: subclass `Struct`, give nodes `NodeBase` (or document
`@ga.node`), emit the eight kinds from descriptors, implement `_snapshot()`
for pre-recording adoption, add a branch in `layout/__init__._layout_one`,
and decide its dimming eligibility (`DIMMABLE` in the compiler). `Matrix` is
the model citizen to copy (~100 lines + a 3-line layout).

**A new layout**: pure function `members/edges -> {id: (x, y)}` in grid units,
deterministic, ideally warm-startable. Wire it in `_layout_one`.

**A new theme**: a dict of the 17 tokens in `themes.py`.

Known sharp edges for contributors: `sys.settrace` only (the `sys.monitoring`
backend for 3.12+ is designed in SPEC §4.1 but not built); `is` comparisons
are invisible (no hook exists); per-class `_CUSTOM_NAMES` is global state —
tests reset via the `fresh` fixture; the dev sandbox used to build this had a
file-sync quirk — if tests behave impossibly, delete `__pycache__` and set
`PYTHONDONTWRITEBYTECODE=1`.

**Release**: bump `__version__` + `pyproject.toml` together (the build script
asserts they match). `python -m build` on a normal machine, or
`python tools/build_dist.py` (zero-dep, spec-compliant, reproducible). Verify
with `tools`' fresh-venv procedure, then twine.
