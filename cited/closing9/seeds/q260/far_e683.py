#!/usr/bin/env python3
"""Q260 round 9 offline step: E943's post hoc far-vertex reading (a sweep misses HA's image iff a
vertex of the rounded triangle lies past the target's far edge, x > W or y > H; 12 of 12 with one
missed, 16 of 20 without one exact), read on E683's 240 S3 cases (negative coordinates, k = 12),
which E943 never read: per case, HA's wrong pixels, whether a vertex lies past the far edge (HA's
grid vertex, x > W or y > H in pixels), the longest edge, and the pixel's distance to the nearest
edge line. Read only over resgx545-data/isp/coverage-envelope (its model and loader, imported).
Numpy, scratch only.
    .venv/bin/python -I far_e683.py"""
import sys
import numpy as np
D = '/Users/jtorra/src/resgx545-data/isp/coverage-envelope'
sys.path.insert(0, D + '/recompute')
import model1140 as M, recompute_p1140 as R  # noqa


def edges(v):
    p = [(float(v[i][0]), float(v[i][1])) for i in range(3)]
    return [(p[i], p[(i + 1) % 3]) for i in range(3)]


def dist(px, py, a, b):
    (x0, y0), (x1, y1) = a, b
    L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    return abs((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)) / L, L


d = f'{D}/main'
cases, jobs = R.load(d)
rows = [r for r in R.collect(d, cases, jobs, {'S3'}, {c.set for c in cases}) if r[2] is not None]
tab = {}
for c, txt, img, cols, ok in rows:
    ha = M.coverage(c.v, c.unit, c.w, c.h, 'HA')
    bad = np.argwhere(ha != img)
    vp = np.asarray(c.v, dtype=float) / (1 << c.unit)          # pixels
    far = bool((vp[:, 0] > c.w).any() or (vp[:, 1] > c.h).any())
    es = edges(vp)
    longest = max(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in es)
    dmax, lmin = 0.0, 1e9
    for y, x in bad:
        dd = min((dist(x + 0.5, y + 0.5, a, b) for a, b in es), key=lambda t: t[0])
        dmax = max(dmax, dd[0]); lmin = min(lmin, dd[1])
    k = ('far' if far else 'nofar', 'long' if longest >= 195 else 'short')
    t = tab.setdefault(k, [0, 0, 0, 0.0])
    t[0] += 1; t[1] += len(bad) > 0; t[2] += len(bad); t[3] = max(t[3], dmax)
    if len(bad):
        print(f'case {c.id:4d} {c.cls:10s} {c.w}x{c.h} far={int(far)} longest={longest:7.1f} wrong={len(bad):3d} maxdist={dmax:.2e} edge>={lmin:6.1f}')
print()
for k, (n, inexact, px, dm) in sorted(tab.items()):
    print(f'{k[0]:5s} {k[1]:5s}: cases {n:3d}  off HA {inexact:3d}  pixels {px:4d}  max distance {dm:.2e}')
