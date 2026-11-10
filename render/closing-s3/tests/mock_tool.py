#!/usr/bin/env python3
"""Every job command of the S3 tables against the landed tool's in-process mock (local, no laptop): an option
the tool does not know, a bad value or a missing staged program shows up as rc 2 or a usage message.  The
mock has no debugfs: --dump-render fails there and is retried without it; it cannot hold a fault or read
xfer_ro (the xferro row is skipped).  Also checks the tool's own "targets up to" echo, the knob proof the
scorers read.  Output: a summary; nothing is written.
  python3 tests/mock_tool.py
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

S3 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.expanduser("~/src/resgx545/userspace/libsgxfive/build/sgxfive-test")
bad = n = 0
for st in open(os.path.join(S3, "stages.txt")).read().split():
    for line in open(os.path.join(S3, "tables", st + ".txt")).read().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, knobs, rt, args = line.split("|", 5)
        if "xferro" in knobs.split():
            print("skip %s/%s (debugfs xfer_ro: not in the mock)" % (st, name))
            continue
        n += 1
        w = tempfile.mkdtemp(prefix="s3-mock-tool-")
        os.mkdir(os.path.join(w, "dump"))
        a = args.replace("$W", w).replace("$S", os.path.join(S3, "bins"))
        r = subprocess.run([TOOL, "--mock"] + shlex.split(a), capture_output=True, text=True, timeout=120)
        txt, rc = r.stdout + r.stderr, r.returncode
        if "--dump-render: No such file" in txt:
            a2 = re.sub(r'--dump-render \S+', "", a)
            r = subprocess.run([TOOL, "--mock"] + shlex.split(a2), capture_output=True, text=True, timeout=120)
            txt, rc = "(retried without --dump-render)\n" + r.stdout + r.stderr, r.returncode
        usage = rc == 2 or "usage" in txt.lower() or "bad " in txt
        m = re.search(r"--max-width (\d+) --max-height (\d+)", a)
        echo_ok = not m or ("targets up to %sx%s" % m.groups()) in txt
        if usage or not echo_ok:
            bad += 1
            print("FAIL %s/%s: rc %d echo %s: %s" % (st, name, rc, echo_ok, txt.strip().splitlines()[-1][:160]))
        else:
            first = [x for x in txt.splitlines() if x.startswith(("job:", "probe", "diff:"))][:2]
            print("ok   %s/%s: rc %d %s" % (st, name, rc, " | ".join(first)[:150]))
print("%d of %d commands accepted by the tool's mock" % (n - bad, n))
sys.exit(1 if bad else 0)
