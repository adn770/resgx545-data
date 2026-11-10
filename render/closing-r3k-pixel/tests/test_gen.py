#!/usr/bin/env python3
"""Generator tests of R3K-pixel: job counts, order (fault rows last in their stages, bif last of the session), the knobs of every
row, the frozen layout sizes against closing3/kernel/layout_f4.out, the pokes of p3 against the landed twin, the predictions of every
row, and that regenerating changes nothing.  Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import klib as L  # noqa: E402
import kgen as G  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("ok   %s" % name)
    else:
        fails += 1
        print("FAIL %s %s" % (name, detail))


def rows(st):
    return [ln.split("|", 5) for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines() if ln and not ln.startswith("#")]


def preds(st):
    return [ln.split("\t") for ln in open(os.path.join(KP, "predictions", st + ".tsv")).read().splitlines()[1:]]


check("stages.txt order: k-f4, k-pb0, k-pb, k-bif (the riskiest stage last)", open(os.path.join(KP, "stages.txt")).read().split() == ["k-f4", "k-pb0", "k-pb", "k-bif"])
check("conditional.txt is empty (no conditional stage)", open(os.path.join(KP, "conditional.txt")).read().strip() == "")
n = {st: len(rows(st)) for st in ("k-f4", "k-pb0", "k-pb", "k-bif")}
check("jobs: 11 + 3 + 5 + 5 = 24 (design: ~24 jobs: f4 11, pb 8 with the dump run, bif 5)", n == {"k-f4": 11, "k-pb0": 3, "k-pb": 5, "k-bif": 5}, n)
f4 = rows("k-f4")
check("k-f4: the held fault row c1 is last; every other row completes", f4[-1][0].startswith("c1") and "held" in f4[-1][3] and all("held" not in r[3] for r in f4[:-1]))
check("k-f4: render_rgn_arrays 4 only on c2 and the eight held-out rows (R3-K6: default 1 for everything else), 1 on c1 and c3",
      [r[0] for r in f4 if "rgn:4" in r[3].split()] == ["c2-64x64-k4"] + [x[0] for x in G.F4_HELD] and all("rgn:1" in r[3].split() for r in f4 if r[0].startswith(("c1", "c3"))))
check("k-f4: the held-out sizes are the design's (288x144 256x288 384x384 320x160 512x384 640x480 320x400 1024x768)",
      [(w, h) for _, w, h in G.F4_HELD] == [(288, 144), (256, 288), (384, 384), (320, 160), (512, 384), (640, 480), (320, 400), (1024, 768)])
out = open(os.path.join(KP, "..", "kernel", "layout_f4.out")).read()
sizes = [int(m, 16) for m in re.findall(r"knob 4: size\s+(0x[0-9a-f]+)", out)]
check("the frozen f=4 sizes of h1-h7 agree with layout_f4.out (0x8000 0x8000 0xb000 0x8000 0xb000 0x13000 0xc000) and h8 0x1e000",
      [G.F4_SIZES[x[0]] for x in G.F4_HELD][:6] == [0x8000, 0x8000, 0xb000, 0x8000, 0xb000, 0x13000] and G.F4_SIZES["h7-320x400-k4"] == 0xc000
      and G.F4_SIZES["h8-1024x768-k4"] == 0x1e000 and 0x8000 in sizes and 0x13000 in sizes and 0xc000 in sizes)
check("klib.layout(w, h, 4) gives those sizes, f = 1 gives E729's / E788's (0x6000, 0xa000 for 320x400 at max 544)",
      all(L.layout(w, h, 4)["size"] == G.F4_SIZES[nm] for nm, w, h in G.F4_HELD) and L.layout(288, 144)["size"] == 0x6000 and L.layout(544, 400)["size"] == 0xa000)
check("every k-f4 row but c1 has expectdiff, --keep-going, the e0 sample words and a dump", all("expectdiff" in r[3] and "--keep-going" in r[5] and "cmd:1=0xe0000000" in r[5] and "--dump-render" in r[5] for r in f4))
check("k-f4: the h rows are a hypothesis group (a fault is measured, two end the rows); c1 is its own group of 1",
      all("hypo:h4:2" in r[3] for r in f4 if r[0].startswith("h")) and "hypo:c1:1" in f4[-1][3])
check("k-f4: only h8 carries --keep-overflow", [r[0] for r in f4 if "--keep-overflow" in r[5]] == ["h8-1024x768-k4"])
P = preds("k-f4")
check("k-f4 predictions: every row has its frozen quantities (outcome; diff, echo, TA data size, arrays for the completing ones)",
      all(any(p[0] == r[0] and p[1] == "outcome" for p in P) for r in f4) and all(any(p[0] == r[0] and p[1] == "tadata_size" for p in P) for r in f4[:-1]))
check("k-f4 predictions: c1 is 0x90004 at page 0x20006 (E729)", ("c1-288x144-k1", "fault_word", "0x90004") in [tuple(p[:3]) for p in P] and ("c1-288x144-k1", "fault_page", "0x20006") in [tuple(p[:3]) for p in P])
check("k-f4 predictions: the knob proof (TA data size of knob 1) is frozen beside every h row", sum(1 for p in P if p[1] == "tadata_size_if_knob_1") == 8)
pb0, pb = rows("k-pb0"), rows("k-pb")
check("k-pb0: the dump run, p0 (TE 0x60) and p1 (TE 0x40), split flow -n 2 --geometry 1, 64x64, mode 2",
      [r[0] for r in pb0] == ["pb-d0-te40", "pb-p0-te60", "pb-p1-te40"] and all("-n 2 --geometry 1" in r[5] and "cmd:13=0x80000002" in r[5] and "--width 64" in r[5] for r in pb0)
      and "cmd:1=0x60000000" in pb0[1][5] and "cmd:1=0x40000000" in pb0[0][5] and "cmd:1=0x40000000" in pb0[2][5])
check("k-pb0 rows carry no poke into the buffer", all("--kpoke-render" not in r[5] for r in pb0))
check("k-pb: p2, p3 x2, p4 x2 in that order; TE 0x40; pokes only as 2:par:INDEX=0xVALUE", [r[0] for r in pb] == ["pb-p2-own11", "pb-p3a-twin", "pb-p3b-twin", "pb-p4a-ffff", "pb-p4b-ffff"]
      and all("cmd:1=0x40000000" in r[5] for r in pb) and all(re.fullmatch(r"2:par:\d+=0x[0-9a-f]+", x) for r in pb for x in re.findall(r"--kpoke-render (\S+)", r[5])))
own, twin = G.pb_words()
p3 = {int(a): int(b, 16) for a, b in re.findall(r"--kpoke-render 2:par:(\d+)=(0x[0-9a-f]+)", pb[1][5])}
check("p3 pokes the landed twin's dwords 11-26 (16 pokes: the tool's and the kernel's limit are 16), p3b the same, p2 dword 11's own value, p4 dword 11 = 0xffffffff",
      p3 == {i: twin[i] for i in range(11, 27)} and len(p3) == 16 and pb[2][5] == pb[1][5].replace("p3a", "p3b") and "par:11=0x%08x" % own[11] in pb[0][5] and "par:11=0xffffffff" in pb[3][5])
check("E728's relation holds in the landed words the pokes come from: own[i+1] = twin[i] for 11..25; twin words differ from own only in 11-26",
      all(own[i + 1] == twin[i] for i in range(11, 26)) and [i for i in range(27) if own[i] != twin[i]] == [11, 12] + list(range(16, 27)))
check("the stream words 04000004 00030001 04000000 are dwords 0-2 of both landed dumps (par's index is the dword index)", [own[i] for i in range(3)] == [0x04000004, 0x00030001, 0x04000000] == [twin[i] for i in range(3)])
P = preds("k-pb")
check("k-pb predictions cover the dump run, p0, p1, p2, p3 x2 and p4 x2 (the controls are frozen from E728 and the landed twin)",
      {p[0] for p in P} == {"pb-d0-te40", "pb-p0-te60", "pb-p1-te40", "pb-p2-own11", "pb-p3a-twin", "pb-p3b-twin", "pb-p4a-ffff", "pb-p4b-ffff"})
check("... with both hypotheses frozen for p3 and p4", {(p[0], p[3]) for p in P if p[0] in ("pb-p3a-twin", "pb-p4a-ffff")} >= {("pb-p3a-twin", "H-OLD"), ("pb-p3a-twin", "H-FIELD"), ("pb-p4a-ffff", "H-OLD"), ("pb-p4a-ffff", "H-FIELD")})
bif = rows("k-bif")
check("k-bif: n0 (idle), f1, f1r, f2, f3 in that order, f3 (the texture fault) last", [r[0] for r in bif] == ["n0-idle", "f1-ta-read", "f1r-ta-read", "f2-ta-write", "f3-tex"])
check("k-bif: n0 is idle with the bif knob, the four others held with the bif knob in one hypothesis group of 4",
      "idle" in bif[0][3] and "bif" in bif[0][3] and all("held" in r[3] and "bif" in r[3].split() and "hypo:bif:4" in r[3] for r in bif[1:]))
check("k-bif f2 is E788's a6 command at knob 1; f1 is E444's `tri --fault`; f3 is S3's texture probe (d-L2e2-16)",
      "rgn:1" in bif[3][3] and "--max-width 320 --max-height 400" in bif[3][5] and bif[1][5].startswith("tri --fault") and "--scratch-pages 16" in bif[4][5] and "s1d-tw64x64-l2e2__0.bin" in bif[4][5])
P = preds("k-bif")
check("k-bif predictions: the three hypotheses frozen per fault row (cleared after step 2 and 3), the control that can fail, the reset lines",
      all({(p[3]) for p in P if p[0] == f and p[1] == "cleared_after2"} == {"H-W1C", "H-CLR", "H-RST"} for f in ("f1-ta-read", "f2-ta-write", "f3-tex"))
      and any(p[1] == "cleared_after1" for p in P) and any(p[1] == "reset_halt_int_stat" for p in P))
check("the hypotheses are distinguishable by the two writes: W1C (yes, yes), CLR (no, yes), RST (no, no)", G.BIF_H == {"H-W1C": ("yes", "yes"), "H-CLR": ("no", "yes"), "H-RST": ("no", "no")})
for st in ("k-f4", "k-pb0", "k-pb", "k-bif"):
    t = rows(st)
    check("%s: every tri row has expectdiff and --keep-going (the runner refuses otherwise); the whole table has 6 fields" % st,
          all(len(r) == 6 for r in t) and all(("expectdiff" in r[3] and "--keep-going" in r[5]) for r in t if r[5].startswith("tri ") and r[0] != "f1-ta-read" and r[0] != "f1r-ta-read")
          and all("--keep-going" in r[5] for r in t if r[5].startswith("tri ")))
check("k-bif f1 and f1r (tri --fault) are tri rows: they must carry expectdiff too (runner rule)", all("expectdiff" in r[3] for r in rows("k-bif") if r[5].startswith("tri ")))
before = {f: hashlib.sha256(open(os.path.join(KP, f), "rb").read()).hexdigest() for f in
          ["tables/k-f4.txt", "tables/k-pb0.txt", "tables/k-pb.txt", "tables/k-bif.txt", "predictions/k-f4.tsv", "predictions/k-pb.tsv", "predictions/k-bif.tsv", "TABLES.md", "stages.txt"]}
subprocess.run([sys.executable, os.path.join(KP, "gen", "kgen.py")], capture_output=True, check=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
after = {f: hashlib.sha256(open(os.path.join(KP, f), "rb").read()).hexdigest() for f in before}
check("regenerating changes nothing (the generator is deterministic)", before == after, [f for f in before if before[f] != after[f]])
sys.exit(1 if fails else 0)
