#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A fake regtimeline for the R1-events mock tests: `fake_rt.py 0 0.3 REGS -- TOOL ARGS...` runs the (fake) tool, prints its
output, then a timeline in the real format (`timeline: regs ... samples N seconds 0 start S end E rc 0`, `tl T v1 v2 ...`)
built from MOCK_DIR/lastjob.json and the fake EDM's event words for the job: the previous job's 0x0624 first (stale), the
job's own 0x0624 once the TA runs, 0x0658 bit 0 for each partial render, and a pulse of CR_EVENT_STATUS bit (22 - pa1 bit)
for every non-command entry of the job in its order (bit 19 is status bit 3)."""
import json
import os
import subprocess
import sys

MOCK = os.environ["MOCK_DIR"]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "mockfw"))
import fwtask_run as M  # noqa: E402

a = sys.argv[1:]
regs = a[2].split(",")
cmd = a[a.index("--") + 1:]
p = subprocess.run(cmd, capture_output=True, text=True)
sys.stdout.write(p.stdout + p.stderr)
try:
    info = json.load(open(os.path.join(MOCK, "lastjob.json")))
except (OSError, ValueError):
    info = None
start = 300_000_000
rows = []


def row(t, **v):
    cols = {"0x012c": 0x20000000, "0x0118": 0x400, "0x0624": 0x400, "0x0658": 0, "0x0724": 0}
    cols.update(v)
    rows.append((t, [cols[r] for r in regs]))


row(100_000, **{"0x0624": 0x400})                       # the previous job's value, sampled before the job
if info:
    knob = info["pb"] - 0x22                              # S1b: 0x0624 = render_pb_pages - 0x22 (0x422 gives 0x400)
    t = start + 1_000_000
    row(t, **{"0x0624": knob, "0x0724": 0x10})
    t += 200_000
    for bit, is_cmd in M.raised_words(info["kind"]):
        if is_cmd:
            continue
        if bit == 21:                                     # a partial render starts (the overflow path's first bit)
            row(t, **{"0x0624": knob, "0x0724": 0x10, "0x0658": 1})
            t += 50_000
            row(t, **{"0x0624": knob, "0x0724": 0x10, "0x0658": 0})
        row(t, **{"0x0624": knob, "0x0724": 0x10, "0x012c": 0x20000000 | (1 << (22 - bit))})
        t += 10_000
        row(t, **{"0x0624": knob, "0x0724": 0x10})
        t += 100_000
print(f"timeline: regs {' '.join(regs)} samples {len(rows) * 100} seconds 0 start {start} end {start + 600_000_000} rc {p.returncode}")
for t, v in rows:
    print("tl " + str(t) + " " + " ".join(f"{x:08x}" for x in v))
sys.exit(p.returncode)
