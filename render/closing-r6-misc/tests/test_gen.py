#!/usr/bin/env python3
"""test_gen.py: the generated tables and frozen predictions against the plan's own offline outputs and the kept records.
  - gen/m6gen.py is deterministic (a second run into a copy writes the same bytes) and the tables hold 23 + 20 + 21 = 64 jobs;
  - the byte copies gen/r3_geo.py and gen/rules1126.py are the published files (round 3's model, E511's rules), rules' selftest passes;
  - q289: the control's frozen hash is E876's (0x97334f75829dab25); the baselines' is the tool mock's (0xf7befd67a3c8e325, read off
    the rgn4 mock: tests/mock_all.py checks it again); every row's unwritten tiles under OR and ADD are the ranking's
    closing6/rank/q289_predict.out lines, and the rows it marks SEPARATES are the rows frozen as separating (8);
  - q287: the A / FLOOR separation per height is closing6/rank/q287_cells.out's; the controls freeze E831's 924;
  - q086: H-COV freezes 7 completions (R and the 6 U2/U2Q) and 14 faults (FX, HS); R's words at 1024 x 768 are the rule's
    (0x82010018, 0x03018024, 0x60: E331's sample in rules1126.selftest).
  python3 tests/test_gen.py
"""
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
RANK = "/Users/jtorra/src/scratch/resgx545/closing6/rank"
DATA = "/Users/jtorra/src/resgx545-data"
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402
bad = n = 0


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


def preds(st):
    P = {}
    for ln in open(os.path.join(KP, "predictions", st + ".tsv")).read().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        P.setdefault(c, {"set": s}).setdefault(q, {})[m] = v
    return P


T = tempfile.mkdtemp(prefix="gen.", dir=os.path.join(KP, "debug"))
for d in ("gen", "tables", "predictions"):
    shutil.copytree(os.path.join(KP, d), os.path.join(T, d))
subprocess.run([sys.executable, os.path.join(T, "gen", "m6gen.py")], check=True, capture_output=True)
same = all(filecmp.cmp(os.path.join(KP, p), os.path.join(T, p), shallow=False)
           for p in ["TABLES.md", "stages.txt"] + ["tables/%s.txt" % s for s in ("q289", "q287", "q086")] + ["predictions/%s.tsv" % s for s in ("q289", "q287", "q086")])
check(same, "m6gen.py is deterministic: a second run writes the same tables, predictions, TABLES.md and stages.txt")
cnt = {s: sum(1 for ln in open(os.path.join(KP, "tables", s + ".txt")) if ln.strip() and not ln.startswith("#")) for s in ("q289", "q287", "q086")}
check(cnt == {"q289": 23, "q287": 20, "q086": 21}, "job counts: %s (64 jobs)" % cnt)
check(filecmp.cmp(os.path.join(KP, "gen/r3_geo.py"), DATA + "/render/closing-r3-geo-c/gen/r3_geo.py", shallow=False)
      and filecmp.cmp(os.path.join(KP, "gen/rules1126.py"), DATA + "/ta/mtile-msaa-risky/analysis/rules.py", shallow=False),
      "gen/r3_geo.py and gen/rules1126.py are byte copies of the published files")
check(M.RU.selftest() is True, "rules1126.selftest passes (E257 / E331 words)")

P = preds("q289")
check(P["f-ctl-64x32-x10"]["hash"]["E876"] == "0x97334f75829dab25" == P["f-ctl-64x32-x10"]["hash"]["M-OR"], "q289: the control freezes E876's hash")
check(P["f-base-128x64"]["hash"]["M-OR"] == P["f-base-256x32"]["hash"]["M-OR"] == "0xf7befd67a3c8e325", "q289: the baselines freeze the tool mock's hash")
rank = {}
size = None
for ln in open(os.path.join(RANK, "q289_predict.out")):
    m = re.match(r"fill (\d+)x(\d+):", ln)
    if m:
        size = "%sx%s" % m.groups()
    m = re.match(r"\s+([xy])\^(0x[0-9a-f]+): OR \[(.*?)\] ADD \[(.*?)\]\s*(SEPARATES)?", ln)
    if m:
        rank[(size, m.group(1), int(m.group(2), 16))] = (m.group(3).replace(" ", "") or "-", m.group(4).replace(" ", "") or "-", bool(m.group(5)))
ok = nsep = 0
rows = [r for r in P if r.startswith("f-1") or r.startswith("f-2")]
for r in rows:
    m = re.match(r"f-(\d+x\d+)-([xy])([0-9a-f]+)$", r)
    if not m:
        continue
    key = (m.group(1), m.group(2), int(m.group(3), 16))
    want = rank[key]
    got = (P[r]["unwritten"]["M-OR"], P[r]["unwritten"]["M-ADD"], P[r]["separates"]["OR-vs-ADD"] == "yes")
    ok += got == want
    nsep += got[2]
check(ok == 20 and nsep == 8, "q289: the 20 held-out rows' unwritten tiles (OR, ADD) and SEPARATES are q289_predict.out's (%d of 20; %d separate)" % (ok, nsep))

P = preds("q287")
cells = {}
for ln in open(os.path.join(RANK, "q287_cells.out")):
    m = re.match(r"H\s+(\d+) .* A (\d+) FLOOR (\d+) ", ln)
    if m:
        cells[int(m.group(1))] = int(m.group(2)) != int(m.group(3))
good = all((P[r]["separates"]["A-vs-FLOOR"] == "yes") == cells.get(int(P[r]["size"]["all"].split("x")[1]), False) for r in P)
check(good, "q287: every row's A / FLOOR separation is q287_cells.out's for its height")
check(all(P[r]["stored_count"]["E831"] == "924" == P[r]["stored_count"]["A"] for r in P if P[r]["set"] == "control"), "q287: the three controls freeze E831's 924 (rule A's set)")
check(P["z-fit-34x19-y-r1"]["stored_count"]["A"] == "1008" and P["z-fit-34x19-y-r1"]["stored_count"]["FLOOR"] == "966",
      "q287: at 34 x 19, A stores 42 x 24 = 1008 and FLOOR 42 x 23 = 966")

P = preds("q086")
cls = [P[r]["class"]["H-COV"] for r in P]
check(cls.count("ok") == 7 and cls.count("fault") == 14 and all(P[r]["class"]["H-COV"] == "ok" for r in P if re.search(r"-(R|U2|U2Q)$", r)),
      "q086: H-COV freezes 7 completions (R, U2, U2Q) and 14 faults (FX, HS)")
check(P["q086-1024x768-R"]["words"]["all"] == "0x82010018,0x03018024,0x60", "q086: R at 1024 x 768 runs the rule's words (E331's sample)")
print("%d of %d generator checks" % (n - bad, n))
sys.exit(1 if bad else 0)
