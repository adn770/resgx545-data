#!/usr/bin/env python3
"""extra5_p1138.py DIR [SET]: post-hoc (after the fit data were read): snap grids finer than the frozen grid (1/128 and 1/64
pixel, round and floor) and the exact model at the centre with the fitted rule, on the fit set or any listed set."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
from recompute_p1138 import Data, load, log  # noqa: E402

L.SNAPS.update({"r2": (2, "r"), "f2": (2, "f"), "r4u": (4, "r"), "f4u": (4, "f"), "f1": (1, "r"), "r128": (2, "r")})


def main():
    cases, jobs = load(sys.argv[1])
    sets = sys.argv[2].split(",") if len(sys.argv) > 2 else ["fit"]
    data = Data(sys.argv[1], cases, jobs)
    cs = [c for c in cases if c.set in sets and data.cov(c.id) is not None]
    px = L.Pixels(cs)
    obs, ok = L.observed(px, [data.cov(c.id) for c in cs])
    log("sets %s: %d cases, %d pixels" % (sets, len(cs), px.tri.size))
    for sn in ("none", "r2", "f2", "r4u", "f4u", "r32", "r16"):
        for S in ((128, 128), (127, 127), (129, 129), (120, 128), (128, 120), (136, 128), (128, 136)):
            for r in ("R4", "R1", "R2", "R3"):
                m = int(np.count_nonzero(L.covered(px, sn, S, r) != obs))
                if m < 400 or (sn == "none" and S == (128, 128)):
                    log("   snap %-4s S=%s %s: %d mismatching pixels" % (sn, S, r, m))
    # the exact model per class
    pred = L.covered(px, "none", (128, 128), "R4")
    by = {}
    for i, c in enumerate(cs):
        s = px.tri == i
        d = by.setdefault((c.set, c.cls, "%dx%d" % (c.w, c.h)), [0, 0, 0])
        d[0] += 1
        d[1] += int(np.count_nonzero(pred[s] != obs[s]))
        d[2] += int(np.count_nonzero(s))
    for k in sorted(by):
        log("   exact model (none, centre, R4) %-8s %-10s %-8s triangles %3d mismatching pixels %d of %d" % (k + tuple(by[k])))


if __name__ == "__main__":
    main()
