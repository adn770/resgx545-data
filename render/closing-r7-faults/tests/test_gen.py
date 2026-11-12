#!/usr/bin/env python3
"""test_gen.py: the tables, predictions, TABLES.md, stages.txt and sources.lst are exactly what gen/fgen.py writes, and bins/ what
gen/asm_l.py assembles (l0 and l4 E088's kept programs byte for byte); the plan's numbers (s0 2 rows, l 5, d 7, m 6 in the order M0
M1 M2 M2 M1 M0); the layout's pages against every kept fault page (E507's six faulting sizes, E729's three, E789's a6, E848's two,
and E507/E729's completed sizes give no page); 0x20007 has no size (the README's deviation) and 0x20009 only at side 64; every
control declares a reading its row can produce (scorekit.refuse_unreadable), and a control on a row that cannot produce it is
refused; every prediction names a row of its table and a quantity the scorer reads.
"""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import fgen  # noqa: E402
import scorekit  # noqa: E402

fails = 0


def check(c, m):
    global fails
    print(("ok   " if c else "FAIL ") + m)
    fails += 0 if c else 1


for g in ("fgen.py", "asm_l.py"):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen", g), "--check"], capture_output=True, text=True)
    check(r.returncode == 0, "gen/%s --check: the generated files are current %s" % (g, r.stdout.strip()))


def rows(st):
    return [l.split("|") for l in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines() if l and not l.startswith("#")]


check([r[0] for r in rows("s0")] == ["n0-clr-idle", "c1-tri"], "s0: n0 (the kregnow gate row) and c1")
check([r[0][:2] for r in rows("l")] == ["l0", "l1", "l2", "l3", "l4"], "l: five rows l0 to l4, l4 (the kept hang) last")
check(len(rows("d")) == 7 and [r[0][:2] for r in rows("d")[:2]] == ["d0", "d1"], "d: seven cells, the two controls first")
check([r[0][1:3] for r in rows("m")] == ["0a", "1a", "2a", "2b", "1b", "0b"], "m: six cells in the order M0 M1 M2 M2 M1 M0")
check(sum(" clr" in r[3] for r in rows("m")) == 2 and sum(" long" in r[3] for r in rows("m")) == 2, "m: two clr cells, two long cells")
check(sum("ctl640" in r[3] for r in rows("d")) == 1 and "ctl640" in rows("d")[0][3], "d: d0 alone carries ctl640")

# the layout against the kept fault pages (page per size) and completions
KEPT = {(320, 160): 0x20006, (384, 192): 0x20006, (448, 224): 0x20006, (512, 256): 0x20006, (512, 384): 0x20008, (640, 480): 0x2000a,
        (288, 144): 0x20006, (256, 288): 0x20006, (384, 384): 0x20008, (320, 400): 0x20008}
DONE = [(64, 64), (128, 64), (128, 128), (256, 128), (96, 48), (192, 96), (256, 160), (320, 128)]
bad = {s: hex(fgen.fault_page(*s) or 0) for s, p in KEPT.items() if fgen.fault_page(*s) != p}
check(not bad, "the layout gives every kept fault page (E507 6, E729 3, E789 a6): %s" % (bad or "all %d" % len(KEPT)))
check(all(fgen.fault_page(*s) is None for s in DONE), "the layout gives no fault for the %d kept completed sizes (E507, E729)" % len(DONE))
pages = {fgen.fault_page(w, h) for w in range(32, 2049, 32) for h in range(16, 1025, 16) if w * h <= 2048 * 1024}
check(0x20007 not in pages, "no size of 32 to 2048 x 16 to 1024 faults at 0x20007 (the deviation: 384 x 384 takes its cell)")
check(fgen.layout(128, 528)["side"] == 64 and fgen.fault_page(128, 528) == 0x20009, "128 x 528: side 64, page 0x20009")
for name, (w, h), _ in fgen.D_CELLS:
    r = next(x for x in rows("d") if x[0] == name)
    check("--width %d --height %d --max-width %d --max-height %d" % (w, h, w, h) in r[5], "%s: its row runs %d x %d" % (name, w, h))

# the controls: each declares readings its row can produce; a misplaced one is refused
tables = {st: open(os.path.join(KP, "tables", st + ".txt")).read() for st in ("s0", "l", "d", "m")}
preds = {st: open(os.path.join(KP, "predictions", st + ".tsv")).read() for st in ("s0", "l", "d", "m")}
ctl = fgen.controls(tables, preds)
check(len(ctl) >= 30 and not scorekit.control_read_problems(ctl, fgen.producible), "%d controls, each readable from its row" % len(ctl))
bad_ctl = dict(ctl)
bad_ctl["m0a-none:M-CLR"] = (("clr_hidden",), next(l for l in tables["m"].splitlines() if l.startswith("m0a")))
try:
    scorekit.refuse_unreadable(bad_ctl, fgen.producible)
    check(False, "refuse_unreadable refuses clr_hidden on m0a (no clr knob)")
except scorekit.ControlReadError as e:
    check("m0a-none:M-CLR reads clr_hidden" in str(e), "refuse_unreadable refuses clr_hidden on a cell without clr: %s" % str(e)[:80])
bad_ctl = dict(ctl)
bad_ctl["l0-lock-release:L-CTL"] = (("boot_held",), next(l for l in tables["l"].splitlines() if l.startswith("l0")))
try:
    scorekit.refuse_unreadable(bad_ctl, fgen.producible)
    check(False, "refuse_unreadable refuses boot_held on a probe row")
except scorekit.ControlReadError:
    check(True, "refuse_unreadable refuses boot_held on a probe row")

# predictions: cases are table rows, quantities the scorer's
QS = {"s0": {"set_rc", "set_reads", "set_int", "back_reads", "class"}, "l": {"class", "count"},
      "d": {"job_class", "job_int", "job_word", "boot_held", "boot_replay1", "passes_within"},
      "m": {"job_class", "job_int", "job_word", "boot_held", "clr_hidden", "clr_back", "passes_within"}}
for st in ("s0", "l", "d", "m"):
    names = {r[0] for r in rows(st)}
    pr = [l.split("\t") for l in preds[st].splitlines()[1:]]
    check(all(p[0] in names for p in pr) and all(p[1] in QS[st] for p in pr), "predictions/%s.tsv: %d rows, every case a row, every quantity read" % (st, len(pr)))
dp = [l.split("\t") for l in preds["d"].splitlines()[1:]]
check(sum(1 for p in dp if p[3] == "H-PAGE") == 10 and sum(1 for p in dp if p[3] == "H-SIZE") == 5, "d: H-PAGE 10 rows (five cells, two boots), H-SIZE 5")
check(all(p[2] == "up" for p in dp if p[0].startswith("d4") and p[1].startswith("boot")), "d4 (0x20009): both rules say up (it locates R-PAGE's end)")
print("gen checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
