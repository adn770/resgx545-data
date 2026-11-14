# SPDX-License-Identifier: MIT
"""pins.py: r16-usse's view of the repositories it reads, every file at the commit
session.toml's [freeze] names (never a working tree), and the two programs it builds from the
pinned resgx545 source: sgx-sim (the frozen predictor) and usse-asm (the programs' words), both
from `git archive` of the pinned commit into debug/simsrc, built with CARGO_TARGET_DIR=debug/target
(the session's own target, never main's).

  blob("data:PATH") / blob("resgx545:PATH")  the bytes at the frozen commit
  vectors("data:PATH.vec.json")              a kept vector file, parsed
  tool("sgx-sim") / tool("usse-asm")         the path of the built binary
Every path read through blob() is in session.toml's [freeze] pins (tests/test_gen.py checks it)."""
import hashlib
import json
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
SRC = os.path.join(KP, "debug", "simsrc")
TARGET = os.path.join(KP, "debug", "target")
# what the build takes from the pinned commit (the workspace: the sim, the ISA tables, the tools)
ARCHIVE = ("Cargo.toml", "Cargo.lock", "crates", "isa")


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


def vectors(pin):
    return json.loads(blob(pin))


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def _stamp():
    return os.path.join(SRC, ".commit")


def tool(name):
    """The binary NAME (sgx-sim, usse-asm) of sgx-tools at the pinned resgx545 commit, built once
    into debug/target from `git archive` of that commit (the stamp names the commit)."""
    path = os.path.join(TARGET, "release", name)
    stamp = _stamp()
    have = open(stamp).read().strip() if os.path.exists(stamp) else ""
    if have != COMMIT["resgx545"]:
        subprocess.run(["rm", "-rf", SRC], check=True)
        os.makedirs(SRC)
        arc = subprocess.run(["git", "-C", MAIN, "archive", COMMIT["resgx545"], *ARCHIVE],
                             capture_output=True, check=True, timeout=120).stdout
        subprocess.run(["tar", "-x", "-C", SRC], input=arc, check=True)
        with open(stamp, "w") as f:
            f.write(COMMIT["resgx545"] + "\n")
    if have != COMMIT["resgx545"] or not os.path.exists(path):
        env = dict(os.environ, CARGO_TARGET_DIR=TARGET)
        r = subprocess.run(["cargo", "build", "--release", "--offline", "-q", "-p", "sgx-tools",
                            "--bin", "sgx-sim", "--bin", "usse-asm"], cwd=SRC, env=env,
                           capture_output=True, text=True, timeout=1200)
        if r.returncode:
            raise SystemExit("cargo build of the pinned sgx-tools failed:\n" + r.stderr[-2000:])
    return path
