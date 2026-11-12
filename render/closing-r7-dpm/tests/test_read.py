#!/usr/bin/env python3
"""test_read.py: run/r7read.py (the ONE reader of the runner and the scorer; R6-dpm's r6read.py with round 7's additions) on REAL
kept records (the corpus up to R5-dpm, as R6-dpm froze it, and R6-dpm's kept jobs where named).
  1. the twin: on every kept DPM job of R3-geo (g-c4, g-c5, g-c6, g-c7, g-d36), R2-geo (g-c3, g-c2) and R3-geo-c (g-qf) the reading
     equals R3-geo's frozen score/dpm3.py (nparts, thr0, reach, valid, knob, need, class): the rules are R1's, unchanged;
  2. the step rule on the kept calibrations (c3-2048-0x162, k-1500-0x3de, c5a-cal, c5b-cal, c5c-cal) gives section 1's table, and the
     rule max(a, b - 1) is needed (the count before the step alone misses c5b-cal's S2, b - 1 alone misses f-1350-0x36e's S2);
  3. the grow: every kept grow (c4-b3 and R5-dpm's 20) is at a step cell, 21 in all (E874's count);
  4. the pages left by the first partial render on g-c4 (raised cells 2, silent cells below S4 1, above S4 2);
  5. the CLI runs under the laptop's interpreter rules (python3 -I, stdlib only) and prints the line the runner's `field` reads;
  6. round 6: the brackets = F1's (f1_brackets.brackets, E873) on every kept step of every kept job; the timeline burst ends of the
     reference job = f4_phase.out; the run peaks = F7's (f7_replay.kept) on every kept one-triangle job; `model` accepts the 2048x2048
     calibrations against the frozen model and REFUSES c5b-cal against the model's 2048x4096 steps (E874's one miss, S3 0x129 against
     0x12c): the check that re-picks s-m's cells can fail;
  7. round 7: the 2048x4096 steps of the kept calibrations are KEPT_2X4 (the creep cell's scene reference); H-WALK64 places every block
     of the kept u-2048 dump (r1-pixgeo, G1's fit dump) through the scorer's reader and row order does not; the ring reading of R6-dpm's
     kept r-k pages (oomring: no page-count words) gives ring_counts 0, so s-k's premise fails on real pages without oomring2's words;
     the runner's line carries runpeaks and leaves need `-` for a job that took a partial render.
"""
import gzip
import os
import pathlib
import subprocess
import sys
import glob

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
R3 = pathlib.Path("/Users/jtorra/src/scratch/resgx545/closing3/r3-geo/score")
sys.path[:0] = [str(KP / "run"), str(KP / "gen"), str(R3)]
import r7read as R  # noqa: E402
import r7plan as P  # noqa: E402
import dpm3  # noqa: E402
from r1lib import Kept  # noqa: E402

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/render")
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


def gz(p):
    return gzip.open(p).read() if p.exists() else None


# 1. the twin
n = bad = 0
tl_bad = []
for ds, st in [("closing-r3-geo", s) for s in ("g-c4", "g-c5", "g-c6", "g-c7", "g-d36")] + [("closing-r2-geo", "g-c3"), ("closing-r2-geo", "g-c2"),
                                                                                         ("closing-r3-geo-c", "g-qf")]:
    d = DATA / ds / "out" / st
    k = Kept(str(d))
    for name in k.names():
        j = dpm3.read_job(k, name, knob_proof=False)
        if j.get("void"):
            continue
        r = R.reading(gz(d / f"{name}.txt.gz").decode(errors="replace"), gz(d / f"{name}.after.buf09.bin.gz"))
        n += 1
        if r["cls"] != "V" and r["raise_tl"] != (r["cls"] == "R"):
            tl_bad.append(f"{st}/{name}")
        same = all(r[x] == j[x] for x in ("nparts", "thr0", "reach", "valid", "knob", "need")) and r["cls"] == dpm3.cls_of(j)
        if not same:
            bad += 1
            print(f"  differs: {st}/{name}: r7read {[r[x] for x in ('nparts','thr0','valid','knob','need','cls')]} dpm3 "
                  f"{[j[x] for x in ('nparts','thr0','valid','knob','need')]} {dpm3.cls_of(j)}")
