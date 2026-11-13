#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""OZ self-check (control that can fail): ozlib.coverage(var=None) equals model1140's HA image on
every fit job, and the HA counts per source match E914 / E943 (rows exact). Not E683.
    /Users/jtorra/src/nhc/.venv/bin/python -I -B check_engine.py"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ozlib as O
import model1140 as M
t = time.time()
jobs = O.fit_jobs()
diff = 0
per = {}
for j in jobs:
    a = O.coverage(j.v, j.k, j.w, j.h, None)
    m = M.coverage(j.v, j.k, j.w, j.h, "HA")
    diff += int((a != m).sum())
    s = per.setdefault((j.src, j.set), [0, 0, 0])
    s[0] += 1; s[1] += int((a == j.img).all()); s[2] += int((a != j.img).sum())
print("fit jobs", len(jobs), "engine vs model1140 HA pixel differences", diff)
for k, (n, ex, px) in sorted(per.items()):
    print("%s %-8s rows %3d exact under HA %3d pixels off %d" % (k[0], k[1], n, ex, px))
v = {"norm": "major", "b": 24, "q": "RN", "origin": "tile", "cq": "x"}
t1 = time.time()
ex = sum(int((O.coverage(j.v, j.k, j.w, j.h, v) == j.img).all()) for j in jobs)
print(O.vname(v), "rows exact", ex, "of", len(jobs), "")
