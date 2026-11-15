# SPDX-License-Identifier: MIT
"""pins.py: r23-pk's view of the repositories it reads, every file at the commit session.toml's
[freeze] names (never a working tree).

  blob("data:PATH") / blob("resgx545:PATH")  the bytes at the frozen commit (a .gz unpacked)
Every path read here is in session.toml's [freeze] pins (tests/test_plan.py checks it)."""
import gzip
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


def blob(pin):
    if pin not in _CACHE:
        repo, _, path = pin.partition(":")
        r = subprocess.run(["git", "-C", REPO[repo], "show", f"{COMMIT[repo]}:{path}"],
                           capture_output=True, timeout=60)
        if r.returncode:
            raise SystemExit(f"{pin} at {COMMIT[repo][:12]}: {r.stderr.decode().strip()}")
        b = r.stdout
        _CACHE[pin] = gzip.decompress(b) if path.endswith(".gz") else b
    READ.add(pin)
    return _CACHE[pin]

