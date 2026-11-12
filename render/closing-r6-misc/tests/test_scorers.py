#!/usr/bin/env python3
"""test_scorers.py: the frozen scorers on argv-driven worlds (tests/worlds.py kept(): every row answered from its own argv) and on
broken kept directories.  Each verdict must follow the world: model (M-OR, rule A, H-COV), add (M-ADD), xor (the control FAILS:
cannot tell), floor (FLOOR), ceil (neither A nor FLOOR), hany (H-ANY), allfault; a missing file, a void row or a failed control is
never a pass; a store outside the target refutes the half-tile rule; the gate row's refusal reads as `odd heights refused`.
  python3 tests/test_scorers.py
"""
import gzip
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "score")]
import score_m as S  # noqa: E402
import worlds  # noqa: E402

T = tempfile.mkdtemp(prefix="scorers.", dir=os.path.join(KP, "debug"))
bad = n = 0


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


def score(st, world, mutate=None):
    d = worlds.kept(tempfile.mkdtemp(dir=T), st, world)
    if mutate:
        mutate(d)
    return S.SCORERS[st](S.Kept(d), S.load_preds(st))[1]


W = [("q289", "model", "Q289: M-OR held (20 of 20 held-out rows, 8 of 8 separating); M-ADD refuted (12 of 20 held-out rows, 0 of 8 separating); controls pass"),
     ("q289", "add", "Q289: M-OR refuted (12 of 20 held-out rows, 0 of 8 separating); M-ADD held (20 of 20 held-out rows, 8 of 8 separating); controls pass"),
     ("q289", "xor", "Q289: cannot tell: controls: f-ctl-64x32-x10: FAILED"),
     ("q289", "outside", "Q289: a store outside the target"),
     ("q287", "model", "Q287 (odd heights, W 34): rule A held on the held-out cells (7 of 7), FLOOR refuted (0 of 7); fit cell 19: A held, FLOOR refuted"),
     ("q287", "floor", "Q287 (odd heights, W 34): rule A refuted on the held-out cells (0 of 7), FLOOR held (7 of 7); fit cell 19: A refuted, FLOOR held"),
     ("q287", "ceil", "Q287: cannot tell: controls: z-ctl-34x18-y-t4: FAILED"),
     ("q287", "refuse-odd", "Q287: odd heights refused (gateodd: z-dry-34x17-y, class fail): not run"),
     ("q086", "model", "Q086: H-COV held (9 of 9 held-out rows), H-ANY refuted (6 of 9); 11 rows not run; control R passes"),
     ("q086", "hany", "Q086: H-COV refuted (6 of 20 held-out rows), H-ANY held (20 of 20); 0 rows not run; control R passes"),
     ("q086", "allfault", "Q086: H-COV refuted (")]
for st, w, want in W:
    s = score(st, w)
    check(s.startswith(want), "%s world %s: %s" % (st, w, s[:150]))


def drop(name, suf):
    return lambda d: os.remove(os.path.join(d, name + suf + ".gz"))


def ctlfail(d):
    p = os.path.join(d, "cases.tsv")
    s = open(p).read().replace("\tq086-1024x768-R\t", "\tq086-1024x768-R\t")
    lines = s.splitlines(True)
    lines = [ln.replace("\tok\t", "\tfail\t") if ln.startswith("q086-1024x768-R\t") else ln for ln in lines]
    open(p, "w").writelines(lines)


s = score("q287", "model", drop("z-34x7-y-r1", ".depth.1.bin"))
check("rule A held on the held-out cells (6 of 6)" in s, "q287: a missing dump makes its cell cannot tell (the cell's other run does not carry it): %s" % s[:110])
s = score("q287", "model", drop("z-ctl-34x18-y-t4", ".depth.1.bin"))
check(s.startswith("Q287: cannot tell: controls: z-ctl-34x18-y-t4: cannot tell"), "q287: a control without its dump shuts the gate (never a pass)")
s = score("q289", "model", drop("f-128x64-x10", ".txt"))
check("M-OR held (19 of 19 held-out rows, 7 of 7 separating)" in s, "q289: a row without output is cannot tell, not a pass: %s" % s[:100])
s = score("q086", "model", ctlfail)
check(s.startswith("Q086: cannot tell: controls: q086-1024x768-R: cannot tell"), "q086: R that did not complete shuts the gate: %s" % s[:100])


def onefault(d):
    p = os.path.join(d, "cases.tsv")
    lines = open(p).read().splitlines(True)
    lines = [ln.replace("\tok\t-\t-\t", "\tfault\t4\t0x20006061\t") if ln.startswith("q086-320x160-U2\t") else ln for ln in lines]
    open(p, "w").writelines(lines)


s = score("q086", "model", onefault)
check("H-COV refuted" in s and "H-ANY refuted" in s, "q086: a TA-side fault (not the 3D-side class) refutes both models: %s" % s[:100])


def mixed(d):
    src = os.path.join(d, "z-34x7-y-r2.depth.1.bin.gz")
    w2 = worlds.kept(tempfile.mkdtemp(dir=T), "q287", "floor")
    shutil.copy(os.path.join(w2, "z-34x7-y-r2.depth.1.bin.gz"), src)


s = score("q287", "model", mixed)
check("rule A refuted on the held-out cells (6 of 7)" in s, "q287: two runs of a cell that disagree are mixed, never held: %s" % s[:110])
print("%d of %d scorer checks" % (n - bad, n))
sys.exit(1 if bad else 0)
