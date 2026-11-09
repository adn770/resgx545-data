#!/usr/bin/env python3
"""fine_extra_p1138.py DIR: post-hoc (after the fine data were read; the frozen PF1 to PF3 had predicted no snapping below 1/256 and
failed): which rounding of the vertices to 1/256 pixel reproduces the fine sweeps and the random fine triangles, and the depth
plane through the vertices so rounded."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
import fine_p1138 as F  # noqa: E402
from recompute_p1138 import log  # noqa: E402


def snapped(c, mode, bits=8):
    g = 1 << (c.unit - bits)
    v = c.v.copy()
    if g == 1:
        return v
    q, r = np.divmod(v, g)
    half = g // 2
    if mode == "half-up":
        v = (q + (r >= half)) * g
    elif mode == "half-down":
        v = (q + (r > half)) * g
    elif mode == "half-even":
        up = (r > half) | ((r == half) & (q % 2 == 1))
        v = (q + up) * g
    elif mode == "floor":
        v = q * g
    elif mode == "ceil":
        v = (q + (r > 0)) * g
    elif mode == "none":
        pass
    return v


def cov(c, mode, bits=8):
    c2 = F.FCase(["0", "x", "x", str(c.w), str(c.h)] + [str(x) for x in snapped(c, mode, bits).ravel()] + ["0", "0", "0", "-", "D", str(c.unit)])
    return F.covered(c2)


def main():
    d = sys.argv[1]
    cases, jobs = F.load(d)
    ok = [c for c in cases if jobs.get((c.id, "D"))]
    imgs = {c.id: F.cov_image(d, c) for c in ok}
    log("coverage of all %d fine cases against the exact test on vertices rounded to 1/256 pixel, per rounding" % len(ok))
    for mode in ("half-up", "half-down", "half-even", "floor", "ceil", "none"):
        byc = collections.defaultdict(lambda: [0, 0])
        for c in ok:
            m = int(np.count_nonzero(cov(c, mode) != imgs[c.id]))
            k = "sweep" if "sweep" in c.cls else c.cls
            byc[k][0] += int(m > 0)
            byc[k][1] += m
        log("   %-9s inexact cases / mismatching pixels: %s" % (mode, {k: tuple(v) for k, v in sorted(byc.items())}))
    for bits in (7, 8, 9, 10):
        mm = sum(int(np.count_nonzero(cov(c, "half-up", bits) != imgs[c.id])) for c in ok)
        log("   half-up to 1/%d pixel: %d mismatching pixels" % (1 << bits, mm))
    log("\ndepth of the covered pixels against the plane through the vertices rounded half-up to 1/256 at the centre")
    allc = collections.defaultdict(list)
    for c in ok:
        dp = os.path.join(d, "D", "%d.depth.gz" % c.id)
        if not os.path.exists(dp) or imgs[c.id] is None:
            continue
        g = max(1, (c.w + 31) // 32 - 1)
        img = L.depth_image(L.read_gz(dp), c.w, c.h, g)
        ys, xs = np.nonzero(imgs[c.id])
        if not xs.size:
            continue
        v = snapped(c, "half-up").astype(np.float64) / (1 << c.unit)
        z = np.array(c.z)
        area = (v[1][0] - v[0][0]) * (v[2][1] - v[0][1]) - (v[1][1] - v[0][1]) * (v[2][0] - v[0][0])
        sx, sy = xs + 0.5, ys + 0.5
        l1 = ((sx - v[0][0]) * (v[2][1] - v[0][1]) - (sy - v[0][1]) * (v[2][0] - v[0][0])) / area
        l2 = ((v[1][0] - v[0][0]) * (sy - v[0][1]) - (v[1][1] - v[0][1]) * (sx - v[0][0])) / area
        ref = z[0] + l1 * (z[1] - z[0]) + l2 * (z[2] - z[0])
        obs = L.f32(img[ys, xs]).astype(np.float64)
        allc[c.cls.replace("far", "").replace("near", "")].append(np.abs(obs - ref) / 2.0 ** -23)
    for k in sorted(allc):
        e = np.concatenate(allc[k])
        log("   %-12s pixels %6d  within 1 ulp %.4f  above 4 ulp %.4f  max %.2f ulp" % (k, e.size, float(np.mean(e <= 1)), float(np.mean(e > 4)), float(e.max())))


if __name__ == "__main__":
    main()
