#!/usr/bin/env python3
"""test_twin.py: the argv-twin test (round 6 rule: round 4's o2 control ran the default triangle where its plan row said the full
one).  Every row's COMMAND is parsed back into what it runs (tool, size, stride, pokes, ramp, depth words, kpokes, 4x options) and
compared with the plan row TYPED HERE BY HAND from closing6/rank/rank-round6.md section 1 and 2 (R6-1, R6-2, R6-4: session A), not
from gen/; each control is compared token for token with the kept command of the record it repeats (E876's sweep, E831's g-z
control, E824's / round 5's s0 4x row).
  python3 tests/test_twin.py
"""
import os
import re
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
DATA = "/Users/jtorra/src/resgx545-data"
bad = n = 0


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


def rows(st):
    out = []
    for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if ln and not ln.startswith("#"):
            name, sset, risk, knobs, tool, args = ln.split("|", 5)
            out.append(dict(name=name, set=sset, knobs=knobs.split(), tool=tool, argv=shlex.split(args.replace("$W", "W"))))
    return out


def opt(a, k, cast=str):
    return cast(a[a.index(k) + 1]) if k in a else None


def opts(a, k):
    return [a[i + 1] for i, t in enumerate(a) if t == k]


# ---- q289: typed from R6-1 ("128 x 64 fill, x pokes ^0x8 .. ^0x40 (8) and y pokes ^0x1000 .. ^0x8000 (8), 256 x 32 x pokes ^0x10,
# ^0x18, ^0x30, ^0x50, baseline at each size (2) and a repeat of the 64 x 32 ^0x10 case")
PLAN_Q289 = [(64, 32, 0x10, "control"), (128, 64, None, "control"), (256, 32, None, "control"),
             (128, 64, 0x8, "heldout"), (128, 64, 0x10, "heldout"), (128, 64, 0x18, "heldout"), (128, 64, 0x20, "heldout"),
             (128, 64, 0x28, "heldout"), (128, 64, 0x30, "heldout"), (128, 64, 0x38, "heldout"), (128, 64, 0x40, "heldout"),
             (128, 64, 0x1000, "heldout"), (128, 64, 0x2000, "heldout"), (128, 64, 0x3000, "heldout"), (128, 64, 0x4000, "heldout"),
             (128, 64, 0x5000, "heldout"), (128, 64, 0x6000, "heldout"), (128, 64, 0x7000, "heldout"), (128, 64, 0x8000, "heldout"),
             (256, 32, 0x10, "heldout"), (256, 32, 0x18, "heldout"), (256, 32, 0x30, "heldout"), (256, 32, 0x50, "heldout")]
R = rows("q289")
check(len(R) == len(PLAN_Q289) == 23, "q289: 23 rows, as the plan (%d)" % len(R))
got = []
for r in R:
    a = r["argv"]
    pk = opt(a, "--poke")
    v = int(re.match(r"pds:pixev:12\^=(0x[0-9a-f]+)$", pk).group(1), 16) if pk else None
    w, h, s = opt(a, "--width", int), opt(a, "--height", int), opt(a, "--stride", int)
    check(a[0] == "fill" and r["tool"] == "t4" and s == 4 * w and len(opts(a, "--poke")) <= 1 and {"expectdiff", "needhash"} <= set(r["knobs"]),
          "q289/%s: fill with t4, stride 4 W (%s), one poke at most, expectdiff needhash" % (r["name"], s))
    got.append((w, h, v, r["set"]))
check(sorted(got, key=str) == sorted(PLAN_Q289, key=str), "q289: every row's (size, poke, set) is a plan row and every plan row is there")
# the control is E876's kept case: the default fill (64 x 32, stride 256) with the same poke
e876 = [ln for ln in open(DATA + "/pds/end-of-tile/values-doutu1-x/raw.txt") if "fill --poke 'pds:pixev:12^=0x10'" in ln]
ctl = [r for r in R if r["name"] == "f-ctl-64x32-x10"][0]["argv"]
check(len(e876) == 1 and shlex.split(e876[0].split(" -- ")[1])[1:] == ["fill", "--poke", "pds:pixev:12^=0x10"]
      and ctl == ["fill", "--width", "64", "--height", "32", "--stride", "256", "--poke", "pds:pixev:12^=0x10"],
      "q289: the control is E876's kept command with the tool's defaults (64 x 32, stride 256) written out")

# ---- q287: typed from R6-2 ("W 34: fit H 19; held out H 7, 11, 23, 35; confirmations H 17, 21; control 34 x 18 (E831's exact
# set); two runs each" + "a dry 34 x 17 job first") and this build's x-ramp replicates (README.md, Deviations)
PAGES = {7: 17, 11: 17, 17: 18, 18: 18, 19: 18, 21: 18, 23: 18, 35: 19}     # r3_geo.depth_pages(34, H), worked by hand
PLAN_Q287 = [("gate", 17, "y", "t6"), ("control", 18, "y", "t4"), ("control", 18, "y", "t6"), ("control", 18, "x", "t6"),
             ("fit", 19, "y", "t6"), ("fit", 19, "y", "t6"),
             ("heldout", 7, "y", "t6"), ("heldout", 7, "y", "t6"), ("heldout", 11, "y", "t6"), ("heldout", 11, "y", "t6"),
             ("heldout", 23, "y", "t6"), ("heldout", 23, "y", "t6"), ("heldout", 35, "y", "t6"), ("heldout", 35, "y", "t6"),
             ("heldout", 19, "x", "t6"), ("heldout", 23, "x", "t6"), ("heldout", 35, "x", "t6"),
             ("confirm", 17, "y", "t6"), ("confirm", 21, "y", "t6"), ("confirm", 21, "y", "t6")]
