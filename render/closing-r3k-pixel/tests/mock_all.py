#!/usr/bin/env python3
"""Every job command of the R3K tables (k-f4, k-pb0, k-pb, k-bif) against the landed tool's
in-process mock (local, no laptop): an option the tool does not know, a bad value or a missing staged program shows up as
rc 2 or a usage message.  The mock has no debugfs: --dump-render fails there and is retried without it.  Also checks the
tool's own "targets up to" echo (the knob proof) and the probe's `scratch at ... (N KiB)` line.  Nothing is written.
  python3 tests/mock_all.py
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.expanduser("~/src/resgx545/userspace/libsgxfive/build/sgxfive-test")
bad = n = 0
stages = open(os.path.join(KP, "stages.txt")).read().split()
for st in stages:
    for line in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if not line or line.startswith("#"):
            continue
        if line.split("|", 5)[5] == "-":
            continue                      # an idle row runs no tool
        name, sset, risk, knobs, rt, args = line.split("|", 5)
        n += 1
        w = tempfile.mkdtemp(prefix="k-mock-tool-")
        os.mkdir(os.path.join(w, "dump"))
        a = args.replace("$W", w).replace("$S", os.path.join(KP, "bins"))
        r = subprocess.run([TOOL, "--mock"] + shlex.split(a), capture_output=True, text=True, timeout=120, env=dict(os.environ, SGXFIVE_KPOKE="/dev/null"))
        txt, rc = r.stdout + r.stderr, r.returncode
        if "--dump-render: No such file" in txt:
            a2 = re.sub(r'--dump-render \S+', "", a)
            r = subprocess.run([TOOL, "--mock"] + shlex.split(a2), capture_output=True, text=True, timeout=120)
            txt, rc = "(retried without --dump-render)\n" + r.stdout + r.stderr, r.returncode
        pk = re.findall(r"--kpoke-render (\S+)", a)
        pk_ok = all(("kpoke par:%s" % p.split(":", 1)[1]) in txt or ("kpoke before render" in txt) for p in pk) or not pk
        usage = rc == 2 or "usage" in txt.lower() or "bad " in txt
        m = re.search(r"--max-width (\d+) --max-height (\d+)", a)
        echo_ok = not m or ("targets up to %sx%s" % m.groups()) in txt
        p = re.search(r"--scratch-pages (\d+)", a)
        scr_ok = not p or ("(%d KiB)" % (4 * int(p.group(1)))) in txt
        if usage or not echo_ok or not scr_ok:
            bad += 1
            print("FAIL %s/%s: rc %d echo %s scratch line %s: %s" % (st, name, rc, echo_ok, scr_ok, txt.strip().splitlines()[-1][:160]))
        else:
            first = [x for x in txt.splitlines() if x.startswith(("job:", "probe", "diff:"))][:2]
            print("ok   %s/%s: rc %d %s" % (st, name, rc, " | ".join(first)[:150]))
print("%d of %d commands accepted by the tool's mock" % (n - bad, n))
sys.exit(1 if bad else 0)
