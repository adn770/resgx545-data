#!/usr/bin/env python3
"""test_scorer.py: the frozen scorer replayed on KEPT records before the freeze (round 6 addition: every scorer on the kept files it
must hold on and on ones it must fail on; plan section 4 "Dry runs before the freeze").
  1. R5-dpm's kept attempt (closing5/r5-dpm/out/a2, round 5 on rgn4) scored by THIS scorer against R5-dpm's frozen predictions gives
     E860 to E864's tables: d-a0's premise, d-a1's 5 of 5 grows, d-a2's H-PEND (H-BLOCK 5 FAILED), d-t's H-TAIL 6 of 8 (E862), d-b's
     H-CNT 16 of 20 (E863), d-a3's H-BITS 6 of 6 (E864); and a2b-cal-4x2's S2 HELD under H-IV (E873), where R5's point rule failed it;
  2. real-record r-a0, r-b and r-k directories assembled from kept rgn4 jobs of the same cells (R5-dpm's d-a0, d-t, d-b, d-a3) hold
     every control the stage gates on; the same directories with ONE file planted fail it: a g-qf timeline in a 1500-vertex control
     (scene: never a second global page), a 1500-vertex timeline in a g-qf control (scene: more than one global page), a ring page
     swapped between c4-b5 and c4-b6 (the bits), a knob that did not land;
  3. the reader's H-PHASE inputs on kept rows: the 2048x2048 rows F4 scored (f4_phase.out) read the same pages left here, and the
     frozen rule gives F4's column for each;
  4. the object size L from a real dump: r2-geo c3-2048-0x354 (complete, F2's "lists empty: PB page 1; L 67") reads 67; a page with
     no recurring head reads None (cannot tell, never a value).
"""
import csv
import gzip
import os
import pathlib
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
os.environ["R6_SCORE_NOFREEZE"] = "1"
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "run"), str(KP / "gen")]
import score_r6 as S  # noqa: E402
import r6read as R  # noqa: E402
import r6plan as P  # noqa: E402

R5 = KP.parent.parent / "closing5" / "r5-dpm" / "out" / "a2"
DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/render")
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


# 1. R5-dpm's attempt, rescored
res = S.replay_r5(R5)
t = lambda st, m: (res[st][m].held, res[st][m].failed, res[st][m].cannot_tell) if m in res[st] else None
check(t("d-a0", "TABLE") == (7, 0, 0) and t("d-a0", "CTL") == (14, 0, 0) and not res["d-a0"]["_controls_failed"],
      "d-a0 (E860): the premise rows all held, steps in their brackets")
check(t("d-a1", "H-GREQ") == (14, 0, 0), "d-a1 (E860): H-GREQ 14 of 14 (5 of 5 grows, 4 neighbours silent)")
check(t("d-a2", "H-GREQ") == (16, 0, 0) and t("d-a2", "H-PEND") == (13, 0, 3) and t("d-a2", "H-BLOCK")[1] == 5,
      "d-a2 (E861): H-GREQ 16 of 16, H-PEND 13 held 0 FAILED, H-BLOCK 5 FAILED")
check(t("d-a2b", "TABLE") == (11, 0, 0), "d-a2b (E861, E873): every step of the three calibrations HELD under H-IV, a2b-cal-4x2's S2 included")
c4x2 = R.reading(gzip.open(R5 / "d-a2b" / "a2b-cal-4x2.txt.gz").read().decode())
check(c4x2["iv"][2] == (0x97, 0x98) and c4x2["S"][2] == 0x98,
      "a2b-cal-4x2: bracket [0x97, 0x98] holds the frozen 0x97 where R5's point rule read 0x98 (E861's gate)")
check(t("d-t", "H-TAIL") == (6, 2, 0), "d-t (E862): H-TAIL 6 held, 2 FAILED")
check(t("d-b", "H-CNT") == (16, 4, 0) and t("d-b", "CTL") == (5, 0, 0), "d-b (E863): the five g-qf controls; H-CNT 16 of 20 (4 misses)")
check(t("d-a3", "H-BITS") == (6, 0, 0) and t("d-a3", "CTL-A3") == (4, 0, 0), "d-a3 (E864): H-BITS 6 of 6 and the task-armed controls")


