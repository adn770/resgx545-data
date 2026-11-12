#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/depth_read.py (added at the fold, 2026-11-12, not by the run; POST HOC): for every D row of zd and zf the depth error the
frozen scorer measures (score_g.d_row's plane, |stored - plane| / 2^-23 over the predicted covered pixels), with the triangle's
class, covered pixels, frozen gradient, E606's value range per root area and the pixels above 3 U; then the tallies by class and by
covered-pixel band.  Reads only the kept files and the frozen tables; changes nothing.
  fold/depth_read.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(K, "score"))
import numpy as np  # noqa: E402
import score_g as S  # noqa: E402
M = S.M


def rows(att, st):
    T = S.table(st, K)
    P = S.preds(st, K)
    d = os.path.join(att, st)
    cases = S.tsv_rows(d, "cases.tsv")
    for t in T:
        n = t["name"]
        if t["set"] == "control" or n not in cases or cases[n]["cls"] != "ok":
            continue
        w, h = S.wh(t["args"])
        v, z = S.tri_v(t["args"]), S.tri_z(t["args"])
        raw = S._open(os.path.join(d, n + S.DUMP))
        dimg, dcov = S._cov_from_depth(raw, w, h)
        pc = M.cover(v, w, h)
        err = np.abs(M.f32(dimg) - M.plane_image(v, z, w, h)) / M.U
        e = err[pc]
        cls = n.split("-")[2]
        yield dict(n=n, size="%dx%d" % (w, h), cls=cls, px=int(pc.sum()), grad=float(P[n]["gradient"]["all"]),
                   rpra=M.value_range_per_root_area(v, z), emax=float(e.max()) if e.size else 0.0,
                   over=int((e > M.DEPTH_TOL).sum()), area=float(M.area_px(v)))


def main(att):
    allr = []
    for st in ("zd", "zf"):
        for r in rows(att, st):
            allr.append(r)
            if r["over"]:
                print("OVER %-22s %-9s %-6s px %5d area %9.3f grad %.6f rpra %.4f max %.2f U, %d px above 3 U" % (
                    r["n"], r["size"], r["cls"], r["px"], r["area"], r["grad"], r["rpra"], r["emax"], r["over"]))
    for cls in ("s", "m"):
        sub = [r for r in allr if r["cls"] == cls]
        print("CLASS %s: %d rows, %d above 3 U, max %.2f U, covered px %d..%d" % (
            cls, len(sub), sum(1 for r in sub if r["over"]), max(r["emax"] for r in sub), min(r["px"] for r in sub),
            max(r["px"] for r in sub)))
    for lo, hi in ((1, 4), (5, 16), (17, 64), (65, 256), (257, 10 ** 9)):
        sub = [r for r in allr if lo <= r["px"] <= hi]
        if sub:
            print("PIXELS %d..%s: %d rows, %d above 3 U, max %.2f U" % (lo, hi if hi < 10 ** 9 else "", len(sub),
                  sum(1 for r in sub if r["over"]), max(r["emax"] for r in sub)))
    for lo, hi in ((0, 0.05), (0.05, 0.2), (0.2, 1e9)):
        sub = [r for r in allr if lo <= r["rpra"] < hi]
        if sub:
            print("RANGE/ROOT-AREA [%g, %s): %d rows, %d above 3 U, max %.2f U" % (lo, hi if hi < 1e9 else "inf", len(sub),
                  sum(1 for r in sub if r["over"]), max(r["emax"] for r in sub)))
    print("PIXELS above 3 U: %d of %d covered" % (sum(r["over"] for r in allr), sum(r["px"] for r in allr)))


if __name__ == "__main__":
    main(sys.argv[1])
