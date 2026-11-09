#!/usr/bin/env python3
"""post_dist_1140.py DIR...: post hoc: for every pixel where the hardware image differs from H0 (S4 far, and S3 under HU and under
HA), the distance of the pixel centre to the nearest of the three edge lines (exact, in pixels of the rounded triangle) and the
length of the longest edge, to see whether the mismatches are ties / precision or something else."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

dirs = sys.argv[1:]
rows = []
for d in dirs:
    cases, jobs = R.load(d)
    rows += [r for r in R.collect(d, cases, jobs, {"S4", "S3"}, {"fit", "heldout"}) if r[2] is not None]
out = []
for c, txt, img, cols, ok in rows:
    var = "HA" if c.group == "S3" else "HU"
    m = M.coverage(c.v, c.unit, c.w, c.h, var)
    d_ = np.argwhere(m != img)
    if not len(d_):
        continue
    v = M.to_grid(c.v, c.unit, var).astype(float)
    L = max(math.dist(v[i], v[(i + 1) % 3]) / 256 for i in range(3))
    for y, x in d_:
        cx, cy = (x + 0.5) * 256, (y + 0.5) * 256
        dist = min(abs((v[(i + 1) % 3][0] - v[i][0]) * (cy - v[i][1]) - (v[(i + 1) % 3][1] - v[i][1]) * (cx - v[i][0])) /
                   math.dist(v[i], v[(i + 1) % 3]) for i in range(3)) / 256
        out.append((c.group, c.set, c.w, c.cls, int(x), int(y), bool(img[y, x]), dist, L))
for g in ("S4", "S3"):
    sel = [o for o in out if o[0] == g]
    print(g, "mismatching pixels", len(sel), "distance to the nearest edge line (pixel): min %.2e median %.2e max %.2e" % (
        min(o[7] for o in sel), float(np.median([o[7] for o in sel])), max(o[7] for o in sel)))
    for o in sorted(sel, key=lambda o: o[7])[:6] + sorted(sel, key=lambda o: o[7])[-3:]:
        print("   ", o[1:4], "pixel", o[4:6], "hardware covers" if o[6] else "hardware leaves out", "dist %.3e px, longest edge %.0f px" % (o[7], o[8]))
