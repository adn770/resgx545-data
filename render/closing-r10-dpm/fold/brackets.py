#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/brackets.py (r10-dpm fold, POST HOC, written after the frozen score was read): the sampled
bracket of S_6 (the samples' 0x0724 high halves a, b around the 0x072c step, S_6 = max(a, b - 1) is
its upper end) of every replicate and of r9-ldpm's kept calibrations, against the replay R. Whether R
lies inside the bracket: the frozen rule read the upper end only.
  python3 fold/brackets.py out/20261113-102513 [r9-ldpm out dir]"""
import gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "kit"), os.path.join(KP, "gen")]
import score as SC, plan as PL, kitscore as K, read as R  # noqa: E401,E402
att = sys.argv[1]
rds = SC.readings("s6rep", os.path.join(att, "s6rep"))
inside = tot = 0
print("row              replay  bracket S_6        step(a,b)        in-bracket")
for r in K.table(KP, "s6rep"):
    rd = rds[r["name"]]
    if rd is None or 6 not in rd["iv"]:
        continue
    w, h = PL.target(r)
    Rv = PL.model(w, h)[0][6]
    lo, hi = rd["iv"][6]
    a, b = rd["steps"][6]
    tot += 1
    inside += lo <= Rv <= hi
    print(f"{r['name']:16s} 0x{Rv:x}  [0x{lo:x}, 0x{hi:x}] width {hi - lo + 1:3d}  samples 0x{a:x}/0x{b:x}  {'IN' if lo <= Rv <= hi else 'out'} ({hi - Rv:+d})")
print(f"replay inside the bracket: {inside} of {tot}")
