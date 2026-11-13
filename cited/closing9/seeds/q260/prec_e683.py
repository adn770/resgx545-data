#!/usr/bin/env python3
"""Q260 round 9 offline step 2 (exploratory, in sample, [infer]): on E683's 240 S3 cases, is the
set of pixels off HA's image separated from the right ones near an edge by the pixel's distance to
the edge line relative to a scale of that edge (its length L, or the largest |coordinate| of its
endpoints M)? Prints, per scale, the largest ratio over wrong pixels and the smallest over right
pixels within 3e-3 pixel of an edge line. Read only; numpy (scratch only).
    PY -I -B prec_e683.py"""
import sys
import numpy as np
D = '/Users/jtorra/src/resgx545-data/isp/coverage-envelope'
sys.path.insert(0, D + '/recompute')
import model1140 as M, recompute_p1140 as R  # noqa
d = f'{D}/main'
cases, jobs = R.load(d)
rows = [r for r in R.collect(d, cases, jobs, {'S3'}, {c.set for c in cases}) if r[2] is not None]
W, Rt = {'L': [], 'M': [], 'LM': [], 'd': []}, {'L': [], 'M': [], 'LM': [], 'd': []}
for c, txt, img, cols, ok in rows:
    ha = M.coverage(c.v, c.unit, c.w, c.h, 'HA')
    vp = np.asarray(c.v, dtype=float) / (1 << c.unit)
    ys, xs = np.mgrid[0:c.h, 0:c.w]
    px, py = xs + 0.5, ys + 0.5
    best = np.full((c.h, c.w), np.inf); sc = {k: np.zeros((c.h, c.w)) for k in ('L', 'M', 'LM')}
    for i in range(3):
        (x0, y0), (x1, y1) = vp[i], vp[(i + 1) % 3]
        L = np.hypot(x1 - x0, y1 - y0)
        dd = np.abs((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)) / L
        m = max(abs(x0), abs(y0), abs(x1), abs(y1))
        upd = dd < best
        best = np.where(upd, dd, best)
        for k, v in (('L', L), ('M', m), ('LM', L * m)):
            sc[k] = np.where(upd, v, sc[k])
    wrong = ha != img
    near = (best < 3e-3) & ~wrong
    for k in ('L', 'M', 'LM'):
        W[k] += list(best[wrong] / sc[k][wrong]); Rt[k] += list(best[near] / sc[k][near])
    W['d'] += list(best[wrong]); Rt['d'] += list(best[near])
for k in ('d', 'L', 'M', 'LM'):
    w, r = np.array(W[k]), np.array(Rt[k])
    print(f'scale {k:2s}: wrong {len(w)} max ratio {w.max():.3e}; right near-edge {len(r)}: below that max {int((r <= w.max()).sum())}, min {r.min():.3e}')
