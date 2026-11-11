#!/usr/bin/env python3
"""fake regtimeline: fake_rt.py TOTAL LEAD REGS -- COMMAND...  Runs COMMAND (its output passes through), then prints the
timeline the real tool prints: `timeline: regs ...` and `tl TIME values...` rows.  Environment:
  FAKE_PEAKS=19,29,...  the 0x0724 low-half peak of the 1st, 2nd, ... timeline job (a counter in $FAKE_STATE; the last
                        value repeats); default 19
  FAKE_COUNT=N          the 0x072c count (both halves) while the TA runs, default 1
  FAKE_BAD072C=1        0x072c reads 0xffffffff
  FAKE_STUCK0=1         0x072c reads 0 throughout
  FAKE_FEWROWS=1        only 6 rows
Registers are read from the REGS ranges (LO-HI inclusive, step 4)."""
import os
import subprocess
import sys

args = sys.argv[1:]
regs_arg, cmd = args[2], args[args.index("--") + 1:]
r = subprocess.run(cmd, stdout=sys.stdout, stderr=subprocess.STDOUT)
regs = []
for part in regs_arg.split(","):
    ends = [int(x, 16) for x in part.split("-")]        # LO-HI, or a single register (S1b's 0x0748)
    regs += [f"0x{a:04x}" for a in range(ends[0], ends[-1] + 1, 4)]
state = os.environ.get("FAKE_STATE", "/tmp/fake_rt.state")
try:
    n = int(open(state).read())
except Exception:
    n = 0
open(state, "w").write(str(n + 1))
peaks = [int(x) for x in os.environ.get("FAKE_PEAKS", "19").split(",")]
peak = peaks[min(n, len(peaks) - 1)]
cnt = int(os.environ.get("FAKE_COUNT", "1"))
rows = []
n_rows = 6 if os.environ.get("FAKE_FEWROWS") else peak + 4
for i in range(n_rows):
    s = 0 if i == 0 or i == n_rows - 1 else min(i, peak)
    row = []
    for rg in regs:
        if rg == "0x0624":
            v = 0x400
        elif rg == "0x0724":
            v = (s << 16) | s
        elif rg == "0x072c":
            v = 0xffffffff if os.environ.get("FAKE_BAD072C") else 0 if os.environ.get("FAKE_STUCK0") else \
                ((cnt << 16) | cnt if s else 0)
        else:
            v = 0
        row.append(v)
    rows.append(row)
print("timeline: regs " + " ".join(regs) + f" samples {n_rows} seconds 0 start 100 end {100 + 10 * n_rows} rc {r.returncode}")
for i, row in enumerate(rows):
    print(f"tl {100 + 10 * i} " + " ".join(f"{v:08x}" for v in row))
sys.exit(r.returncode)
