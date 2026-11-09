#!/usr/bin/env python3
"""post_neg_1140.py DIR: post hoc (after the frozen criteria failed): for each S3 case, which of the two neighbouring 1/256
grid values (floor, ceil) each negative coordinate must take to reproduce the hardware image; tabulated against the
position of the coordinate inside its 1/256 cell (units of 1/4096, 0..15) and against its sign and magnitude."""
import itertools
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

d = sys.argv[1]
cases, jobs = R.load(d)
rows = R.collect(d, cases, jobs, {"S3"}, {"fit", "heldout"})
tab = defaultdict(Counter)           # (fraction in cell) -> Counter of 'up'/'down' for single-negative-coordinate cases
unres = 0
tot = 0
for c, txt, img, cols, ok in rows:
    if img is None:
        continue
    flat = c.v.ravel()
    neg = [i for i, x in enumerate(flat) if x < 0]
    hu = M.to_grid(flat, 12, "HU")
    fl = flat // 16
    fr = flat % 16
    if (M.coverage(c.v, 12, c.w, c.h, "HU") == img).all():
        for i in neg:
            tab[(int(fr[i]))]["HU-ok"] += 1
        continue
    tot += 1
    sols = []
    free = [i for i in range(6) if fr[i] != 0]       # every coordinate with a fraction can go either way
    for combo in itertools.product((0, 1), repeat=len(free)):
        g = fl.copy()
        for i, b in zip(free, combo):
            g[i] += b
        m = M.coverage(g.reshape(3, 2), 8, c.w, c.h, "NONE")
        if (m == img).all():
            sols.append(dict(zip(free, combo)))
    if not sols:
        unres += 1
        continue
    # coordinates that are the same in every solution
    for i in neg:
        if i not in free:
            continue
        vals = {s[i] for s in sols}
        if len(vals) == 1:
            tab[int(fr[i])]["up" if vals.pop() else "down"] += 1
print("mismatching cases", tot, "no combination of floor/ceil reproduces the image:", unres)
for f in sorted(tab):
    print("fraction %2d/16 of a 1/256 step: %s" % (f, dict(tab[f])))
