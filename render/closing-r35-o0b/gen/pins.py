# SPDX-License-Identifier: MIT
"""pins.py: r35-o0b's view of the repositories it reads, every file at the commit session.toml's
[freeze] names (never a working tree), and the bound tool sources at their own commits.

  blob("data:PATH") / blob("resgx545:PATH")  the bytes at the frozen commit (a .gz unpacked)
  tool_source(NAME)  the source a [tools.NAME] is built from, its sha256 checked against the
                     session's TOOLSRC.sha256 (the kit's binding of the tool)
Every data/resgx545 path read here is in session.toml's [freeze] pins (tests/test_gen.py)."""
import gzip
import hashlib
import os
import subprocess
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
_CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COMMIT = {"data": _CFG["freeze"]["data"], "resgx545": _CFG["freeze"]["resgx545"]}
REPO = {"data": DATA, "resgx545": MAIN}
READ = set()
_CACHE = {}


def _show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True,
                       timeout=60)
    if r.returncode:
        raise SystemExit(f"{path} at {rev[:12]}: {r.stderr.decode().strip()}")
    return r.stdout


def blob(pin):
    if pin not in _CACHE:
        repo, _, path = pin.partition(":")
        b = _show(REPO[repo], COMMIT[repo], path)
        _CACHE[pin] = gzip.decompress(b) if path.endswith(".gz") else b
    READ.add(pin)
    return _CACHE[pin]


def tool_source(name):
    """The bytes of [tools.NAME]'s source at its commit, checked against TOOLSRC.sha256."""
    src = _CFG["tools"][name]["source"]
    rev, _, path = src.partition(":")
    b = _show(MAIN, rev, path)
    want = {ln.split()[1]: ln.split()[0] for ln in open(os.path.join(KP, "TOOLSRC.sha256"))
            if ln.strip() and not ln.startswith("#")}
    got = hashlib.sha256(b).hexdigest()
    if want.get(src) != got:
        raise SystemExit(f"{src}: sha256 {got}, TOOLSRC.sha256 {want.get(src)}")
    return b
