#!/usr/bin/env python3
"""Every job command of the R4-G tables, and the cell steps' commands, against the rgn4 tool's in-process mock (the build of
tests/build_mock_tool.sh: resgx545 r3-rgn4 4623753, sgxfive-test.c sha256 703cbcea..., the source of ~/sgxfive-test-rgn4).  Local, no
laptop, nothing written but temporary directories under debug/.

Per command:
  1. as frozen: the options parse (no rc 2, no usage, no "bad option"); a tri row's "targets up to" echo is the row's; the mock models fork
     a2788bd8's submission check, so a TE_AA with bit 31 or 30 on a context without --aa4 is "rejected (Invalid argument)": the reason a
     row with such a word and no --aa4 carries rgn:1 (the mock has no render_rgn_arrays);
  2. a tri row with --aa4 (or without the 4x word) completes in the mock; a row with pb:0xNN is also run with --mock-pb-pages=0xNN (the
     mock's PB size) and must still parse; --dump-render needs debugfs: it is dropped for the mock; --regs prints "not available on the mock";
  3. a probe row's program is read, the options parse and the job runs to the mock's end (the mock's interpreter has no smp: the job
     "faulted" there, and that is not a parse failure); --tadata-fill-render reaches "tadata_fill: No such file" (the mock has no debugfs).
  python3 tests/mock_all.py
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
TOOL = os.environ.get("R4G_MOCK_TOOL", os.path.join(KP, "debug/tool4623753/userspace/libsgxfive/build/sgxfive-test"))
if not os.path.exists(TOOL):
    subprocess.run([os.path.join(HERE, "build_mock_tool.sh")], check=True, capture_output=True)
bad = n = 0
BINS = os.path.join(KP, "bins")


def run(args, extra=()):
    r = subprocess.run([TOOL, "--mock"] + list(extra) + list(args), capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def parsed(rc, txt):
    return rc != 2 and "usage" not in txt.lower() and "bad option" not in txt and "bad " not in txt.split("\n")[0].lower()


def sub(args, w):
    a = args.replace("$W", w).replace("$S", BINS)
    return re.sub(r'--dump-render \S+', "", a)


for st in open(os.path.join(KP, "stages.txt")).read().split():
    for line in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, knobs, rt, args = line.split("|", 5)
        n += 1
        w = tempfile.mkdtemp(prefix="r4g-mock-tool-", dir=os.path.join(KP, "debug"))
        a = shlex.split(sub(args, w))
        rc, txt = run(a)
        ok = parsed(rc, txt)
        notes = []
        if a[0] == "tri":
            m = re.search(r"--max-width (\d+) --max-height (\d+)", " ".join(a))
            ok &= (not m) or ("targets up to %sx%s" % m.groups()) in txt
            te = re.search(r"--poke cmd:1=(0x[0-9a-f]+)", " ".join(a))
            refused = "job: rejected (Invalid argument)" in txt
            want_refused = bool(te) and int(te.group(1), 16) & 0xC0000000 != 0 and "--aa4" not in a
            ok &= refused == want_refused
            notes.append("refused (no forced count in the mock: the row's rgn:1 covers it)" if refused else "accepted")
            if refused:
                ok &= "rgn:1" in knobs.split()
                rc2, txt2 = run(["tri", "--aa4"] + a[1:])
                ok &= parsed(rc2, txt2) and "job: ok" in txt2
            elif "tadata-fill-render" in " ".join(a):
                ok &= "tadata_fill: No such file" in txt
                notes.append("tadata_fill reached")
            elif "--kpoke" in " ".join(a):
                ok = False
            else:
                ok &= "job: ok" in txt or "overflowed" in txt
        elif a[0] == "probe":
            ok &= "programs asm" in txt and "probe " in txt
            ok &= os.path.exists(a[-1])
            notes.append("program read, options parsed")
        pb = re.search(r"pb:(0x[0-9a-f]+)", knobs)
        if pb:
            rc3, txt3 = run(a if "--aa4" in a or not any("0xe0000000" in x for x in a) else ["tri", "--aa4"] + a[1:], extra=["--mock-pb-pages=" + pb.group(1)])
            ok &= parsed(rc3, txt3)
            notes.append("--mock-pb-pages=%s parses" % pb.group(1))
        if not ok:
            bad += 1
            print("FAIL %s/%s: rc %d: %s" % (st, name, rc, txt.strip().splitlines()[-1][:140] if txt.strip() else ""))
        else:
            print("ok   %s/%s: %s" % (st, name, "; ".join(notes)))

# the cell steps' commands (run_stage.sh cell_step / cell_health) and the health pair
steps = [["tri"], ["fill"], "tri --width 64 --height 64 --max-width 1024 --max-height 768 --keep-going".split()]
for a in steps:
    n += 1
    rc, txt = run(a)
    if parsed(rc, txt) and rc == 0 and ("diff: 0 of" in txt):
        print("ok   step: %s: draws exactly in the mock" % " ".join(a))
    else:
        bad += 1
        print("FAIL step %s: rc %d %s" % (" ".join(a), rc, txt.strip().splitlines()[-1][:100]))
# the runner's step command is the one the guard and the runner contain
rs = open(os.path.join(KP, "run", "run_stage.sh")).read()
for need in ("cell_step \"$name\" ctx tri --width 64 --height 64 --max-width 1024 --max-height 768 --keep-going", 'cell_step "$name" fill fill',
             'cell_step "$nm" h1 tri'):
    if need not in rs:
        bad += 1
        print("FAIL run_stage.sh lacks: %s" % need)
print("%d of %d commands accepted by the rgn4 tool's mock" % (n - bad, n))
sys.exit(1 if bad else 0)
