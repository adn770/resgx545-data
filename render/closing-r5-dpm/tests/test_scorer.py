#!/usr/bin/env python3
"""test_scorer.py: the frozen scorer replayed on REAL kept records before the freeze (plan section 5, brief "Round 5 additions").
  1. holds on: the kept g-c4 (E799: flip 0xe2 / 0xe3 at 2048x2048, controls pass, c4-b3 the only grow), g-c5 (E801: last raises
     0x1b2, 0x1b6, 0x1e8) and g-qf (E832: the 22 counts) read as this session reads its own jobs;
  2. must fail on: a planted copy of g-c4 whose control c3-2048-0xe2 carries a g-qf job's timeline (round 4's o2: a control run with
     the default triangle): the replay's controls FAIL, and so does a session-shaped d-a0 built from the same real records;
  3. session-shaped stages built from real records (cases renamed to this session's rows, P and args as round 3 ran them): d-a0's rows
     on the kept jobs hold, d-a1's replicate row on c4-b3 holds grow = 1 and silent; NODATA for a missing job is never a pass;
  4. A3: pages written by sgx-sim running bins/oomring.blob over known event passes are decoded rung by rung, and the H-BITS rungs
     (decision, next, end of render) come out as the passes put them, for the pend, block and bit-9 readings;
  5. score/scorekit.py is the landed tools/closing/scorekit.py byte for byte; the scorer refuses when the freeze does not verify.
"""
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "run"), str(KP / "gen"), str(KP / "tests")]
os.environ["R5_SCORE_NOFREEZE"] = "1"
import score_r5 as S  # noqa: E402
import r5read as R  # noqa: E402

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/render")
C4, C5, QF = DATA / "closing-r3-geo/out/g-c4", DATA / "closing-r3-geo/out/g-c5", DATA / "closing-r3-geo-c/out/g-qf"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="r5score-", dir=str(KP / "debug")))
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


# 1. holds on the kept records
rp = S.replay(C4)
check(rp["grows"] == ["c4-b3"], f"g-c4 replay: c4-b3 is the only grow ({rp['grows']})")
check(rp["flips"].get((2048, 2048)) == (0xe2, 0xe3), f"g-c4 replay: E799's exact flip at 2048x2048, last raise 0xe2, first silent 0xe3 ({rp['flips']})")
check(rp["controls"] == "controls PASS", f"g-c4 replay: {rp['controls']} (its four ctl:R/N rows, scene checks included)")
rp5 = S.replay(C5)
check(rp5["flips"] == {(4096, 2048): (0x1b2, 0x1b3), (2048, 4096): (0x1b6, 0x1b7), (3072, 3072): (0x1e8, 0x1e9)},
      "g-c5 replay: E801's last raises 0x1b2, 0x1b6, 0x1e8 (C 0x1d2, 0x1d6, 0x208)")
check(rp5["grows"] == [] and not any("SCENE" in ln for ln in rp5["lines"]), "g-c5 replay: no grow, every job passes the scene check")
E832 = {0x2: 9, 0x3: 9, 0x5: 8, 0x6: 8, 0x7: 8, 0xa: 7, 0xb: 7, 0xf: 7, 0x10: 6, 0x17: 5, 0x18: 5, 0x21: 5, 0x22: 4, 0x31: 4, 0x32: 3,
        0x4b: 3, 0x4c: 2, 0x7e: 2, 0x7f: 2, 0x80: 2, 0x81: 1, 0x8e: 1}
rq = S.replay(QF, scene="tri")
check(rq["counts"] == E832, "g-qf replay: E832's 22 counts (9 at thr0 2 down to 1 at 0x8e)")
check(not any("SCENE" in ln for ln in rq["lines"]), "g-qf replay: every job stays at 1 global page (the default triangle)")

# 2. must fail on the planted directory
pl = TMP / "planted-g-c4"
shutil.copytree(C4, pl)
shutil.copy(QF / "qf-0x53.txt.gz", pl / "c3-2048-0xe2.txt.gz")
rpp = S.replay(pl)
check(rpp["controls"].startswith("controls FAILED") and "c3-2048-0xe2" in rpp["controls"],
      f"planted g-c4 (a control with a g-qf timeline): {rpp['controls'][:90]}")
check(any("c3-2048-0xe2" in ln and "SCENE" in ln for ln in rpp["lines"]), "planted: the scene check names the default triangle")


# 3. session-shaped stages from real records
def build(stage, mapping, out):
    """mapping: our row name -> (kept dir, kept name); cases.tsv with OUR P, knobs, args from the frozen table, the kept job's files."""
    import r5plan as P
    out.mkdir(parents=True, exist_ok=True)
    rows = ["name\tstage\tset\trisk\tP\tknobs\trt\targs\trc\tclass\tnote"]
    for r in P.tables()[stage]:
        if r["name"] not in mapping:
            continue
        d, k = mapping[r["name"]]
        for kind in ("out", "buf09"):
            src = d / {"out": f"{k}.txt.gz", "buf09": f"{k}.after.buf09.bin.gz"}[kind]
            shutil.copy(src, out / R.kept_name(r["name"], kind))
        rows.append("\t".join((r["name"], stage, r["set"], "safe", r["P"], r["knobs"], r["rt"], r["cmd"], "3", "ok", "-")))
    (out / "cases.tsv").write_text("\n".join(rows) + "\n")


G1 = DATA / "closing-r1-pixgeo/out/g-c1"
G3 = DATA / "closing-r2-geo/out/g-c3"
a0map = {"a0-c4-b5": (C4, "c4-b5"), "a0-c4-b6": (C4, "c4-b6"), "a0-c3-2048-0xe2": (C4, "c3-2048-0xe2"), "a0-c3-2048-0x122": (C4, "c3-2048-0x122"),
         "a0-cal-2048": (G3, "c3-2048-0x162")}
