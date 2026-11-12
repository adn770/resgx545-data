# Q260, round 7 ranking (offline, post hoc on seen data, [infer]). H-TILEREL: each vertex
# coordinate is rounded to the 1/256 grid RELATIVE TO THE ORIGIN (top-left corner) OF THE TILE being
# rasterised, half away from zero (sign-magnitude). Since the origin lies on the grid, this equals
# half up (HU) of the coordinate in tiles whose origin is at or before it on that axis, and half
# down (HD) in tiles whose origin lies after it. For a negative coordinate every tile is "after":
# HD. Compared with E607's global HU and E683's best global variant HA, on E683's S3 cases
# (negative coordinates, k = 12) and on S2 (E681's positive ties), which it must not break.
# Read-only over resgx545-data/isp/coverage-envelope; imports its model and loader.
import sys, itertools, numpy as np
D = '/Users/jtorra/src/resgx545-data/isp/coverage-envelope'
sys.path.insert(0, D + '/recompute')
import model1140 as M, recompute_p1140 as R

def tilerel(V, k, w, h, tw, th):
    flat = V.ravel()
    hu = M.to_grid(flat, k, 'HU'); hd = M.to_grid(flat, k, 'HD')
    one = 1 << k
    out = np.zeros((h, w), dtype=bool); cache = {}
    for ty in range(0, h, th):
        for tx in range(0, w, tw):
            o = [tx * one, ty * one] * 3
            key = tuple(bool(o[i] > flat[i]) for i in range(6))
            if key not in cache:
                g = np.where(np.array(key), hd, hu).reshape(3, 2)
                cache[key] = M.coverage(g, 8, w, h, 'NONE')
            out[ty:ty + th, tx:tx + tw] = cache[key][ty:ty + th, tx:tx + tw]
    return out

for grp in ('S3', 'S2'):
    d = f'{D}/main'
    cases, jobs = R.load(d)
    rows = [r for r in R.collect(d, cases, jobs, {grp}, {c.set for c in cases}) if r[2] is not None]
    res = {}
    for c, txt, img, cols, ok in rows:
        models = [('HU', lambda: M.coverage(c.v, c.unit, c.w, c.h, 'HU')),
                  ('HA', lambda: M.coverage(c.v, c.unit, c.w, c.h, 'HA')),
                  ('HD', lambda: M.coverage(c.v, c.unit, c.w, c.h, 'HD'))]
        models += [(f'TREL{tw}x{th}', (lambda tw=tw, th=th: tilerel(c.v, c.unit, c.w, c.h, tw, th)))
                   for tw, th in ((32, 16), (16, 16), (16, 8), (32, 32), (64, 64))]
        for name, f in models:
            n = int((f() != img).sum())
            r = res.setdefault(name, [0, 0, 0]); r[0] += 1; r[1] += n > 0; r[2] += n
    print(f'== {grp}: {len(rows)} cases with an image')
    for name, (nc, bad, px) in res.items():
        print(f'  {name:10s} cases {nc}  inexact {bad}  wrong pixels {px}', flush=True)
