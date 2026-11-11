#!/usr/bin/env python3
"""tests/test_scorers_a.py: score/score_a.py on worlds built from the REAL R3K-regress kept files (tests/worlds.py).

Every world is scored as a whole session (a-pb0 then a-pb, the gate between, the verdict) and must give the line the README
predicts.  Also: scorekit is main's byte for byte; a control that is not PASS (FAIL, NODATA) gates every row; replicates that
disagree are mixed, never held; rows that were read and match no hypothesis say so; a void job is never a pass.
  PY tests/test_scorers_a.py
"""
import filecmp
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "score"))
import worlds as W  # noqa: E402
import score_a as S  # noqa: E402

fails = 0


def check(name, cond, info=""):
    global fails
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else ": " + str(info)))
    if not cond:
        fails += 1


S.preds()
check("score/scorekit.py is main's tools/closing/scorekit.py byte for byte",
      filecmp.cmp(os.path.join(KP, "score/scorekit.py"), "/Users/jtorra/src/resgx545/tools/closing/scorekit.py", shallow=False))
check("the scorer draws its gate, combine and headline from scorekit", S.K.gate is not None and S.gate_rows.__module__ == "score_a")


def session(world, skip=()):
    root = tempfile.mkdtemp(prefix="r4a-w-%s-" % world)
    W.kept(os.path.join(root, "a-pb0"), "a-pb0", world, skip)
    W.kept(os.path.join(root, "a-pb"), "a-pb", world, skip)
    return root


def run(root):
    _, r0 = S.pb0_stage(os.path.join(root, "a-pb0"))
    code, gmsg = S.gate("a-pb", [root])
    _, r1 = S.pb_stage(os.path.join(root, "a-pb"), [root])
    return r0, code, gmsg, r1, S.verdict([root])


# --- the hypothesis worlds ---------------------------------------------------------------------------------------------
r0, code, gmsg, r1, v = run(session("old"))
check("old: the three controls PASS on the regress two-render values", r0["verdicts"] == {"pb-d0-te40": "PASS", "pb-p0-te60": "PASS",
                                                                                         "pb-p1-te40": "PASS"}, r0["verdicts"])
check("old: the gate is open", code == 0 and "open" in gmsg, gmsg)
check("old: p2 PASS", r1["verdicts"]["pb-p2-own11"] == "PASS", r1["verdicts"])
check("old: Q285 H-OLD with 4 of 4 rows decided", r1["q285"].startswith("H-OLD") and "(4 of 4 rows decided)" in r1["q285"], r1["q285"])
check("old: the verdict line is H-OLD", "SUMMARY: Q285: H-OLD" in v, v)
check("old: p3's hash is reported against the twin's two-render value, not used to decide",
      any("twin two-render hash 0xd2bfb75560f4c325" in x for x in S.pb_stage(os.path.join(session("old"), "a-pb"))[0]))

_, _, _, r1, v = run(session("field"))
check("field: Q285 H-FIELD with 4 of 4 rows decided", r1["q285"].startswith("H-FIELD") and "(4 of 4 rows decided)" in r1["q285"], r1["q285"])
_, _, _, r1, v = run(session("q030"))
check("q030: p3 and p4 both empty: cannot tell, park under Q030", r1["q285"].startswith("cannot tell") and "Q030" in r1["q285"], r1["q285"])
_, _, _, r1, v = run(session("both"))
check("both: twin and drawn: cannot tell, both effects", r1["q285"].startswith("cannot tell") and "both effects" in r1["q285"], r1["q285"])
_, _, _, r1, v = run(session("mixed"))
check("mixed: p3 replicates disagree: mixed, never held", r1["q285"].startswith("cannot tell") and "p3 mixed" in r1["q285"]
      and "H-OLD" not in r1["q285"].split("cannot tell")[0], r1["q285"])

