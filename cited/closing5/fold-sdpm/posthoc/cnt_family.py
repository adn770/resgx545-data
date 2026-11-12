#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""R5-dpm fold, POST HOC (2026-11-12; read after the run, not frozen): the count family of E854,
n = min{n >= 1 : thr0 + n (thr0 + 0x20 - d) >= U + k} (d 0 to 6 in sixteenths, k -12 to 15), and
E625's form, scored on E832's 22 g-qf cells (U 287), s275's 6 (U 275) and the 20 held-out cells of
stage d-b (s119, s198), read from closing5/dpm/qf_pages.out (copied beside this file) and the
session's kept score-d-b.txt.  Pure python; prints counts of fitting members only."""
import fractions
import pathlib
import re
import sys

F = fractions.Fraction
HERE = pathlib.Path(__file__).resolve().parent
SCORE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "score-d-b.txt"
rows = [ln.split() for ln in open(HERE / "qf_pages.out") if ln.startswith("q")]
sets = {"g-qf (U 287)": (287, [(int(r[2], 16), int(r[3])) for r in rows if r[0].startswith("qf-")]),
        "s275 (U 275)": (275, [(int(r[2], 16), int(r[3])) for r in rows if "s275" in r[0]])}
for U in (119, 198):
    cells = []
    for ln in open(SCORE):
        m = re.match(rf"b-s{U}-0x([0-9a-f]+)\s+nparts\s+pred\s+\d+\s+obs\s+(\d+)\s+\[H-CNT\]", ln)
        if m:
            cells.append((int(m[1], 16), int(m[2])))
    sets[f"s{U} (U {U}, d-b)"] = (U, cells)


def pred(thr0, U, d, k):
    n = 1
    while thr0 + n * (thr0 + 0x20 - d) < U + k:
        n += 1
    return n


grid = [(F(i, 16), k) for i in range(0, 97) for k in range(-12, 16)]
for name, (U, cells) in sets.items():
    print(f"{name}: {len(cells)} cells")
fit = {name: {(d, k) for d, k in grid if all(pred(t, U, d, k) == n for t, n in cells)}
       for name, (U, cells) in sets.items()}
for name in sets:
    ds = sorted({d for d, _ in fit[name]})
    rng = f"d {float(ds[0])} to {float(ds[-1])}" if ds else "none"
    print(f"members fitting all of {name}: {len(fit[name])} of {len(grid)} ({rng})")
both = fit["s119 (U 119, d-b)"] & fit["s198 (U 198, d-b)"]
print("members fitting s119 and s198:", len(both))
allfour = both & fit["g-qf (U 287)"] & fit["s275 (U 275)"]
print("members fitting g-qf, s275, s119 and s198:", len(allfour))
for d, k in ((F(1), 0), (F(5, 4), 0), (F(7, 4), 0)):
    miss = {name: sum(pred(t, U, d, k) != n for t, n in cells) for name, (U, cells) in sets.items()}
    print(f"d={d} k={k} misses:", miss)
old = {name: [(s, k) for s in range(0x18, 0x22) for k in range(-12, 16)
              if all(1 + (U + k - t) // (t + s) == n for t, n in cells)]
       for name, (U, cells) in sets.items()}
print("E625 form (integer s 0x18..0x21, k -12..15) fitting each set:",
      {name: len(v) for name, v in old.items()})
