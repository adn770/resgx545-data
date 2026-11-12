#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r6model.py: the frozen offline rules of round 6's dpm stage (E873 to E875), loaded unchanged, and the few build-side
extensions R6-dpm's predictions need.  Pure python, no I/O but reading the frozen scripts.

The frozen rules are imported from the PUBLISHED copy (resgx545-data cited/closing6/dpm/offline, the files E873-E875 cite) and
each file's sha256 is checked against the FREEZE-f<n>.sha256 the offline stage wrote before its first run: a changed rule refuses
to load (SystemExit).  Used:
  f5lib.py   (F5, E874)  the block-level replay of the 1500-vertex scene: steps S_k, U, page count after each tiled object
  f5_stepmodel.bands     B_k, the burst end (H-PHASE's flip, E874: 86 of 87 kept rows)
  f4_phase.ends          the timeline burst-end rule E_k (X = 75 us), F4's frozen rival; the runner uses it to place r-v cells
  f9_loss.run            F9's replay with partial renders (exploratory in E874: 43 of 43 kept counts at 2048x2048)
  f7_replay.regions/replay/dcount  F7 (E875): the page replay of one-triangle scenes, walk orders, E854's spacing rivals

Build-side extensions (NOT frozen offline; frozen here with the session, each checked against the frozen rule where they meet):
  replay_L(w, h, ents, L, mode)  f5lib.replay with the object block size L as a parameter (H-OBJPAGE: b_k = floor(1024 (k - 1) / L))
                                 and mode 'cap' (f5lib's rule: a block opens when the next entry does not fit; = f5lib.replay at
                                 L = 67, tested) or 'page' (H-BURST-PAGE: every region with an entry at object b_k also opens a new
                                 block there).  For stage r-v (--vtx-coords).
  bursts(opens)                  the objects whose block openings are at least half the scene's most (the bursts)
  burst_end_L(S, opens, after, L) B_k for any L: the page count after the first burst object tiled at or after the step's tile
                                 b_k - lag (= f5_stepmodel.bands at L = 67, tested)
"""
from __future__ import annotations

import hashlib
import importlib
import os
import pathlib
import sys

DATA = pathlib.Path(os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data"))
OFF = DATA / "cited" / "closing6" / "dpm" / "offline"
# the frozen files this session imports, by the FREEZE file that pins each (offline stage FREEZE-LOG.txt)
PINNED = {"f5lib.py": "FREEZE-f5.sha256", "f5_stepmodel.py": "FREEZE-f5.sha256", "f4_phase.py": "FREEZE-f4.sha256",
          "f9_loss.py": "FREEZE-f9.sha256", "f7_replay.py": "FREEZE-f7.sha256", "f1_brackets.py": "FREEZE-f1.sha256",
          "r6lib.py": "FREEZE-f1.sha256"}
HU1_SHA = "5e338cd6d3461de32728abee490c694d3eca4572faad11489bafb49ddd16309e"   # closing-r5-dpm/gen/hu1.py (R5-dpm's FROZEN.sha256)


def _check():
    bad = []
    for f, frz in PINNED.items():
        want = [ln.split()[0] for ln in (OFF / frz).read_text().splitlines() if ln.strip().endswith("  " + f)]
        got = hashlib.sha256((OFF / f).read_bytes()).hexdigest()
        if got not in want:
            bad.append(f"{f}: {got[:12]} not in {frz}")
    h = DATA / "render" / "closing-r5-dpm" / "gen" / "hu1.py"
    if hashlib.sha256(h.read_bytes()).hexdigest() != HU1_SHA:
        bad.append("closing-r5-dpm/gen/hu1.py is not R5-dpm's frozen file")
    if bad:
        raise SystemExit("r6model: a frozen offline rule changed: " + "; ".join(bad))


_check()
os.environ.setdefault("RESGX545_DATA", str(DATA))
sys.path.insert(0, str(OFF))
sys.dont_write_bytecode = True
F5 = importlib.import_module("f5lib")
F5S = importlib.import_module("f5_stepmodel")
F4 = importlib.import_module("f4_phase")
F9 = importlib.import_module("f9_loss")
F7 = importlib.import_module("f7_replay")
H = F5.H                                 # hu1 (the same module object F7 imports)
LAG = 3                                  # f5_stepmodel.out: "fit 2048x2048: lag 3" (E874)
X_US = 75                                # f4_phase.out: "X = 75 us" (E874)
D_OFF = 0x22

_ents: dict = {}


def ents(w, h):
    if (w, h) not in _ents:
        _ents[(w, h)] = F5.entries(w, h)
    return _ents[(w, h)]


def model(w, h):
    """(S {k: S_k}, B {k: B_k}, U, after) of the 1500-vertex scene at w x h: f5lib.replay and f5_stepmodel.bands, lag 3 (E874)."""
    S, opens, after = F5.replay(w, h, ents(w, h), LAG)
    B = F5S.bands(S, after, LAG)
    return S, B, after[-1], after


def phase_left(thr0, S, B):
    """H-PHASE (E874, f4_phase.predict with the model's B): pages left by the first partial render: 2 iff S_k < thr0 < B_k for the
    band's step, 1 at or after B_k and below S2; None at thr0 = S_k (a grow cell, not scored)."""
    return F4.predict(thr0, S, B)


def guard_class(thr0, S, B):
    """R-5's guard with H-PHASE (3d.md 6.4, E874: the first silent cell of the raise is B3): a first partial render that leaves 2 global
    pages or below S3 (dword 36 floors at 0) raises; 1 page left from B3 up is silent.  On a step cell (a grow): S2, S3 raise, S4 and
    above silent (H-PEND, E861)."""
    if thr0 in S.values():
        k = next(k for k, v in S.items() if v == thr0)
        return "R" if k <= 3 else "N"
    if thr0 < S[3]:
        return "R"
    return "R" if thr0 < B[3] else "N"


def f9_count(w, h, thr0, raised):
    """F9's replay with partial renders (exploratory): (partial renders, run peaks) or None."""
    return F9.run(ents(w, h), thr0, raised, w, h)


# ---------------------------------------------------------------------------------------------- r-v: the object size L
def replay_L(w, h, e, L, mode="cap", lag=LAG):
    """f5lib.replay with the block size L and the burst cause `mode` ('cap' = f5lib's rule; 'page' = H-BURST-PAGE).
    Returns (S, opens, after)."""
    bk = lambda k: (1024 * (k - 1)) // L
    gk = {bk(k): k for k in range(2, 64) if bk(k) < F5.OBJS}
    used, mtb, pages, S, opens, after = {}, {}, 1, {}, {}, []
    writes = {}
    for b in range(F5.OBJS):
        writes.setdefault(max(0, b - lag), []).append(b)
    for t in range(F5.OBJS):
        for b in writes.get(t, []):
            if b in gk:
                S[gk[b]] = pages
                pages += 1
        o = 0
        for c, r, dw in e[t]:
            dw += 1 if t in gk else 0
            key = (c, r)
            force = mode == "page" and t in gk
            if key not in used or used[key] + dw > F5.CAP or force:
                used[key] = 0
                o += 1
                m = F5.mtile(w, h, c, r)
                nb = mtb.get(m, 0)
                if nb % F5.BPP == 0:
                    pages += 1
                mtb[m] = nb + 1
            used[key] += dw
        opens[t] = o
        after.append(pages)
    return S, opens, after


def bursts(opens):
    top = max(opens.values())
    return [t for t, o in sorted(opens.items()) if o * 2 >= top and t > 0]


def burst_end_L(S, opens, after, L, lag=LAG):
    """B_k: the page count after the first burst object tiled at or after the step's tile b_k - lag; None if no burst follows."""
    bl = bursts(opens)
    out = {}
    for k in S:
        t0 = (1024 * (k - 1)) // L - lag
        b = next((t for t in bl if t >= t0), None)
        out[k] = after[b] if b is not None else None
    return out


def model_L(w, h, L, mode):
    S, opens, after = replay_L(w, h, ents(w, h), L, mode)
    return S, burst_end_L(S, opens, after, L), after[-1], bursts(opens)


# ---------------------------------------------------------------------------------------------- r-b: one-triangle scenes (F7)
ORDERS = ("row", "col")         # row: the order E875 names (54 of 56, post hoc); col: W*, the order F7's frozen rule picked


def scene(dx, dy, w=4096, h=4096):
    tris = H.moved(w, h, dx, dy)
    return tris, H.hu1(w, h, tris)[0]


_regs: dict = {}


def walk(dx, dy, order, w=4096, h=4096):
    key = (dx, dy, order, w, h)
    if key not in _regs:
        _regs[key] = F7.regions(w, h, H.moved(w, h, dx, dy), order)
    return _regs[key]


def h_replay(dx, dy, thr0, order, w=4096, h=4096):
    """(partial renders, run peaks) of F7's replay in the walk order, or None."""
    return F7.replay(walk(dx, dy, order, w, h), thr0)


def dcount(thr0, U, d):
    return F7.dcount(thr0, U, d)
