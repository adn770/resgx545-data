#!/usr/bin/env python3
"""Scorer tests of R3K-regress: kept-output worlds built from the real records (tests/worlds.py): the old records replayed (every
rg-ctl row and every E728-shape row must PASS), then mutated or mixed worlds where each verdict of rg-pb wins and loses, void
data, faults, the gate and the freeze refusal.  Needs a current freeze.  Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, HERE)
import score_rg as S  # noqa: E402
import worlds as W  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("ok   %s" % name)
    else:
        fails += 1
        print("FAIL %s %s" % (name, detail))


ok, msg = S.L.verify_freeze()
check("the freeze verifies (run/freeze_k.sh freeze first)", ok, msg)
S.preds()
T = tempfile.mkdtemp(prefix="rg-score-")
n = [0]


def world(stage, **kw):
    n[0] += 1
    return W.build(os.path.join(T, "w%d" % n[0], stage), stage, **kw)


def sub(a, b):
    return lambda t: t.replace(a, b)


# ---- rg-ctl -------------------------------------------------------------------------------------------------------------
d = world("rg-ctl")
lines, r = S.ctl_stage(d)
res = r["verdicts"]
check("rg-ctl: the old records replayed give 23 of 23 PASS", len(res) == 23 and all(v == "PASS" for v in res.values()), res)
check("rg-ctl: the SUMMARY says every row reproduced its old value, controls and held-out tallied apart",
      "every row reproduced" in r["summary"] and "control 2 PASS of 2" in r["summary"] and "heldout 21 PASS of 21" in r["summary"], r["summary"])
d = world("rg-ctl", mutate={"ctl-u-1024-n1": sub("hash 0xc9e301d225fe2325", "hash 0xc9e301d225fe2326")})
_, r = S.ctl_stage(d)
check("rg-ctl: a changed target hash FAILs that row only", r["verdicts"]["ctl-u-1024-n1"] == "FAIL" and sum(v == "PASS" for v in r["verdicts"].values()) == 22
      and "NOT PASS" in r["summary"])
d = world("rg-ctl", mutate={"ctl-green-8x8": sub("o0 0xff00ff00 (64 of 64)", "o0 0xff00ff00 (60 of 64)")})
_, r = S.ctl_stage(d)
check("rg-ctl: a changed probe o0 count FAILs", r["verdicts"]["ctl-green-8x8"] == "FAIL")
d = world("rg-ctl", mutate={"ctl-a1-256x160-tee0": sub("diff: 0 of 40960", "diff: 12 of 40960")})
_, r = S.ctl_stage(d)
check("rg-ctl: a changed diff FAILs", r["verdicts"]["ctl-a1-256x160-tee0"] == "FAIL")
d = world("rg-ctl", mutate={"ctl-dd-p1": lambda t: t})
os.remove(os.path.join(d, "ctl-dd-p1.dd-p1__0.param.bin.gz"))
_, r = S.ctl_stage(d)
check("rg-ctl: a missing dump is NODATA, not a verdict", r["verdicts"]["ctl-dd-p1"] == "NODATA")
d = world("rg-ctl", skip=("ctl-u-640x480",))
_, r = S.ctl_stage(d)
check("rg-ctl: a row that was not run (no cases.tsv row) is NODATA", r["verdicts"]["ctl-u-640x480"] == "NODATA")
d = world("rg-ctl", cls={"ctl-u-1280x1024": (124, "fail")})
_, r = S.ctl_stage(d)
check("rg-ctl: rc 124 (a freeze) is NODATA", r["verdicts"]["ctl-u-1280x1024"] == "NODATA")
d = world("rg-ctl", cls={"ctl-u-1280x1024": (1, "fault")})
_, r = S.ctl_stage(d)
check("rg-ctl: class fault is a FAULT result, never PASS", r["verdicts"]["ctl-u-1280x1024"] == "FAULT")
d = world("rg-ctl", mutate={"ctl-u-640x480": lambda t: t + "\nBIF fault 0x90004 at 0x20006000\n"})
_, r = S.ctl_stage(d)
check("rg-ctl: a BIF fault line in the whole output is a FAULT even with class ok", r["verdicts"]["ctl-u-640x480"] == "FAULT")
d = world("rg-ctl")
open(os.path.join(d, "ctl-u-640x480.snap0.regs.gz"), "wb").close()
import gzip
with gzip.open(os.path.join(d, "ctl-u-640x480.snap0.regs.gz"), "wb") as f:
    f.write(b"sgxfive regs 1\nreg 0x0118 0x400\nreg 0x012c 0x20000000\nreg 0x0c04 0x90004\n")
_, r = S.ctl_stage(d)
check("rg-ctl: a fault latched before the job (snap 0) is NODATA", r["verdicts"]["ctl-u-640x480"] == "NODATA")
d = world("rg-ctl", mutate={"ctl-u-640x480": lambda t: ""})
_, r = S.ctl_stage(d)
check("rg-ctl: an empty tool output is NODATA", r["verdicts"]["ctl-u-640x480"] == "NODATA")

# ---- rg-pb --------------------------------------------------------------------------------------------------------------
d = world("rg-pb")
lines, r = S.pb_stage(d)
v = r["verdicts"]
check("rg-pb replay (E728 for the E rows, K2 for the n rows): 9 PASS, 3 H-NEW, the twin row H-NEW",
      all(v[x] == "PASS" for x in S.E_HELD + S.E_CTL) and [v[x] for x in S.N_ROWS] == ["H-NEW"] * 4, v)
check("rg-pb replay: the verdict is H-SHAPE (the module did not change E728's image; k-pb0's value is the job shape's)",
      r["q"].startswith("H-SHAPE") and "reproducible" in r["q"], r["q"])
# H-MOD: the E rows at TE 0x40/0x80/0xc0 give the NEW values (K2's dump-run output and dumps), stable, controls fine
mod = {x: ("k2", "pb-d0-te40") for x in S.E_HELD[:6]}
d = world("rg-pb", srcmap=mod)
_, r = S.pb_stage(d)
check("rg-pb H-MOD world: E-shape rows at the empty-image TE give K2's values, stable, both controls PASS -> H-MOD",
      r["q"].startswith("H-MOD") and "0x8ea26cdfee74a325" in r["q"], r["q"])
# not reproducible: one TE 0x40 run differs
d = world("rg-pb", srcmap={"pb-e40-m2-64b": ("k2", "pb-d0-te40")})
_, r = S.pb_stage(d)
check("rg-pb: the three E728-shape TE 0x40 runs disagree -> not reproducible", r["q"].startswith("not reproducible"), r["q"])
# the n rows not reproducible while E fine
d = world("rg-pb", srcmap={"pb-n40-b": ("e728", "t29-m2-40-64x64"), "pb-n40-c": ("e728", "t29-m2-40-64x64")})
_, r = S.pb_stage(d)
check("rg-pb: E rows as E728 but the -n 2 rows not H-NEW -> k-pb0's value is not stable (not a verdict for the module)",
      "NOT reproducible" in r["q"] and not r["q"].startswith("H-"), r["q"])
# the controls fail too: general difference
d = world("rg-pb", srcmap={x: ("k2", "pb-d0-te40") for x in S.E_HELD[:6] + S.E_CTL})
_, r = S.pb_stage(d)
check("rg-pb: E rows AND E728's TE 0x20/0xe0 controls differ -> general difference, not specific to TE 0x40",
      "in general" in r["q"], r["q"])
# a fault in an E row
d = world("rg-pb", cls={"pb-e80-m2-64": (1, "fault")})
_, r = S.pb_stage(d)
check("rg-pb: a fault-class row makes the verdict cannot tell", r["q"].startswith("cannot tell") and r["verdicts"]["pb-e80-m2-64"] == "FAULT", r["q"])
# a row with a value matching neither model
d = world("rg-pb", mutate={"pb-n60": sub("hash 0xd2bfb75560f4c325", "hash 0x1111111111111111")})
_, r = S.pb_stage(d)
check("rg-pb: a row that matches neither H-NEW nor H-OLD is OTHER", r["verdicts"]["pb-n60"] == "OTHER")
# a replay where the two-model row matches H-OLD (E728's hash in the -n 2 shape)
d = world("rg-pb", srcmap={"pb-n40-a": ("e728", "t29-m2-40-64x64")})
_, r = S.pb_stage(d)
check("rg-pb: a -n 2 row that gives E728's own values is H-OLD", r["verdicts"]["pb-n40-a"] == "H-OLD", r["verdicts"])

# ---- the gate -----------------------------------------------------------------------------------------------------------
root = os.path.join(T, "gate-ok")
W.build(os.path.join(root, "rg-ctl"), "rg-ctl")
code, m = S.gate("rg-pb", [root])
check("gate: rg-ctl kept, every row run, class ok -> open", code == 0, m)
root2 = os.path.join(T, "gate-miss")
W.build(os.path.join(root2, "rg-ctl"), "rg-ctl", skip=("ctl-u-640x480",))
code, m = S.gate("rg-pb", [root2])
check("gate: a row not run -> closed, names the rerun", code == 1 and "rerun" in m, m)
root3 = os.path.join(T, "gate-fault")
W.build(os.path.join(root3, "rg-ctl"), "rg-ctl", cls={"ctl-u-640x480": (1, "fault")})
code, m = S.gate("rg-pb", [root3])
check("gate: a fault-class row -> closed", code == 1, m)
root4 = os.path.join(T, "gate-wrong")
W.build(os.path.join(root4, "rg-ctl"), "rg-ctl", mutate={"ctl-u-1024-n1": sub("hash 0xc9e301d225fe2325", "hash 0xdeadbeef")})
code, m = S.gate("rg-pb", [root4])
check("gate: an image mismatch is a result, the gate stays open", code == 0, m)
code, m = S.gate("rg-pb", [os.path.join(T, "nothing")])
check("gate: no rg-ctl kept -> closed", code == 1, m)
# newest attempt first: the first root that has rg-ctl
code, m = S.gate("rg-pb", [os.path.join(T, "nothing"), root])
check("gate: the stage is read from the first root that has it", code == 0, m)

# ---- the CLI and the freeze refusal -------------------------------------------------------------------------------------
PYX = sys.executable
r = subprocess.run([PYX, os.path.join(KP, "score", "score_rg.py"), "rg-ctl", os.path.join(root, "rg-ctl")], capture_output=True, text=True)
check("CLI: rg-ctl prints a line a row and one SUMMARY", r.returncode == 0 and r.stdout.count("\n") == 24 and r.stdout.strip().splitlines()[-1].startswith("SUMMARY: rg-ctl"), r.stdout[-300:])
r = subprocess.run([PYX, os.path.join(KP, "score", "score_rg.py"), "verdict", root], capture_output=True, text=True)
check("CLI: verdict names rg-pb as not run when only rg-ctl is kept", "SUMMARY: rg-pb: not run" in r.stdout and "SUMMARY: rg-ctl:" in r.stdout, r.stdout)
cp = os.path.join(T, "copy")
shutil.copytree(KP, cp, ignore=shutil.ignore_patterns("out", "tests", "__pycache__"))
with open(os.path.join(cp, "gen", "data", "old_values.tsv"), "a") as f:
    f.write("x\ty\tz\tOLD\tw\n")
r = subprocess.run([PYX, os.path.join(cp, "score", "score_rg.py"), "rg-ctl", os.path.join(root, "rg-ctl")], capture_output=True, text=True)
check("freeze: a changed frozen file makes the scorer refuse (rc 3)", r.returncode == 3 and "FROZEN FILES CHANGED" in r.stdout, r.stdout[-200:])
print("work dir: %s" % T)
sys.exit(1 if fails else 0)
