#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""insample.py: post hoc, not frozen as a verdict: the face-local laws on E930's kept 32 x 32 jobs and the edge
rivals on E931's kept edge jobs (other edges than cube2's), run before the freeze to see what the held-out
rows can tell. Usage: python3 gen/insample.py (RESGX545_DATA, default /Users/jtorra/src/resgx545-data)."""
import collections
import gzip
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cube as C, texprog as T
D = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data") + "/render/closing-r8-geo/out/20261113-015842/cube/"
R = C.rule()
for k in ("b1", "b2", "b3"):
    px = T.pixels(gzip.open(D + "cube-n32-%s.txt.gz" % k, "rt").read())
    for law in C.SIZE_LAWS:
        pp = C.pixel_predictions(R, C.SIZED[k], 32, law)
        ok = [p for p, (s, v) in pp.items() if s == "ok"]
        print(k, law, sum(px[p] == pp[p][1] for p in ok), len(ok))
r8edge = {"dx": (C.const(0.75), C.lin("x", 0.1875, 0.376953125), C.const(0.046875)),
          "dz": (C.lin("y", -0.1875, -0.37890625), C.const(0.046875), C.const(0.75))}
for k, spec in r8edge.items():
    px = T.pixels(gzip.open(D + "cube-edge-%s.txt.gz" % k, "rt").read())
    cells = C.edge_cells(R, spec)
    for kind in ("in", "out"):
        for rv in C.EDGE_RIVALS:
            n = m = dec = 0
            for p, (f, kk) in cells.items():
                if kk != kind: continue
                c = tuple(T.coord(s, *p) for s in spec)
                tl = C.blend(R, c, 16, rv)
                if tl is None: continue
                b = C.blend_bytes(tl)
                n += 1
                if all(abs(((px[p] >> (8*i)) & 255) - b[i]) <= C.TOL for i in range(4)): m += 1
            print(k, kind, rv, m, "of", n)
