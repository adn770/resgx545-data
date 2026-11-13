#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ol7lib.py (round 8, leftovers OL7, Q210 and Q211; offline, read-only, standard library only):
the frozen offline rules OL7 and session r8-ldpm start from, loaded unchanged from their
published copies in resgx545-data and checked against the FREEZE files their stages wrote before
any held-out set was opened (R7-dpm's gen/r7model.py check, the same files):

  cited/closing6/dpm/offline  f5lib, f4_phase, f9_loss, f7_replay, r6lib (E873 to E875)
  cited/closing7/b/offline    olib, g1_walk64, g2_replay64, g3_span (E899, E900)
  render/closing-r5-dpm/gen/hu1.py                                (HU1, E773; R5-dpm's frozen copy)

No number is fitted here. The data root is RESGX545_DATA (default ~/src/resgx545-data)."""
from __future__ import annotations

import hashlib
import importlib
import os
import pathlib
import sys

DATA = pathlib.Path(os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data"))
OFF6 = DATA / "cited" / "closing6" / "dpm" / "offline"
OFF7 = DATA / "cited" / "closing7" / "b" / "offline"
HU1 = DATA / "render" / "closing-r5-dpm" / "gen" / "hu1.py"
PINNED = {OFF6: {"f5lib.py": "FREEZE-f5.sha256", "f4_phase.py": "FREEZE-f4.sha256",
                 "f9_loss.py": "FREEZE-f9.sha256", "f7_replay.py": "FREEZE-f7.sha256",
                 "r6lib.py": "FREEZE-f1.sha256"},
          OFF7: {"olib.py": "FREEZE-g1.sha256", "g1_walk64.py": "FREEZE-g1.sha256",
                 "g2_replay64.py": "FREEZE-g2.sha256", "g3_span.py": "FREEZE-g3.sha256"}}
HU1_SHA = "5e338cd6d3461de32728abee490c694d3eca4572faad11489bafb49ddd16309e"


def _check():
    bad = []
    for d, files in PINNED.items():
        for f, frz in files.items():
            want = [ln.split()[0] for ln in (d / frz).read_text().splitlines()
                    if ln.strip().endswith("  " + f)]
            got = hashlib.sha256((d / f).read_bytes()).hexdigest()
            if got not in want:
                bad.append(f"{d.name}/{f}: {got[:12]} not in {frz}")
    if hashlib.sha256(HU1.read_bytes()).hexdigest() != HU1_SHA:
        bad.append("closing-r5-dpm/gen/hu1.py is not R5-dpm's frozen file")
    if bad:
        raise SystemExit("ol7lib: a frozen offline rule changed: " + "; ".join(bad))


_check()
os.environ.setdefault("RESGX545_DATA", str(DATA))
sys.dont_write_bytecode = True
sys.path[:0] = [str(OFF7), str(OFF6)]
G3 = importlib.import_module("g3_span")
G2 = importlib.import_module("g2_replay64")
F5 = importlib.import_module("f5lib")
F9 = importlib.import_module("f9_loss")
F7 = importlib.import_module("f7_replay")
R6 = importlib.import_module("r6lib")
H = F7.H
WALK64 = G2.KEYS["walk64"]          # H-REPLAY64's order on f7_replay.regions tuples (c, r, m)
D_OFF = 0x22                        # P = thr0 + 0x22
RAISE = 0x20

_ents: dict = {}
_model: dict = {}


def ents(w, h):
    if (w, h) not in _ents:
        _ents[(w, h)] = F5.entries(w, h)
    return _ents[(w, h)]


def model(w, h):
    """(S, A, B, U) of g3_span.model: E874's step replay (lag 3), H-SPAN's A_k, E874's B_k."""
    if (w, h) not in _model:
        _model[(w, h)] = G3.model(w, h)
    return _model[(w, h)]


def span_left(thr0, S, E):
    return G3.pred(thr0, S, E)


def guard_class(thr0, S, A):
    """R-5's guard with H-SPAN's margin (R7-dpm gen/r7model.py guard_class, unchanged)."""
    if thr0 in S.values():
        k = next(k for k, v in S.items() if v == thr0)
        return "R" if k <= 3 else "N"
    if thr0 < S[3]:
        return "R"
    return "R" if span_left(thr0, S, A) == 2 else "N"


def gps_abort(thr0, S):
    """The global pages the first TA run holds at its abort: 1 + the steps below thr0."""
    return 1 + sum(1 for v in S.values() if v < thr0)


def f9_count(w, h, thr0):
    """F9's replay with partial renders: (count, run peaks) or None, raised by R-5's guard."""
    S, A, B, U = model(w, h)
    return F9.run(ents(w, h), thr0, guard_class(thr0, S, A) == "R", w, h)


def dcount(thr0, U, d):
    return F7.dcount(thr0, U, d)


# ---- one or several triangles, one or several kicks ------------------------------------------
def tri_moved(w, h, dx, dy):
    return H.default_tri(w, h, dx, dy)


def scene(w, h, moves):
    """The triangles of `tri -n K --move i:DX,DY`: moves[i] for render i + 1 ((0, 0) unmoved)."""
    return [tri_moved(w, h, dx, dy) for dx, dy in moves]


def u_of(w, h, tris):
    """HU1's page need of the union (a region counted once)."""
    return H.hu1(w, h, tris)[0]


def walk(w, h, tris):
    """The regions of the triangles (a region once) in H-WALK64's order."""
    return sorted(F7.regions(w, h, tris, "row"), key=WALK64)


def replay_union(w, h, tris, thr0):
    """The rival of several kicks: E875's replay of the union in one walk (H-REPLAY64)."""
    return F7.replay(walk(w, h, tris), thr0)
