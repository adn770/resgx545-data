#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: added at the fold (2026-11-13), not by the run; post hoc readings of the kept
files of attempt out/20261113-083450 with the frozen model gen/bgl_model.py (nothing here was
frozen before the run):

1. range: every background pixel whose u or v under the model that held (H-VM in s1, H-VPLANE in
   s2) lies outside [0, 1) (and 1/64 texel off a texel edge): which texel the hardware gave,
   against clamp (to 0 and 63) and repeat (mod 64);
2. coverage: in s2, how many background pixels are not a texel and how many pixels hold the
   triangle's colour (E590: the box is covered whatever the vertex words say);
3. s3: the texels of the five rows that changed (words 11, 12, 14 and 10 at 0xffffffff, and
   cmd:24 at 0 rows): which coordinates survive and the offsets from the pixel's own texel.
   python3 fold/posthoc.py > fold/posthoc.out"""
import collections
import math
import os
import sys
from fractions import Fraction

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, d) for d in ("gen", "kit", "score")]
import bgl_model as M  # noqa: E402
import kitscore as K  # noqa: E402
import score as S  # noqa: E402

A = os.path.join(KP, "out/20261113-083450")
MASK = M.load_mask()


def img(st, n):
    return M.tri_rows(K.text(os.path.join(A, st), n + ".txt"))


print("== 1. pixels outside [0, 1): clamp or repeat")
for st, model in (("s1", "H-VM"), ("s2", "H-VPLANE")):
    t = collections.Counter()
    for r in K.table(KP, st):
        im = img(st, r["name"])
        u, v, verts = M.coords(model, M.obj(S.pokes_of(r)))
        for x, y in MASK:
            px, py = Fraction(2 * x + 1, 2), Fraction(2 * y + 1, 2)
            tu, tv = M.plane(verts, u, px, py) * 64, M.plane(verts, v, px, py) * 64
            if 0 <= tu < 64 and 0 <= tv < 64:
                continue
            if any(abs(c - round(c)) < M.EDGE for c in (tu, tv)):
                t["at an edge, not read"] += 1
                continue
            got = M.decode(im[y][x])
            fu, fv = math.floor(tu), math.floor(tv)
            t["pixels"] += 1
            t["clamp"] += got == (min(max(fu, 0), 63), min(max(fv, 0), 63))
            t["repeat"] += got == (fu % 64, fv % 64)
    print("%s (%s): %d pixels out of range, clamp gives %d, repeat %d; %d at an edge not read"
          % (st, model, t["pixels"], t["clamp"], t["repeat"], t["at an edge, not read"]))

print("== 2. s2 coverage")
for r in K.table(KP, "s2"):
    im = img("s2", r["name"])
    nt = sum(1 for x, y in MASK if M.decode(im[y][x]) is None)
    tri = sum(1 for y in range(64) for x in range(64) if im[y][x] == M.TRI)
    print("%-8s background pixels not a texel %d, triangle pixels %d" % (r["name"], nt, tri))

print("== 3. the s3 rows that changed")
for n in ("e-b11-ff", "e-b12-ff", "e-b14-ff", "e-b10-ff", "e-rows0"):
    im = img("s3", n)
    dec = {(x, y): M.decode(im[y][x]) for x, y in MASK}
    c = collections.Counter(dec.values())
    txs = {t[0] for t in dec.values() if t}
    tys = {t[1] for t in dec.values() if t}
    ex = sum(1 for p, t in dec.items() if t == p)
    print("%-9s not a texel %d; %d distinct texels, %d tx values, %d ty values; own texel %d of %d;"
          " top %s" % (n, c.get(None, 0), len(c), len(txs), len(tys), ex, len(MASK),
                       c.most_common(3)))
    tx_is_x = sum(1 for (x, y), t in dec.items() if t and t[0] == x)
    ty_is_y = sum(1 for (x, y), t in dec.items() if t and t[1] == y)
    print("          tx = x at %d, ty = y at %d; tx = 0 at %d, ty = 0 at %d" % (
        tx_is_x, ty_is_y, sum(1 for t in dec.values() if t and t[0] == 0),
        sum(1 for t in dec.values() if t and t[1] == 0)))
    if n == "e-rows0":
        dx = [t[0] - x for (x, y), t in dec.items() if t]
        dy = [t[1] - y for (x, y), t in dec.items() if t]
        print("          tx - x from %d to %d (|d| <= 8 at %d), ty - y from %d to %d (|d| <= 4 at %d)"
              % (min(dx), max(dx), sum(1 for d in dx if abs(d) <= 8), min(dy), max(dy),
                 sum(1 for d in dy if abs(d) <= 4)))
