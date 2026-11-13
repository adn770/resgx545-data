#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""FP score (held out): verifies fp_rule.json and fplib.py/ozlib.py hashes, then scores HA and the
frozen best + per-family bests on E683's 240 S3 cases. Gate 235; HA 173.
    /Users/jtorra/src/resgx545/.venv/bin/python -I -B fp_score.py > fp_score.out"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fplib as F
O = F.O
b = open(os.path.join(HERE, "fp_rule.json"), "rb").read()
want = open(os.path.join(HERE, "fp_rule.sha256")).read().split()[0]
assert hashlib.sha256(b).hexdigest() == want
rule = json.loads(b)
assert hashlib.sha256(open(os.path.join(HERE, "fplib.py"), "rb").read()).hexdigest() == rule["fplib_sha256"]
assert hashlib.sha256(open(os.path.join(F.OZ, "ozlib.py"), "rb").read()).hexdigest() == rule["ozlib_sha256"]
print("fp_rule.json sha256 %s verified (rule, fplib, ozlib)" % want)
cases = O.e683_cases()
print("E683 S3: %d cases (held out)" % len(cases))
cands = [("HA", None)] + [("best " + rule["best"]["name"], rule["best"]["var"])] + \
        [("fam " + v["name"], v["var"]) for v in rule["per_family"].values()]
seen = set()
for n, v in cands:
    if n in seen:
        continue
    seen.add(n)
    ex = px = 0
    for j in cases:
        img = O.coverage(j.v, j.k, j.w, j.h, None) if v is None else F.coverage(j.v, j.k, j.w, j.h, v)
        d = int((img != j.img).sum()); ex += d == 0; px += d
    print("  %-40s exact %3d of %d, pixels off %4d%s" % (n, ex, len(cases), px, "" if v is None else ("  PASSES gate" if ex >= 235 else "  fails gate")))
