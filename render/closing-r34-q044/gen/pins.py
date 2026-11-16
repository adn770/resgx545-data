# SPDX-License-Identifier: MIT
"""pins.py: r34-q044's view of the repositories it reads, every file at the commit session.toml's
[freeze] names (never a working tree), and the pinned modules imported from those bytes.

  blob("data:PATH") / blob("resgx545:PATH")  the bytes at the frozen commit
  module("data:PATH")                        the module, loaded from those bytes
  kept_pixels("data:PATH.txt.gz")            the `row N:` pixels of a kept output, raster order
Every path read here is in session.toml's [freeze] pins (tests/test_gen.py checks it)."""
import gzip
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
_CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COMMIT = {"data": _CFG["freeze"]["data"], "resgx545": _CFG["freeze"]["resgx545"]}
REPO = {"data": DATA, "resgx545": MAIN}
READ = set()
_TMP = tempfile.mkdtemp(prefix="r34p-pins.")
_CACHE = {}


def blob(pin):
    if pin not in _CACHE:
        repo, _, path = pin.partition(":")
        r = subprocess.run(["git", "-C", REPO[repo], "show", f"{COMMIT[repo]}:{path}"],
                           capture_output=True, timeout=60)
        if r.returncode:
            raise SystemExit(f"{pin} at {COMMIT[repo][:12]}: {r.stderr.decode().strip()}")
        _CACHE[pin] = r.stdout
    READ.add(pin)
    return _CACHE[pin]


def module(pin, name=None):
    """A pinned module, loaded from its frozen bytes (its siblings it imports must be pinned and
    loaded first, under the names they import)."""
    name = name or os.path.splitext(os.path.basename(pin))[0]
    if name in sys.modules:
        return sys.modules[name]
    path = os.path.join(_TMP, os.path.basename(pin))
    with open(path, "wb") as f:
        f.write(blob(pin))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    sys.dont_write_bytecode = True
    spec.loader.exec_module(m)
    return m


ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)


def pixels(text, n=None):
    """The `row N: v v ...` pixels of an output (probe or tri form), raster order, or None when a
    row is missing or the count is not n."""
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if n is None or len(px) == n else None


def kept_pixels(pin, n=2048):
    return pixels(gzip.decompress(blob(pin)).decode(errors="replace"), n)


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()