# 2. real-record stage directories
def assemble(dst, rows):
    """rows: (new name, source dir, source name, P, knobs, args or None = the source's): copy every kept file under the new name."""
    dst.mkdir(parents=True)
    out = []
    for new, sd, sn, Pv, kn, args in rows:
        src = {c["name"]: c for c in csv.DictReader(open(sd / "cases.tsv"), delimiter="\t")}[sn]
        for f in sd.iterdir():
            if f.name.startswith(sn + "."):
                shutil.copy(f, dst / (new + f.name[len(sn):]))
        out.append(dict(src, name=new, P=Pv, knobs=kn, args=args or src["args"]))
    with open(dst / "cases.tsv", "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(out)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="score6-", dir=str(KP / "debug")))
A0 = [("a0-cal-2048", R5 / "d-a0", "a0-cal-2048", "0x162", "stophang prem cal:c2048", None),
      ("a0-c4-b5", R5 / "d-a0", "a0-c4-b5", "0x104", "stophang prem ctl:R", None),
      ("a0-c4-b6", R5 / "d-a0", "a0-c4-b6", "0x105", "stophang prem ctl:N", None),
      ("a0-t-s3m7", R5 / "d-t", "t-s3m7", "0xb8", "stophang prem ctlleft:2", None),
      ("a0-t-s3m6", R5 / "d-t", "t-s3m6", "0xb9", "stophang prem ctlleft:1", None),
      ("a0-qf-0xa2", R5 / "d-b", "b-qf-0xa2", "0xa2", "stophang expectdiff prem ctlcnt:2", None)]


def a0_controls(d):
    rows = S.score_rows("r-a0", d, [d])
    return {f"{x['case']} {x['quantity']}": x["state"] for x in rows if x["set"] == "control" and x["case"] != "a0-cal-2048f"}, rows


assemble(tmp / "a0" / "r-a0", A0)
ctl, rows = a0_controls(tmp / "a0" / "r-a0")
check(all(v is True for v in ctl.values()) and len(ctl) == 25,
      f"r-a0 from kept rgn4 jobs of its six cells: every control row held ({sum(v is True for v in ctl.values())} of {len(ctl)})")
pl = list(A0)
pl[1] = ("a0-c4-b5", R5 / "d-b", "b-qf-0xa2", "0x104", "stophang prem ctl:R", A0[1][5] or
         {c["name"]: c for c in csv.DictReader(open(R5 / "d-a0" / "cases.tsv"), delimiter="\t")}["a0-c4-b5"]["args"])
assemble(tmp / "a0p" / "r-a0", pl)
ctl, rows = a0_controls(tmp / "a0p" / "r-a0")
bad = [x for x in rows if x["case"] == "a0-c4-b5" and x["state"] is False and "scene:" in x["why"]]
check(bool(bad) and ctl.get("a0-c4-b5 cls") is False, "PLANTED: a g-qf timeline in the 1500-vertex control a0-c4-b5 FAILS it (scene)")
pl = list(A0)
pl[5] = ("a0-qf-0xa2", R5 / "d-a0", "a0-c4-b5", "0xa2", "stophang expectdiff prem ctlcnt:2",
         {c["name"]: c for c in csv.DictReader(open(R5 / "d-b" / "cases.tsv"), delimiter="\t")}["b-qf-0xa2"]["args"])
assemble(tmp / "a0q" / "r-a0", pl)
ctl, rows = a0_controls(tmp / "a0q" / "r-a0")
check(ctl.get("a0-qf-0xa2 nparts") is False and any("default-triangle job with" in x["why"] for x in rows if x["case"] == "a0-qf-0xa2"),
      "PLANTED: a 1500-vertex timeline in the g-qf control FAILS it (scene: more than one global page)")
pl = list(A0)
pl[2] = ("a0-c4-b6", R5 / "d-a0", "a0-c4-b6", "0x106", "stophang prem ctl:N", None)
assemble(tmp / "a0k" / "r-a0", pl)
ctl, rows = a0_controls(tmp / "a0k" / "r-a0")
check(ctl.get("a0-c4-b6 cls") is False and any(x["why"].startswith("knob did not land") for x in rows if x["case"] == "a0-c4-b6"),
      "PLANTED: a control whose knob did not land (P written 0x106, 0x0624 read 0xe3) FAILS")
# r-b's four controls from R5-dpm's kept g-qf repeats
B = [(f"b-qf-0x{p:x}", R5 / "d-b", f"b-qf-0x{p:x}", f"0x{p:x}", "stophang expectdiff", None) for p in (0x53, 0x54, 0xa2, 0xa3)]
assemble(tmp / "b" / "r-b", B)
rows = S.score_rows("r-b", tmp / "b" / "r-b", [tmp / "b" / "r-b"])
qf = [x for x in rows if x["case"].startswith("b-qf-") and x["set"] == "control"]
check(len(qf) == 12 and all(x["state"] is True for x in qf), f"r-b's controls from kept rgn4 g-qf repeats: {sum(x['state'] is True for x in qf)} of 12 held")
pk = [x for x in rows if x["case"] == "b-qf-0x53" and x["quantity"] == "peaks"]
check(any(x["state"] is True and x["model"] == "H-REPLAY-ROW" for x in pk), "b-qf-0x53's run peaks read 0x31 0x51 0x51 0x51 0x2 (F7's reading, E875)")
# r-k from R5-dpm's kept task-armed jobs (E864)
K = [("k-b5", R5 / "d-a3", "a3-b5a", "0x104", "stophang fw", None), ("k-b6", R5 / "d-a3", "a3-b6a", "0x105", "stophang fw", None),
     ("k-b3", R5 / "d-a3", "a3-r1", "0x10a", "stophang fw", None), ("k-s3", R5 / "d-a3", "a3-s3", "0xbf", "stophang fw", None)]
assemble(tmp / "k" / "r-k", K)
rows = S.score_rows("r-k", tmp / "k" / "r-k", [tmp / "k" / "r-k", R5 / "d-a0"])
dec = {x["case"]: x["state"] for x in rows if x["quantity"] == "dec_sa8_380" and x["case"] in ("k-b5", "k-b6", "k-b3", "k-s3")}
check(dec == {"k-b5": True, "k-b6": True, "k-b3": True, "k-s3": True}, f"r-k's sa8 rows on E864's kept rings: {dec}")
K2 = [("k-b5", R5 / "d-a3", "a3-b6a", "0x104", "stophang fw", None), ("k-b6", R5 / "d-a3", "a3-b6b", "0x105", "stophang fw", None)]
assemble(tmp / "k2" / "r-k", K2)
rows = S.score_rows("r-k", tmp / "k2" / "r-k", [tmp / "k2" / "r-k"])
check(any(x["case"] == "k-b5" and x["state"] is False for x in rows if x["set"] == "control"),
      "PLANTED: c4-b6's files under k-b5 FAIL the task-armed control (knob and bits)")

# 3. H-PHASE on the kept 2048x2048 rows F4 printed
f4 = (pathlib.Path("/Users/jtorra/src/resgx545-data/cited/closing6/dpm/offline") / "f4_phase.out").read_text().split("== 2048x4096")[0]
n = ok = 0
for ln in f4.splitlines():
    m = re.match(r"\s+(fit|held)\s+thr0 (0x[0-9a-f]+) left (\d)\s+timeline-rule (\S+)\s+F5-rule (\S+)\s+(\S+)", ln)
    if not m:
        continue
    sess, rest = m.group(6).split("/", 1)
    d = DATA / f"closing-{sess}" / "out" / rest.rsplit("/", 1)[0]
    name = rest.rsplit("/", 1)[1]
    r = R.reading(gzip.open(d / f"{name}.txt.gz").read().decode(errors="replace"))
    Sx, Bx, _ = P.MODEL[(2048, 2048)]
    v = P.M.phase_left(int(m.group(2), 16), Sx, Bx)
    n += 1
    ok += str(r["gps_left"]) == m.group(3) and str(v if v is not None else "grow") == m.group(5)
check(n == 34 and ok == n, f"the reader's pages left and the frozen H-PHASE rule = f4_phase.out on the {n} kept 2048x2048 rows ({ok})")

# 4. L from a dump
param = gzip.open(DATA / "closing-r2-geo/out/g-c3/c3-2048-0x354.p1139-green.param.bin.gz").read()
check(S.obj_L(param) == 67, f"obj_L of r2-geo c3-2048-0x354's dump: {S.obj_L(param)} (F2: 67)")
check(S.obj_L(b"\x01\x00\x00\x00" * 1024) is None and S.obj_L(None) is None, "obj_L of a page with no recurring head: None (cannot tell)")
shutil.rmtree(tmp)
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