check(n >= 100 and bad == 0, f"r7read = R3-geo's dpm3 on {n - bad} of {n} kept DPM jobs (nparts, thr0, reach, valid, knob, need, class)")

check(not tl_bad, f"the plan's second raise clause (0x0624 above thr0 after the first resume) agrees with dword 38 on every valid job {tl_bad}")

# 2. the step rule on the kept calibrations
CALS = {(2048, 2048): DATA / "closing-r2-geo/out/g-c3/c3-2048-0x162.txt.gz", (4096, 4096): DATA / "closing-r2-geo/out/g-c2/k-1500-0x3de.txt.gz",
        (4096, 2048): DATA / "closing-r3-geo/out/g-c5/c5a-cal.txt.gz", (2048, 4096): DATA / "closing-r3-geo/out/g-c5/c5b-cal.txt.gz",
        (3072, 3072): DATA / "closing-r3-geo/out/g-c5/c5c-cal.txt.gz"}
STEPS = {(2048, 2048): {2: 0x51, 3: 0x9d, 4: 0xe8, 5: 0x132}, (4096, 4096): {2: 0x125, 3: 0x240, 4: 0x35b},
         (4096, 2048): {2: 0x97, 3: 0x126, 4: 0x1b9}, (2048, 4096): {2: 0x9a, 3: 0x12c, 4: 0x1be, 5: 0x255},
         (3072, 3072): {2: 0xa9, 3: 0x14d, 4: 0x1ef, 5: 0x293}}            # E852's table
for wh, p in CALS.items():
    r = R.reading(gz(p).decode(errors="replace"))
    got = {k: v for k, v in r["S"].items() if k in STEPS[wh]}
    inb = all(r["iv"][k][0] <= v <= r["iv"][k][1] for k, v in STEPS[wh].items() if k in r["iv"])
    check(got == STEPS[wh] and r["mono"] and inb, f"{p.name}: steps {dict((k, hex(v)) for k, v in got.items())} = E852's table at {wh[0]}x{wh[1]}, in their brackets, monotone")
r = R.reading(gz(CALS[(2048, 4096)]).decode(errors="replace"))
check(r["steps"][2] == (0x99, 0x9b) and r["amb"][2], "c5b-cal's step 2 is seen between 0x99 and 0x9b (ambiguous): max(a, b - 1) = 0x9a, a alone = 0x99")
f = DATA / "closing-r1-pixgeo/out/g-c1/f-1350-0x36e.txt.gz"
if f.exists():
    r = R.reading(gz(f).decode(errors="replace"))
    check(r["steps"][2] == (0x125, 0x125) and r["S"][2] == 0x125, "f-1350-0x36e's step 2 seen with the count unchanged (0x125, 0x125]: b - 1 alone = 0x124, the rule 0x125")

# 3. the grow
grows, nj = [], 0
SESS = ("closing-r1-pixgeo", "closing-r2-geo", "closing-r2-pixel", "closing-r3-geo-c", "closing-r3-geo", "closing-r3-pixel", "closing-r3-rgn4",
        "closing-r3k-pixel", "closing-r3k-regress", "closing-r4-pixel", "closing-r4-q285", "closing-r4-render4x", "closing-r5-dpm",
        "closing-r5-pixel", "closing-r5-render4x", "closing-s1", "closing-s1b", "closing-s3")   # R6-dpm's data view (postrun/data-view.txt)
for p in sorted(x for s_ in SESS for x in glob.glob(str(DATA / s_ / "out/**/*.txt.gz"), recursive=True)):
    name = os.path.basename(p)[:-7]
    if "." in name:
        continue
    t = gzip.open(p, "rt", errors="replace").read()
    if "0x072c" not in t:
        continue
    r = R.reading(t)
    if r.get("void"):
        continue
    nj += 1
    if r["grow"]:
        grows.append(p.split("/out/")[1])
