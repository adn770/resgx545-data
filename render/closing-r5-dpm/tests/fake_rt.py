#!/usr/bin/env python3
"""fake regtimeline: fake_rt.py TOTAL LEAD REGS -- COMMAND...  Runs COMMAND (its output passes through), then prints the timeline the
world (tests/world_r5.py, FAKE_WORLD) gives for the job the command describes, as the real tool prints it after the command's output.
REGS must be the frozen 16-register list (the world prints those columns)."""
import os
import subprocess
import sys

args = sys.argv[1:]
cmd = args[args.index("--") + 1:]
if args[2] != "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74":
    print("fake regtimeline: not the frozen register list"); sys.exit(2)
r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
here = os.path.dirname(os.path.abspath(__file__))
t = subprocess.run([os.environ["PY"], os.path.join(here, "world_r5.py"), "timeline"] + cmd[1:], capture_output=True, text=True,
                   env=dict(os.environ, FAKE_NO_ARM_WRITE="1"))
out = r.stdout + t.stdout
# FAKE_CUT=PATTERN:N: such a job's whole text stops after N bytes, mid-line (attempt 1: a full work filesystem cut it at 4096)
cut = os.environ.get("FAKE_CUT", "")
if cut and cut.rsplit(":", 1)[0] in " ".join(cmd):
    out = out[:int(cut.rsplit(":", 1)[1])]
sys.stdout.write(out)
sys.exit(r.returncode)
