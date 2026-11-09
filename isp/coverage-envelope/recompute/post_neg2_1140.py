#!/usr/bin/env python3
"""post_neg2_1140.py DIR: post hoc: for the S3 fit cases that half-away-from-zero rounding (negative ties go down) does not
reproduce, the offsets (-1, 0, +1 in 1/256 pixel) of the six coordinates, from that rounding, that do; shows whether a
coordinate other than a negative one has to move."""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

d = sys.argv[1]
cases, jobs = R.load(d)
rows = R.collect(d, cases, jobs, {"S3"}, {"fit"})
for c, txt, img, cols, ok in rows:
    if img is None:
        continue
    flat = c.v.ravel().astype(np.int64)
    base = M.to_grid(flat, 12, "HA")
    if (M.coverage(base.reshape(3, 2), 8, c.w, c.h, "HU") == img).all():
        continue
    best = []
    for off in itertools.product((-1, 0, 1), repeat=6):
        g = (base + np.array(off)).reshape(3, 2)
        if (M.coverage(g, 8, c.w, c.h, "HU") == img).all():
            best.append(off)
    best.sort(key=lambda o: sum(abs(x) for x in o))
    print(c.id, c.w, "coords", [int(x) for x in flat], "frac", [int(x % 16) for x in flat], "neg", [int(x < 0) for x in flat],
          "fewest-moves offsets", best[:3], "(%d solutions)" % len(best))