check(len(grows) == 21 and "g-c4/c4-b3.txt.gz" in grows and all(x.startswith(("g-c4/", "a2/")) for x in grows) and nj >= 250,
      f"{len(grows)} grows in {nj} kept timelines with 0x072c (c4-b3 and R5-dpm's 20; E874): {grows[:3]}...")

# 4. the pages left on g-c4
d = DATA / "closing-r3-geo/out/g-c4"
left = {}
for name in ("c4-b1", "c4-b2", "c4-b3", "c4-b4", "c4-b5", "c4-b6", "c3-2048-0xe2", "c3-2048-0x122"):
    r = R.reading(gz(d / f"{name}.txt.gz").decode(errors="replace"), gz(d / f"{name}.after.buf09.bin.gz"))
    left[name] = (r["cls"], r["gps_abort"], r["gps_left"])
check(left["c4-b5"] == ("R", 3, 2) and left["c4-b6"] == ("N", 3, 1) and left["c4-b4"] == ("N", 3, 1) and left["c4-b2"] == ("N", 4, 2)
      and left["c4-b3"] == ("N", 3, 2), f"g-c4 pages at the abort and left by the first partial render: {left}")

# 5. the CLI under the laptop's rules
tmp = KP / "debug" / "tmp"
tmp.mkdir(parents=True, exist_ok=True)
(tmp / "c4-b3.out").write_bytes(gz(d / "c4-b3.txt.gz"))
(tmp / "c4-b3.buf09").write_bytes(gz(d / "c4-b3.after.buf09.bin.gz"))
o = subprocess.run([sys.executable, "-I", str(KP / "run/r7read.py"), "line", str(tmp / "c4-b3.out"), str(tmp / "c4-b3.buf09")], capture_output=True, text=True)
check(o.returncode == 0 and "cls=N" in o.stdout and "grow=1" in o.stdout and "knob=0xe8" in o.stdout and "S4=0xe8" not in o.stdout
      and "S3=0x9d" in o.stdout, f"python3 -I r7read.py line (stdlib only): {o.stdout.strip()[:150]}")
o = subprocess.run([sys.executable, "-I", str(KP / "run/r7read.py"), "kept", "x", "page"], capture_output=True, text=True)
check(o.stdout.strip() == "x.page.json.gz", "r7read.py kept NAME page = NAME.page.json.gz (the one name function)")
src = (KP / "run/r7read.py").read_text()
imports = sorted({ln.split()[1].split(".")[0] for ln in src.splitlines() if ln.startswith(("import ", "from ")) and "__future__" not in ln})
check(set(imports) <= {"struct", "sys"}, f"r7read.py imports only the standard library: {imports}")
# 6. round 6
OFF = pathlib.Path("/Users/jtorra/src/resgx545-data/cited/closing6/dpm/offline")
import importlib  # noqa: E402
P.M()
sys.path.insert(0, str(OFF))
iv = importlib.import_module("f1_brackets").brackets()
byjob = {}
for (whs, sc, k), L in iv.items():
    for a, b, nm in L:
        byjob.setdefault(nm, {})[k] = (a, b)
nb = okb = 0
for nm, ks in byjob.items():
    sess, rest = nm.split("/", 1)
    pth = DATA / f"closing-{sess}" / "out" / f"{rest}.txt.gz"
    r = R.reading(gz(pth).decode(errors="replace"))
    for k, br in ks.items():
        nb += 1
        okb += r["iv"].get(k) == br
check(nb > 300 and okb == nb, f"r7read's brackets = F1's on {okb} of {nb} kept steps (E873)")
ref = R.reading(gz(DATA / "closing-r2-geo/out/g-c3/c3-2048-0x354.txt.gz").decode(errors="replace"))
check(ref["ends"] == {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x178, 6: 0x1c1, 7: 0x1cc}, f"the timeline burst ends of r2-geo c3-2048-0x354 = f4_phase.out's E: {ref['ends']}")
f7 = P.M().F7
kk = f7.kept()
okp = sum(1 for (s_, t0, n_, peaks, nm, side) in kk
          if R.reading(gz(DATA / f"closing-{nm.split('/')[0]}" / "out" / (nm.split('/', 1)[1] + ".txt.gz")).decode(errors="replace"))["runpeaks"] == peaks
          and R.reading(gz(DATA / f"closing-{nm.split('/')[0]}" / "out" / (nm.split('/', 1)[1] + ".txt.gz")).decode(errors="replace"))["nparts"] == n_)
