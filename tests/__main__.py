"""Zero-dependency test runner: `python -m tests` (also pytest-compatible)."""
import importlib
import pkgutil
import sys
import time
import traceback

import tests

fails = []
count = 0
t0 = time.time()
for mod in pkgutil.iter_modules(tests.__path__):
    if not mod.name.startswith("test_"):
        continue
    m = importlib.import_module(f"tests.{mod.name}")
    for attr in sorted(dir(m)):
        if not attr.startswith("test_"):
            continue
        fn = getattr(m, attr)
        if not callable(fn):
            continue
        count += 1
        try:
            fn()
            print(f"  PASS {mod.name}.{attr}")
        except Exception:
            fails.append((mod.name, attr))
            print(f"  FAIL {mod.name}.{attr}")
            traceback.print_exc()
dt = time.time() - t0
print(f"\n{count - len(fails)}/{count} passed in {dt:.1f}s")
sys.exit(1 if fails else 0)
