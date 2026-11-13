#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""OZ post hoc (after oz_score.py, disclosed as such; not a fit, not a freeze): every declared
variant of both families on E683's 240 S3 cases, to say whether any of them would reach the gate
of 235 at all. Prints each variant's count and the ten best.
    /Users/jtorra/src/nhc/.venv/bin/python -I -B oz_post.py > oz_post.out"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ozlib as O

e683 = O.e683_cases()
res = []
for v in [None] + O.variants() + O.variants_prod():
    ex = px = 0
    for j in e683:
        d = int((O.coverage(j.v, j.k, j.w, j.h, v) != j.img).sum())
        ex += d == 0
        px += d
    res.append((ex, -px, O.vname(v)))
    print("%-30s exact %3d pixels %6d" % (O.vname(v), ex, px), flush=True)
res.sort(reverse=True)
print()
print("best ten on E683 (post hoc):")
for ex, npx, n in res[:10]:
    print("  %-30s exact %3d pixels %6d" % (n, ex, -npx))
print("variants at or above 235: %d of %d" % (sum(r[0] >= 235 for r in res[1:]), len(res) - 1))
