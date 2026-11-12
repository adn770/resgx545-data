#!/usr/bin/env python3
"""test_gen.py: the tables, predictions, TABLES.md, stages.txt and sources.lst are exactly what gen/hgen.py writes; the plan's numbers
(2 s0 rows, 6 q cells, 3 flushed, 3 with a fill, the order a0 b0 a1 b1 a2 b2); every q cell has its H-JOB controls and H-END; every
flushed cell its H-KEEP controls and one H-FLUSH and one H-PEND first_tri row; every fill cell H-FILL; H-LIST and H-WORD each in a1 and
a2 only, with different words; every prediction row of q names a cell of the table and every quantity is one the scorer reads.
"""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
import score_h as S  # noqa: E402

fails = 0


def check(c, m):
    global fails
    print(("ok   " if c else "FAIL ") + m)
    fails += 0 if c else 1


r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen", "hgen.py"), "--check"], capture_output=True, text=True)
check(r.returncode == 0, "gen/hgen.py --check: the generated files are current %s" % r.stdout.strip())
rows = [l.split("|") for l in open(os.path.join(KP, "tables", "q.txt")).read().splitlines() if l and not l.startswith("#")]
names = [x[0] for x in rows]
check(names == ["a0-640-health", "b0-640-flush-health", "a1-640-fill", "b1-640-flush-fill", "a2-288-fill", "b2-288-flush-health"],
      "q: six cells in the order a0 b0 a1 b1 a2 b2")
check(sum(" flush" in x[3] for x in rows) == 3 and sum("cell:fill" in x[3] for x in rows) == 3, "q: three flushed cells, three with a fill")
s0 = [l.split("|") for l in open(os.path.join(KP, "tables", "s0.txt")).read().splitlines() if l and not l.startswith("#")]
check([x[0] for x in s0] == ["n0-gate", "c1-tri"], "s0: n0-gate, c1-tri")
P = S.load_predictions("q.tsv", KP)
by = lambda c, m=None, q=None: [p for p in P if p["case"] == c and (m is None or p["model"] == m) and (q is None or p["q"] == q)]  # noqa: E731
for c in names:
    check(len(by(c, "H-JOB")) == 3 and len(by(c, "H-END")) == 1, "%s: three H-JOB controls and H-END" % c)
    if "flush" in c:
        check(len(by(c, "H-KEEP")) == 2 and len(by(c, "H-FLUSH", "first_tri")) == 1 and len(by(c, "H-PEND", "first_tri")) == 1
              and len(by(c, "H-BOOT")) == 1 and len(by(c, "H-LATCH")) == 2, "%s: H-KEEP 2, H-FLUSH, H-PEND, H-BOOT, H-LATCH 2" % c)
    if "fill" in c:
        check(len(by(c, "H-FILL")) == 1, "%s: H-FILL" % c)
for c in names:
    l, w = by(c, "H-LIST"), by(c, "H-WORD")
    if c in ("a1-640-fill", "a2-288-fill"):
        check(len(l) == 1 and len(w) == 1 and l[0]["want"] != w[0]["want"], "%s: H-LIST %s and H-WORD %s differ" % (c, l[0]["want"], w[0]["want"]))
    else:
        check(not l and not w, "%s: no H-LIST or H-WORD row" % c)
QS = {"job_class", "job_int", "job_word", "fill_class", "first_tri", "first_word", "passes_within", "flush_rc", "flush_ctrl_same",
      "flush_int", "flush_word", "minus110_reset"}
check(all(p["case"] in names for p in P), "every q prediction names a cell of the table")
check({p["q"] for p in P} <= QS, "every q quantity is one score_h.cell_got reads")
check({p["set"] for p in P} <= {"control", "heldout", "replicate"}, "sets: control, heldout, replicate")
print("generator checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
