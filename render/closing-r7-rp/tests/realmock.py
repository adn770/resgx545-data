#!/usr/bin/env python3
"""realmock.py: run a table row through the PINNED tool build's in-process mock (--mock), on the Mac, no laptop.

  t4 = resgx545 4623753 (the source of the laptop's ~/sgxfive-test-rgn4, TOOLSRC.sha256)
  t6 = resgx545 d9b2969 (R6's t6, TOOL6SRC.sha256)
  t7 = resgx545 1c64f3a (this session's t7: odd widths, TOOL7SRC.sha256)

Builds live in debug/tool<commit>/ (git archive of the commit, `make build/sgxfive-test`); build() makes a missing one and
checks its sgxfive-test.c against the session's pin.  run(tool, args) substitutes $W (a fresh work dir with depth/ and dump/,
as the runner makes) and $S (the session's bins/), sends the tool's debugfs kpoke to a plain file and returns
(rc, out, err, kpoke_lines, workdir).  The work dir is left for the caller to read; it is under debug/ (scratch).
"""
import os
import shlex
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
MAIN = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
PIN = {"t4": ("4623753", "TOOLSRC.sha256"), "t6": ("d9b2969", "TOOL6SRC.sha256"), "t7": ("1c64f3a", "TOOL7SRC.sha256")}


def _sha(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build(tool):
    commit, pinfile = PIN[tool]
    d = os.path.join(KP, "debug", "tool" + commit)
    exe = os.path.join(d, "userspace/libsgxfive/build/sgxfive-test")
    if not os.path.exists(exe):
        os.makedirs(d, exist_ok=True)
        subprocess.run("git -C %s archive %s userspace/libsgxfive include | tar -x -C %s" % (MAIN, commit, d),
                       shell=True, check=True)
        with open(os.path.join(KP, "debug", "mock-build-%s.log" % commit), "w") as log:
            subprocess.run(["make", "-C", os.path.join(d, "userspace/libsgxfive"), "-j4", "build/sgxfive-test"],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    pin = os.path.join(KP, pinfile)
    if os.path.exists(pin):
        want = open(pin).read().split()[0]
        got = _sha(os.path.join(d, "userspace/libsgxfive/tools/sgxfive-test.c"))
        if want != got:
            raise RuntimeError("%s mock source %s is not the pinned %s" % (tool, got, want))
    return exe


def run(tool, args, timeout=120, workdir=None):
    exe = build(tool)
    base = os.path.join(KP, "debug", "realmock")
    os.makedirs(base, exist_ok=True)
    w = workdir or tempfile.mkdtemp(prefix="w.", dir=base)
    os.makedirs(os.path.join(w, "depth"), exist_ok=True)
    os.makedirs(os.path.join(w, "dump"), exist_ok=True)
    kp = os.path.join(w, "kpoke")
    open(kp, "w").close()
    s = os.path.join(KP, "bins")
    argv = [a.replace("$W", w).replace("$S", s) for a in shlex.split(args.replace('"$W', '"$W').replace('"$S', '"$S'))]
    env = dict(os.environ, SGXFIVE_KPOKE=kp, SGXFIVE_DEBUGFS=os.path.join(w, "dbgfs"))
    os.makedirs(env["SGXFIVE_DEBUGFS"], exist_ok=True)
    for k in ("render_rgn_arrays", "render_pb_pages", "hold_recovery", "kpoke", "render_param", "render_tadata"):
        open(os.path.join(env["SGXFIVE_DEBUGFS"], k), "a").close()
    p = subprocess.run([exe, "--mock"] + argv, capture_output=True, text=True, timeout=timeout, env=env, cwd=w)
    lines = [l for l in open(kp).read().splitlines() if l.strip()]
    return p.returncode, p.stdout, p.stderr, lines, w


if __name__ == "__main__":
    import sys
    rc, out, err, kp, w = run(sys.argv[1], " ".join(sys.argv[2:]))
    print(out, end="")
    print(err, end="")
    print("rc", rc, "kpoke", kp, "dir", w)