# --- controls that fail gate every row ---------------------------------------------------------------------------------
r0, code, gmsg, r1, v = run(session("ctl-k2"))
check("ctl-k2: one-render values FAIL the three two-render controls", set(r0["verdicts"].values()) == {"FAIL"}, r0["verdicts"])
check("ctl-k2: the gate is closed and names the controls", code == 1 and "closed" in gmsg and "pb-d0-te40" in gmsg, gmsg)
check("ctl-k2: Q285 is not stated (controls FAILED)", r1["q285"].startswith("controls FAILED"), r1["q285"])
r0, code, gmsg, r1, v = run(session("ctl-nodata"))
check("ctl-nodata: p0 without output is NODATA, not PASS", r0["verdicts"]["pb-p0-te60"] == "NODATA", r0["verdicts"])
check("ctl-nodata: a NODATA control closes the gate", code == 1, gmsg)
check("ctl-nodata: a NODATA control gates every row: cannot tell", r1["q285"].startswith("cannot tell") and "pb-p0-te60" in r1["q285"],
      r1["q285"])
_, _, _, r1, v = run(session("p2-notapplied"))
check("p2-notapplied: p2 without its applied line FAILS", r1["verdicts"]["pb-p2-own11"] == "FAIL", r1["verdicts"])
check("p2-notapplied: Q285 not stated", not r1["q285"].startswith(("H-OLD", "H-FIELD")), r1["q285"])
_, _, _, r1, v = run(session("p2-armed"))
check("p2-armed: a poke still armed after p2 FAILS it", r1["verdicts"]["pb-p2-own11"] == "FAIL", r1["verdicts"])
_, _, _, r1, v = run(session("p3-short"))
check("p3-short: 15 of 16 pokes applied: p3a NODATA, never a reading", r1["verdicts"]["pb-p3a-twin"] == "NODATA", r1["verdicts"])
check("p3-short: Q285 cannot tell", r1["q285"].startswith("cannot tell"), r1["q285"])
_, _, _, r1, v = run(session("p4-hang"))
check("p4-hang: the hang row is no reading, p4b not run: cannot tell", r1["verdicts"]["pb-p4a-ffff"] not in ("drawn", "empty")
      and r1["verdicts"]["pb-p4b-ffff"] == "NODATA" and r1["q285"].startswith("cannot tell"), (r1["verdicts"], r1["q285"]))
_, _, _, r1, v = run(session("p4-other"))
check("p4-other: 0 triangle with other pixels is read and matches no hypothesis (said so)",
      r1["verdicts"]["pb-p4a-ffff"] == "other" and "read" in r1["q285"] and "matched no hypothesis" in r1["q285"], (r1["verdicts"], r1["q285"]))

# --- the a-pb stage without a kept a-pb0 ---------------------------------------------------------------------------------
root = tempfile.mkdtemp(prefix="r4a-nopb0-")
W.kept(os.path.join(root, "a-pb"), "a-pb", "old")
code, gmsg = S.gate("a-pb", [root])
check("no kept a-pb0: the gate is closed", code == 1 and "no a-pb0" in gmsg, gmsg)
_, r1 = S.pb_stage(os.path.join(root, "a-pb"), [root])
check("no kept a-pb0: Q285 cannot tell (the controls cannot tell)", r1["q285"].startswith("cannot tell"), r1["q285"])
check("verdict with no kept a-pb: not run", "SUMMARY: Q285: not run" in S.verdict([tempfile.mkdtemp()]))

# --- the command line refuses to score on a changed freeze --------------------------------------------------------------
r = subprocess.run([sys.executable, os.path.join(KP, "score/score_a.py"), "a-pb0", session("old") + "/a-pb0"], capture_output=True, text=True)
check("the scorer's command line prints one SUMMARY on a frozen tree", r.returncode == 0 and r.stdout.count("SUMMARY:") == 1, r.stdout[-300:])
print("%d FAIL" % fails)
sys.exit(1 if fails else 0)
