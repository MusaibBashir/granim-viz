"""Zero-dependency test runner: emulates the pytest subset the suite uses
(fixture(autouse), raises, tmp_path). `pytest` works too when available."""
import contextlib
import inspect
import sys
import tempfile
import traceback
import types
from pathlib import Path

shim = types.ModuleType("pytest")


def fixture(fn=None, *, autouse=False):
    def deco(f):
        f._fixture, f._autouse = True, autouse
        return f
    return deco(fn) if fn else deco


@contextlib.contextmanager
def raises(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


shim.fixture, shim.raises = fixture, raises
sys.modules.setdefault("pytest", shim)

import test_granim as suite  # noqa: E402

fixtures = [f for _, f in inspect.getmembers(suite, inspect.isfunction)
            if getattr(f, "_autouse", False)]
tests = [(n, f) for n, f in inspect.getmembers(suite, inspect.isfunction)
         if n.startswith("test_")]

failed = 0
for name, fn in tests:
    gens = [f() for f in fixtures]
    for g in gens:
        next(g)
    try:
        kwargs = {}
        if "tmp_path" in inspect.signature(fn).parameters:
            kwargs["tmp_path"] = Path(tempfile.mkdtemp())
        fn(**kwargs)
        print(f"  ok    {name}")
    except Exception:
        failed += 1
        print(f"  FAIL  {name}")
        traceback.print_exc()
    finally:
        for g in gens:
            with contextlib.suppress(StopIteration):
                next(g)

print(f"\n{len(tests) - failed}/{len(tests)} passed")
sys.exit(1 if failed else 0)