for nm, k in (("a0-4096-0x35a", "f-1500-0x37c"), ("a0-4096-0x35c", "f-1500-0x37e")):
    if (G1 / f"{k}.txt.gz").exists():
        a0map[nm] = (G1, k)
build("d-a0", a0map, TMP / "real" / "d-a0")
rows = S.score_rows("d-a0", TMP / "real" / "d-a0", [TMP / "real" / "d-a0"])
ran = [x for x in rows if x["case"] in a0map]
check(ran and all(x["state"] is True for x in ran), f"real-record d-a0: {len(ran)} rows of {len(a0map)} kept jobs all held "
      f"({[(x['case'], x['quantity']) for x in ran if x['state'] is not True][:3]})")
miss = [x for x in rows if x["case"] == "a0-cal-4096"]
check(miss and all(x["state"] is None and "NODATA" in x["why"] for x in miss), "real-record d-a0: the job never run is NODATA, cannot tell (never a pass)")
v = S.stage_verdict("d-a0", rows, {}, {})
check("cannot tell" in v[0] or "FAILED" in v[0], f"real-record d-a0 with a missing control: no headline ({v[0][:80]})")
pl0 = TMP / "planted" / "d-a0"
build("d-a0", dict(a0map, **{"a0-c3-2048-0xe2": (QF, "qf-0x53")}), pl0)
rows = S.score_rows("d-a0", pl0, [pl0])
bad = [x for x in rows if x["case"] == "a0-c3-2048-0xe2"]
check(bad and all(x["state"] is False for x in bad) and "scene" in bad[0]["why"], "planted d-a0: the control with a g-qf timeline is FAILED by the scene check")
check(S.stage_verdict("d-a0", rows, {}, {})[0].startswith("controls FAILED"), "planted d-a0: the premise headline is 'controls FAILED'")
build("d-a1", {"a1-rep1": (C4, "c4-b3"), "a1-b4": (C4, "c4-b4"), "a1-b2": (C4, "c4-b2")}, TMP / "real" / "d-a1")
rows = S.score_rows("d-a1", TMP / "real" / "d-a1", [TMP / "real" / "d-a1", TMP / "real" / "d-a0"])
st = {(x["case"], x["quantity"], x["model"]): x["state"] for x in rows}
check(st[("a1-rep1", "grow", "H-GREQ")] is True and st[("a1-rep1", "cls", "H-PEND")] is True and st[("a1-b4", "grow", "H-GREQ")] is True
      and st[("a1-b2", "cls", "H-BLOCK")] is True and st[("a1-rep1", "x734_clear", "H-GREQ")] is None,
      "real-record d-a1: c4-b3 as a1-rep1 holds grow 1 and silent; c4-b4, c4-b2 no grow, silent; 0x0734 never sampled there: cannot tell")
check(st[("a1-rep2", "grow", "H-GREQ")] is None, "real-record d-a1: a replicate not run is cannot tell")

# 4. A3 pages through sgx-sim
import simring  # noqa: E402
import world_r5 as W  # noqa: E402
for mode, raised, grow, want in (("pend", True, False, dict(dec_sa8_380=0x180, next_sa8_380=0x380, eor_sa9_b8=0)),
                                 ("pend", False, True, dict(dec_sa8_380=0x0, eor_sa9_b8=0)),
                                 ("block", False, True, dict(dec_sa8_380=0x0, eor_sa9_b8=1)),
                                 ("bit9", False, False, dict(dec_sa8_380=0x380, eor_sa9_b8=0))):
    w = W.World(f"bits={mode}")
    ev = W.a3_events(w, dict(w=2048, h=2048), 0xe8, dict(raised=raised, grow=grow))
    page, res = simring.run_events(ev)
    ring = S.decode_ring(page)
    logged = [e for e in ev if e[2] & 0x00700610]
    same = len(ring["rungs"]) == len(logged) and all(
        (r["slot"], r["pa0"], r["pa1"], r["sa8"], r["sa9"], r["timer"]) == e for r, e in zip(ring["rungs"], logged))
    got = S.a3_reading(ring)
    check(same and all(got.get(k) == v for k, v in want.items()) and ring["lost"] == 0 and [s for _, s in res] == [e[0] for e in ev],
          f"A3 {mode} raised={raised} grow={grow}: {len(logged)} rungs decoded as the passes wrote them; {dict((k, got.get(k)) for k in want)}; "
          f"every pass continued to its own slot")
check(ring["passes"] == [sum(1 for e in ev if e[0] == k) for k in range(4)], f"A3: the pass counters per slot {ring['passes']}")
check(S.a3_reading(S.decode_ring([0] * 1024)) == {}, "A3: an empty ring has no reading (cannot tell, not a pass)")

# 5. scorekit, the freeze refusal
check((KP / "score/scorekit.py").read_bytes() == pathlib.Path("/Users/jtorra/src/resgx545/tools/closing/scorekit.py").read_bytes(),
      "score/scorekit.py is the landed tools/closing/scorekit.py byte for byte")
cp = TMP / "copy"
shutil.copytree(KP, cp, ignore=shutil.ignore_patterns("debug", "out"))
(cp / "debug").mkdir()
with open(cp / "tables" / "d-a1.txt", "a") as f:
    f.write("# changed\n")
env = dict(os.environ)
env.pop("R5_SCORE_NOFREEZE")
o = subprocess.run([sys.executable, str(cp / "score/score_r5.py"), "d-a1", str(TMP / "real" / "d-a1")], capture_output=True, text=True, env=env)
check("refused: the frozen files do not verify" in o.stdout, f"the scorer refuses when a frozen file changed ({o.stdout.strip()[:80]})")
shutil.rmtree(TMP)
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
