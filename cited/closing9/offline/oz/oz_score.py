#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""OZ score (round 9, Q260): checks oz_rule.json against oz_rule.sha256 and ozlib.py against the
hash the rule names, then scores the frozen variants (best, best_coef, best_prod) and HA on E683's
240 S3 cases (isp/coverage-envelope, held out: no variant has seen them). Gate: exact on at least
235 of 240. Then the same on the dataset's other groups (S1, S2, S4, S5: E680-E684's positive and
far-vertex cases), a control that can fail: a candidate must not lose cases HA gets right there.
    /Users/jtorra/src/nhc/.venv/bin/python -I -B oz_score.py > oz_score.out"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ozlib as O

b = open(os.path.join(HERE, "oz_rule.json"), "rb").read()
want = open(os.path.join(HERE, "oz_rule.sha256")).read().split()[0]
assert hashlib.sha256(b).hexdigest() == want, "oz_rule.json differs from its freeze"
rule = json.loads(b)
assert hashlib.sha256(open(os.path.join(HERE, "ozlib.py"), "rb").read()).hexdigest() == rule["ozlib_sha256"], "ozlib.py changed"
print("oz_rule.json sha256 %s verified; ozlib.py verified" % want)
cands = [("HA (baseline)", None)] + [(k + " " + rule[k]["name"], rule[k]["var"]) for k in ("best", "best_coef", "best_prod")]


def score(jobs, var):
    ex = px = 0
    for j in jobs:
        d = int((O.coverage(j.v, j.k, j.w, j.h, var) != j.img).sum())
        ex += d == 0
        px += d
    return ex, px


e683 = O.e683_cases()
print("E683 S3: %d cases" % len(e683))
for name, var in cands:
    ex, px = score(e683, var)
    gate = "" if var is None else ("  PASSES the gate" if ex >= 235 else "  fails the gate (< 235)")
    print("  %-40s exact %3d of %d, pixels off %4d%s" % (name, ex, len(e683), px, gate))
print()
for g in ("S1", "S2", "S4", "S5"):
    jobs = O.env_cases({g})
    print("control %s: %d cases" % (g, len(jobs)))
    for name, var in cands:
        ex, px = score(jobs, var)
        print("  %-40s exact %3d, pixels off %4d" % (name, ex, px))
