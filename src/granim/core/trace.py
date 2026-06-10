"""Scoped sys.settrace: only frames from the traced function's file are
followed. The trace adds step boundaries and locals; animation events come
from the structures."""
from __future__ import annotations

import sys


class Trace:
    def __init__(self, recorder, code):
        self._rec = recorder
        self._file = code.co_filename

    def __enter__(self):
        self._prev = sys.gettrace()
        sys.settrace(self._global)
        return self

    def __exit__(self, *exc):
        sys.settrace(self._prev)
        return False

    def _global(self, frame, event, arg):
        if event != "call" or frame.f_code.co_filename != self._file:
            return None
        self._rec.on_call(frame)
        return self._local

    def _local(self, frame, event, arg):
        if event == "line":
            self._rec.on_line(frame)
        elif event == "return":
            self._rec.on_return(frame)
        return self._local
