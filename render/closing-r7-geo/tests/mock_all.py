#!/usr/bin/env python3
"""mock_all.py: every r7-geo job command against the in-process mock (--mock) of the tool its row names, built on the Mac from the
pinned sources (no laptop): t4 = resgx545 4623753 (the source of ~/sgxfive-test-rgn4, sgxfive-test.c = TOOLSRC.sha256), t6 = resgx545
d9b2969 (round 6's t6, sgxfive-test.c = TOOL6SRC.sha256).  Builds into debug/tool<commit>/ when missing.  The tool's debugfs kpoke
goes to a plain file (SGXFIVE_KPOKE), so the kernel pokes a row would write are read back here.
Per command: it parses (no rc 2, no usage) and runs in its tool's mock (a fill prints its target and hash; a tri row renders once
at the row's size; a probe loads its staged program: the mock runs no shader, so a texture probe ends rc 3 "no pixel written"); a --depth row's kernel pokes are the depth recipe's (ta:7, rd:1, rd:11 = the
row's --depth-ctl, rd:12, rd:13) and nothing else is poked; a baseline fill's hash is the frozen prediction's; TOOL COLUMN: every
odd-height row is refused by the t4 mock and accepted by the t6 mock; the health pair draws exactly in the rgn4 tool's mock.
  PY tests/mock_all.py"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
MAIN = "/Users/jtorra/src/resgx545"
PIN = {"t4": ("4623753", "TOOLSRC.sha256"), "t6": ("d9b2969", "TOOL6SRC.sha256")}
bad = n = 0


def build(commit):
    d = os.path.join(KP, "debug", "tool" + commit)
    exe = os.path.join(d, "userspace/libsgxfive/build/sgxfive-test")
    if not os.path.exists(exe):
        os.makedirs(d, exist_ok=True)
        subprocess.run("git -C %s archive %s userspace/libsgxfive include | tar -x -C %s" % (MAIN, commit, d), shell=True, check=True)
        with open(os.path.join(KP, "debug", "mock-build-%s.log" % commit), "w") as log:
            subprocess.run(["make", "-C", os.path.join(d, "userspace/libsgxfive"), "-j4", "build/sgxfive-test"], stdout=log, stderr=log, check=True)
    return d, exe


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


TOOLS = {}
for t, (commit, pinf) in PIN.items():
    d, exe = build(commit)
    want = open(os.path.join(KP, pinf)).read().split()[0]
    got = subprocess.run(["shasum", "-a", "256", os.path.join(d, "userspace/libsgxfive/tools/sgxfive-test.c")], capture_output=True, text=True).stdout.split()[0]
    check(want == got, "%s mock built from %s: sgxfive-test.c is %s's pin (%s...)" % (t, commit, pinf, want[:8]))
    TOOLS[t] = exe


def run(tool, args, w):
    kpf = os.path.join(w, "kpoke")
    open(kpf, "w").close()
    r = subprocess.run([TOOLS[tool], "--mock"] + args, capture_output=True, text=True, timeout=900, env=dict(os.environ, SGXFIVE_KPOKE=kpf))
    return r.returncode, r.stdout, r.stderr, open(kpf).read().split()


def preds(st):
    P = {}
    for ln in open(os.path.join(KP, "predictions", st + ".tsv")).read().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        P.setdefault(c, {}).setdefault(q, {})[m] = v
    return P


S = os.path.join(KP, "bins")
for st in open(os.path.join(KP, "stages.txt")).read().split():
    P = preds(st)
    nrow = nok = 0
    for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tool, args = ln.split("|", 5)
        w = tempfile.mkdtemp(prefix="mock.", dir=os.path.join(KP, "debug"))
        os.makedirs(os.path.join(w, "depth"))
        a = shlex.split(args.replace("$W", w).replace("$S", S))
        rc, out, err, kp = run(tool, a, w)
        txt = out + err
        good = rc != 2 and "usage" not in txt.lower() and (rc == 0 or (rc == 1 and "diff:" in out) or (a[0] == "probe" and rc == 3))
        note = ""
        if a[0] == "fill":
            m = re.search(r"^target: (\d+)x(\d+) hash (0x[0-9a-f]+)", out, re.M)
            good = good and m is not None and (int(m.group(1)), int(m.group(2))) == (128, 64)
            if good and "--poke" not in a:
                good = int(m.group(3), 16) == int(P[name]["hash"]["E884"], 16)
                note = " (baseline hash = the frozen one)"
            good = good and kp == []
        elif a[0] == "tri":
            W, H = int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
            good = good and "tri: 1 renders ok" in out and ("tri %dx%d #1:" % (W, H)) in out
            if "--depth" in a:
                want_kp = ["ta:7^=0x80", "rd:1=0x3e000000", "rd:11=0x%08x" % int(a[a.index("--depth-ctl") + 1], 16), "rd:12=0x1000", "rd:13=0x1000"]
                good = good and kp == want_kp and os.path.exists(os.path.join(w, "depth", "depth.1.bin"))
            else:
                good = good and kp == []
            if H % 2:
                rc4, out4, err4, _ = run("t4", a, w)
                refused = rc4 != 0 and "render: Invalid argument" in out4 + err4
                good = good and tool == "t6" and refused
                note = "; t4 refuses this odd height" if refused else "; t4 does NOT refuse"
        else:
            # the mock executes no shader: a texture probe's job "writes no pixel" there (rc 3); what it shows is that the tool took
            # the argv, loaded the staged program (no "not 1 to 256 USSE words") and built and ran the job
            nm = os.path.basename(a[-1]).split(".")[0]
            good = good and kp == [] and re.search(r"^probe %s: " % re.escape(nm), out, re.M) is not None and "USSE words" not in txt
        nrow += 1
        nok += bool(good)
        if not good:
            check(False, "%s/%s: rc %d: %s%s" % (st, name, rc, (txt.strip().splitlines() or [""])[-1][:150], note))
        for f in os.listdir(os.path.join(w, "depth")):
            os.remove(os.path.join(w, "depth", f))
    check(nok == nrow, "%s: %d of %d rows parse and run in their own tool's mock (kernel pokes, tool column, hashes checked)" % (st, nok, nrow))
for a in (["fill"], ["tri"]):
    rc, out, err, _ = run("t4", a, tempfile.mkdtemp(prefix="mock.", dir=os.path.join(KP, "debug")))
    check(rc == 0 and "diff: 0 of" in out, "health: %s draws exactly in the rgn4 tool's mock" % a[0])
print("%d of %d mock checks" % (n - bad, n))
sys.exit(1 if bad else 0)
