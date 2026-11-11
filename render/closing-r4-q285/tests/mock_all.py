#!/usr/bin/env python3
"""Every job command of the R4-A tables against the rgn4 tool's in-process mock (the build of the worktree closing3/kernel/wt-rgn4,
whose sgxfive-test.c is the blob of resgx545 r3-rgn4 4623753, sha256 703cbcea..., the source of ~/sgxfive-test-rgn4).  Local, no
laptop, nothing written but temporary directories.

Per command:
  1. as frozen: the options parse (no rc 2, no usage) and the "targets up to" echo is the row's; the mock models fork a2788bd8's
     submission check, so a TE_AA with bit 30 on a context without the flag is "rejected (Invalid argument)": the reason every row
     carries rgn:1 (the mock has no render_rgn_arrays);
  2. with --aa4 added (only to get past that check in the mock): render 1 completes as geometry only; a row with --kpoke-render
     then stops at the mock's missing debugfs kpoke ("kpoke: No such file"), the others complete.  --dump-render needs debugfs: it is
     dropped for the mock.
  python3 tests/mock_all.py
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.environ.get("R4A_MOCK_TOOL", "/Users/jtorra/src/scratch/resgx545/closing3/kernel/wt-rgn4/userspace/libsgxfive/build/sgxfive-test")
bad = n = 0


def run(args):
    r = subprocess.run([TOOL, "--mock"] + args, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


for st in open(os.path.join(KP, "stages.txt")).read().split():
    for line in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, knobs, rt, args = line.split("|", 5)
        n += 1
        w = tempfile.mkdtemp(prefix="r4a-mock-tool-")
        a = re.sub(r'--dump-render \S+', "", args.replace("$W", w))
        rc, txt = run(shlex.split(a))
        usage = rc == 2 or "usage" in txt.lower() or "bad " in txt
        m = re.search(r"--max-width (\d+) --max-height (\d+)", a)
        echo_ok = not m or ("targets up to %sx%s" % m.groups()) in txt
        te = re.search(r"--poke cmd:1=(0x[0-9a-f]+)", a)
        refused = "job: rejected (Invalid argument)" in txt
        want_refused = bool(te) and int(te.group(1), 16) & 0xC0000000 != 0
        rc2, txt2 = run(["tri", "--aa4"] + shlex.split(a)[1:])
        geo = "geometry only, the scene left open" in txt2
        kp = "--kpoke-render" in a
        tail_ok = ("kpoke: No such file" in txt2) if kp else ("job: ok" in txt2.split("geometry only")[-1])
        good = not usage and echo_ok and refused == want_refused and rc2 != 2 and geo and tail_ok
        if not good:
            bad += 1
            print("FAIL %s/%s: rc %d usage %s echo %s refused %s (want %s) | with --aa4: rc %d geometry %s tail %s: %s"
                  % (st, name, rc, usage, echo_ok, refused, want_refused, rc2, geo, tail_ok, txt2.strip().splitlines()[-1][:120]))
        else:
            print("ok   %s/%s: as frozen %s; with --aa4 render 1 geometry only, %s"
                  % (st, name, "refused (no forced count in the mock)" if refused else "accepted", "kpoke reached" if kp else "render 2 ok"))
print("%d of %d commands accepted by the rgn4 tool's mock" % (n - bad, n))
sys.exit(1 if bad else 0)
