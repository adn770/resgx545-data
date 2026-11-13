#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""q139_o1_score.py (round 8 planning, leftovers; offline, no run).
Step 2: checks q139_o1_pred.json against q139_o1_pred.sha256, THEN opens the kept tool outputs
(dumps/NAME.txt.gz) of ta/mtile-fields{,-risky} through E877's loader (its published copy) and
compares each job's observed wrong-tile set (tiles with a pixel that is not the triangle's) with
each write order's prediction.  Jobs without a whole image (faults, cut output) are not scored.

  python3 -I -B q139_o1_score.py DATA_REPO q139_o1_pred.json q139_o1_pred.sha256
"""
import hashlib, json, os, sys
data, pj, ph = sys.argv[1:4]
want = open(ph).read().split()[0]
got = hashlib.sha256(open(pj, "rb").read()).hexdigest()
if want != got: sys.exit("the predictions are not the frozen ones")
print("freeze verified:", got)
sys.path.insert(0, os.path.join(data, "cited/closing6/fold-misc/q139"))
import q139_model as M
P = json.load(open(pj))["cases"]
orders = ["raster", "N", "rowblk", "blkcol", "pair"]
tot = {k: [0, 0] for k in orders}; tw = {k: [0, 0] for k in orders}; rows = []; nos = 0
for key, c in sorted(P.items()):
    if "wrong" not in c: continue
    ds, name = key.split(":")
    W, H, job, bad = M.load(os.path.join(data, ds, "dumps", name + ".txt.gz"))
    if bad is None: nos += 1; continue
    obs = sorted("%d.%d" % t for t in bad)
    res = {k: c["wrong"][k] == obs for k in orders}
    for k in orders:
        tot[k][0] += res[k]; tot[k][1] += 1
        if obs: tw[k][0] += res[k]; tw[k][1] += 1
    distinct = len({tuple(c["wrong"][k]) for k in orders}) > 1
    if obs or distinct or not all(res.values()):
        rows.append("%-46s obs %3d  %s%s" % (name, len(obs), " ".join("%s:%s(%d)" % (k, "ok" if res[k] else "NO", len(c["wrong"][k])) for k in orders),
                                              "  [orders part]" if distinct else ""))
print("jobs with a whole image scored:", tot["raster"][1], "; without one (not scored):", nos)
for k in orders: print("%-7s all jobs %d of %d; wrong images %d of %d" % (k, tot[k][0], tot[k][1], tw[k][0], tw[k][1]))
print("\n".join(rows))
