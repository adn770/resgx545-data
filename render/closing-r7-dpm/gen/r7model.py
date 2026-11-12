#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r7model.py: the frozen offline rules R7-dpm's predictions start from, loaded unchanged and hash-checked.  Pure python, no I/O but
reading the frozen scripts (and, through them, the published corpus they scan at import: none of the functions used here scans it).

Round 7's offline stage (resgx545-data cited/closing7/b/offline, E899 and E900), each file checked against the FREEZE-g<n>.sha256
the stage wrote before its held-out set was opened:
  olib.py        (FREEZE-g1)  paths, dumps, regions_of(pre, w, h) and place(regs, key): G1's reading of a dump's walk (H-WALK64)
  g1_walk64.py   (FREEZE-g1)  ORDERS['walk64'] = (r // 8, c // 4, r, c) on (column, row) of 16 x 16 tiles... as olib.place uses it
  g2_replay64.py (FREEZE-g2)  KEYS['walk64'] = (z[1] // 4, z[0] // 2, z[1], z[0]) on f7_replay.regions' (c, r, m): H-REPLAY64
  g3_span.py     (FREEZE-g3)  model(w, h) -> (S, A, B, U) and pred(thr0, S, E): H-SPAN (A_k, E900) and E874's B_k (the rival)
Round 6's offline stage (resgx545-data cited/closing6/dpm/offline, E873 to E875), checked against its FREEZE-f<n>.sha256:
  f5lib.py, f5_stepmodel.py (F5, E874)  the 1500-vertex scene's step replay (H-STEPMODEL: S_k, U), used through g3_span.model
  f4_phase.py (F4)   predict(); f9_loss.py (F9) the replay with partial renders (exploratory count, R-5's cls only where it gives 2+)
  f7_replay.py (F7, E875)  regions() and replay(): the one-triangle page replay; r6lib.py the readers they share
  hu1.py (render/closing-r5-dpm/gen, R5-dpm's frozen copy)  HU1, the page need of a one-triangle scene (E773)
No number is fitted here.  E900: no step rule for larger objects was frozen (G5: H-CUM 9 of 12 at N 4), so nothing here models
--vtx-coords scenes (stage s-v is exploration, its predictions are R6-dpm's kept readings repeated).
"""
from __future__ import annotations

import hashlib
import importlib
import os
import pathlib
import sys

DATA = pathlib.Path(os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data"))
OFF6 = DATA / "cited" / "closing6" / "dpm" / "offline"
OFF7 = DATA / "cited" / "closing7" / "b" / "offline"
PINNED = {OFF6: {"f5lib.py": "FREEZE-f5.sha256", "f5_stepmodel.py": "FREEZE-f5.sha256", "f4_phase.py": "FREEZE-f4.sha256",
                 "f9_loss.py": "FREEZE-f9.sha256", "f7_replay.py": "FREEZE-f7.sha256", "r6lib.py": "FREEZE-f1.sha256"},
          OFF7: {"olib.py": "FREEZE-g1.sha256", "g1_walk64.py": "FREEZE-g1.sha256", "g2_replay64.py": "FREEZE-g2.sha256",
                 "g3_span.py": "FREEZE-g3.sha256"}}
HU1_SHA = "5e338cd6d3461de32728abee490c694d3eca4572faad11489bafb49ddd16309e"   # closing-r5-dpm/gen/hu1.py (R5-dpm's FROZEN.sha256)


def _check():
    bad = []
    for d, files in PINNED.items():
        for f, frz in files.items():
            want = [ln.split()[0] for ln in (d / frz).read_text().splitlines() if ln.strip().endswith("  " + f)]
            got = hashlib.sha256((d / f).read_bytes()).hexdigest()
            if got not in want:
                bad.append(f"{d.name}/{f}: {got[:12]} not in {frz}")
    h = DATA / "render" / "closing-r5-dpm" / "gen" / "hu1.py"
    if hashlib.sha256(h.read_bytes()).hexdigest() != HU1_SHA:
        bad.append("closing-r5-dpm/gen/hu1.py is not R5-dpm's frozen file")
    if bad:
        raise SystemExit("r7model: a frozen offline rule changed: " + "; ".join(bad))


_check()
os.environ.setdefault("RESGX545_DATA", str(DATA))
sys.dont_write_bytecode = True
sys.path[:0] = [str(OFF7), str(OFF6)]
G3 = importlib.import_module("g3_span")          # imports olib (paths), f5lib, f4_phase, r6lib
G2 = importlib.import_module("g2_replay64")      # imports f7_replay
G1 = importlib.import_module("g1_walk64")
O = importlib.import_module("olib")
F5 = importlib.import_module("f5lib")
F4 = importlib.import_module("f4_phase")
F9 = importlib.import_module("f9_loss")
F7 = importlib.import_module("f7_replay")
H = F7.H
LAG = G3.LAG                                     # 3 (E874)
D_OFF = 0x22
WALK64 = G2.KEYS["walk64"]                       # H-REPLAY64's order on f7_replay.regions tuples (c, r, m)
WALK64_DUMP = G1.ORDERS["walk64"]                # H-WALK64's order on a dump's regions (olib.place key(c, r))

_ents: dict = {}
_model: dict = {}


def ents(w, h):
    if (w, h) not in _ents:
        _ents[(w, h)] = F5.entries(w, h)
    return _ents[(w, h)]


def model(w, h):
    """(S {k: S_k}, A {k: A_k}, B {k: B_k}, U): g3_span.model (E874's step replay, lag 3; H-SPAN's A_k; E874's B_k)."""
    if (w, h) not in _model:
        _model[(w, h)] = G3.model(w, h)
    return _model[(w, h)]


def span_left(thr0, S, A):
    """H-SPAN (E900): pages left by the first partial render: 2 iff S_k < thr0 < A_k, 1 at or after A_k; None on a step cell
    (a grow, not scored); '?' where the band has no A_k."""
    return G3.pred(thr0, S, A)


def guard_class(thr0, S, A):
    """R-5's guard (3d.md 6.4, E864) with the margin of H-SPAN (A3 = B3 at every target, E900): a first partial render that leaves 2
    global pages or comes below S3 (dword 36 floors at 0) raises; 1 page left from A3 up is silent.  On a step cell (a grow): S2, S3
    raise, S4 and above silent (H-PEND, E861)."""
    if thr0 in S.values():
        k = next(k for k, v in S.items() if v == thr0)
        return "R" if k <= 3 else "N"
    if thr0 < S[3]:
        return "R"
    return "R" if span_left(thr0, S, A) == 2 else "N"


def gps_abort(thr0, S):
    """The global pages the first TA run holds at its abort (1 + the steps below thr0): at a step cell thr0 = S_k the k-th page is
    the refused request (H-PENDREQ, E874), so it is not counted."""
    return 1 + sum(1 for v in S.values() if v < thr0)


def f9_count(w, h, thr0, raised):
    """F9's replay with partial renders (exploratory): (partial renders, run peaks) or None."""
    return F9.run(ents(w, h), thr0, raised, w, h)


# ---------------------------------------------------------------------------------------------- one-triangle scenes (H-REPLAY64)
_regs: dict = {}


def scene_u(w, h, dx, dy):
    """HU1's page need of `tri -n 1 --move 1:DX,DY` at w x h (E773)."""
    return H.hu1(w, h, H.moved(w, h, dx, dy))[0]


def walk(w, h, dx, dy, order):
    key = (w, h, dx, dy, order)
    if key not in _regs:
        base = F7.regions(w, h, H.moved(w, h, dx, dy), "row")
        _regs[key] = sorted(base, key=WALK64) if order == "walk64" else F7.regions(w, h, H.moved(w, h, dx, dy), order)
    return _regs[key]


def replay(w, h, dx, dy, thr0, order="walk64"):
    """(partial renders, run peaks) of E875's replay in the given walk order (walk64: H-REPLAY64; row: E875's order, the rival)."""
    return F7.replay(walk(w, h, dx, dy, order), thr0)


def dcount(thr0, U, d):
    return F7.dcount(thr0, U, d)


def dump_walk(tadata_prefix, w, h):
    """H-WALK64 on a kept dump: (exact, total, real pages, replayed pages) by olib.place in G1's frozen order."""
    return O.place(O.regions_of(tadata_prefix, w, h), WALK64_DUMP)
