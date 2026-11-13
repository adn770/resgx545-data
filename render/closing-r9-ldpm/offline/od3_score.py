#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""od3_score.py (round 9, S9-ldpm offline step OD-3, part 2 of 2: the semi-held-out score; Q211).

Scores the candidate od3_fit.py froze (FREEZE-od3.sha256 names it: H-FLUSH, the fit's best, 30 of
31 counts) and, as tallies, the other candidates of od3_fit.py's family, on E938's 20 multi-kick
cells: r8-ldpm stage k's explore rows (render-closing-r8-ldpm, here its scratch copy
closing8/r8-ldpm/out/20261113-021431/k, read-only), each read as OL7 (b) reads a kept job
(ol7_b_multikick.kept_reading: the partial renders and every TA run's peak). The five
calibrations are not cells. Semi-held-out: E938 printed H-KICKS's aggregate (11 of 20) and that
4096x4096 held; no candidate saw these cells' runs.

Decision (the plan, R9-5 (a)): stage k2 runs only if the frozen candidate gives the count at 18 or
more of the 20 cells.

  python3 -I -B od3_score.py > od3_score.out
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ol7lib as L  # noqa: E402
from ol7_b_multikick import kept_reading, kicks_of  # noqa: E402
from od3_fit import CANDIDATES, replay  # noqa: E402

FROZEN = "H-FLUSH"
K = os.path.normpath(os.path.join(HERE, "../../../closing8/r8-ldpm/out/20261113-021431/k"))


def cells():
    out = []
    for r in csv.DictReader(open(os.path.join(K, "cases.tsv")), delimiter="\t"):
        if r["set"] != "explore":
            continue
        knob = next(w for w in r["knobs"].split() if w.startswith("dbg:render_pb_pages="))
        thr0 = int(knob.split("=")[1], 16) - L.D_OFF
        args = r["args"].split(" -- ", 1)[1].split(" ", 1)[1]
        w, h, kicks = kicks_of(args)
        got = kept_reading(os.path.join(K, r["name"] + ".txt.gz"))
        out.append((r["name"], w, h, kicks, thr0, got))
    return out


def main():
    cs = cells()
    print(f"{len(cs)} cells")
    res = {}
    for name in CANDIDATES:
        c_ok = a_ok = 0
        lines = []
        for n, w, h, kicks, thr0, got in cs:
            p = replay(name, w, h, kicks, thr0)
            ok = got is not None and p is not None and p[0] == got[0]
            c_ok += ok
            a_ok += ok and p[1] == got[1]
            lines.append(f"    {n:16s} {w}x{h} K {len(kicks)} thr0 {thr0:#x} kept "
                         f"{got[0] if got else None} {[hex(x) for x in got[1]] if got else None} | "
                         f"{p[0] if p else None} {[hex(x) for x in p[1]] if p else None} {'ok' if ok else 'OFF'}")
        res[name] = c_ok
        print(f"{name}{' (FROZEN)' if name == FROZEN else ''}: count {c_ok} of {len(cs)}, "
              f"count and every run peak {a_ok} of {len(cs)}")
        print("\n".join(lines))
    n = res[FROZEN]
    print(f"OD-3 VERDICT: {FROZEN} gives {n} of {len(cs)} counts: "
          + ("stage k2 RUNS (at least 18)" if n >= 18 else "stage k2 does NOT run (fewer than 18)"))


if __name__ == "__main__":
    main()
