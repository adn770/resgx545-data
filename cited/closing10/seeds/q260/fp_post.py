#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""FP post hoc (disclosed, after the freeze and fp_score): all 352 variants on E683's 240 cases,
and on E979's 46 band pixels (how many of the 46 each reproduces; the exact image gets 20).
    /Users/jtorra/src/resgx545/.venv/bin/python -I -B fp_post.py > fp_post.out"""
import os, sys
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fplib as F
O = F.O
G = {}


def init():
    G["c"] = O.e683_cases()
    G["far"], G["FA"] = F.far_jobs()
    FA = G["FA"]
    band = []
    for j in G["far"]:
        V = [(FA.grid(FA.F(int(j.v[i][0]), 256)), FA.grid(FA.F(int(j.v[i][1]), 256))) for i in range(3)]
        cov = FA.coverage(V)
        band.append([(x, y, j.img[y, x]) for (x, y), (_, near) in cov.items() if near])
    G["band"] = band


def one(v):
    ex = px = 0
    for j in G["c"]:
        img = O.coverage(j.v, j.k, j.w, j.h, None) if v is None else F.coverage(j.v, j.k, j.w, j.h, v)
        d = int((img != j.img).sum()); ex += d == 0; px += d
    ok = tot = 0
    for j, b in zip(G["far"], G["band"]):
        img = O.coverage(j.v, j.k, j.w, j.h, None) if v is None else F.coverage(j.v, j.k, j.w, j.h, v)
        for x, y, hw in b:
            tot += 1; ok += bool(img[y, x]) == bool(hw)
    return ex, px, ok, tot


if __name__ == "__main__":
    vs = [None] + F.variants()
    with Pool(12, initializer=init) as pool:
        sc = pool.map(one, vs, chunksize=1)
    rows = []
    for v, s in zip(vs, sc):
        rows.append((s[0], -s[1], s[2], F.vname(v)))
        print("%-32s E683 exact %3d px %5d | E979 band pixels reproduced %2d of %d" % (F.vname(v), s[0], s[1], s[2], s[3]))
    rows.sort(reverse=True)
    print("\nbest ten on E683 (post hoc):")
    for ex, npx, ok, n in rows[:10]:
        print("  %-32s exact %3d px %5d band %d/46" % (n, ex, -npx, ok))
    print("variants >= 235:", sum(r[0] >= 235 for r in rows if r[3] != "HA-exact"), "of", len(rows) - 1)
    b = sorted(rows, key=lambda r: -r[2])[:10]
    print("best ten on the 46 band pixels:")
    for ex, npx, ok, n in b:
        print("  %-32s band %d/46 E683 exact %d" % (n, ok, ex))
