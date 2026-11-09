#!/usr/bin/env python3
"""post_thresh_1140.py DIR: post hoc: S3 mismatching pixels when a negative coordinate n (1/4096 pixel) goes to floor((n + t) / 16)
(1/256 pixel) and positive ones stay half up (t = 8 is E607's rule, t = 7 half away from zero)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

d = sys.argv[1]
cases, jobs = R.load(d)
rows = [r for r in R.collect(d, cases, jobs, {"S3"}, {"fit", "heldout"}) if r[2] is not None]
for t in range(4, 13):
    tot, nc = {"fit": 0, "heldout": 0}, {"fit": 0, "heldout": 0}
    for c, txt, img, cols, ok in rows:
        n = c.v.astype(np.int64)
        g = np.where(n < 0, (n + t) // 16, (n + 8) // 16)
        x = int((M.coverage(g, 8, c.w, c.h, "HU") != img).sum())
        tot[c.set] += x
        nc[c.set] += x > 0
    print("t=%2d: fit %d px (%d cases) heldout %d px (%d cases)" % (t, tot["fit"], nc["fit"], tot["heldout"], nc["heldout"]))
