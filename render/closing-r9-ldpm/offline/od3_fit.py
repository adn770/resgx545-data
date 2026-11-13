#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""od3_fit.py (round 9, S9-ldpm offline step OD-3, part 1 of 2: the FIT; Q211, the partial-render
count of scenes of several kicks; offline, read-only, standard library only).

A closed family of count rules, written here before this script first ran, each a variant of OL7
(b)'s H-KICKS (ol7_b_multikick.replay_kicks, the byte copy beside this file: the kicks walked in
turn, each kick's regions in H-WALK64's order, a region once, 32 blocks a page, a page request
above the threshold a partial render that keeps 1 page and frees the rest, the threshold raised by
0x20 after the first):

  H-KICKS        OL7 (b) unchanged.
  H-KICKS-NORAISE the seeds' first candidate: no raise when the partial render leaves 2 global
                 pages (E918, E938). A scene of the default triangle keeps 1 global page (one
                 object), so on these scenes it is H-KICKS; printed to show it.
  H-NR           no raise at all (the threshold stays thr0).
  H-LASTNR       the raise only when the first partial render comes in a kick that is not the
                 scene's last (in the last kick the threshold stays thr0) [infer].
  H-FLUSH        H-KICKS, and after the first partial render each kick end that is not the last
                 kick's, and that is not in the kick of the first partial render, ends the TA run
                 with a partial render (a run peaking below the threshold, E938's 2048x2048 runs).
  H-FLUSH-LASTNR H-FLUSH with H-LASTNR's raise.

FIT: OL7 (b)'s 31 kept cells (closing-s1 g-e2a and g-e2b, closing-r1-pixgeo g-u1, every `tri
--geometry` job; seen by E899's G4 and OL7 (b)), count and every run's peak. The candidate with the
most counts is frozen (its name and this file's sha256 in FREEZE-od3.sha256) BEFORE od3_score.py
reads E938's 20 cells (semi-held-out: E938 printed H-KICKS's aggregate and that 4096x4096 held).

  python3 -I -B od3_fit.py > od3_fit.out
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ol7lib as L  # noqa: E402
from ol7_b_multikick import STAGES, kept_reading, kicks_of  # noqa: E402

CANDIDATES = ("H-KICKS", "H-KICKS-NORAISE", "H-NR", "H-LASTNR", "H-FLUSH", "H-FLUSH-LASTNR")


def replay(name, w, h, kicks, thr0, cap=32, keep=1):
    """(partial renders, run peaks) of candidate `name`, or None (a raised threshold holding no
    page, or more than 40 renders)."""
    flush = name.startswith("H-FLUSH")
    lastnr = name.endswith("LASTNR")
    noraise = name == "H-NR"
    used, cur, seen, peaks, n, thr = 1, {}, set(), [], 0, thr0
    first_kick = None
    gl = 1                                   # global pages: one object, one page (the tool's triangle)
    K = len(kicks)
    for ki, tris in enumerate(kicks):
        for c, r, m in L.walk(w, h, tris):
            if (c, r) in seen:
                continue
            seen.add((c, r))
            if cur.get(m, 0) == 0:
                if used + 1 > thr:
                    peaks.append(used)
                    n += 1
                    if n == 1:
                        first_kick = ki
                    raise_ = 0x20
                    if noraise or (lastnr and first_kick == K - 1) or (name == "H-KICKS-NORAISE" and gl == 2):
                        raise_ = 0
                    used, cur, seen = keep, {}, {(c, r)}
                    thr = thr0 + raise_ if n == 1 else thr
                    if used + 1 > thr or n > 40:
                        return None
                used += 1
                cur[m] = cap
            cur[m] -= 1
        if flush and n >= 1 and ki < K - 1 and ki != first_kick:
            peaks.append(used)
            n += 1
            used, cur, seen = keep, {}, set()
    peaks.append(used)
    return n, peaks


def fit_cells():
    """[(label, w, h, kicks, thr0, (count, peaks))] of OL7 (b)'s kept cells."""
    out = []
    for ds, stg in STAGES:
        d = os.path.join(str(L.DATA), "render", ds, "out", stg)
        for r in csv.DictReader(open(os.path.join(d, "cases.tsv")), delimiter="\t"):
            args = r.get("args") or ""
            if "--geometry" not in args or not args.startswith("tri"):
                continue
            got = kept_reading(os.path.join(d, r["name"] + ".txt.gz"))
            if got is None:
                continue
            w, h, kicks = kicks_of(args)
            out.append((f"{ds[8:]}/{stg}/{r['name']}", w, h, kicks, int(r["P"], 16) - L.D_OFF, got))
    return out


def score(cells, name):
    c_ok = a_ok = 0
    miss = []
    for lab, w, h, kicks, thr0, got in cells:
        p = replay(name, w, h, kicks, thr0)
        ok = p is not None and p[0] == got[0]
        c_ok += ok
        a_ok += ok and p[1] == got[1]
        if not ok:
            miss.append(f"{lab} kept {got[0]} {[hex(x) for x in got[1]]} got "
                        f"{p[0] if p else None} {[hex(x) for x in p[1]] if p else None}")
    return c_ok, a_ok, miss


def main():
    cells = fit_cells()
    best = None
    for name in CANDIDATES:
        c, a, miss = score(cells, name)
        print(f"{name}: count {c} of {len(cells)}, count and every run peak {a} of {len(cells)}")
        for m in miss:
            print("    miss", m)
        if best is None or (c, a) > best[1:]:
            best = (name, c, a)
    print(f"FIT BEST: {best[0]} (count {best[1]}, peaks {best[2]} of {len(cells)})")


if __name__ == "__main__":
    main()
