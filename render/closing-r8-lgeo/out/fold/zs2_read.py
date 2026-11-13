#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""out/fold/zs2_read.py (added at the fold, 2026-11-13, not by the run; POST HOC): stage zs2 pixel by
pixel. For every row whose kept image differs from HA's frozen image (predictions/zs2/NAME.HA.spans),
each differing pixel: kept or lost, its distance from the nearest edge line of the HA-rounded
triangle, that edge's length and its slope (|minor| / |major| of the edge vector, the axis it runs
along); and, for every sweep, the aimed pixel's distance from its edge at each step. Reads only the
kept files and the frozen tables, through the frozen scorer's readers.
  python3 out/fold/zs2_read.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "score"))
import score as S  # noqa: E402
Z, K = S.Z, S.K


def edge_info(v, x, y):
    r = [Z.rnd(n, "HA") / 256.0 for n in v]
    pts = [(r[0], r[1]), (r[2], r[3]), (r[4], r[5])]
    best = None
    for i in range(3):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 3]
        ln = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        dist = abs((bx - ax) * (y + 0.5 - ay) - (by - ay) * (x + 0.5 - ax)) / ln
        ax_ = "x" if abs(bx - ax) >= abs(by - ay) else "y"
        sl = min(abs(bx - ax), abs(by - ay)) / max(abs(bx - ax), abs(by - ay))
        if best is None or dist < best[0]:
            best = (dist, ln, ax_, sl)
    return best


def main(att):
    d = os.path.join(att, "zs2")
    P, cases = K.predictions(KP, "zs2"), K.rows(d)
    for t in K.table(KP, "zs2"):
        n = t["name"]
        if t["set"] == "control" or not S.done(cases, n):
            continue
        w, h, v = S.zs_args(t)
        img = S.tri_image(K.text(d, n + ".txt"), w, h)
        sp = Z.spans_parse(open(os.path.join(KP, "predictions/zs2/%s.HA.spans" % n)).read(), h)
        cx, cy = (int(c) for c in P[n]["aimed_px"]["all"].split(","))
        cd = edge_info(v, cx, cy)
        off = S.off_pixels(img, sp)
        print("%-26s %s aimed (%d,%d) %d: %.1e px from an edge of %.0f px along %s (slope %.3f); off HA %d" % (
            n, "%dx%d" % (w, h), cx, cy, int(cx in img[cy]), cd[0], cd[1], cd[2], cd[3], len(off)))
        for x, y in off:
            e = edge_info(v, x, y)
            print("    (%d,%d) %s %.1e px from an edge of %.0f px along %s (slope %.3f)" % (
                x, y, "kept" if x in img[y] else "lost", e[0], e[1], e[2], e[3]))


if __name__ == "__main__":
    main(sys.argv[1])
