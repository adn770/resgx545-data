#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q261 offline (post hoc): for E979's rows with band pixels off the exact image,
the interval of far-vertex displacements (along x and along y, in pixels, each alone) that makes
every band pixel of the far edges agree with the hardware (the near vertex fixed)."""
import gzip
import os
import re
import sys
from fractions import Fraction as F

S = "/Users/jtorra/src/resgx545-data/render/closing-r9-x"
sys.path.insert(0, os.path.join(S, "gen"))
import far as FA  # noqa: E402

ATT = os.path.join(S, "out/20261113-081821/far")


def drawn(name):
    t = gzip.open(f"{ATT}/{name}.txt.gz", "rt").read()
    out = {}
    for m in re.finditer(r"^row (\d+): (.*)$", t, re.M):
        for x, v in enumerate(m.group(2).split()):
            out[(x, int(m.group(1)))] = int(v, 16) == FA.TRI_COLOUR
    return out


def cov(V, x, y):
    a, b, c = V
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if area < 0:
        b, c = c, b
    ins = True
    for p, q in ((a, b), (b, c), (c, a)):
        dx, dy = q[0] - p[0], q[1] - p[1]
        e = dx * (F(2 * y + 1, 2) - p[1]) - dy * (F(2 * x + 1, 2) - p[0])
        ins &= e > 0 or (e == 0 and (dy < 0 or (dy == 0 and dx > 0)))
    return ins


for name, vp in FA.FAR:
    if name not in ("far-x23p", "far-x24p", "far-x25n"):
        continue
    V = [(F(FA.grid(x), 256), F(FA.grid(y), 256)) for x, y in vp]
    fi = max(range(3), key=lambda i: abs(V[i][0]) + abs(V[i][1]))
    d = drawn(name)
    band = [(x, y) for (x, y), (i, n) in FA.coverage([(FA.grid(a), FA.grid(b)) for a, b in vp]).items() if n]
    for ax in (0, 1):
        ok = []
        for k in range(-400, 401):
            W = [list(v) for v in V]
            W[fi][ax] += k
            W = [tuple(v) for v in W]
            if all(cov(W, x, y) == d[(x, y)] for x, y in band):
                ok.append(k)
        print(f"{name} far vertex {tuple(float(c) for c in V[fi])}: displacement along {'xy'[ax]} (whole px, -400..400) consistent: "
              + (f"{ok[0]}..{ok[-1]} ({len(ok)} values)" if ok else "none"))
