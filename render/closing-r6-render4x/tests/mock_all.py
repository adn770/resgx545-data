#!/usr/bin/env python3
"""Every job command of the r6-render4x stage A tables against the rgn4 tool's in-process mock (the build of tests/build_mock_tool.sh:
resgx545 r3-rgn4 4623753, sgxfive-test.c sha256 703cbcea..., the source of ~/sgxfive-test-rgn4).  Local, no laptop, nothing written but
temporary directories under debug/.  Copied from r5-render4x's mock_all.py (R4-G's), with t7's check: its -n 2 --geometry 1
--kpoke-render form parses and reaches the poke before render 2 (the mock has no debugfs kpoke: "kpoke: No such file").

Per command:
  1. as frozen: the options parse (no rc 2, no usage, no "bad option"); a tri row's "targets up to" echo is its maximum (m1's
     --max-height 1040 included); the mock models fork a2788bd8's submission check, so a TE_AA with bit 31 or 30 on a context without
     --aa4 is "rejected (Invalid argument)": the reason such a row carries rgn:1 (the mock has no render_rgn_arrays);
  2. a tri row completes in the mock; --dump-render needs debugfs: dropped for the mock; --regs prints "not available on the mock";
     a row with pb:0xNN also runs with --mock-pb-pages=0xNN and must still parse;
  3. THE SCENE (exp 2.1 dry run 2): for every row with a frozen need, the triangle counts the tool's own mock prints are the counts of
     the kept twin the need came from (predictions tri1_scene): a default triangle where the need was frozen for the full one fails
     here.  REGRESSION: round 4's o2 command, whose need 97 was the full triangle's model, fails this check;
  4. a probe row's program is read and its options parse.
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
sys.path[:0] = [os.path.join(KP, "gen")]
import rlib as L  # noqa: E402

TOOL = os.environ.get("R6X_MOCK_TOOL", os.path.join(KP, "debug/tool4623753/userspace/libsgxfive/build/sgxfive-test"))
if not os.path.exists(TOOL):
    subprocess.run([os.path.join(HERE, "build_mock_tool.sh")], check=True, capture_output=True)
R4 = "/Users/jtorra/src/scratch/resgx545/closing4/r4-render4x"
BINS = os.path.join(KP, "bins")
bad = n = 0


def run(args, extra=()):
    r = subprocess.run([TOOL, "--mock"] + list(extra) + list(args), capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout + r.stderr


def parsed(rc, txt):
    return rc != 2 and "usage" not in txt.lower() and "bad option" not in txt and "bad " not in txt.split("\n")[0].lower()


def sub(args, w):
    a = args.replace("$W", w).replace("$S", BINS)
    return re.sub(r'--dump-render \S+', "", a)


def tri1(txt):
    m = re.search(r"^tri \d+x\d+ #1: (?:overflowed, )?(\d+ triangle, \d+ background, \d+ other);", txt, re.M)
    return m.group(1) if m else None


os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
for st in open(os.path.join(KP, "stages.txt")).read().split():
    P = L.load_predictions(st + ".tsv", KP)
    for line in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, knobs, rt, args = line.split("|", 5)
        n += 1
        w = tempfile.mkdtemp(prefix="r6x-mock-tool-", dir=os.path.join(KP, "debug"))
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
            if refused:
                ok &= "rgn:1" in knobs.split()
                notes.append("refused (no forced count in the mock: the row's rgn:1 covers it)")
            else:
                ok &= "job: ok" in txt
                notes.append("completes in the mock")
            scene = L.pred_or(P, name, "tri1_scene")
            if scene:
                ok &= tri1(txt) == scene
                notes.append("scene %s = its twin's" % tri1(txt))
            if "--kpoke-render" in a:
                # the same command with TE_AA 0x20000000 (accepted by the mock): render 1 runs geometry only, then the poke is tried
                a2 = [x.replace("cmd:1=0x40000000", "cmd:1=0x20000000") for x in a]
                rc2, txt2 = run(a2)
                ok &= "geometry only, the scene left open" in txt2 and "kpoke: No such file" in txt2
                notes.append("-n 2 --geometry 1 --kpoke-render parses; render 1 geometry only, the poke tried before render 2")
        elif a[0] == "probe":
            ok &= "programs asm" in txt and "probe " in txt and os.path.exists(a[-1])
            notes.append("program read, options parsed")
        pb = re.search(r"pb:(0x[0-9a-f]+)", knobs)
        if pb:
            rc3, txt3 = run(a, extra=["--mock-pb-pages=" + pb.group(1)])
            ok &= parsed(rc3, txt3)
            notes.append("--mock-pb-pages=%s parses" % pb.group(1))
        if not ok:
            bad += 1
            print("FAIL %s/%s: rc %d: %s" % (st, name, rc, txt.strip().splitlines()[-1][:140] if txt.strip() else ""))
        else:
            print("ok   %s/%s: %s" % (st, name, "; ".join(notes)))

# REGRESSION: round 4's o2 (the default triangle) against the scene its need 97 was frozen for (the full triangle at 1024 x 768)
o2 = [ln.split("|", 5)[5] for ln in open(os.path.join(R4, "tables", "o.txt")) if ln.startswith("o2-")][0]
rc, txt = run(shlex.split(sub(o2, os.path.join(KP, "debug"))))
full = "786432 triangle, 0 background, 0 other"
n += 1
if tri1(txt) != full and tri1(txt) == "207456 triangle, 578976 background, 0 other":
    print("ok   REGRESSION: round 4's o2 command draws the default triangle in the tool's mock (%s), not the full triangle its need 97 was frozen for" % tri1(txt))
else:
    bad += 1
    print("FAIL REGRESSION: round 4's o2 in the mock: %s" % tri1(txt))
# the health pair the runner and health.sh use
for a in (["tri"], ["fill"]):
    n += 1
    rc, txt = run(a)
    if parsed(rc, txt) and rc == 0 and "diff: 0 of" in txt:
        print("ok   health: %s draws exactly in the mock" % " ".join(a))
    else:
        bad += 1
        print("FAIL health %s: rc %d" % (" ".join(a), rc))
print("%d of %d commands accepted by the rgn4 tool's mock" % (n - bad, n))
sys.exit(1 if bad else 0)
