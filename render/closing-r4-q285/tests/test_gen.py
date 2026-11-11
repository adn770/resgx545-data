#!/usr/bin/env python3
"""tests/test_gen.py: the generated tables and predictions of R4-A (Q285 rerun) against their sources.

- every command is K2's own (resgx545-data render/closing-r3k-pixel tables k-pb0, k-pb), byte for byte;
- every row carries the knob rgn:1 and expectdiff, and nothing else;
- the controls' frozen values are the R3K-regress kept values of jobs of the SAME shape (-n 2 --geometry 1, two renders), read
  from the published kept files, and the three regress replicates agree on them;
- no control value is a one-render (E728-shape) value (K2's k-pb0 lesson);
- the rows are no more than K2's (8).
  PY tests/test_gen.py
"""
import gzip
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))

fails = 0


def check(name, cond, info=""):
    global fails
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else ": " + str(info)))
    if not cond:
        fails += 1


import agen as G  # noqa: E402
import alib as L  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
K2 = os.path.join(DATA, "render/closing-r3k-pixel/tables")
REG = os.path.join(DATA, "render/closing-r3k-regress/out/20261110-222647/rg-pb")


def table(path):
    rows = []
    for ln in open(path).read().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(ln.split("|", 5))
    return rows


def gzt(p):
    with gzip.open(p, "rb") as f:
        return f.read()


k2 = {r[0]: r for r in table(os.path.join(K2, "k-pb0.txt")) + table(os.path.join(K2, "k-pb.txt"))}
ours = {}
for st in ("a-pb0", "a-pb"):
    for r in table(os.path.join(KP, "tables", st + ".txt")):
        ours[r[0]] = (st, r)

check("stages.txt names a-pb0 then a-pb", open(os.path.join(KP, "stages.txt")).read().split() == ["a-pb0", "a-pb"])
check("8 rows, no more than K2's 8", len(ours) == 8 and len(k2) == 8, (len(ours), len(k2)))
check("the same row names as K2's k-pb0 and k-pb", set(ours) == set(k2), sorted(set(ours) ^ set(k2)))
for n, (st, r) in ours.items():
    if n not in k2:
        continue
    check("%s: command byte for byte K2's" % n, r[5] == k2[n][5], (r[5][:80], k2[n][5][:80]))
    check("%s: set as K2's (%s)" % (n, k2[n][1]), r[1] == k2[n][1], r[1])
    check("%s: knobs exactly 'rgn:1 expectdiff'" % n, r[3] == "rgn:1 expectdiff", r[3])
    check("%s: no regtimeline" % n, r[4] == "-", r[4])
    want_st = "a-pb0" if n in ("pb-d0-te40", "pb-p0-te60", "pb-p1-te40") else "a-pb"
    check("%s: in stage %s" % (n, want_st), st == want_st, st)
    check("%s: two-render shape (-n 2 --geometry 1) with a dump" % n,
          "-n 2 --geometry 1" in r[5] and '--dump-render "$W/dump"' in r[5], r[5][:60])
    check("%s: no --aa4 (the session forces one array instead)" % n, "--aa4" not in r[5])
order = [r[0] for r in table(os.path.join(KP, "tables", "a-pb0.txt"))] + [r[0] for r in table(os.path.join(KP, "tables", "a-pb.txt"))]
check("row order is K2's", order == ["pb-d0-te40", "pb-p0-te60", "pb-p1-te40", "pb-p2-own11", "pb-p3a-twin", "pb-p3b-twin",
                                    "pb-p4a-ffff", "pb-p4b-ffff"], order)

# the extracted values are the regress kept files', and the three TE 0x40 replicates agree
V = G.load_values()
for job in ("pb-n40-a", "pb-n40-b", "pb-n40-c", "pb-n60"):
    out = gzt(os.path.join(REG, job + ".txt.gz")).decode()
    par = gzt(os.path.join(REG, job + ".tri.param.bin.gz"))
    tad = gzt(os.path.join(REG, job + ".tri.tadata.bin.gz"))
    check("%s: target hash as kept" % job, V[job]["target_hash"] == L.target_hash(out), V[job].get("target_hash"))
    check("%s: param sha256 as kept" % job, V[job]["param_sha256"] == hashlib.sha256(par).hexdigest())
    check("%s: tadata sha256 as kept" % job, V[job]["tadata_sha256"] == hashlib.sha256(tad).hexdigest())
    check("%s: dwords 0-63 as kept" % job, V[job]["par_0_64"] == ",".join("%08x" % x for x in L.dwords(par)[:64]))
    check("%s: render 2 line as kept" % job, V[job]["tri2"] == L.tri_text(out, 2), V[job].get("tri2"))
