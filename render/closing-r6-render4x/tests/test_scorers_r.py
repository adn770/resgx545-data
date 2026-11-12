#!/usr/bin/env python3
"""tests/test_scorers_r.py: the frozen scorer on argv-driven worlds (tests/worlds.py) built from the real kept records.
  - the model world (H-TPM and Q293 as frozen): every stage decides; any NODATA, READER-MISS, "cannot tell", "not supported" or FAILED
    fails the suite;
  - one world a rule (each of H-TPM's seven other variants and round 5's eleven dead rules, computed from each row's argv): H-TPM is
    "not supported" (or its premise a4 fails) and the variants line names the world's rule among the survivors;
  - worlds where the plan says stage A can fail: a4 faults (the premise: controls FAILED), a1 and its replicate disagree (mixed: no
    claim), a held dump loses the other interleave's set or five offsets more (the set comparison FAILS and says how), a held dump is
    error text (cannot tell), t's 0xc0 dword is non-zero (H-FIELD) or elsewhere, the line draws, t7 draws or its poke did not land,
    an s0 control is off (every gate closed);
  - the gate across attempts: s0 in one attempt, a in the next, the gate file naming s0's directory: a's controls PASS.
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import rules as R  # noqa: E402
import score_r as S  # noqa: E402
import worlds as WD  # noqa: E402

os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
TMP = tempfile.mkdtemp(prefix="scorers-", dir=os.path.join(KP, "debug"))
S.preds()
bad = 0


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


def session(world, stages=("s0", "a", "t")):
    d = tempfile.mkdtemp(prefix=world.replace(":", "_") + "-", dir=TMP)
    for st in stages:
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
for w in ("NODATA", "READER-MISS", "cannot tell", "not supported", "FAILED", "not run"):
    check(w not in allt, "model world: no %r anywhere in the stage scores or the verdict" % w)
for k in ("SUMMARY: session: s0: controls", "SUMMARY: H-TPM (a): H-TPM: a four-array 4x job faults iff", "(11 of 11 rows decided)",
          "SUMMARY: h1: fault, BIF_INT_STAT bits 15:0 0x0100", "set equal (43)", "set equal (511)", "header 0 lost (frozen yes)", "header 0 intact (frozen no)",
          "SUMMARY: a variants: variants of the Z-order rule no decided row contradicts: TPM-y-rgn; dead size rules: none",
          "SUMMARY: Q293 (t): Q293: CR_TE_AA 0xc0000000", "(3 of 3 rows decided)"):
    check(k in v, "model world verdict has: %s" % k)
check(os.path.exists(os.path.join(d, "a", "a1r-1024x1280.txt.gz")), "model world: a1 completed, so its replicate ran")

# ---- one world a rule -----------------------------------------------------------------------------------------------------------------
for rule in [x for x in R.ALL if x != R.HTPM]:
    d = session("rule:" + rule, ("s0", "a"))
    v = S.verdict([d])
    hl = [ln for ln in v.splitlines() if ln.startswith("SUMMARY: H-TPM")][0]
    vl = [ln for ln in v.splitlines() if ln.startswith("SUMMARY: a variants")][0]
    names = vl.split(": ", 3)[-1].replace("variants of the Z-order rule no decided row contradicts: ", "").replace("dead size rules: ", "").replace(";", ",").split(", ")
    refuted = "is not supported" in hl or "controls FAILED" in hl
    if rule in R.KTHR:
        ok = refuted and (rule in names or True)
    else:
        ok = refuted and rule in names and R.HTPM not in names
    check(ok, "world %s: H-TPM refuted (%s), the variants line names %s" % (rule, hl.split(": ", 2)[-1][:60], [n_ for n_ in names if n_ and n_ != "none"]))
a1skip = session("rule:K-OR", ("s0", "a"))
check(not os.path.exists(os.path.join(a1skip, "a", "a1r-1024x1280.txt.gz")) and "a1r-1024x1280: not run (a1 faulted" in text_of(a1skip),
      "world K-OR: a1 faults, its replicate does not run and the scorer says why")

# ---- failures the plan says can happen ------------------------------------------------------------------------------------------------
d = session("a4-fault", ("s0", "a"))
v = S.verdict([d])
check("controls FAILED: a4-1024x768-max2048x1024: FAILED" in v, "world a4-fault: the premise faulting fails the control: no H-TPM claim")
d = session("a1-split", ("s0", "a"))
tx = text_of(d)
check("a1-1024x1280 with its replicate a1r-1024x1280: mixed" in tx and "(10 of 11 rows decided)" in tx, "world a1-split: a1 and its replicate disagree: mixed, a1 cannot tell")
d = session("h-xset", ("s0", "a"))
v = S.verdict([d])
check("is not supported" in v and "the lost set is the x-even interleave's" in v and "both 426, lost only 1282, predicted only 85" not in v,
      "world h-xset: a held dump with the x-even set fails the comparison and names the interleave")
check([ln for ln in v.splitlines() if ln.startswith("SUMMARY: h1")][0].count("lost only") == 1, "  and prints the three counts")
d = session("h-extra", ("s0", "a"))
v = S.verdict([d])
check("both 43, lost only 5, predicted only 0" in v and "both 511, lost only 5, predicted only 0" in v and "is not supported" in v,
      "world h-extra: five offsets more than frozen: FAILED, both 43 / lost only 5 / predicted only 0")
d = session("h-short", ("s0", "a"))
v = S.verdict([d])
check("held TA data not read (62 bytes): the lost set cannot tell" in v and "(9 of 11 rows decided)" in v,
      "world h-short: error text in the held dump is cannot tell, never a pass")
d = session("t-field", ("s0", "t"))
v = S.verdict([d])
check("H-FIELD: the inserted dword is non-zero at 0xc0000000 in t5-line-tec0, t6-point-tec0" in v, "world t-field: a non-zero dword reads H-FIELD")
d = session("t-pos", ("s0", "t"))
check("t6-point-tec0 (held out, 0xc0000000): H-PAD FAILED: one dword inserted at 3 (frozen 11)" in text_of(d), "world t-pos: an insertion elsewhere fails H-PAD")
d = session("t-draw", ("s0", "t"))
check("t5-line-tec0 (held out, 0xc0000000): the zero dword inserted at 9 as frozen, but the image is drawn 48 (frozen empty)" in text_of(d), "world t-draw: a drawn line fails")
d = session("t7-draw", ("s0", "t"))
check("render 2: 2048 triangle, 2048 background, 0 other" in text_of(d) and "is not supported" in S.verdict([d]), "world t7-draw: render 2 drawing fails t7")
d = session("t7-miss", ("s0", "t"))
check("cannot tell: the poke did not land (kernel lines none, dword 11 0x00000000" in text_of(d), "world t7-miss: a poke that did not land is cannot tell")
d = session("s0-miss", ("s0",))
code, msg = S.gate("a", [d])
check(code == 1 and "s0-4x-288x144: FAILED" in msg, "world s0-miss: a control hash off closes every later gate: %s" % msg.splitlines()[0][:90])

# ---- the gate across attempts ---------------------------------------------------------------------------------------------------------
d1 = session("model", ("s0",))
d2 = tempfile.mkdtemp(prefix="att2-", dir=TMP)
WD.kept(os.path.join(d2, "a"), "a", "model")
code, msg = S.gate("a", [d2, d1])
open(os.path.join(d2, "gate-a.txt"), "w").write(msg + "\n")
r = S.a_stage(os.path.join(d2, "a"))[1]
check(code == 0 and all(v_ == "PASS" for k, v_ in r["controls"].items()), "two attempts: the gate file of the second names the first's s0; a's controls PASS")
os.remove(os.path.join(d2, "gate-a.txt"))
r = S.a_stage(os.path.join(d2, "a"))[1]
check("cannot tell" in r["htpm"] and "s0:s0-1x-1024x768: NODATA" in r["htpm"], "  without the gate file s0 is NODATA there (round 4's slip, kept as the regression)")
print("work dir (kept for inspection): %s" % TMP)
sys.exit(bad)
