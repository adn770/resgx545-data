#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""Post hoc reading of R6-dpm attempt a2 (round 6 fold, 2026-11-12), written after the run and its scores were read.

Every headline of the frozen scorer printed "cannot tell", gated by one r-a0 control (a0-cal-2048f grow) that has no reading by
construction: a calibration at knob 0x400 never takes a partial render, so no grow can be read.  This script does NOT re-score:
  1. it tallies the held / FAILED / cannot tell states the frozen scorer printed line by line in the kept score files
     (out/a2/score-STAGE.txt, re-run byte-identical at the fold), per stage, model, quantity and scene, without the gate;
  2. it reads, with the frozen reader (score/score_r6.py read_job), the two r-k creep jobs the scene check voided (their
     2048x4096 step 3 at 0x12c, E874's own miss) and prints their class, partial renders, pages left and sa8 bits;
  3. it prints the periods of the global list head pair on PB page 1 of the two r-v calibration dumps (the frozen obj_L
     returned None at --vtx-coords 8);
  4. it prints, per r-m band, the first thr0 that left one global page.
usage: postrun/ungated.py [SESSION]   (default: the session directory above postrun/)
"""
import collections
import gzip
import os
import pathlib
import re
import struct
import sys

HERE = pathlib.Path(__file__).resolve().parent
S = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent
A2 = S / "out" / "a2"
LINE = re.compile(r"^(\S+)\s+(\S+)\s+pred (.*?)\s+obs (.*?)\s+\[([^\]]+)\]\s+(\S+)\s+(held|FAILED|cannot tell)")


def rows(stage):
    for ln in (A2 / f"score-{stage}.txt").read_text().splitlines():
        m = LINE.match(ln)
        if m:
            case, q, pred, obs, model, label, st = m.groups()
            yield dict(case=case, q=q, pred=pred.strip(), obs=obs.strip(), model=model, label=label, st=st)


def tally(xs):
    c = collections.Counter(x["st"] for x in xs)
    return f"{c['held']} held, {c['FAILED']} FAILED, {c['cannot tell']} cannot tell of {len(xs)}"


def group(case):
    m = re.match(r"^[a-z]+-(cal-)?([a-z0-9]+)", case)
    return m.group(2) if m else case


print("# ungated tallies of R6-dpm out/a2 (post hoc)")
for st in ("r-a0", "r-m", "r-n", "r-v", "r-b", "r-k"):
    rs = list(rows(st))
    print(f"== {st}")
    qk = lambda q: "steps" if re.fullmatch(r"S\d+", q) else q      # the steps S2, S3, ... tallied together
    keys = sorted({(x["model"], qk(x["q"]), x["label"]) for x in rs})
    for mdl, q, lab in keys:
        xs = [x for x in rs if (x["model"], qk(x["q"]), x["label"]) == (mdl, q, lab)]
        print(f"  {mdl:20} {q:12} {lab:8} all: {tally(xs)}")
        if st in ("r-n", "r-v", "r-b") and lab == "heldout":
            for g in sorted({group(x["case"]) for x in xs}):
                print(f"  {'':20} {'':12} {'':8} {g:6} {tally([x for x in xs if group(x['case']) == g])}")

print("== r-m: first thr0 with one global page left, per band (observed; H-PHASE's B_k 0x176, 0x1c1, 0x20c)")
left = collections.defaultdict(dict)
for x in rows("r-m"):
    if x["q"] == "gps_left" and x["model"] == "H-PHASE":
        b, t = re.match(r"m-(b\d)-(0x[0-9a-f]+)", x["case"]).groups()
        left[b][int(t, 16)] = int(x["obs"])
for b, d in sorted(left.items()):
    first = min((t for t, v in d.items() if v == 1), default=None)
    print(f"  {b}: " + " ".join(f"0x{t:x}:{v}" for t, v in sorted(d.items())) + f"  first 1 at {first and hex(first)}")

print("== r-b: row-order peaks within 3 pages and exact, per scene (from the printed pred and obs)")
for sc in ("s262", "s243", "s220", "s179"):
    xs = [x for x in rows("r-b") if x["case"].startswith(f"b-{sc}-") and x["model"] == "H-REPLAY-ROW" and x["q"] == "peaks"]
    print(f"  {sc}: exact {sum(x['st'] == 'held' for x in xs)} of {len(xs)}")

sys.path.insert(0, str(S / "score"))
os.environ.setdefault("R6_SCORE_NOFREEZE", "1")
import score_r6 as SC  # noqa: E402

print("== r-k creep jobs read without the scene check (the frozen reader)")
d = A2 / "r-k"
cs = SC.cases(d)
for n in ("k-creep", "k-creep2"):
    r, why = SC.read_job(d, n, cs[n], [d])
    keys = ("thr0", "cls", "grow", "nparts", "gps_left", "dw36", "dec_sa8_380", "next_sa8_380", "scene_fail")
    hx = ("thr0", "dec_sa8_380", "next_sa8_380")
    print(f"  {n}: " + ", ".join(f"{k}={hex(r[k]) if k in hx and isinstance(r.get(k), int) else r.get(k)}" for k in keys))

print("== r-v calibration dumps: PB page 1 head pair offsets and periods")
for n in ("v-cal-c4", "v-cal-c8"):
    p = gzip.open(A2 / "r-v" / f"{n}.p1139-green.param.bin.gz").read()
    w = struct.unpack_from("<1024I", p, 0)
    pos = [i for i in range(1023) if (w[i], w[i + 1]) == (w[0], w[1])]
    print(f"  {n}: offsets {pos}, periods {[b - a for a, b in zip(pos, pos[1:])]}, frozen obj_L {SC.obj_L(p)}")
