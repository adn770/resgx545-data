#!/usr/bin/env python3
"""fake regtimeline: fake_rt.py TOTAL LEAD REGS -- COMMAND...  Runs COMMAND (its output passes through), then prints the timeline the world
FAKE_WORLD (tests/world_r3.py) gives for the job the command describes, as the real tool prints it."""
import subprocess
import sys
import pathlib

args = sys.argv[1:]
cmd = args[args.index("--") + 1:]
r = subprocess.run(cmd, stdout=sys.stdout, stderr=subprocess.STDOUT)
sys.stdout.flush()
here = pathlib.Path(__file__).resolve().parent
t = subprocess.run([sys.executable, str(here / "fake_world.py"), "timeline"] + cmd[1:], capture_output=True, text=True)
sys.stdout.write(t.stdout)
sys.exit(r.returncode)
