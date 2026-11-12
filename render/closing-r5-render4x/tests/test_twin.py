#!/usr/bin/env python3
"""tests/test_twin.py: the argv-twin test (round 5's addition to the brief).  Every row's COMMAND, parsed from the generated table, is
checked against its PLAN row typed here from exp-render4x-r5.md (2.1, 2.2, 3.1 to 3.5) and never from the generator: the triangle
(the default triangle, the full one, a line or a point probe), the sample mode (1x or 4x: --aa4 and CR_TE_AA 0xe0000000), the target
and the context's maximum, the PB size knob, the TE_AA word of a t row (poke or --cmd), the region-array knob and the held flow.
Then the scene twin: every frozen need is its kept twins' (gen/twins.py), and the same check run on ROUND 4's o table must fail at o2
(a default triangle frozen with the full triangle's need 97; its twins say 19): the slip this test exists to catch, kept as a
regression.  Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), HERE]
import rlib as L  # noqa: E402
import twins as TW  # noqa: E402
import worlds as WD  # noqa: E402

R4 = "/Users/jtorra/src/scratch/resgx545/closing4/r4-render4x"
bad = 0


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


# name: (triangle, mode, W, H, MW, MH, P, te word, rgn knob, held)   triangle: default | full | line | point
F4 = ("full", "4x")
PLAN = {
    "s0-1x-1024x768": ("default", "1x", 1024, 768, 1024, 768, 0x422, None, 0, False),
    "s0-4x-288x144": F4 + (288, 144, 288, 144, 0x422, 0xE0000000, 0, False),
    "s0-4x-1024x768": F4 + (1024, 768, 1024, 768, 0x422, 0xE0000000, 0, False),
    "t6-ctl-te40-1array": ("full", "1x", 64, 64, 64, 64, 0x422, 0x40000000, 1, False),
    "t3b-line-base": ("line", "1x", 64, 64, 64, 64, 0x422, None, 0, False),
    "t4b-point-base": ("point", "1x", 64, 64, 64, 64, 0x422, None, 0, False),
    "t1-aa4-te40": ("full", "4x-te", 64, 64, 64, 64, 0x422, 0x40000000, 0, False),
    "t2-aa4-te80": ("full", "4x-te", 64, 64, 64, 64, 0x422, 0x80000000, 0, False),
    "t3-line-te40": ("line", "1x", 64, 64, 64, 64, 0x422, 0x40000000, 1, False),
    "t4-point-te40": ("point", "1x", 64, 64, 64, 64, 0x422, 0x40000000, 1, False),
    "t3c-line-te80": ("line", "1x", 64, 64, 64, 64, 0x422, 0x80000000, 1, False),
    "t4c-point-te80": ("point", "1x", 64, 64, 64, 64, 0x422, 0x80000000, 1, False),
    "o1-1x-1024x768-p35": ("default", "1x", 1024, 768, 1024, 768, 0x35, None, 0, False),
    "o2-1x-1024x768-p34": ("default", "1x", 1024, 768, 1024, 768, 0x34, None, 0, False),
    "o3-4x-1024x768-pe3": F4 + (1024, 768, 1024, 768, 0xe3, 0xE0000000, 0, False),
    "o4-4x-1024x768-pe2": F4 + (1024, 768, 1024, 768, 0xe2, 0xE0000000, 0, False),
    "o5-4x-288x144-p23": F4 + (288, 144, 288, 144, 0x23, 0xE0000000, 0, False),
    "o6-4x-640x480-p6e": F4 + (640, 480, 640, 480, 0x6e, 0xE0000000, 0, False),
    "o7-4x-640x480-p6d": F4 + (640, 480, 640, 480, 0x6d, 0xE0000000, 0, False),
    "o8-4x-512x384-p53": F4 + (512, 384, 512, 384, 0x53, 0xE0000000, 0, False),
    "o9-4x-512x384-p52": F4 + (512, 384, 512, 384, 0x52, 0xE0000000, 0, False),
    "o10-1xf-1024x768-p53": ("full", "1x", 1024, 768, 1024, 768, 0x53, None, 0, False),
    "o11-1xf-1024x768-p52": ("full", "1x", 1024, 768, 1024, 768, 0x52, None, 0, False),
    "m0-1024x768-max2048x2048": F4 + (1024, 768, 2048, 2048, 0x422, 0xE0000000, 0, False),
    "m1-1280x1024-max1280x1040": F4 + (1280, 1024, 1280, 1040, 0x422, 0xE0000000, 0, False),
    "m2-1280x1024-max2048x2048": F4 + (1280, 1024, 2048, 2048, 0x422, 0xE0000000, 0, False),
    "m3-1280x1024-max2048x1024": F4 + (1280, 1024, 2048, 1024, 0x422, 0xE0000000, 0, False),
    "m4-2048x1536-max4096x4096": F4 + (2048, 1536, 4096, 4096, 0x422, 0xE0000000, 0, False),
    "l1-2048x240": F4 + (2048, 240, 2048, 240, 0x422, 0xE0000000, 0, False),
    "l2-256x1536": F4 + (256, 1536, 256, 1536, 0x422, 0xE0000000, 0, False),
    "l3-768x2048": F4 + (768, 2048, 768, 2048, 0x422, 0xE0000000, 0, False),
    "l4-1280x768": F4 + (1280, 768, 1280, 768, 0x422, 0xE0000000, 0, False),
    "l5-1024x1024": F4 + (1024, 1024, 1024, 1024, 0x422, 0xE0000000, 0, False),
    "x1-1024x512": F4 + (1024, 512, 1024, 512, 0x422, 0xE0000000, 0, False),
    "x2-1184x768": F4 + (1184, 768, 1184, 768, 0x422, 0xE0000000, 0, False),
    "x3-1024x800": F4 + (1024, 800, 1024, 800, 0x422, 0xE0000000, 0, False),
    "d1-1280x1024-held": F4 + (1280, 1024, 1280, 1024, 0x422, 0xE0000000, 0, True),
}


def from_argv(args, knobs):
    """The plan tuple read from a row's command and knobs alone."""
    t = TW.tokens(args)
    a = WD.parse(t)
    if a["verb"] == "probe":
        tri = {"p1131-green__0": "line", "p1131-psizes__1": "point"}.get(a["prog"], "?")
    else:
        tri = "full" if a["full"] else "default"
    te = a["cmd"] if a["verb"] == "probe" else (a["te"] if any(x.startswith("cmd:1=") for x in t) else None)
    if a["aa4"] and a["te"] == 0xE0000000:
        mode = "4x"
    elif a["aa4"]:
        mode = "4x-te"
    else:
        mode = "1x"
    k = knobs.split()
    pb = int(next((x[3:] for x in k if x.startswith("pb:")), "0x422"), 16)
    return (tri, mode, a["w"], a["h"], a["mw"], a["mh"], pb, te, 1 if "rgn:1" in k else 0, "held" in k)


