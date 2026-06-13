# Changelog

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
