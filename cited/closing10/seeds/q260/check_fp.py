#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Control that can fail: (1) the HA-exact engine matches the E979 rows as the planner read them
(HA off 26 of 46 band pixels); (2) a p=24 coef variant on small coordinates; (3) variant count;
(4) at p=24 RE on HA vertices the variants equal ozlib HA on the fit jobs except where stated."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fplib as F
O = F.O
vs = F.variants()
print("variants", len(vs))
far, FA = F.far_jobs()
print("far rows", len(far), [j.name for j in far])
off = 0
for j in far:
    d = int((O.coverage(j.v, j.k, j.w, j.h, None) != j.img).sum())
    off += d
    print(j.name, "HA pixels off", d)
print("HA total pixels off on far rows", off)
jobs = O.fit_jobs()
print("fit jobs", len(jobs))
for v in (vs[7], [x for x in vs if x["fam"] == "coef" and x["p"] == 24 and x["vq"] == "HA" and x["rm"] == "RE"][0]):
    n = sum(int((F.coverage(j.v, j.k, j.w, j.h, v) == j.img).all()) for j in jobs)
    print(F.vname(v), "rows exact on 395:", n)