seen = set()
for st in open(os.path.join(KP, "stages.txt")).read().split():
    for row in WD.table(st):
        seen.add(row["name"])
        want = PLAN.get(row["name"])
        got = from_argv(row["args"], row["knobs"])
        check(want == got, "argv twin %s/%s: %s" % (st, row["name"], got if want == got else "%s, the plan says %s" % (got, want)))
# the test can fail: round 4's o2 command (the default triangle) put in the place of o10 (the 1x full triangle), and a row whose rgn:1
# knob is dropped, do not pass
o2r4 = [ln.split("|", 5) for ln in open(os.path.join(R4, "tables", "o.txt")) if ln.startswith("o2-")][0]
check(from_argv(o2r4[5], "expectdiff pb:0x53") != PLAN["o10-1xf-1024x768-p53"], "the argv twin fails a default triangle in a full-triangle row")
t3 = [r for r in WD.table("t") if r["name"] == "t3-line-te40"][0]
check(from_argv(t3["args"], "-") != PLAN["t3-line-te40"], "the argv twin fails a TE_AA row without its rgn:1 knob")
check(seen == set(PLAN), "every plan row is a table row and every table row a plan row (%d)" % len(PLAN))

# the scene twin on this session's needs (controls, replicates and held out have a twin; o10, o11 the [model] 49)
tb = TW.table()
rows = []
for st in ("s0", "o"):
    P = L.load_predictions(st + ".tsv", KP)
    for row in WD.table(st):
        need = L.pred_or(P, row["name"], "need") or L.pred_or(P, row["name"], "pb_used")
        rows.append((row["name"], row["args"], row["knobs"], need, row["set"], row["set"] == "explore"))
pr = TW.check(rows, tb)
check(not pr, "scene twins: no row of r5's s0 and o has a need its kept twins contradict%s" % ("" if not pr else ": " + "; ".join(pr)))
nomodel = TW.check([(n, a, k, need, "control", False) for n, a, k, need, s, _ in rows if n.startswith("o10")], tb)
check(nomodel and "no kept twin" in nomodel[0], "a control with no twin and a [model] need fails the build: %s" % nomodel[:1])

# the regression: round 4's o table with its frozen needs (exp 2.1: 97 for o1, o2 from the 1x model; 193; 12; o7 1153 and o8 2049 had
# no twin and were held out) must fail at o2
r4rows = []
need4 = {"o1-1x-1024x768-p83": 97, "o2-1x-1024x768-p82": 97, "o3-4x-1024x768-pe3": 193, "o4-4x-1024x768-pe2": 193, "o5-4x-288x144-p23-held": 12}
for ln in open(os.path.join(R4, "tables", "o.txt")).read().splitlines():
    if ln and not ln.startswith("#"):
        name, sset, risk, knobs, rt, args = ln.split("|", 5)
        if name in need4:
            r4rows.append((name, args, knobs, need4[name], sset, False))
pr4 = TW.check(r4rows, tb)
check(any(p.startswith("o2-1x-1024x768-p82: frozen need 97, its 6 kept twins say 19") for p in pr4),
      "REGRESSION: the twin check on round 4's o table fails at o2 (97 frozen, the twins say 19): %s" % [p[:60] for p in pr4])
check(any(p.startswith("o1-1x-1024x768-p83: frozen need 97") for p in pr4) and not any(p.startswith(("o3", "o4", "o5")) for p in pr4),
      "  and at o1 (the same scene), not at o3, o4, o5 (their needs were the twins')")
sys.exit(bad)
