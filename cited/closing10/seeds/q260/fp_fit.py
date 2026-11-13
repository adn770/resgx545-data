#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""FP fit (Q260/Q261): every variant of fplib (352) on the fit set = E914 zs + E943 zs2 (395 jobs)
+ E979's 11 far rows (406 rows); never reads E683. Rank: rows exact, then fewest pixels off, then
declaration order. Freezes the best overall and the best per family (fp_rule.json + sha256).
    /Users/jtorra/src/resgx545/.venv/bin/python -I -B fp_fit.py > fp_fit.out"""
import hashlib, json, os, sys
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fplib as F
O = F.O

JOBS = None


def init():
    global JOBS
    fj = O.fit_jobs()
    far, _ = F.far_jobs()
    JOBS = (fj, far)


def score(var):
    out = []
    for js in JOBS:
        ex = px = 0
        for j in js:
            d = int((F.coverage(j.v, j.k, j.w, j.h, var) != j.img).sum())
            ex += d == 0
            px += d
        out.append((ex, px))
    return out


def ha():
    fj = O.fit_jobs(); far, _ = F.far_jobs()
    res = []
    for js in (fj, far):
        ex = px = 0
        for j in js:
            d = int((O.coverage(j.v, j.k, j.w, j.h, None) != j.img).sum()); ex += d == 0; px += d
        res.append((ex, px))
    return res


if __name__ == "__main__":
    vs = F.variants()
    base = ha()
    print("fit set: 395 jobs (E914 zs, E943 zs2) + 11 E979 far rows = 406")
    print("variants declared: %d (coef 32, rel 128, orig 64, slope 128)" % len(vs))
    print("HA: 395: %d rows exact, %d px off; far 11: %d exact, %d px off" % (base[0][0], base[0][1], base[1][0], base[1][1]))
    with Pool(12, initializer=init) as pool:
        sc = pool.map(score, vs, chunksize=1)
    res = []
    for i, (v, s) in enumerate(zip(vs, sc)):
        ex, px = s[0][0] + s[1][0], s[0][1] + s[1][1]
        res.append((v, ex, px, s, i))
        print("%-32s 395: %3d (%6d px)  far: %2d (%6d px)" % (F.vname(v), s[0][0], s[0][1], s[1][0], s[1][1]))
    res.sort(key=lambda r: (-r[1], r[2], r[4]))
    print("\ntop 15 (rows exact of 406, then pixels):")
    for r in res[:15]:
        print("  %-32s %3d  %6d px  (395: %d, far: %d)" % (F.vname(r[0]), r[1], r[2], r[3][0][0], r[3][1][0]))
    best = {fam: next(r for r in res if r[0]["fam"] == fam) for fam in ("coef", "rel", "orig", "slope")}
    ent = lambda r: {"name": F.vname(r[0]), "var": r[0], "rows406": r[1], "pixels": r[2],
                     "rows395": r[3][0][0], "far_rows": r[3][1][0]}
    rule = {"selection": "max rows exact on 395+11, then min pixels, then declaration order",
            "fit_set": "E914 zs + E943 zs2 (395 jobs) + E979 far (11 rows)",
            "baseline_HA": {"rows395": base[0][0], "far_rows": base[1][0], "pixels395": base[0][1], "far_pixels": base[1][1]},
            "best": ent(res[0]), "per_family": {k: ent(v) for k, v in best.items()},
            "fplib_sha256": hashlib.sha256(open(os.path.join(HERE, "fplib.py"), "rb").read()).hexdigest(),
            "ozlib_sha256": hashlib.sha256(open(os.path.join(F.OZ, "ozlib.py"), "rb").read()).hexdigest(),
            "gate": "E683: 235 of 240; HA 173"}
    b = (json.dumps(rule, indent=1, sort_keys=True) + "\n").encode()
    open(os.path.join(HERE, "fp_rule.json"), "wb").write(b)
    h = hashlib.sha256(b).hexdigest()
    open(os.path.join(HERE, "fp_rule.sha256"), "w").write("%s  fp_rule.json\n" % h)
    print("\nfrozen best:", F.vname(res[0][0]), "| per family:", {k: F.vname(v[0]) for k, v in best.items()})
    print("fp_rule.json sha256", h)
