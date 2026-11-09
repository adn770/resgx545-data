#!/usr/bin/env python3
"""extra3_p1138.py DIR [SET]: post-hoc (after the fit data were read): float32 plane-equation variants against the stored
depth of the covered pixels: which arithmetic reproduces the stored bits.  Variants differ in the origin vertex, the
division (true divide or reciprocal), and the evaluation order.  Fitted on the fit set; run on heldout with the same
variant for the test."""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
from recompute_p1138 import Data, load, log  # noqa: E402

f = np.float32


def plane32(c, px_x, px_y, org, variant):
    """float32 plane through c's vertices (screen depths c.z), origin vertex org, at the pixel centres"""
    v = (c.v.astype(np.float64) / 256.0).astype(f)
    z = np.array(c.z, dtype=f)
    i, j, k = org, (org + 1) % 3, (org + 2) % 3
    x0, y0, z0 = v[i][0], v[i][1], z[i]
    dx1, dy1, dz1 = f(v[j][0] - x0), f(v[j][1] - y0), f(z[j] - z0)
    dx2, dy2, dz2 = f(v[k][0] - x0), f(v[k][1] - y0), f(z[k] - z0)
    det = f(f(dx1 * dy2) - f(dx2 * dy1))
    nx = f(f(dz1 * dy2) - f(dz2 * dy1))
    ny = f(f(dz2 * dx1) - f(dz1 * dx2))
    sx = (px_x.astype(f) + f(0.5))
    sy = (px_y.astype(f) + f(0.5))
    if "recip" in variant:
        inv = f(f(1.0) / det)
        gx, gy = f(nx * inv), f(ny * inv)
    else:
        gx, gy = f(nx / det), f(ny / det)
    if "rel" in variant:          # origin at the vertex: z0 + gx*(x - x0) + gy*(y - y0)
        return (z0 + (gx * (sx - x0) + gy * (sy - y0)).astype(f)).astype(f) if "sum" in variant else \
            ((z0 + (gx * (sx - x0)).astype(f)).astype(f) + (gy * (sy - y0)).astype(f)).astype(f)
    # absolute: c = z0 - gx*x0 - gy*y0 ; z = gx*x + gy*y + c
    cc = f(f(z0 - f(gx * x0)) - f(gy * y0))
    return ((gx * sx).astype(f) + (gy * sy).astype(f)).astype(f) + cc


def main():
    cases, jobs = load(sys.argv[1])
    sets = sys.argv[2].split(",") if len(sys.argv) > 2 else ["fit"]
    data = Data(sys.argv[1], cases, jobs)
    cs = [c for c in cases if c.set in sets and c.id in data.dep and data.cov(c.id) is not None and
          c.cls not in ("degenerate", "sliver", "needle")]
    log("cases %d (sets %s)" % (len(cs), sets))
    variants = [("rel", "div"), ("rel", "div", "sum"), ("rel", "recip"), ("rel", "recip", "sum"), ("abs", "div"), ("abs", "recip")]
    res = {}
    for org in range(3):
        for var in variants:
            ex = tot = within1 = 0
            for c in cs:
                cov = data.cov(c.id)
                ys, xs = np.nonzero(cov)
                if not xs.size:
                    continue
                with np.errstate(all="ignore"):
                    p = plane32(c, xs, ys, org, var)
                obs = L.f32(data.dep[c.id][ys, xs])
                ex += int(np.count_nonzero(p.view(np.uint32) == obs.view(np.uint32)))
                within1 += int(np.count_nonzero(np.abs(p.astype(np.float64) - obs) <= 2.0 ** -23))
                tot += xs.size
            res[(org, var)] = (ex, within1, tot)
    # the float64 exact plane rounded to float32 as the reference
    ex = tot = 0
    for c in cs:
        cov = data.cov(c.id)
        ys, xs = np.nonzero(cov)
        if not xs.size:
            continue
        px = L.Pixels([c], margin=0)
        m = cov[px.y, px.x]
        ref = L.plane_at(px, "none", (128, 128), np.array([c.z]))[m].astype(f)
        obs = L.f32(data.dep[c.id][px.y[m], px.x[m]])
        ex += int(np.count_nonzero(ref.view(np.uint32) == obs.view(np.uint32)))
        tot += int(m.sum())
    log("   exact plane (float64) rounded to float32: bit-equal %d of %d (%.4f)" % (ex, tot, ex / tot))
    for k, (e, w, t) in sorted(res.items(), key=lambda kv: -kv[1][0]):
        log("   origin vertex %d %-22s bit-equal %6d of %d (%.4f), within 1 ulp %.4f" % (k[0], "+".join(k[1]), e, t, e / t, w / t))


if __name__ == "__main__":
    main()
