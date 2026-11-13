#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""OZ fit (round 9, Q260): every declared variant (ozlib.variants(): coefficients quantised, 1323;
ozlib.variants_prod(): products rounded, 290) on E914's and E943's kept zs/zs2 images only (395
jobs, controls included); never reads E683. Ranks by rows exact, then fewest pixels off, and
freezes the best variant of each family and the overall best (oz_rule.json + oz_rule.sha256),
before oz_score.py reads E683.
    /Users/jtorra/src/nhc/.venv/bin/python -I -B oz_fit.py > oz_fit.out"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ozlib as O

jobs = O.fit_jobs()


def score(var):
    ex = px = 0
    for j in jobs:
        d = int((O.coverage(j.v, j.k, j.w, j.h, var) != j.img).sum())
        ex += d == 0
        px += d
    return ex, px


base = score(None)
print("fit set: %d jobs (E914 zs, E943 zs2); HA exact: %d rows exact, %d pixels off" % (len(jobs), *base))
res = []
for fam, vs in (("coef", O.variants()), ("prod", O.variants_prod())):
    for i, v in enumerate(vs):
        ex, px = score(v)
        res.append((fam, i, v, ex, px))
        print("%-4s %-30s rows %3d pixels %7d" % (fam, O.vname(v), ex, px), flush=True)
key = lambda r: (-r[3], r[4], r[0] != "prod", r[1])
res.sort(key=key)
print()
print("top 15:")
for r in res[:15]:
    print("  %-4s %-30s rows %3d pixels %7d" % (r[0], O.vname(r[2]), r[3], r[4]))
best = {f: next(r for r in res if r[0] == f) for f in ("coef", "prod")}
rule = {"selection": "max rows exact on the fit set, then min pixels off, prod before coef, then declaration order",
        "fit_set": "E914 zs (closing-r7-geo 20261112-211113) + E943 zs2 (closing-r8-lgeo 20261113-024441), %d jobs" % len(jobs),
        "baseline_HA": {"rows": base[0], "pixels": base[1]},
        "best": {"name": O.vname(res[0][2]), "var": res[0][2], "rows": res[0][3], "pixels": res[0][4]},
        "best_coef": {"name": O.vname(best["coef"][2]), "var": best["coef"][2], "rows": best["coef"][3], "pixels": best["coef"][4]},
        "best_prod": {"name": O.vname(best["prod"][2]), "var": best["prod"][2], "rows": best["prod"][3], "pixels": best["prod"][4]},
        "ozlib_sha256": hashlib.sha256(open(os.path.join(HERE, "ozlib.py"), "rb").read()).hexdigest(),
        "gate": "kept only if exact on at least 235 of E683's 240 S3 cases (HA: 173)"}
b = (json.dumps(rule, indent=1, sort_keys=True) + "\n").encode()
open(os.path.join(HERE, "oz_rule.json"), "wb").write(b)
open(os.path.join(HERE, "oz_rule.sha256"), "w").write("%s  oz_rule.json\n" % hashlib.sha256(b).hexdigest())
print()
print("frozen:", O.vname(res[0][2]), "| coef:", O.vname(best["coef"][2]), "| prod:", O.vname(best["prod"][2]))
print("oz_rule.json sha256", hashlib.sha256(b).hexdigest())
