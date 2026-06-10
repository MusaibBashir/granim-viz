"""Groups events into steps; everything in a step animates simultaneously."""
from __future__ import annotations

from dataclasses import dataclass, field

from .events import BATCHABLE, Event, PASSIVE


@dataclass(slots=True)
class Step:
    i: int
    line: int | None
    depth: int
    label: str | None
    ops: list[Event]
    vars: list[Event]
    stack: list[dict]
    mut_sig: frozenset = field(default=frozenset())


class StepBuilder:
    def __init__(self, stack_snapshot):
        self.steps: list[Step] = []
        self._snapshot = stack_snapshot
        self._pending: list[Event] = []
        self._line: int | None = None
        self._depth = 0
        self._carry_vars: list[Event] = []
        self._batch = 0

    def add(self, e: Event) -> None:
        self._pending.append(e)

    def boundary(self, line: int | None = None, depth: int = 0, label: str | None = None) -> None:
        """Flush on line change, call/return, or explicit rec.step()."""
        if self._batch:
            return
        if self._pending:
            self._flush(label)
        elif label:  # explicit empty step() forces a titled beat on next flush
            self._flush(label)
        self._line, self._depth = line, depth

    def begin_batch(self) -> None:
        if not self._batch and self._pending:
            self._flush(None)
        self._batch += 1

    def end_batch(self) -> None:
        self._batch -= 1
        if not self._batch and self._pending:
            self._flush(None, mergeable=False)

    def finish(self) -> list[Step]:
        if self._pending:
            self._flush(None)
        if self.steps:  # trailing step so the final state renders
            self.steps.append(Step(
                i=len(self.steps), line=None, depth=0, label=None,
                ops=[], vars=self._carry_vars, stack=self._snapshot(),
            ))
            self._carry_vars = []
        return self.steps

    # -- internals -----------------------------------------------------------

    def _flush(self, label: str | None, mergeable: bool = True) -> None:
        pending, self._pending = self._pending, []
        ops = [e for e in pending if e.kind != "var_set"]
        var_evts = [e for e in pending if e.kind == "var_set"]
        if not ops:
            self._carry_vars += var_evts  # var-only flushes attach to the next step
            if label and self.steps:
                self.steps[-1].label = label
            return
        var_evts = self._carry_vars + var_evts
        self._carry_vars = []
        mut = frozenset(e.kind for e in ops if e.kind not in PASSIVE)

        last = self.steps[-1] if self.steps else None
        if (  # merge same-line state/add mutations into one parallel step
            mergeable and label is None and last is not None
            and last.label is None and last.line == self._line
            and last.depth == self._depth and mut and mut <= BATCHABLE
            and last.mut_sig == mut
        ):
            last.ops += ops
            _merge_vars(last.vars, var_evts)
            return

        self.steps.append(Step(
            i=len(self.steps), line=self._line, depth=self._depth, label=label,
            ops=ops, vars=var_evts, stack=self._snapshot(), mut_sig=mut,
        ))


def _merge_vars(into: list[Event], new: list[Event]) -> None:
    names = {e.payload["name"]: i for i, e in enumerate(into)}
    for e in new:
        i = names.get(e.payload["name"])
        if i is None:
            into.append(e)
        else:
            into[i] = e
