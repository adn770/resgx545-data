#!/usr/bin/env python3
"""post_far_power_1140.py DIR: the power of the S4 set (model only, no hardware): for each limit P (clamp or wrap of every
coordinate to 2^P pixels) the number of far cases (k <= 21) whose coverage under the limit differs from the exact one, and, with
the hardware images, how many of those the hardware sides with (exact) or with the limit."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

rows = []
for d in sys.argv[1:]:
    cases, jobs = R.load(d)
    rows += [r for r in R.collect(d, cases, jobs, {"S4"}, {"fit", "heldout"}) if r[2] is not None]
print("limit      cases-where-it-differs-from-exact  hardware-equals-exact  hardware-equals-limit(0 mismatch)")
for kind in ("clamp", "wrap"):
    for p in range(14, 24):
        diff = ex = lim = 0
        for c, txt, img, cols, ok in rows:
            e = M.coverage(c.v, c.unit, c.w, c.h, "HU")
            l = M.coverage(c.v, c.unit, c.w, c.h, "HU", (kind, p))
            if (e != l).any():
                diff += 1
                ex += int((e != img).sum() <= 2)
                lim += int((l != img).sum() == 0)
        print("%s %2d  %3d  %3d  %3d" % (kind, p, diff, ex, lim))
