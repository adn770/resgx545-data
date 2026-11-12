#!/usr/bin/env python3
"""Every job command of the R5-pixel tables (p5-o4, g5-rwa, g5-rw; R4-pixel's mock_all.py) against the landed tool's in-process mock (local, no laptop): an option the
tool does not know, a bad value or a missing staged program shows up as rc 2 or a usage message.  The mock has no debugfs: --dump-render
fails there and is retried without it, and it does not execute loops (every shader draws what the host computes), so this checks
ACCEPTANCE, not behaviour (the simulator checks the loops: tests/test_loops.py).  Also checks the tool's echoes: the target size (`tri
WxH`), the fill's `(2048 of 2048)` line, `triangle (0,0) (3W,0) (0,3H)` for --tri-full, and `(N vertices)`.  The tool is the landed build
(RESGX545_TOOL, default RESGX545_MAIN/userspace/libsgxfive/build/sgxfive-test, else ~/src/resgx545/...).  Nothing is written.
  python3 tests/mock_all.py"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

R5 = R4 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [os.environ.get("RESGX545_TOOL"), os.path.join(os.environ.get("RESGX545_MAIN", ""), "userspace/libsgxfive/build/sgxfive-test"),
              os.path.expanduser("~/src/resgx545/userspace/libsgxfive/build/sgxfive-test")]
TOOL = next((c for c in CANDIDATES if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)
if TOOL is None:
    print("FAIL: no landed sgxfive-test build (set RESGX545_TOOL)")
    sys.exit(1)
bad = n = 0
stages = open(os.path.join(R4, "stages.txt")).read().split()
for st in stages:
    for line in open(os.path.join(R4, "tables", st + ".txt")).read().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, knobs, rt, args = line.split("|", 5)
        n += 1
        w = tempfile.mkdtemp(prefix="r5-mock-tool-")
        os.mkdir(os.path.join(w, "dump"))
        a = args.replace("$W", w).replace("$S", os.path.join(R4, "bins"))
        r = subprocess.run([TOOL, "--mock"] + shlex.split(a), capture_output=True, text=True, timeout=600)
        txt, rc = r.stdout + r.stderr, r.returncode
        if "--dump-render: No such file" in txt or "dump" in txt.lower() and rc != 0 and "--dump-render" in a:
            a2 = re.sub(r'--dump-render \S+', "", a)
            r = subprocess.run([TOOL, "--mock"] + shlex.split(a2), capture_output=True, text=True, timeout=600)
            txt, rc = "(retried without --dump-render)\n" + r.stdout + r.stderr, r.returncode
        usage = rc == 2 or "usage" in txt.lower() or "bad " in txt
        m = re.search(r"--width (\d+) --height (\d+)", a)
        echo_ok = True
        if m and "--tri" in a:
            echo_ok = f"tri {m[1]}x{m[2]}" in txt
            if "--tri-full" in a:
                W_, H_ = int(m[1]), int(m[2])
                echo_ok = echo_ok and f"triangle (0,0) ({3 * W_},0) (0,{3 * H_})" in txt
        v = re.search(r"--vertices (\d+)", a)
        if v:
            echo_ok = echo_ok and f"({v[1]} vertices" in txt
        fill_ok = True
        if a.startswith("probe ") and "--tri" not in a:
            fill_ok = "(2048 of 2048)" in txt
        if usage or not echo_ok or not fill_ok or rc not in (0, 1, 3):
            bad += 1
            print("FAIL %s/%s: rc %d echo %s fill line %s: %s" % (st, name, rc, echo_ok, fill_ok, txt.strip().splitlines()[-1][:160] if txt.strip() else ""))
        else:
            first = [x for x in txt.splitlines() if x.startswith(("job:", "probe", "diff:"))][:2]
            print("ok   %s/%s: rc %d %s" % (st, name, rc, " | ".join(first)[:150]))
print("%d of %d commands accepted by the tool's mock" % (n - bad, n))
sys.exit(1 if bad else 0)
