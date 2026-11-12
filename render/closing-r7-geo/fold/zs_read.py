#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/zs_read.py (added at the fold, 2026-11-12, not by the run; POST HOC): stage zs row by row.  For each sweep, one line per
step d (1/4096 pixel from the 1/512 tie) with the rivals whose frozen covered image equals the kept one (HU, HA, FAR, S7 =
SETUP(c = 7), the c the fit chose) and the pixels the kept image differs from HU's; then each non-tie case the same way; then the
rows of each set no rival matches; last, for each row no rival matches, the pixels it differs from HU's image in, with
their distance (in pixels) from the nearest edge line of the HU-rounded triangle and that edge's length.  The images are compared exactly as score_g.score_zs does (the covered sha of the frozen
predictions); the pixel counts come from models.cover4096 (the frozen model).  Reads only the kept files and the frozen tables.
  fold/zs_read.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(K, "score"))
import numpy as np  # noqa: E402
import score_g as S  # noqa: E402
M = S.M
RIV = (("HU", "H-HU"), ("HA", "H-HA"), ("FAR", "H-FAR"), ("S7", "SETUP7"))


def main(att):
    d = os.path.join(att, "zs")
    P = S.preds("zs", K)
    T = [t for t in S.table("zs", K) if not t["name"].startswith("zs-ctl-")]
    none = {}
    last = None
    for t in T:
        n = t["name"]
        img = S.image(S.parse_out(S._open(os.path.join(d, n + ".txt")).decode(errors="replace")), M.SW, M.SH)
        cov = img == M.GREEN
        sha = M.cov_sha(cov)
        hit = [a for a, k in RIV if P[n]["covered_sha"].get(k) == sha]
        v = [int(x) for x in S.shlex.split(t["args"])[S.shlex.split(t["args"]).index("--tri-v") + 1].split(",")]
        dhu = int(np.count_nonzero(cov != M.cover4096(v, M.SW, M.SH, "HU")))
        sw = P[n].get("sweep", {}).get("all")
        grp = " ".join(sw.split()[:2]) if sw else "nontie"
        if grp != last:
            print("== %s (%s)" % (grp, t["set"]))
            last = grp
        print("%-22s %-8s px %4d  vs HU %2d  %s" % (n, t["set"], int(cov.sum()), dhu, ",".join(hit) or "none"))
        if not hit:
            none.setdefault(t["set"], []).append((n, v, cov))
    for s, ns in none.items():
        print("NO RIVAL (%s): %d: %s" % (s, len(ns), " ".join(n for n, _, _ in ns)))
    for s, ns in none.items():
        for n, v, cov in ns:
            r = [M.rnd(x, "HU") / 256.0 for x in v]
            pts = [(r[0], r[1]), (r[2], r[3]), (r[4], r[5])]
            ys, xs = np.nonzero(cov != M.cover4096(v, M.SW, M.SH, "HU"))
            out = []
            for y, x in zip(ys, xs):
                best = None
                for i in range(3):
                    (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 3]
                    ln = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
                    dist = abs((bx - ax) * (y + 0.5 - ay) - (by - ay) * (x + 0.5 - ax)) / ln
                    if best is None or dist < best[0]:
                        best = (dist, ln)
                out.append("(%d,%d) %s %.1e px from an edge of %.1f px" % (x, y, "kept" if cov[y, x] else "lost", best[0], best[1]))
            print("OFF HU %s: %s" % (n, "; ".join(out)))


if __name__ == "__main__":
    main(sys.argv[1])
