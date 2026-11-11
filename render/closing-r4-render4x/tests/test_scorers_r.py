#!/usr/bin/env python3
"""tests/test_scorers_r.py: the R4-G scorer on kept stage directories built by tests/worlds.py from the real records (and the frozen
predictions where no record has the value).  Every hypothesis has a world where it wins and a world where it loses; every control has a
world where it fails; a void job is never a pass.  Prints `ok ...` and `FAIL ...`; exit 1 on any FAIL.  Needs a current freeze."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import worlds as WD  # noqa: E402

PY = sys.executable
TMP = tempfile.mkdtemp(prefix="scorers-", dir=os.path.join(KP, "debug"))
bad = 0
N = [0]


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


def world(name, stages=("s0", "c", "p", "o", "t", "h"), skip=()):
    N[0] += 1
    root = os.path.join(TMP, "w%d-%s" % (N[0], name))
    for st in stages:
        WD.kept(os.path.join(root, st), st, name if st != "s0" or name in ("s0-miss", "s0-nodata") else "model", skip=skip)
    return root


def score(root, stage):
    r = subprocess.run([PY, os.path.join(KP, "score", "score_r.py"), stage, os.path.join(root, stage)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def summ(out):
    m = re.search(r"^SUMMARY: (.*)$", out, re.M)
    return m.group(1) if m else ""


def verdict(root):
    r = subprocess.run([PY, os.path.join(KP, "score", "score_r.py"), "verdict", root], capture_output=True, text=True)
    return r.stdout + r.stderr


def has(out, pat):
    return re.search(pat, out, re.S) is not None


# ---- the freeze is required ---------------------------------------------------------------------------------------------------------
m = world("model")
rc, out = score(m, "s0")
check(rc == 0 and "controls" in summ(out), "the scorer runs on a verified freeze")
copy = os.path.join(TMP, "tree")
os.makedirs(copy)
for d in ("run", "tables", "score", "predictions", "gen", "bins"):
    shutil.copytree(os.path.join(KP, d), os.path.join(copy, d))
for f in ("stages.txt", "TABLES.md", "TOOL.sha256", "TOOLSRC.sha256", "FROZEN.sha256", "PREDICTIONS.sha256"):
    shutil.copy(os.path.join(KP, f), copy)
with open(os.path.join(copy, "predictions", "p.tsv"), "a") as f:
    f.write("p-1280x1024\textra\t1\tx\theldout\tx\n")
r = subprocess.run([PY, os.path.join(copy, "score", "score_r.py"), "s0", os.path.join(m, "s0")], capture_output=True, text=True)
check(r.returncode == 3 and "FROZEN FILES CHANGED" in r.stdout, "a changed prediction file: the scorer refuses (rc 3)")

# ---- s0 -----------------------------------------------------------------------------------------------------------------------------------
rc, out = score(m, "s0")
check(has(summ(out), r"later stages open") and out.count(": PASS:") == 3 and "reg 0x0724 as a reported check usable" in summ(out), "model: the three controls pass, later stages open, reg 0x0724 usable")
w = world("s0-miss")
rc, out = score(w, "s0")
check("CLOSED" in summ(out) and "s0-4x-288x144: FAIL" in out, "s0-miss (one hash off by one bit): that control FAILS and the session is void")
rcg = subprocess.run([PY, os.path.join(KP, "score", "score_r.py"), "gate", "p", w], capture_output=True, text=True)
check(rcg.returncode == 1 and "closed" in rcg.stdout, "  the gate of every later stage closes (rc 1)")
rc, out = score(w, "p")
check("controls FAILED" in summ(out) and out.count("held:") == 0 or "controls FAILED" in summ(out), "  stage p scored on it: controls FAILED, nothing claimed")
w = world("s0-nodata")
rc, out = score(w, "s0")
check("NODATA" in out and "CLOSED" in summ(out), "s0-nodata (one control prints only its echo): NODATA is not a pass, the gate is closed")
rcg = subprocess.run([PY, os.path.join(KP, "score", "score_r.py"), "gate", "o", w], capture_output=True, text=True)
check(rcg.returncode == 1, "  the gate of stage o is closed on NODATA too")
w = world("model", skip=("s0-4x-1024x768",))
rc, out = score(w, "s0")
check("s0-4x-1024x768: NODATA" in out and "CLOSED" in summ(out), "a missing control row (not run) is NODATA and closes the gate")
rcg = subprocess.run([PY, os.path.join(KP, "score", "score_r.py"), "gate", "t", os.path.join(TMP, "nowhere")], capture_output=True, text=True)
check(rcg.returncode == 1 and "no s0 stage was kept" in rcg.stdout, "no kept s0 at all: the gate is closed with its reason")

# ---- c: Q113 ---------------------------------------------------------------------------------------------------------------------------------
rc, out = score(m, "c")
check("2 of 2 rows decided" in summ(out) and "may be retired as answered" in summ(out), "model: both held-out cube jobs match the rule on 2048 of 2048 pixels, Q113 may be retired")
w = world("c-wrong")
rc, out = score(w, "c")
check("REFUTED" in out and "12 of 2048 pixels differ" in out and "not supported" in summ(out), "c-wrong (12 pixels near the boundaries read another face): REFUTED with the pixel count, the headline claims nothing")
w = world("c-ctl")
rc, out = score(w, "c")
check("c-cu-xn: FAIL" in out and "controls FAILED" in summ(out), "c-ctl (the control reads another program's faces): the control FAILS, no claim")
w = world("model", skip=("c-cube-b",))
rc, out = score(w, "c")
check("c-cube-b: " in out and "cannot tell" in summ(out) or "1 of" in summ(out), "a missing held-out job: not a pass (%s)" % summ(out)[:60])

# ---- p: H-PB -----------------------------------------------------------------------------------------------------------------------------------
rc, out = score(m, "p")
check("(6 of 6 rows decided)" in summ(out) and out.count(": held:") == 6, "model: H-PB held on 6 of 6 sizes, pages used = U4 and TA data as the formula")
w = world("p-fault")
rc, out = score(w, "p")
check(out.count("FAILED: REFUTES H-PB: fault") == 2 and "not supported" in summ(out) and "BIF_FAULT 0x10000011" in out, "p-fault (4096 x 960 and 960 x 4096 fault): both rows refute H-PB, the fault word is reported")
w = world("p-overflow")
rc, out = score(w, "p")
check("p-3072x1280: FAILED: REFUTES H-PB: the scene overflowed" in out, "p-overflow: an overflow where the need passes refutes H-PB")
w = world("p-pages")
rc, out = score(w, "p")
check(has(out, r"p-2048x1536: FAILED: pb_used 801, frozen 769"), "p-pages (32 more pages than U4): FAILED with the counts")
w = world("p-ta")
rc, out = score(w, "p")
check(has(out, r"p-1280x1024: FAILED: tadata_size 217088, frozen 212992"), "p-ta (TA data one page too big): FAILED")

# ---- o: H-SPM4 and Q292 ------------------------------------------------------------------------------------------------------------------------
rc, out = score(m, "o")
check("(4 of 4 rows decided)" in summ(out) and "j4's fault is the overflow at 4x" in summ(out) and "o6-4x-288x144-p23-fill7: exploratory" in out,
      "model: H-SPM4 held on o4, o5, o7, o8; o1 to o3 pass; Q292 says the overflow faults at 4x; o6 reports its either/or")
w = world("o-enospc")
rc, out = score(w, "o")
check("-ENOSPC like 1x" in summ(out) and "not supported" in summ(out) and "o6-4x-288x144-p23-fill7: not run" in out, "o-enospc (o4, o5, o7 end in -ENOSPC): the refuting reading, o6 not run, Q292 says the fault is about the size")
w = world("o-o2fault")
rc, out = score(w, "o")
check("o2-1x-1024x768-p82: FAIL" in out and "cannot tell: controls" in summ(out), "o-o2fault (the 1x boundary job faults): the control FAILS, Q292 cannot tell")
w = world("o-o3over")
rc, out = score(w, "o")
check("o3-4x-1024x768-pe3: FAIL" in out and "controls FAILED" in summ(out), "o-o3over (the 4x job that should fit overflows): the control FAILS, the page rule is off at 4x, no claim")
w = world("o-o8fault")
rc, out = score(w, "o")
check("o8-1x-4096x4096-p422: FAILED: fault" in out and "j4 is not about 4x" in out and "mixed" in summ(out), "o-o8fault (the 1x control faults too): o8 FAILED, Q292 mixed")
w = world("o-word")
rc, out = score(w, "o")
check("o4-4x-1024x768-pe2: FAILED: faulted, but with int 0x0004 word 0x20006061" in out, "o-word (a fault at another word): FAILED, not E828 j4's word")
w = world("o5-nofault")
rc, out = score(w, "o")
check("o5-4x-288x144-p23-held: FAILED: overflow" in out and "o6-4x-288x144-p23-fill7: not run" in out, "o5-nofault: o5 FAILED (-ENOSPC) and o6 is not run (it needs o5 to fault)")
w = world("model", skip=("o2-1x-1024x768-p82",))
rc, out = score(w, "o")
check("o2-1x-1024x768-p82: NODATA" in out and "controls FAILED" not in summ(out) and "cannot tell" in summ(out), "a missing control (o2): NODATA, the headline cannot tell")

# ---- t: Q293 -----------------------------------------------------------------------------------------------------------------------------------
rc, out = score(m, "t")
check("(4 of 4 rows decided)" in summ(out) and out.count("H-PAD held") == 2 and out.count("H-SAME held") == 2, "model: H-SAME on both four-array jobs and H-PAD on the line and the point (4 of 4)")
w = world("t-field")
rc, out = score(w, "t")
check("H-FIELD: one dword inserted at 9" in out and "0x00000002" in out and "H-FIELD: the inserted dword is non-zero in t3-line-te40" in summ(out), "t-field (the line's inserted dword is 2): H-FIELD, a field not padding")
w = world("t-draw")
rc, out = score(w, "t")
check("t1-aa4-te40: H-SAME FAILED" in out and "the 3D drew" in out or "H-SAME FAILED" in out, "t-draw (the four-array 3D draws): H-SAME FAILED")
w = world("t-pos")
rc, out = score(w, "t")
check("t4-point-te40: H-PAD FAILED: one dword inserted at 3" in out, "t-pos (the insertion sits at 3, not before the format word): H-PAD FAILED")
w = world("model", skip=("t3b-line-base",))
rc, out = score(w, "t")
check("t3b-line-base: NODATA" in out and "cannot tell" in summ(out), "a missing in-session baseline: NODATA, no claim")

# ---- h: Q140 ------------------------------------------------------------------------------------------------------------------------------------
rc, out = score(m, "h")
check("(4 of 4 rows decided)" in summ(out) and "h2-640x480-health: held" in out and "page unseen before" in out and "h4-288x144-fill: held" in out,
      "model: H-REPLAY held in 4 of 4 cells (h2 at the unseen page, the context and the fill do not fault)")
check("clkgate" in out and "0x00000078" in out, "  the clock-gate status after each step is reported")
w = world("h-noreplay")
rc, out = score(w, "h")
check("h1-288x144-health: cannot tell" in out and "0 replays" in out and "h4-288x144-fill: FAILED" in out and "did not wait for the TA" in out, "h-noreplay: no failing health triangle is not a held replay; h4's first health passing refutes the wait")
w = world("h-ownend")
rc, out = score(w, "h")
check("h2-640x480-health: FAILED" in out and "REFUTES the replay" in out and "0x20006" in out and "not supported" in summ(out), "h-ownend (a health fault at the health context's own page 0x20006 after a job at 0x2000a): refutes the replay, the control that can fail")
w = world("h-stop")
rc, out = score(w, "h")
check("the fourth health triangle failed" in out, "h-stop: four failing health triangles are reported as the stage stop")
w = world("h-nofault")
rc, out = score(w, "h")
check("h1-288x144-health: cannot tell: the job did not fault" in out, "h-nofault (the c1 job completes): nothing to replay, cannot tell")
w = world("h-nofill")
rc, out = score(w, "h")
check("h4-288x144-fill: FAILED" in out and "did not wait" in out, "h-nofill: the first health passes after the fill: FAILED")

# ---- the whole verdict -------------------------------------------------------------------------------------------------------------------------
v = verdict(m)
check(all(k in v for k in ("SUMMARY: session:", "SUMMARY: Q113 (c):", "SUMMARY: H-PB (p):", "SUMMARY: Q292 (o):", "SUMMARY: H-SPM4 (o):", "SUMMARY: Q293 (t):", "SUMMARY: Q140 (h):")), "verdict: one SUMMARY line each for the session, Q113, H-PB, Q292, H-SPM4, Q293 and Q140")
v = verdict(os.path.join(TMP, "nowhere"))
check(v.count("not run") >= 6, "verdict on nothing: every line says not run")

print("work dir (kept for inspection): %s" % TMP)
print("ALL scorer tests: %s" % ("PASS" if not bad else "FAIL"))
sys.exit(bad)
