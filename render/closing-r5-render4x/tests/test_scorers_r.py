#!/usr/bin/env python3
"""tests/test_scorers_r.py: the frozen scorer on argv-driven worlds (tests/worlds.py) built from the real kept records.
  - the all-hypotheses-held world: every stage decides; any NODATA, READER-MISS or "cannot tell" fails the suite;
  - one world a Q292 rule (the rule's faults computed from each row's argv; a threshold rule at one threshold): the verdict names that
    rule and no other, except the threshold rules the session's cells cannot separate (K-TPM, K-P, K-AREA: named together, the
    world's rule among them); x runs only in the H-TPC worlds (the gate);
  - worlds where o, t, s0, m or d fail as the plan says they can, each read as that failure;
  - the reader: a probe dump under round 4's assumed name (NAME.tri.*) is a READER-MISS, not NODATA; insertion() refuses a missing side;
  - the gate across attempts: s0 in one attempt, t in the next, the gate file naming s0's directory: t's controls PASS (round 4 printed
    NODATA there); without the gate file the parent is read (the old behaviour, NODATA);
  - REGRESSION: round 4's own frozen scorer on this world's correctly named t directory prints NODATA for t3b and t4b.
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import score_r as S  # noqa: E402
import worlds as WD  # noqa: E402

PY = os.environ.get("PY", sys.executable)
R4 = "/Users/jtorra/src/scratch/resgx545/closing4/r4-render4x"
os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
TMP = tempfile.mkdtemp(prefix="scorers-", dir=os.path.join(KP, "debug"))
S.preds()
bad = 0


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


def session(world, stages=("s0", "t", "o", "m", "l", "x", "d")):
    """A kept attempt as the driver makes it: x only when its gate is open."""
    d = tempfile.mkdtemp(prefix=world.replace(":", "_") + "-", dir=TMP)
    for st in stages:
        if st == "x" and S.gate("x", [d])[0] != 0:
            continue
        WD.kept(os.path.join(d, st), st, world)
    return d


def text_of(d):
    out = []
    for st in WD.STAGES:
        if os.path.exists(os.path.join(d, st, "cases.tsv")):
            ls, r = S.score_stage(st, os.path.join(d, st))
            out += ls + ["SUMMARY: " + r["summary"]]
    return "\n".join(out)


# ---- the model world ----------------------------------------------------------------------------------------------------------------
d = session("model")
v = S.verdict([d])
allt = text_of(d) + "\n" + v
for w in ("NODATA", "READER-MISS", "cannot tell", "not supported", "FAILED"):
    check(w not in allt, "model world: no %r anywhere in the stage scores or the verdict" % w)
for k in ("SUMMARY: session: s0: controls", "SUMMARY: Q293 (t): Q293: the dword", "(6 of 6 rows decided)", "SUMMARY: H-ENOSPC4 (o): H-ENOSPC4",
          "SUMMARY: H-TPC (m): H-TPC", "(4 of 4 rows decided)", "SUMMARY: Q292 (m, l, x): the rules no decided row contradicts (13 rows of m, l, x): TPC-d-rgn",
          "SUMMARY: d: E845's fault replicated; scene pages 321", "extent fits d (TPC-d-rgn or TPC-d-state)", "the need is 49: E846's sentence"):
    check(k in v, "model world verdict has: %s" % k)
check(os.path.exists(os.path.join(d, "x", "cases.tsv")), "model world: H-TPC held in m, so x's gate opened")

# ---- one world a rule -----------------------------------------------------------------------------------------------------------------
for rule in R.RULES:
    d = session("rule:" + rule)
    v = S.verdict([d])
    line = [ln for ln in v.splitlines() if ln.startswith("SUMMARY: Q292")][0]
    names = line.split(": ", 3)[-1]
    xran = os.path.exists(os.path.join(d, "x", "cases.tsv"))
    got = [r for r in R.RULES if r in names.split("; ")[0].replace(",", " ").split()]
    if rule in R.KTHR:
        ok = rule in got and set(got) <= set(R.KTHR) and len(got) >= 2 and "not separated" in names
        check(ok and not xran, "world %s: the verdict names the threshold family %s (the world's rule among them, x gated)" % (rule, got))
    else:
        check(got == [rule] and xran == (rule in R.HTPC), "world %s: the verdict names %s and no other (x %s)" % (rule, got, "ran" if xran else "gated"))

# ---- failures the plan says can happen ------------------------------------------------------------------------------------------------
d = session("m-split", ("s0", "m"))
v = S.verdict([d])
check("SPLIT: m1 fault, m2 complete" in v and "not supported" in v and S.gate("x", [d])[0] == 1, "world m-split: reported as a split, H-TPC not held, x gated")
d = session("d-complete", ("s0", "m", "l", "d"))
v = S.verdict([d])
check("VOID: row d (E845's own cell) completed" in v and "COMPLETED: stages l and m are void" in v, "world d-complete: a completion in d voids l and m")
d = session("d-short", ("s0", "d"))
v = S.verdict([d])
check("held dump not read (61 bytes, 62 bytes): the dump lines cannot tell" in v and "E845's fault replicated" in v,
      "world d-short: an error-text held dump is 'held dump not read', the fault still replicated")
d = session("o-fault4", ("s0", "o"))
v = S.verdict([d])
check("REFUTED by a fault in o4-4x-1024x768-pe2, o5-4x-288x144-p23, o7-4x-640x480-p6d, o9-4x-512x384-p52" in v and "not supported" in v,
      "world o-fault4: a fault in an overflowing 4x row refutes H-ENOSPC4")
d = session("o-ctl", ("s0", "o"))
v = S.verdict([d])
check("controls FAILED: o2-1x-1024x768-p34" in v, "world o-ctl: o2 completing (one page under its twins' need) fails the control: no H-ENOSPC4 claim")
d = session("t-field", ("s0", "t"))
v = S.verdict([d])
check("H-FIELD: the inserted dword is non-zero in t3c-line-te80, t4c-point-te80" in v, "world t-field: a non-zero dword at 0x80 reads H-FIELD")
d = session("t-pos", ("s0", "t"))
v = text_of(d)
check("t4c-point-te80 (held out): H-PAD FAILED: one dword inserted at 3 (frozen 11)" in v, "world t-pos: an insertion elsewhere fails H-PAD")
d = session("t-draw", ("s0", "t"))
check("t1-aa4-te40 (replicate of E847): H-SAME FAILED" in text_of(d), "world t-draw: a drawn image fails H-SAME")
d = session("s0-miss", ("s0",))
code, msg = S.gate("t", [d])
check(code == 1 and "s0-4x-288x144: FAILED" in msg, "world s0-miss: a control hash off closes every later gate: %s" % msg.splitlines()[0][:90])

# ---- the reader ----------------------------------------------------------------------------------------------------------------------
d = session("model", ("s0", "t"))
t2 = os.path.join(TMP, "t-r4names", "t")
shutil.copytree(os.path.join(d, "t"), t2)
for f in os.listdir(t2):
    if ".p1131-" in f:
        os.rename(os.path.join(t2, f), os.path.join(t2, f.replace(".p1131-green__0.", ".tri.").replace(".p1131-psizes__1.", ".tri.")))
ls, r = S.t_stage(t2, os.path.join(d, "s0"))
check(r["misses"] == ["t3b-line-base", "t4b-point-base", "t3-line-te40", "t4-point-te40", "t3c-line-te80", "t4c-point-te80"] and r["q293"].startswith("READER-MISS"),
      "a probe dump under the name round 4 assumed (NAME.tri.*) is a READER-MISS, named in the summary: %s" % r["q293"][:70])
try:
    S.insertion(None, [1, 2, 3])
    check(False, "insertion() refuses a missing side")
except ValueError:
    check(True, "insertion() refuses a missing side (round 4 printed 'no single insertion' on no data)")

# ---- the gate across attempts --------------------------------------------------------------------------------------------------------
a1 = tempfile.mkdtemp(prefix="att1-", dir=TMP)
a2 = tempfile.mkdtemp(prefix="att2-", dir=TMP)
WD.kept(os.path.join(a1, "s0"), "s0", "model")
WD.kept(os.path.join(a2, "t"), "t", "model")
code, msg = S.gate("t", [a2, a1])
open(os.path.join(a2, "gate-t.txt"), "w").write(msg + "\n")
check(code == 0 and ("s0 at %s/s0" % a1) in msg, "gate across attempts: open, and it names the attempt that holds s0")
ls, r = S.t_stage(os.path.join(a2, "t"))
check(all(v == "PASS" for k, v in r["controls"].items() if k.startswith("s0:")) and "(6 of 6 rows decided)" in r["q293"],
      "the stage scorer reads s0 where the gate file says: its controls PASS (round 4: NODATA)")
os.remove(os.path.join(a2, "gate-t.txt"))
ls, r = S.t_stage(os.path.join(a2, "t"))
check(all(v == "NODATA" for k, v in r["controls"].items() if k.startswith("s0:")),
      "REGRESSION: without the gate file the parent is read and s0 is NODATA (round 4's slip, reproduced)")

# ---- REGRESSION: round 4's frozen scorer on the correctly named mock ----------------------------------------------------------------
d = session("model", ("s0", "t"))
code = ("import sys; sys.path[:0] = [%r, %r]; import score_r as S; S.preds(); lines, r = S.t_stage(%r, [%r]); print('\\n'.join(lines))"
        % (R4 + "/score", R4 + "/gen", os.path.join(d, "t"), d))
p = subprocess.run([PY, "-c", code], capture_output=True, text=True, cwd=TMP, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
out = p.stdout
check("t3b-line-base: NODATA" in out and "t4b-point-base: NODATA" in out,
      "REGRESSION: round 4's frozen scorer on the correctly named mock prints NODATA for t3b and t4b (%s)" % (p.stderr.strip().splitlines()[-1:] or "ran"))
ls, r = S.t_stage(os.path.join(d, "t"))
check(r["controls"]["t3b-line-base"] == "PASS" and r["controls"]["t4b-point-base"] == "PASS", "  the fixed scorer on the same directory: t3b and t4b PASS")
print("work dir (kept for inspection): %s" % TMP)
sys.exit(bad)
