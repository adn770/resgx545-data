#!/usr/bin/env python3
"""mock_all.py: every r6-misc job command against the in-process mock (--mock) of the tool its row names, built on the Mac from the
pinned sources (no laptop): t4 = resgx545 4623753 (the source of ~/sgxfive-test-rgn4, sgxfive-test.c = TOOLSRC.sha256), t6 = resgx545
d9b2969 (the t6 build's source, sgxfive-test.c = TOOL6SRC.sha256).  Builds into debug/tool<commit>/ when missing.  The tool's debugfs
kpoke goes to a plain file (SGXFIVE_KPOKE), so the kernel pokes a row would write are read back here.

Per command:
  1. it parses (no rc 2, no usage) and completes in its tool's mock: a fill prints its target and hash; a depth row renders once
     (`tri: 1 renders ok`) at the row's size; a 4x row prints the context `made for 4x targets` at the row's maximum and `job: ok`;
  2. the kernel pokes the tool wrote are the row's: q287's --depth recipe (ta:7, rd:1, rd:11 the row's --depth-ctl, rd:12, rd:13),
     q086's --kpoke-render words (ta:143, 144, 146 as E511's script lists them);
  3. a baseline fill's hash in the mock (the reference colour everywhere) is the frozen prediction's (models.fnv = the tool's hash);
  4. TOOL COLUMN: every odd-height row is REFUSED by the t4 mock (`render: Invalid argument`) and accepted by the t6 mock, so a row
     pointing at the wrong tool cannot pass here;
  5. the health pair (`fill`, `tri`) of the rgn4 tool draws exactly.
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
MAIN = "/Users/jtorra/src/resgx545"
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402

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
    got = subprocess.run(["shasum", "-a", "256", os.path.join(d, "userspace/libsgxfive/tools/sgxfive-test.c")], capture_output=True,
                         text=True).stdout.split()[0]
    check(want == got, "%s mock built from %s: sgxfive-test.c is %s's pin (%s...)" % (t, commit, pinf, want[:8]))
    TOOLS[t] = exe

os.makedirs(os.path.join(KP, "debug"), exist_ok=True)


def run(tool, args, w):
    kpf = os.path.join(w, "kpoke")
    open(kpf, "w").close()
    r = subprocess.run([TOOLS[tool], "--mock"] + args, capture_output=True, text=True, timeout=600,
                       env=dict(os.environ, SGXFIVE_KPOKE=kpf))
    return r.returncode, r.stdout, r.stderr, open(kpf).read().split()


def preds(st):
    P = {}
    for ln in open(os.path.join(KP, "predictions", st + ".tsv")).read().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        P.setdefault(c, {}).setdefault(q, {})[m] = v
    return P


for st in ("q289", "q287", "q086"):
    P = preds(st)
    for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tool, args = ln.split("|", 5)
        w = tempfile.mkdtemp(prefix="mock.", dir=os.path.join(KP, "debug"))
        a = shlex.split(args.replace("$W", w))
        rc, out, err, kp = run(tool, a, w)
        txt = out + err
        parsed = rc != 2 and "usage" not in txt.lower()
        W, H = int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
        if a[0] == "fill":
            m = re.search(r"^target: (\d+)x(\d+) hash (0x[0-9a-f]+)", out, re.M)
            good = parsed and rc == 0 and m and (int(m.group(1)), int(m.group(2))) == (W, H)
            note = "fill %dx%d in the mock" % (W, H)
            if good and "--poke" not in a:
                good = int(m.group(3), 16) == int(P[name]["hash"]["M-OR"], 16)
                note += ", baseline hash %s = the frozen prediction (the model's FNV-1a is the tool's)" % m.group(3)
        elif "--depth" in a:
            good = parsed and rc == 0 and "tri: 1 renders ok" in out and ("tri %dx%d #1:" % (W, H)) in out
            want_kp = ["ta:7^=0x80", "rd:1=0x3e000000", "rd:11=0x%08x" % int(a[a.index("--depth-ctl") + 1], 16), "rd:12=0x1000", "rd:13=0x1000"]
            good = good and kp == want_kp
            note = "depth render %dx%d with %s, the --depth kernel pokes %s" % (W, H, tool, " ".join(kp))
            if H % 2:
                rc4, out4, err4, _ = run("t4", a, w)
                refused = rc4 != 0 and "render: Invalid argument" in out4 + err4
                good = good and tool == "t6" and refused
                note += "; t4 refuses this odd height (%s)" % ("yes" if refused else "NO")
        else:
            want_kp = ["ta:%s" % x.split(":ta:")[1] for x in re.findall(r"--kpoke-render (\S+)", args)]
            good = parsed and rc == 0 and "job: ok" in out and ("targets up to %dx%d" % (W, H)) in out and "made for 4x targets" in out \
                and len(re.findall(r"^row \d+: ", out, re.M)) == H and kp == want_kp
            note = "4x render %dx%d in the mock, kpokes %s" % (W, H, " ".join(kp) or "none")
        check(bool(good), "%s/%s: %s" % (st, name, note if good else "rc %d: %s" % (rc, (txt.strip().splitlines() or [""])[-1][:150])))
for a in (["fill"], ["tri"]):
    rc, out, err, _ = run("t4", a, tempfile.mkdtemp(prefix="mock.", dir=os.path.join(KP, "debug")))
    check(rc == 0 and "diff: 0 of" in out, "health: %s draws exactly in the rgn4 tool's mock" % a[0])
print("%d of %d mock checks" % (n - bad, n))
sys.exit(1 if bad else 0)
