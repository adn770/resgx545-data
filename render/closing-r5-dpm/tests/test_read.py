#!/usr/bin/env python3
"""test_read.py: run/r5read.py (the ONE reader of the runner and the scorer) on REAL kept records.
  1. the twin: on every kept DPM job of R3-geo (g-c4, g-c5, g-c6, g-c7, g-d36), R2-geo (g-c3, g-c2) and R3-geo-c (g-qf) the reading
     equals R3-geo's frozen score/dpm3.py (nparts, thr0, reach, valid, knob, need, class): the rules are R1's, unchanged;
  2. the step rule on the kept calibrations (c3-2048-0x162, k-1500-0x3de, c5a-cal, c5b-cal, c5c-cal) gives section 1's table, and the
     rule max(a, b - 1) is needed (the count before the step alone misses c5b-cal's S2, b - 1 alone misses f-1350-0x36e's S2);
  3. the grow: c4-b3 is the only grow of every kept timeline with 0x072c (196 jobs);
  4. the pages left by the first partial render on g-c4 (raised cells 2, silent cells below S4 1, above S4 2);
  5. the CLI runs under the laptop's interpreter rules (python3 -I, stdlib only) and prints the line the runner's `field` reads.
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
import r5read as R  # noqa: E402
import r5plan as P  # noqa: E402
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
            print(f"  differs: {st}/{name}: r5read {[r[x] for x in ('nparts','thr0','valid','knob','need','cls')]} dpm3 "
                  f"{[j[x] for x in ('nparts','thr0','valid','knob','need')]} {dpm3.cls_of(j)}")
check(n >= 100 and bad == 0, f"r5read = R3-geo's dpm3 on {n - bad} of {n} kept DPM jobs (nparts, thr0, reach, valid, knob, need, class)")

check(not tl_bad, f"the plan's second raise clause (0x0624 above thr0 after the first resume) agrees with dword 38 on every valid job {tl_bad}")

# 2. the step rule on the kept calibrations
CALS = {(2048, 2048): DATA / "closing-r2-geo/out/g-c3/c3-2048-0x162.txt.gz", (4096, 4096): DATA / "closing-r2-geo/out/g-c2/k-1500-0x3de.txt.gz",
        (4096, 2048): DATA / "closing-r3-geo/out/g-c5/c5a-cal.txt.gz", (2048, 4096): DATA / "closing-r3-geo/out/g-c5/c5b-cal.txt.gz",
        (3072, 3072): DATA / "closing-r3-geo/out/g-c5/c5c-cal.txt.gz"}
for wh, p in CALS.items():
    r = R.reading(gz(p).decode(errors="replace"))
    got = {k: v for k, v in r["S"].items() if k in P.STEPS[wh]}
    check(got == P.STEPS[wh] and r["mono"], f"{p.name}: steps {dict((k, hex(v)) for k, v in got.items())} = section 1's table at {wh[0]}x{wh[1]}, monotone")
r = R.reading(gz(CALS[(2048, 4096)]).decode(errors="replace"))
check(r["steps"][2] == (0x99, 0x9b) and r["amb"][2], "c5b-cal's step 2 is seen between 0x99 and 0x9b (ambiguous): max(a, b - 1) = 0x9a, a alone = 0x99")
f = DATA / "closing-r1-pixgeo/out/g-c1/f-1350-0x36e.txt.gz"
if f.exists():
    r = R.reading(gz(f).decode(errors="replace"))
    check(r["steps"][2] == (0x125, 0x125) and r["S"][2] == 0x125, "f-1350-0x36e's step 2 seen with the count unchanged (0x125, 0x125]: b - 1 alone = 0x124, the rule 0x125")

# 3. the grow
grows, nj = [], 0
for p in sorted(glob.glob(str(DATA / "closing-*/out/*/*.txt.gz"))):
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
check(grows == ["g-c4/c4-b3.txt.gz"] and nj >= 150, f"c4-b3 is the only grow of {nj} kept timelines with 0x072c: {grows}")

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
o = subprocess.run(["python3", "-I", str(KP / "run/r5read.py"), "line", str(tmp / "c4-b3.out"), str(tmp / "c4-b3.buf09")], capture_output=True, text=True)
check(o.returncode == 0 and "cls=N" in o.stdout and "grow=1" in o.stdout and "knob=0xe8" in o.stdout and "S4=0xe8" not in o.stdout
      and "S3=0x9d" in o.stdout, f"python3 -I r5read.py line (stdlib only): {o.stdout.strip()[:150]}")
o = subprocess.run(["python3", "-I", str(KP / "run/r5read.py"), "kept", "x", "page"], capture_output=True, text=True)
check(o.stdout.strip() == "x.page.json.gz", "r5read.py kept NAME page = NAME.page.json.gz (the one name function)")
src = (KP / "run/r5read.py").read_text()
imports = sorted({ln.split()[1].split(".")[0] for ln in src.splitlines() if ln.startswith(("import ", "from ")) and "__future__" not in ln})
check(set(imports) <= {"struct", "sys"}, f"r5read.py imports only the standard library: {imports}")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