check(len(kk) >= 50 and okp == len(kk), f"r7read's run peaks and counts = F7's reading on {okp} of {len(kk)} kept one-triangle jobs (E875)")
for p, model, want, what in ((DATA / "closing-r2-geo/out/g-c3/c3-2048-0x354.txt.gz", P.MODEL[(2048, 2048)][0], 0, "accepts c3-2048-0x354 (2048x2048)"),
                             (DATA / "closing-r3-geo/out/g-c5/c5b-cal.txt.gz", P.MODEL[(2048, 4096)][0], 1, "REFUSES c5b-cal against the 2048x4096 model (S3 0x129 vs 0x12c)")):
    (tmp / "m.out").write_bytes(gz(p))
    o = subprocess.run([sys.executable, "-I", str(KP / "run/r7read.py"), "model", str(tmp / "m.out"), ",".join(f"0x{model[k]:x}" for k in sorted(model))],
                       capture_output=True, text=True)
    check(o.returncode == want, f"r7read.py model {what}: rc {o.returncode} {o.stdout.strip()[:80]}")
o = subprocess.run([sys.executable, "-I", str(KP / "run/r7read.py"), "ends", str(tmp / "m.out")], capture_output=True, text=True)
check(o.returncode == 0 and o.stdout.split("\n")[0].split()[0] == "2", f"r7read.py ends (stdlib only) prints `k E` lines: {o.stdout.split(chr(10))[:2]}")
# 7. round 7
for p in (DATA / "closing-r3-geo/out/g-c5/c5b-cal.txt.gz", DATA / "closing-r5-dpm/out/a2/d-a2b/a2b-cal-2x4.txt.gz"):
    r = R.reading(gz(p).decode(errors="replace"))
    check({k: r["S"][k] for k in (2, 3, 4)} == P.KEPT_2X4, f"{p.name}: S2..S4 = KEPT_2X4 {dict((k, hex(v)) for k, v in P.KEPT_2X4.items())}")
sys.path.insert(0, str(KP / "score"))
import score_r7 as SC  # noqa: E402
u = DATA / "closing-r1-pixgeo/out/g-u1"
tmpd = tmp / "walk"
tmpd.mkdir(exist_ok=True)
import shutil  # noqa: E402
shutil.copy(u / "u-2048.tri.tadata.bin.gz", tmpd / "b-cal-s22.tri.tadata.bin.gz")
w64, wrow = SC.walk_reading(tmpd, "b-cal-s22", "tri --width 2048 --height 2048 -n 1")
check(w64 == "exact" and wrow != "exact", f"H-WALK64 through the scorer on the kept u-2048 dump (G1's fit): walk64 {w64}, row order {wrow}")
import json  # noqa: E402
K = DATA / "closing-r6-dpm/out/a2/r-k"
for n in ("k-b5", "k-b6"):
    o = R.ring_reading(json.loads(gz(K / f"{n}.page.json.gz"))["page"], gz(K / f"{n}.txt.gz").decode(errors="replace"))
    check(o["ring_counts"] is False and o["dec_sa8_380"] == (0x180 if n == "k-b5" else 0) and o["abort_gp"] == 0,
          f"R6-dpm's kept {n} (oomring): ring_counts 0 (no page-count words), dec_sa8_380 0x{o['dec_sa8_380']:x}: the premise can fail")
(tmp / "b5.out").write_bytes(gz(DATA / "closing-r3-geo/out/g-c4/c4-b5.txt.gz"))
o = subprocess.run([sys.executable, "-I", str(KP / "run/r7read.py"), "line", str(tmp / "b5.out")], capture_output=True, text=True)
check("need=-" in o.stdout and "runpeaks=0x" in o.stdout, f"the runner's line: need '-' after a partial render, runpeaks read: {o.stdout.strip()[-60:]}")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