for q in ("rc", "target_hash", "diff", "tri2", "renders", "param_sha256", "tadata_sha256", "par_0_64"):
    check("regress TE 0x40 replicates a, b, c agree on %s" % q, V["pb-n40-a"][q] == V["pb-n40-b"][q] == V["pb-n40-c"][q])

P0 = L.load_predictions("a-pb0.tsv", KP)
P = L.load_predictions("a-pb.tsv", KP)
check("d0 frozen hash is the two-render value 0x8ea26cdfee74a325", L.pred(P0, "pb-d0-te40", "target_hash") == "0x8ea26cdfee74a325")
check("p1 frozen hash is the two-render value 0x8ea26cdfee74a325", L.pred(P0, "pb-p1-te40", "target_hash") == "0x8ea26cdfee74a325")
check("p0 frozen hash is the two-render twin value 0xd2bfb75560f4c325", L.pred(P0, "pb-p0-te60", "target_hash") == "0xd2bfb75560f4c325")
one_render = {"0xfc5ff15e0434a325", "0xd0530839d87ea325"}
for (case, q), vals in list(P0.items()) + list(P.items()):
    for val, model, sset in vals:
        if q == "target_hash" and sset == "control":
            check("%s: control hash is not a one-render value" % case, val not in one_render, val)
check("d0 frozen param sha256 is regress pb-n40's", L.pred(P0, "pb-d0-te40", "param_sha256") == V["pb-n40-a"]["param_sha256"])
check("p0 frozen param sha256 is regress pb-n60's", L.pred(P0, "pb-p0-te60", "param_sha256") == V["pb-n60"]["param_sha256"])
check("p0 frozen dword 26 is 0x04000004 (the two-render twin's), not 0",
      L.pred(P0, "pb-p0-te60", "par_0_64").split(",")[26] == "04000004")
check("p2 frozen param sha256 is d0's (a poke of the word's own value)", L.pred(P, "pb-p2-own11", "param_sha256") == V["pb-n40-a"]["param_sha256"])
check("p2 frozen applied: par:11=0x00000000", L.pred(P, "pb-p2-own11", "applied") == "par:11=0x00000000")
p3pokes = L.pred(P, "pb-p3a-twin", "applied").split(";")
check("p3 applies 16 pokes, dwords 11 to 26", [x.split("=")[0] for x in p3pokes] == ["par:%d" % i for i in range(11, 27)], p3pokes)
check("p3's poked words 11-25 are the twin's 11-25 (regress pb-n60)",
      [int(x.split("=")[1], 16) for x in p3pokes[:15]] == [int(w, 16) for w in V["pb-n60"]["par_0_64"].split(",")[11:26]])
check("p3's dword 26 poke is 0 (K2's, the twin object ends at 25)", p3pokes[15] == "par:26=0x00000000")
check("p3 H-OLD predicts the twin's picture (diff 0 of 4096, 4096 triangle)",
      L.pred(P, "pb-p3a-twin", "reading", "H-OLD") == "twin" and L.pred(P, "pb-p3a-twin", "reading", "H-FIELD") == "not twin")
check("p4 H-FIELD predicts drawn, H-OLD empty",
      L.pred(P, "pb-p4a-ffff", "reading", "H-FIELD") == "drawn" and L.pred(P, "pb-p4a-ffff", "reading", "H-OLD") == "empty")
check("the twin's two-render hash is reported for p3, never a deciding quantity",
      L.pred(P, "pb-p3a-twin", "target_hash", "report") == "0xd2bfb75560f4c325")
sets = {}
for (case, q), vals in P.items():
    for val, model, sset in vals:
        sets.setdefault(case, set()).add(sset)
check("held out p3a, p4a; replicates p3b, p4b; control p2",
      sets.get("pb-p3a-twin") == {"heldout"} and sets.get("pb-p4a-ffff") == {"heldout"} and sets.get("pb-p3b-twin") == {"replicate"}
      and sets.get("pb-p4b-ffff") == {"replicate"} and sets.get("pb-p2-own11") == {"control"}, sets)
print("%d FAIL" % fails)
sys.exit(1 if fails else 0)
