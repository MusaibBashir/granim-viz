# Changelog

## 2.0.0 — 2026-06-13

Major release: richer authoring API and a rebuilt player.

### Added

- `ga.note("text")`: drop an explanatory caption onto the canvas at a point in
  your code. Persists until the next note (`ga.note(None)` clears); a no-op
  outside a recording. Also appears in the per-step feed.
- `@ga.node(graph=True)`: lay a web of decorated nodes out as a graph (layered
  DAG / force-directed) instead of a floating chain. Node-valued fields —
  including lists/sets of nodes — render as clean graph edges, so computation
  graphs (e.g. micrograd-style) just work. `graph="name"` routes instances into
  a *named*, titled graph, letting you split e.g. a forward graph from a
  backward one (`examples/expr_graph.py`).
- `ga.graph(directed=True, title=None)`: a `title` captions the structure on the
  canvas. Two graphs render as two separate titled structures — see the reworked
  `examples/rnn_bptt.py` (forward activations vs. backward gradients).
- Node dragging in the player: grab any node to reposition it (edges follow and
  stay attached); a dragged node holds its spot as later steps re-flow the rest.
  Double-click a node to release it back to the layout, or press `r` to release
  all.

### Changed

- Rebuilt player layout. Left column is two independent panels — **source** (the
  function listing with the executing line highlighted, auto-scrolling in its
  own box) and **this step** (the per-beat change feed, pinned below so the
  source's scrolling never moves it). Right **state** panel splits into
  variables, iterators, node states, and call stack. Replaces the old flat
  execution trace.
- Node labels auto-fit their shape (matrix cells, circles, pills); long labels
  no longer overflow or overlap.
- Timeline now ships the function's full source span for the code view, and
  per-structure titles.

## 1.1.0 — 2026-06-11

- Execution trace panel (left side, `debug=True`): narrates every step —
  the source line being executed, comparisons with outcomes, pointer moves
  and flips, value/state changes, variable updates, loop-iteration and
  call/return markers. Click any entry to jump to that step.
- Timeline now carries the traced source lines and per-step changed
  variables.

## 1.0.1 — 2026-06-10

- Use the full user guide as the PyPI/README landing page.

## 1.0.0 — 2026-06-10

Initial release.

- `@ga.animate`: one decorator turns unmodified algorithm code into an
  interactive single-file HTML animation (scoped tracing, automatic steps,
  parallel-beat batching, debug panel with frame-scoped variables).
- Structures: `ga.array`, `ga.matrix`, `ga.linked_list` (incl. doubly),
  `ga.tree`, `ga.graph` (weighted) — all usable as plain Python without
  recording.
- Custom classes: `@ga.node` instruments user-owned node classes without
  inheritance (incl. ad-hoc pointer fields like `.random`/`.child`);
  `@ga.container` gives wrappers head/tail badges and garbage-rooting.
- Compiler: edge-flip classification (both reversal idioms), orphan dimming
  via event-triggered reachability, deterministic timeline output.
- Layouts: grid, snake-wrapped chains, Buchheim tidy trees, layered DAGs,
  seeded force-directed — all position-stable across steps.
- Player: play/scrub/speed, manim-style dark theme (+light, contrast).
- Verified against a 20-problem LeetCode linked-list harness (20/20).
