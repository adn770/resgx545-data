#!/usr/bin/env python3
"""tests/test_twin.py: the argv-twin test (round 5's addition to the brief, kept in round 6).  Every row's COMMAND, parsed from the
generated table, is checked against its PLAN row typed here from exp-render4x-r6.md (section 2's table, section 5's four rows) and
never from the generator: the triangle (the default triangle, the full one, a line or a point probe), the sample mode (1x or 4x:
--aa4 and CR_TE_AA 0xe0000000), the target and the context's maximum, the TE_AA word of a t row (poke or --cmd), the render count,
the geometry-only first render and the dword poke of t7, the region-array knob and the held flow.  Then it must FAIL on what it exists
to catch: round 4's o2 (a default triangle in a full-triangle row), a row whose maximum was dropped (a8 on its own size), a t row
without its rgn:1 knob, t7 without its poke.  And the scene twin: every frozen need of s0 is its kept twins'.
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
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


# name: (triangle, mode, W, H, MW, MH, te word, n, geometry, kpoke, rgn knob, held)   triangle: default | full | line | point
F4 = ("full", "4x")


def a4x(w, h, mw, mh, held=False):
    return F4 + (w, h, mw, mh, 0xE0000000, 1, None, (), 0, held)


PLAN = {
    "s0-1x-1024x768": ("default", "1x", 1024, 768, 1024, 768, None, 1, None, (), 0, False),
    "s0-4x-288x144": a4x(288, 144, 288, 144),
    "s0-4x-1024x768": a4x(1024, 768, 1024, 768),
    "a4-1024x768-max2048x1024": a4x(1024, 768, 2048, 1024),
    "a1-1024x1280": a4x(1024, 1280, 1024, 1280),
    "a1r-1024x1280": a4x(1024, 1280, 1024, 1280),
    "a12-992x1280": a4x(992, 1280, 992, 1280),
    "a13-512x1536": a4x(512, 1536, 512, 1536),
    "a8-1024x1024-max1024x1280": a4x(1024, 1024, 1024, 1280),
    "a9-1024x800-max1024x1280": a4x(1024, 800, 1024, 1280),
    "a2-1024x1296": a4x(1024, 1296, 1024, 1296),
    "a3-1040x1280": a4x(1040, 1280, 1040, 1280),
    "a5-1024x800-max2048x1024": a4x(1024, 800, 2048, 1024),
    "a14-1024x1536": a4x(1024, 1536, 1024, 1536),
    "h1-1024x800-held": a4x(1024, 800, 1024, 800, held=True),
    "h2-1280x768-held": a4x(1280, 768, 1280, 768, held=True),
    "t8-ctl-te40-1array": ("full", "1x", 64, 64, 64, 64, 0x40000000, 1, None, (), 1, False),
    "t5-line-tec0": ("line", "1x", 64, 64, 64, 64, 0xC0000000, 1, None, (), 1, False),
    "t6-point-tec0": ("point", "1x", 64, 64, 64, 64, 0xC0000000, 1, None, (), 1, False),
    "t7-tri-te40-poke11": ("full", "1x", 64, 64, 64, 64, 0x40000000, 2, 1, ("2:par:11=0x00000001",), 1, False),
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
    return (tri, mode, a["w"], a["h"], a["mw"], a["mh"], te, a["n"], a["geometry"], tuple(a["kpoke"]), 1 if "rgn:1" in k else 0, "held" in k)


seen = set()
for st in open(os.path.join(KP, "stages.txt")).read().split():
    for row in WD.table(st):
        seen.add(row["name"])
        want = PLAN.get(row["name"])
        got = from_argv(row["args"], row["knobs"])
        check(want == got, "argv twin %s/%s: %s" % (st, row["name"], got if want == got else "%s, the plan says %s" % (got, want)))
check(seen == set(PLAN), "every plan row is a table row and every table row a plan row (%d)" % len(PLAN))

# the test can fail
o2r4 = [ln.split("|", 5) for ln in open(os.path.join(R4, "tables", "o.txt")) if ln.startswith("o2-")][0]
check(from_argv(o2r4[5], "expectdiff")[0] == "default" and from_argv(o2r4[5], "expectdiff") != PLAN["s0-4x-1024x768"],
      "must fail: round 4's o2 (the default triangle) in a full-triangle row")
a8 = [r for r in WD.table("a") if r["name"].startswith("a8-")][0]
check(from_argv(a8["args"].replace("--max-height 1280", "--max-height 1024"), a8["knobs"]) != PLAN[a8["name"]],
      "must fail: a8's command on its own size (the maximum dropped: the row would test nothing H-TPM says)")
t5 = [r for r in WD.table("t") if r["name"] == "t5-line-tec0"][0]
check(from_argv(t5["args"], "-") != PLAN["t5-line-tec0"], "must fail: t5 without its rgn:1 knob")
t7 = [r for r in WD.table("t") if r["name"] == "t7-tri-te40-poke11"][0]
check(from_argv(t7["args"].replace("--kpoke-render 2:par:11=0x00000001 ", ""), t7["knobs"]) != PLAN["t7-tri-te40-poke11"], "must fail: t7 without its poke")
check(from_argv(t7["args"].replace("-n 2 --geometry 1 ", ""), t7["knobs"]) != PLAN["t7-tri-te40-poke11"], "must fail: t7 as one render (the poke would land nowhere)")
h1 = [r for r in WD.table("a") if r["name"].startswith("h1-")][0]
check(from_argv(h1["args"], h1["knobs"].replace("held", "")) != PLAN[h1["name"]], "must fail: h1 without its held flow")

# the scene twin on the controls
tb = TW.table()
P = L.load_predictions("s0.tsv", KP)
rows = [(row["name"], row["args"], row["knobs"], L.pred_or(P, row["name"], "pb_used"), row["set"], False) for row in WD.table("s0")]
pr = TW.check(rows, tb)
check(not pr, "scene twins: no s0 control has a need its kept twins contradict%s" % ("" if not pr else ": " + "; ".join(pr)))
pr4 = TW.check([("o2-1x-1024x768-p82", o2r4[5], o2r4[3], 97, "control", False)], tb)
check(any(p.startswith("o2-1x-1024x768-p82: frozen need 97") for p in pr4), "REGRESSION: the twin check fails round 4's o2 (97 frozen, its twins say 19)")
sys.exit(bad)
