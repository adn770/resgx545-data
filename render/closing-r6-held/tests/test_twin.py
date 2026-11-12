#!/usr/bin/env python3
"""test_twin.py: the argv twin.  Every row's command is checked against its plan row, transcribed here BY HAND from rank-round6.md
R6-5 and README.md "Deviations" (not from gen/hgen.py): the triangle, the size, the maximum, the TE word and the other three pokes,
the knobs.  Each q job must also be E848's own job of that size byte for byte (resgx545-data render/closing-r4-render4x
out/20261111-211649/h/cases.tsv, h2 for 640 x 480, h1/h4 for 288 x 144).  It must fail a row with the default triangle, a row on
another maximum, a row without rgn:1, a flushed cell without flush, an --aa4 row (round 4's o2 kind of slip).
"""
import os
import shlex
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E848 = "/Users/jtorra/src/resgx545-data/render/closing-r4-render4x/out/20261111-211649/h/cases.tsv"
# name: (width, height, follow-up, flush)  -- the plan's cells, by hand
PLAN = {
    "a0-640-health": (640, 480, "health", False),
    "b0-640-flush-health": (640, 480, "health", True),
    "a1-640-fill": (640, 480, "fill", False),
    "b1-640-flush-fill": (640, 480, "fill", True),
    "a2-288-fill": (288, 144, "fill", False),
    "b2-288-flush-health": (288, 144, "health", True),
}
POKES = ["cmd:1=0xe0000000", "cmd:10=0xeaa26e26", "cmd:13=0x80000002", "cmd:16=0xeaa26e26"]
fails = 0


def check(c, m):
    global fails
    print(("ok   " if c else "FAIL ") + m)
    fails += 0 if c else 1


def twin(name, knobs, args):
    """[] if the row is its plan row, else the differences."""
    w, h, follow, flush = PLAN[name]
    a = shlex.split(args)
    k = knobs.split()
    bad = []
    if a[:2] != ["tri", "--tri-full"]:
        bad.append("not the full triangle")
    o = lambda n: a[a.index(n) + 1] if n in a else None  # noqa: E731
    if (o("--width"), o("--height")) != (str(w), str(h)):
        bad.append("size")
    if (o("--max-width"), o("--max-height")) != (str(w), str(h)):
        bad.append("maximum")
    pk = [a[i + 1] for i, x in enumerate(a) if x == "--poke"]
    if pk != POKES:
        bad.append("pokes %s" % pk)
    if "--aa4" in a or "--keep-going" not in a or o("--wait-ms") != "20000":
        bad.append("--aa4 / --keep-going / --wait-ms")
    want = {"held", "rgn:1", "expectdiff", "hypo:q:6", "cell:%s" % follow} | ({"flush"} if flush else set())
    if set(k) != want:
        bad.append("knobs %s" % sorted(set(k) ^ want))
    return bad


rows = [l.split("|") for l in open(os.path.join(KP, "tables", "q.txt")).read().splitlines() if l and not l.startswith("#")]
check(sorted(r[0] for r in rows) == sorted(PLAN), "q's rows are the plan's six cells")
e = {}
for l in open(E848).read().splitlines()[1:]:
    f = l.split("\t")
    if "." not in f[0]:
        e[f[0]] = f[6]
for r in rows:
    d = twin(r[0], r[3], r[5])
    check(not d, "%s: its command and knobs are its plan row %s" % (r[0], d or ""))
    src = "h2-640x480-health" if "640" in r[0] else "h4-288x144-fill"
    check(r[5] == e[src], "%s: the job is E848's %s byte for byte" % (r[0], src))
s0 = [l.split("|") for l in open(os.path.join(KP, "tables", "s0.txt")).read().splitlines() if l and not l.startswith("#")]
check(s0[0][3] == "gate" and s0[0][5] == "-" and s0[1][5] == "tri --keep-going" and s0[1][3] == "expectdiff", "s0: n0 the gate row (no command), c1 a plain triangle")
# must fail
r = next(x for x in rows if x[0] == "a1-640-fill")
check(twin(r[0], r[3], r[5].replace("--tri-full ", "")), "twin refuses: the default triangle")
check(twin(r[0], r[3], r[5].replace("--max-width 640 --max-height 480", "--max-width 1024 --max-height 768")), "twin refuses: another maximum")
check(twin(r[0], r[3].replace("rgn:1 ", ""), r[5]), "twin refuses: no rgn:1")
check(twin("b1-640-flush-fill", r[3], r[5]), "twin refuses: a flushed cell without flush")
check(twin(r[0], r[3], r[5].replace("--keep-going", "--keep-going --aa4")), "twin refuses: --aa4")
print("twin checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
