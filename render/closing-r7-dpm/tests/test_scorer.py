#!/usr/bin/env python3
"""test_scorer.py: score_r7.py replayed before the freeze on KEPT records it must hold on and on ones it must fail on (plan section 4,
"Dry runs before the freeze": R6-dpm's out/a2 and R5-dpm's out/a2; the gate itself, G8, is tests/test_controls.py).
  1. s-m: R6-dpm's kept r-m cells at 2048x2048 bands 5 to 7 assembled as s-m's six replicates (A - 1, A: m-r5-0x177 .. m-r7-0x20d) hold
     H-SPAN 6 of 6 and FAIL E874-B at A - 1 (3 of 6), with R6-dpm's kept r-a0 as the premise directory (its gate open);
  2. s-a0 on R5-dpm's kept d-a0 (round 5, rgn4): a0-cal-2048, a0-c4-b5, a0-c4-b6 read held as our controls; the rows R5 did not run
     (a0-cal-2048f, a0-t-s3m6, a0-qf-0xa2) are NO READING and the premise STOPS (a missing control never passes);
  3. s-b's reading of a one-triangle job: R6-dpm's kept g-qf control b-qf-0xa2 read as a0-qf-0xa2 (count 2, run peaks 0x80 0xa0 0x2:
     H-REPLAY64 held); the same job as a cell of a moved scene is never held (planted: the knob proof voids it);
  4. the scene check of the creep cell uses the kept 2048x4096 steps: R6-dpm's kept k-creep (S3 0x12c) passes it now, where R6's
     frozen check against the model (S3 0x129) voided it.
"""
import csv
import os
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
os.environ["R7_SCORE_NOFREEZE"] = "1"
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "run"), str(KP / "gen")]
import score_r7 as S  # noqa: E402
import r7plan as P  # noqa: E402

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/render")
R6, R5 = DATA / "closing-r6-dpm/out/a2", DATA / "closing-r5-dpm/out/a2"
FAIL = []
T = {r["name"]: r for st, rows in P.tables().items() for r in rows}


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


def assemble(dst, rows):
    dst.mkdir(parents=True)
    out = []
    for new, sd, sn in rows:
        src = {c["name"]: c for c in csv.DictReader(open(sd / "cases.tsv"), delimiter="\t")}[sn]
        for f in sd.iterdir():
            if f.name.startswith(sn + "."):
                shutil.copy(f, dst / (new + f.name[len(sn):]))
        t = T[new]
        out.append(dict(src, name=new, P=t["P"] if t["P"].startswith("0x") else src["P"], knobs=t["knobs"], args=t["cmd"]))
    with open(dst / "cases.tsv", "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(out)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="score7-", dir=str(KP / "debug")))
# 1. s-m replicates from R6-dpm's r-m
a0 = tmp / "s-a0"
assemble(a0, [(n, R6 / "r-a0", n) for n in ("a0-cal-2048", "a0-cal-2048f", "a0-c4-b5", "a0-c4-b6", "a0-t-s3m6", "a0-qf-0xa2")])
sm = tmp / "s-m"
reps = [(f"m-r{k}-0x{t:x}", R6 / "r-m", f"m-b{k}-0x{t:x}") for k, A in ((5, 0x178), (6, 0x1c3), (7, 0x20d)) for t in (A - 1, A)]
assemble(sm, reps)
rows, rd = S._score("s-m", sm, [sm, a0])
span = [x["state"] for x in rows if x["model"] == "H-SPAN" and x["case"].startswith("m-r")]
e874 = [x for x in rows if x["model"] == "E874-B" and x["case"].startswith("m-r")]
check(span == [True] * 6, f"R6-dpm's kept r-m cells as s-m's replicates: H-SPAN {span}")
check(sum(x["state"] is False for x in e874) == 3 and all(x["state"] is False for x in e874 if x["case"] in ("m-r5-0x177", "m-r6-0x1c2", "m-r7-0x20c")),
      "... and E874-B FAILS at A - 1 of each band (3 of 6), held at A")
v = S.stage_verdict("s-m", rows, rd, a0)
check(any("H-SPAN at 2048x2048 bands 5 to 7" in x and "(6 of 6 rows decided)" in x for x in v), f"the s-m replicate headline with R6's r-a0 as the gate: {[x for x in v if 'bands 5' in x][0][:90]}")
# 2. s-a0 on R5-dpm's d-a0
r5 = tmp / "r5a0"
assemble(r5, [(n, R5 / "d-a0", n) for n in ("a0-cal-2048", "a0-c4-b5", "a0-c4-b6")])
rows, rd = S._score("s-a0", r5, [r5])
st = {(x["case"], x["quantity"]): x["state"] for x in rows if x["set"] == "control"}
check(all(st[k] is True for k in st if k[0] in ("a0-cal-2048", "a0-c4-b5", "a0-c4-b6")), "R5-dpm's d-a0 jobs read held as s-a0's controls")
check(all(st[k] == S.NO_READING for k in st if k[0] in ("a0-cal-2048f", "a0-t-s3m6", "a0-qf-0xa2")), "the rows R5 did not run: NO READING")
v = S.stage_verdict("s-a0", rows, rd, None)
check(v[0] == "STOP: premise: control a0-cal-2048f did not run", f"the premise STOPS, no headline: {v[0]}")
# 3. a one-triangle control and a planted cell
qf = tmp / "qf"
assemble(qf, [("a0-qf-0xa2", R6 / "r-b", "b-qf-0xa2")])
rows, _ = S._score("s-a0", qf, [qf])
check(all(x["state"] is True for x in rows if x["case"] == "a0-qf-0xa2" and x["set"] == "control"),
      "R6-dpm's kept b-qf-0xa2 as a0-qf-0xa2: count 2, run peaks 0x80 0xa0 0x2 (H-REPLAY64), knob, one global page: held")
sb = tmp / "s-b"
n, w, h, dx, dy, U = P.B_SCENES[0]
cell = f"b-{n}-0x{P.B_CELLS[n][3]:x}"
assemble(sb, [(cell, R6 / "r-b", "b-qf-0xa2")])
rows, _ = S._score("s-b", sb, [sb])
hr = [x for x in rows if x["case"] == cell and x["model"] == "H-REPLAY64"]
check(hr and all(x["state"] is not True for x in hr) and "knob did not land" in hr[0]["why"],
      f"planted: g-qf's timeline as {cell}: never held (the knob proof: {hr[0]['why'][:50] if hr else ''})")
# 4. the creep cell's scene check
kd = tmp / "s-k"
assemble(kd, [("k-creep", R6 / "r-k", "k-creep")])
r, why = S.read_job(kd, "k-creep", S.cases(kd)["k-creep"], [kd])
check(r is not None and not r.get("scene_fail") and r["S"][3] == 0x12c, "R6-dpm's kept k-creep (S3 0x12c) passes the scene check against the kept 2048x4096 steps")
check(S.ref_steps((2048, 4096), [kd])[0] == P.KEPT_2X4 and P.MODEL[(2048, 4096)][0][3] == 0x129, "the reference is KEPT_2X4, not the model's S3 0x129")
shutil.rmtree(tmp)
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
