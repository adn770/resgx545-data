#!/usr/bin/env python3
"""extra4_p1138.py DIR [SET]: post-hoc (after the fit data were read): the same plane variants as extra3_p1138.py with every
float32 operation rounded toward zero (the stored depth is below the exact plane by half an ulp on average)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
from recompute_p1138 import Data, load, log  # noqa: E402

f = np.float32


def rtz(x):
    x = np.asarray(x, dtype=np.float64)
    y = x.astype(f)
    over = np.abs(y.astype(np.float64)) > np.abs(x)
    return np.where(over, np.nextafter(y, f(0)), y).astype(f)


def op(a, b, kind):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return rtz({"+": a + b, "-": a - b, "*": a * b, "/": a / b}[kind])


def plane(c, xs, ys, org, variant, centre=(0.5, 0.5)):
    v = (c.v.astype(np.float64) / 256.0).astype(f)
    z = np.array(c.z, dtype=f)
    i, j, k = org, (org + 1) % 3, (org + 2) % 3
    x0, y0, z0 = v[i][0], v[i][1], z[i]
    dx1, dy1, dz1 = op(v[j][0], x0, "-"), op(v[j][1], y0, "-"), op(z[j], z0, "-")
    dx2, dy2, dz2 = op(v[k][0], x0, "-"), op(v[k][1], y0, "-"), op(z[k], z0, "-")
    det = op(op(dx1, dy2, "*"), op(dx2, dy1, "*"), "-")
    nx = op(op(dz1, dy2, "*"), op(dz2, dy1, "*"), "-")
    ny = op(op(dz2, dx1, "*"), op(dz1, dx2, "*"), "-")
    sx = xs.astype(f) + f(centre[0])
    sy = ys.astype(f) + f(centre[1])
    if "recip" in variant:
        inv = op(f(1.0), det, "/")
        gx, gy = op(nx, inv, "*"), op(ny, inv, "*")
    else:
        gx, gy = op(nx, det, "/"), op(ny, det, "/")
    if "sum" in variant:
        return op(z0, op(op(gx, op(sx, x0, "-"), "*"), op(gy, op(sy, y0, "-"), "*"), "+"), "+")
    return op(op(z0, op(gx, op(sx, x0, "-"), "*"), "+"), op(gy, op(sy, y0, "-"), "*"), "+")


def main():
    cases, jobs = load(sys.argv[1])
    sets = sys.argv[2].split(",") if len(sys.argv) > 2 else ["fit"]
    data = Data(sys.argv[1], cases, jobs)
    cs = [c for c in cases if c.set in sets and c.id in data.dep and data.cov(c.id) is not None and
          c.cls not in ("degenerate", "sliver", "needle")]
    res = {}
    for org in range(3):
        for var in (("div",), ("div", "sum"), ("recip",), ("recip", "sum")):
            ex = tot = 0
            for c in cs:
                ys, xs = np.nonzero(data.cov(c.id))
                if not xs.size:
                    continue
                with np.errstate(all="ignore"):
                    p = plane(c, xs, ys, org, var)
                obs = L.f32(data.dep[c.id][ys, xs])
                ex += int(np.count_nonzero(p.view(np.uint32) == obs.view(np.uint32)))
                tot += xs.size
            res[(org, var)] = (ex, tot)
    for k, (e, t) in sorted(res.items(), key=lambda kv: -kv[1][0]):
        log("   RTZ origin vertex %d %-12s bit-equal %6d of %d (%.4f)" % (k[0], "+".join(k[1]), e, t, e / t))


if __name__ == "__main__":
    main()
