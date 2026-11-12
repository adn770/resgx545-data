#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""frozen_commits.py write|verify: FROZEN.commits, the commit that holds each file from outside this session that the freeze pins or
that the session's checks read (the format of tools/records/frozen.py, as R4's sessions wrote it): `sha256  commit  repo:path`.

  resgx545:PATH       the landed tree (main at the freeze; RESGX545_MAIN), verified by `git show COMMIT:PATH | sha256`
  linux:PATH          the linux fork at the rgn4 commit (forkpin.PIN, a2788bd86537: the module 99CD90DA was built from it); the
                      verifier sources the host build of tests/test_oomring.py compiles, verified the same way (RESGX545_LINUX)
  data:PATH           resgx545-data (the program p1139-green.bin this session stages, published with closing-r3-geo; the frozen
                      offline rules of cited/closing6/dpm/offline and HU1 of closing-r5-dpm, which gen/r6model.py imports)
  untracked           a build product no history holds (the assembler binary), verifiable only against the file itself
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
MAIN = pathlib.Path(os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545"))
LINUX = pathlib.Path(os.environ.get("RESGX545_LINUX", "/Volumes/linux/linux-sgx"))
DATA = pathlib.Path(os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data"))
FORK_PIN = "a2788bd86537"
MAIN_FILES = ["tools/fwtask/fwtask.py", "tools/fwtask/regs.toml", "tools/fwtask/fwtask_run.py", "tools/fwtask/simrun.py",
              "tools/fwtask/layout.py", "tools/fwtask/host/own_host.c", "tools/closing/scorekit.py", "tools/forkpin.py",
              "tools/sweep/regtimeline.c", "userspace/libsgxfive/tools/sgxfive-test.c", "tools/usse-asm/dpm_words.py"]
FORK_FILES = ["drivers/gpu/drm/gma500/sgxfive/sgxfive_owntask.c", "drivers/gpu/drm/gma500/sgxfive/sgxfive_owntask.h",
              "drivers/gpu/drm/gma500/sgxfive/sgx_fw.c", "drivers/gpu/drm/gma500/sgxfive/sgx_own_regs.h"]
DATA_FILES = ["render/closing-r3-geo/bins/p1139-green.bin"]
# the frozen offline rules (round 6 dpm offline stage, E873-E875) and HU1 (R5-dpm), imported by gen/r6model.py
OFF = "cited/closing6/dpm/offline/"
DATA_RULES = [OFF + f for f in ("f5lib.py", "f5_stepmodel.py", "f4_phase.py", "f9_loss.py", "f7_replay.py", "f1_brackets.py",
                                "r6lib.py", "FREEZE-f1.sha256", "FREEZE-f4.sha256", "FREEZE-f5.sha256", "FREEZE-f7.sha256",
                                "FREEZE-f9.sha256")] + ["render/closing-r5-dpm/gen/hu1.py"]
UNTRACKED = ["tools/usse-asm/usse-asm"]


def git(repo, *a, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def sha(b):
    return hashlib.sha256(b).hexdigest()


def lines():
    out = []
    head = git(MAIN, "rev-parse", "HEAD").decode().strip()
    for p in MAIN_FILES:
        b = git(MAIN, "show", f"{head}:{p}")
        if b is None or b != (MAIN / p).read_bytes():
            raise SystemExit(f"resgx545:{p} is not the committed file at {head}")
        out.append(f"{sha(b)}  {head}  resgx545:{p}")
    fork = git(LINUX, "rev-parse", FORK_PIN).decode().strip()
    for p in FORK_FILES:
        b = git(LINUX, "show", f"{fork}:{p}")
        if b is None:
            raise SystemExit(f"linux:{p} not at {fork}")
        out.append(f"{sha(b)}  {fork}  linux:{p}")
    dh = git(DATA, "rev-parse", "HEAD").decode().strip()
    for p in DATA_FILES:
        b = git(DATA, "show", f"{dh}:{p}")
        if b is None or sha(b) != sha((KP / "bins" / pathlib.Path(p).name).read_bytes()):
            raise SystemExit(f"data:{p} is not bins/{pathlib.Path(p).name}")
        out.append(f"{sha(b)}  {dh}  data:{p}")
    for p in DATA_RULES:
        b = git(DATA, "show", f"{dh}:{p}")
        if b is None or b != (DATA / p).read_bytes():
            raise SystemExit(f"data:{p} is not the committed file at {dh}")
        out.append(f"{sha(b)}  {dh}  data:{p}")
    for p in UNTRACKED:
        out.append(f"{sha((MAIN / p).read_bytes())}  untracked  resgx545:{p}")
    return out


HEADER = ("# FROZEN.commits (R6-dpm): the commit that holds each outside file the freeze pins or the checks read.  Verify a line with\n"
          "# `git -C REPO show COMMIT:PATH | shasum -a 256` (resgx545 = RESGX545_MAIN, linux = RESGX545_LINUX at the rgn4 fork commit,\n"
          "# data = resgx545-data: the program and the frozen offline rules).  Written by gen/frozen_commits.py; never rewritten after the first job.\n")


def main(argv):
    f = KP / "FROZEN.commits"
    if argv[1:] == ["write"]:
        f.write_text(HEADER + "\n".join(lines()) + "\n")
        return 0
    if argv[1:] == ["verify"]:
        bad = 0
        for ln in f.read_text().splitlines():
            if ln.startswith("#"):
                continue
            s, c, rp = ln.split("  ")
            repo, p = rp.split(":", 1)
            if c == "untracked":
                b = (MAIN / p).read_bytes() if (MAIN / p).exists() else None
            else:
                b = git({"resgx545": MAIN, "linux": LINUX, "data": DATA}[repo], "show", f"{c}:{p}")
            if b is None or sha(b) != s:
                print(f"FROZEN.commits: {rp} at {c} does not hash to {s[:12]}")
                bad = 1
        return bad
    print("usage: frozen_commits.py write|verify")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
