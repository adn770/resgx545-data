#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/iter_read.py (added at the fold, 2026-11-12, not by the run; POST HOC): for every zi probe row the iterated pa0 error the
frozen scorer measures (score_g.score_zi's plane of the clip z, |pa0 - plane| / 2^-23 over the predicted covered pixels), with the
covered pixels, E606's value range per root area, the signed error (min, mean, max) and the pixels above 4 U.  Reads only the kept files and the frozen tables.
  fold/iter_read.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(K, "score"))
import numpy as np  # noqa: E402
import score_g as S  # noqa: E402
M = S.M


def main(att):
    d = os.path.join(att, "zi")
    cases = S.tsv_rows(d, "cases.tsv")
    tot = over = 0
    for t in S.table("zi", K):
        n = t["name"]
        if t["set"] == "control" or n not in cases or cases[n]["cls"] != "ok":
            continue
        w, h = S.wh(t["args"])
        v, z = S.tri_v(t["args"]), S.tri_z(t["args"])
        img = S.image(S.parse_out(S._open(os.path.join(d, n + ".txt")).decode(errors="replace")), w, h)
        pc = M.cover(v, w, h)
        sg = ((M.f32(img) - M.plane_image(v, [2 * x - 1 for x in z], w, h)) / M.U)[pc]
        e = np.abs(sg)
        k = int((e > M.ITER_TOL).sum())
        tot += int(pc.sum())
        over += k
        print("%s %-16s px %4d rpra %.4f signed %.2f %.2f %.2f max %.2f U, %d px above 4 U" % (
            "OVER" if k else "ok  ", n, int(pc.sum()), M.value_range_per_root_area(v, z), float(sg.min()), float(sg.mean()),
            float(sg.max()), float(e.max()), k))
    print("PIXELS above 4 U: %d of %d covered" % (over, tot))


if __name__ == "__main__":
    main(sys.argv[1])
