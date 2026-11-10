#!/usr/bin/env python3
"""fake_probe.py MODE PAGES BIN: the fake tool's probe job for tests/run_mock.sh, from the frozen layout model HL.
  MODE mode   prints ok | nopix | fault (what the model says the job does)
  MODE fault  prints WORD ADDR of the first faulting read (fault mode only)
  MODE out    prints the probe's output as the real one does (scratch line, job time, rows, or 'failed: no pixel written')
BIN is the staged program's name: *-x1__0.bin is the xor variant, *l0e2* the d-ok-64 program (A4 at 64 pages)."""
import os
import sys

R2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R2, "gen"))
import r2models as M  # noqa: E402

mode, pages, binname = sys.argv[1], int(sys.argv[2]), os.path.basename(sys.argv[3])
name = binname.replace("__0.bin", "")
if "l0e2" in name:
    rows = [r.split("\t") for r in open(os.path.join(R2, "gen", "data", "s1b_p-d-A4.tsv")).read().splitlines()[1:]]
    px = [int(v, 16) for v in next(r for r in rows if r[0] == "d-ok-64")[3].split(",")]
else:
    xor = 1 if name.endswith("-x1") else 0
    # "force": the job completes whatever the model says (a hypothesis HS test): the 19-page image
    px = M.image(19 if len(sys.argv) > 4 and sys.argv[4] == "force" else pages, xor)
if px is None:
    state = "fault"
elif all(v == M.SENTINEL for v in px):
    state = "nopix"
else:
    state = "ok"
if mode == "mode":
    print(state)
elif mode == "fault":
    print("0x90002 %#x" % M.first_fault(pages))
else:
    print("probe %s: scratch at 0x3e003000 (%d KiB)" % (name, pages * 4))
    if state == "nopix":
        print("probe %s: failed: no pixel written" % name)
    elif state == "ok":
        print("probe %s: job time: 548 us" % name)
        for r in range(32):
            print("probe %s: row %d: %s" % (name, r, " ".join("%08x" % v for v in px[r * 64:(r + 1) * 64])))