R = rows("q287")
got = []
for r in R:
    a = r["argv"]
    w, h = opt(a, "--width", int), opt(a, "--height", int)
    ramp = {"0.25,0.75,0.25": "x", "0.25,0.25,0.75": "y"}.get(opt(a, "--tri-z"))
    check(a[0] == "tri" and w == 34 and "--tri-full" in a and "--depth" in a and opt(a, "--depth-ctl") == "0x17100c"
          and opt(a, "--depth-fill") == "0xdeadbeef" and opt(a, "--depth-pages", int) == PAGES[h] and opt(a, "--depth-dump") == "W/depth"
          and opts(a, "--poke") == ["blk:1=0x00400200"] and "expectdiff" in r["knobs"] and (h % 2 == 0 or r["tool"] == "t6"),
          "q287/%s: 34 x %d, ramp %s, %s, depth words and pages (%d) as E831's recipe; an odd height never with t4" % (r["name"], h, ramp, r["tool"], PAGES[h]))
    got.append((r["set"], h, ramp, r["tool"]))
check(sorted(got) == sorted(PLAN_Q287), "q287: every row's (set, height, ramp, tool) is a plan row and every plan row is there (%d)" % len(R))
check(R[0]["name"] == "z-dry-34x17-y" and "gateodd" in R[0]["knobs"], "q287: the dry 34 x 17 job is first and carries gateodd")
e831 = {ln.split("\t")[0]: shlex.split(ln.split("\t")[7].replace("$W", "W"))
        for ln in open(DATA + "/render/closing-r3-geo-c/out/g-z/cases.tsv").read().splitlines()[1:]}
for mine, theirs in (("z-ctl-34x18-y-t4", "z-ctl-34x18-y"), ("z-ctl-34x18-y-t6", "z-ctl-34x18-y"), ("z-ctl-34x18-x-t6", "z-ctl-34x18-x")):
    check([r for r in R if r["name"] == mine][0]["argv"] == e831[theirs], "q287: %s is E831's kept %s token for token" % (mine, theirs))

# ---- q086: E511's 20 skipped cases + the safe script's 1024 x 768 R, words from E511's own script (read here with its own regex)
cases = {}
for ln in open(DATA + "/ta/mtile-msaa-risky/scripts/mtile-msaa-risky.sh"):
    m = re.match(r"^(q086-\d+x\d+-\w+)\|(\w+)\|(\d+)\|(\d+)\|(.*)$", ln.rstrip("\n"))
    if m:
        cases[m.group(1)] = (int(m.group(3)), int(m.group(4)), sorted(re.findall(r"--kpoke-render (1:ta:\d+=0x[0-9a-f]+)", m.group(5))))
skipped = [ln.split("\t")[0] for ln in open(DATA + "/ta/mtile-msaa-risky/skipped.tsv") if ln.strip()]
R = rows("q086")
check(len(R) == 21 and R[0]["name"] == "q086-1024x768-R" and sorted(r["name"] for r in R[1:]) == sorted(skipped),
      "q086: the control R first, then exactly E511's 20 skipped cases")
fam = [r["name"].rsplit("-", 1)[1] for r in R[1:]]
check(fam == sorted(fam, key=lambda f: {"U2": 0, "U2Q": 0, "FX": 1, "HS": 2}[f]), "q086: U2/U2Q, then FX, then HS last (the plan: HS last)")
s0 = [ln.split("|", 5)[5] for ln in open(DATA + "/render/closing-r5-render4x/tables/s0.txt") if ln.startswith("s0-4x-1024x768|")][0]
s0 = shlex.split(s0.replace("$W", "W"))
FOURX = ["--aa4", "--tri-full", "cmd:1=0xe0000000", "cmd:10=0xeaa26e26", "cmd:13=0x80000002", "cmd:16=0xeaa26e26"]
for r in R:
    a = r["argv"]
    w, h = opt(a, "--width", int), opt(a, "--height", int)
    kps = sorted(opts(a, "--kpoke-render"))
    want = cases.get(r["name"], (1024, 768, []))
    grp = {"U2": "u", "U2Q": "u", "FX": "fx", "HS": "hs", "R": None}[r["name"].rsplit("-", 1)[1]]
    hyp = [k for k in r["knobs"] if k.startswith("hypo:")]
    check(a[0] == "tri" and r["tool"] == "t4" and (w, h) == want[:2] and (opt(a, "--max-width", int), opt(a, "--max-height", int)) == (w, h)
          and kps == want[2] and all(t in a for t in FOURX) and "--pixels" in a and {"expectdiff", "strict"} <= set(r["knobs"])
          and (hyp == [] if grp is None else hyp == ["hypo:%s:%d" % (grp, {"u": 1, "fx": 1, "hs": 2}[grp])]),
          "q086/%s: %d x %d on a 4x context of its size, kpokes %s = E511's, group %s" % (r["name"], w, h, " ".join(kps) or "none", grp))
r0 = R[0]["argv"]
check(all(t in s0 for t in FOURX) and opt(s0, "--width") == opt(r0, "--width") and opt(s0, "--max-height") == opt(r0, "--max-height"),
      "q086: R's 4x options are round 5's s0-4x-1024x768 (E824 h8's shape) on the same target and context")
print("%d of %d twin checks" % (n - bad, n))
sys.exit(1 if bad else 0)
