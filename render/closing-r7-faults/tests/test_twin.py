#!/usr/bin/env python3
"""test_twin.py: the argv twin.  Every row's command is checked against its plan row, transcribed here BY HAND from
closing7/c/exp-faults-r7.md (1.4, 2.2) and README.md "Deviations" (not from gen/fgen.py): the triangle, the size, the maximum, the TE
word and the other three pokes, the knobs, the manipulation; each d and m job is E848's own job (resgx545-data
render/closing-r4-render4x out/20261111-211649/h/cases.tsv, h4 at 288 x 144, h2 at 640 x 480) byte for byte, the size aside; each
L row runs its own program, whose lock and release words (bins/LISTING.txt, the assembler's listing) are the plan's.  It must fail a
row with the default triangle, another maximum, no rgn:1, an --aa4, an m1 cell without clr, an m2 cell without long, a d cell at
another size, an L row naming another program, a program with a release dropped.
"""
import os
import re
import shlex
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E848 = "/Users/jtorra/src/resgx545-data/render/closing-r4-render4x/out/20261111-211649/h/cases.tsv"
# the plan's cells, by hand
D = {"d0-640x480": (640, 480), "d1-288x144": (288, 144), "d2-320x400": (320, 400), "d3-256x288": (256, 288),
     "d4-128x528": (128, 528), "d5-384x384": (384, 384), "d6-320x400": (320, 400)}
M = {"m0a-none": "", "m1a-clr": "clr", "m2a-long": "long", "m2b-long": "long", "m1b-clr": "clr", "m0b-none": ""}
L = {"l0-lock-release": ["lock #0", "release #0"],
     "l1-lock0-lock1": ["lock #0", "lock #1", "release #1", "release #0"],
     "l2-lock-lock-rel-rel": ["lock #0", "lock #0", "release #0", "release #0"],
     "l3-lock-lock-rel": ["lock #0", "lock #0", "release #0"],
     "l4-lock-norel": ["lock #0"]}
POKES = ["cmd:1=0xe0000000", "cmd:10=0xeaa26e26", "cmd:13=0x80000002", "cmd:16=0xeaa26e26"]
fails = 0


def check(c, m):
    global fails
    print(("ok   " if c else "FAIL ") + m)
    fails += 0 if c else 1


def held_twin(name, knobs, args, size, extra):
    w, h = size
    a = shlex.split(args)
    k = set(knobs.split())
    bad = []
    if a[:2] != ["tri", "--tri-full"]:
        bad.append("not the full triangle")
    o = lambda n: a[a.index(n) + 1] if n in a else None  # noqa: E731
    if (o("--width"), o("--height")) != (str(w), str(h)):
        bad.append("size")
    if (o("--max-width"), o("--max-height")) != (str(w), str(h)):
        bad.append("maximum")
    if [a[i + 1] for i, x in enumerate(a) if x == "--poke"] != POKES:
        bad.append("pokes")
    if "--aa4" in a or "--keep-going" not in a or o("--wait-ms") != "20000":
        bad.append("--aa4 / --keep-going / --wait-ms")
    want = {"held", "rgn:1", "expectdiff", "cell:health"} | extra
    if k - {x for x in k if x.startswith("hypo:")} != want:
        bad.append("knobs %s" % sorted(k ^ want))
    return bad


def ops(listing, name):
    sect = re.search(r"^== %s\n(.*?)(?=^== |\Z)" % re.escape(name), listing, re.M | re.S)
    return re.findall(r"\t((?:lock|release) #\d)$", sect.group(1), re.M) if sect else None


def rows(st):
    return [l.split("|") for l in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines() if l and not l.startswith("#")]


e = {}
for l in open(E848).read().splitlines()[1:]:
    f = l.split("\t")
    if "." not in f[0]:
        e[f[0]] = f[6]
check(sorted(r[0] for r in rows("d")) == sorted(D), "d's rows are the plan's seven cells")
for r in rows("d"):
    d = held_twin(r[0], r[3], r[5], D[r[0]], {"ctl640"} if r[0].startswith("d0") else set())
    check(not d, "%s: its command and knobs are its plan row %s" % (r[0], d or ""))
    w, h = D[r[0]]
    ref = e["h4-288x144-fill"].replace("--width 288 --height 144 --max-width 288 --max-height 144",
                                      "--width %d --height %d --max-width %d --max-height %d" % (w, h, w, h))
    check(r[5] == ref, "%s: the job is E848's byte for byte at %d x %d" % (r[0], w, h))
check(next(r[5] for r in rows("d") if r[0] == "d0-640x480") == e["h2-640x480-health"], "d0: E848 h2's job byte for byte")
check(next(r[5] for r in rows("d") if r[0] == "d1-288x144") == e["h4-288x144-fill"], "d1: E848 h4's job byte for byte")
check([r[0] for r in rows("m")] == list(M), "m's rows are the plan's six cells in the order M0 M1 M2 M2 M1 M0")
for r in rows("m"):
    d = held_twin(r[0], r[3], r[5], (288, 144), {M[r[0]]} - {""})
    check(not d and r[5] == e["h4-288x144-fill"], "%s: E848 h4's job, knobs with %s %s" % (r[0], M[r[0]] or "no manipulation", d or ""))
listing = open(os.path.join(KP, "bins", "LISTING.txt")).read()
check([r[0] for r in rows("l")] == list(L), "l's rows are the plan's five, l4 last")
for r in rows("l"):
    check(r[5] == 'probe --temps 32 --pixels "$S/%s.bin"' % r[0] and r[3] == "probe", "%s: E088's probe command on its own program" % r[0])
    check(ops(listing, r[0]) == L[r[0]], "%s: its program's locks and releases are the plan's %s" % (r[0], L[r[0]]))
s0 = rows("s0")
check(s0[0][3] == "gate" and s0[0][5] == "-" and s0[1][5] == "tri --keep-going" and s0[1][3] == "expectdiff", "s0: n0 the gate row (no command), c1 a plain triangle")
# must fail
r = next(x for x in rows("d") if x[0] == "d2-320x400")
check(held_twin(r[0], r[3], r[5].replace("--tri-full ", ""), D[r[0]], set()), "twin refuses: the default triangle")
check(held_twin(r[0], r[3], r[5].replace("--max-width 320 --max-height 400", "--max-width 640 --max-height 480"), D[r[0]], set()), "twin refuses: another maximum")
check(held_twin(r[0], r[3].replace("rgn:1 ", ""), r[5], D[r[0]], set()), "twin refuses: no rgn:1")
check(held_twin(r[0], r[3], r[5].replace("--keep-going", "--keep-going --aa4"), D[r[0]], set()), "twin refuses: --aa4")
check(held_twin(r[0], r[3], r[5].replace("--width 320 --height 400", "--width 288 --height 144"), D[r[0]], set()), "twin refuses: another size")
r = next(x for x in rows("m") if x[0] == "m1a-clr")
check(held_twin(r[0], r[3].replace(" clr", ""), r[5], (288, 144), {"clr"}), "twin refuses: an m1 cell without clr")
r = next(x for x in rows("m") if x[0] == "m2a-long")
check(held_twin(r[0], r[3].replace(" long", ""), r[5], (288, 144), {"long"}), "twin refuses: an m2 cell without long")
check(ops(listing.replace("== l3-lock-lock-rel", "== x").replace("== l2-lock-lock-rel-rel", "== l3-lock-lock-rel"), "l3-lock-lock-rel") != L["l3-lock-lock-rel"],
      "twin refuses: l3 running l2's program (an extra release)")
check(ops(listing, "l9-other") is None, "twin refuses: a program that is not in the listing")
print("twin checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
