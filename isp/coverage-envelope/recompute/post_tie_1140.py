#!/usr/bin/env python3
"""post_tie_1140.py DIR...: post hoc: S3 coordinates sitting exactly on a 1/512 pixel tie (fraction 8 of 16 in the case's 1/4096
unit): for each, over the S3 cases in which the images decide which neighbouring 1/256 value (floor / ceil) that one coordinate must
take (the other coordinates left at half-up), the counts by sign and axis.  Only cases in which flipping that one coordinate
alone makes the image equal are counted."""
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

rows = []
for d in sys.argv[1:]:
    cases, jobs = R.load(d)
    rows += [r for r in R.collect(d, cases, jobs, {"S3"}, {"fit", "heldout"}) if r[2] is not None]
tab = Counter()
for c, txt, img, cols, ok in rows:
    flat = c.v.ravel().astype(np.int64)
    base = (flat + 8) // 16
    for i in range(6):
        if flat[i] % 16 != 8:
            continue
        key = ("neg" if flat[i] < 0 else "pos", "xy"[i % 2])
        res = {}
        for name, delta in (("half-up", 0), ("down", -1)):
            g = base.copy()
            g[i] += delta
            res[name] = bool((M.coverage(g.reshape(3, 2), 8, c.w, c.h, "HU") == img).all())
        if res["half-up"] and not res["down"]:
            tab[key + ("hardware = half up (decided)",)] += 1
        elif res["down"] and not res["half-up"]:
            tab[key + ("hardware = down (decided)",)] += 1
        elif not res["down"] and not res["half-up"]:
            tab[key + ("neither alone",)] += 1
        else:
            tab[key + ("undecided",)] += 1
for k in sorted(tab):
    print(k, tab[k])
