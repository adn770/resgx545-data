#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""frozen_commits.py write|verify A|B: FROZEN.commits (set A) or FROZEN-B.commits (set B), the commit that holds each file from outside
this session that the freeze pins or that the session's checks read (the format of tools/records/frozen.py): `sha256  commit  repo:path`.

  resgx545:PATH       the landed tree at main 1c64f3a (MAIN_PIN, the brief's freeze point; RESGX545_MAIN): the working tree's file must
                      be the committed one there, else the freeze refuses (main moves while sessions are built)
  resgx545@OLD:PATH   set B only: tools/fwtask/regs.toml before 7d0ee7f (the OLD register list, which must refuse oomring2)
  linux:PATH          set B only: the linux fork at 664fd0d0 (module 37EC97AB: the verifier that accepts oomring2) and the one file
                      sgx_own_regs.h at 3f0b3e74 (module 41E2F5C7, loaded now: its list refuses oomring2) (RESGX545_LINUX)
  data:PATH           resgx545-data at 830641e6 (DATA_PIN): the program p1139-green.bin, the frozen offline rules of
                      cited/closing6/dpm/offline and cited/closing7/b/offline, HU1 of closing-r5-dpm (gen/r7model.py imports them)
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
MAIN_PIN = "1c64f3a"
DATA_PIN = "830641e6"
FORK_B = "664fd0d00765"
FORK_A = "3f0b3e74b51b"
OLD_REGS = "7d0ee7f^"
MAIN_FILES = ["tools/fwtask/fwtask.py", "tools/fwtask/regs.toml", "tools/fwtask/fwtask_run.py", "tools/fwtask/simrun.py",
              "tools/fwtask/layout.py", "tools/fwtask/host/own_host.c", "tools/closing/scorekit.py", "tools/closing/sessioncheck.py",
              "tools/forkpin.py", "tools/sweep/regtimeline.c", "userspace/libsgxfive/tools/sgxfive-test.c",
              "tools/usse-asm/dpm_words.py"]
FORK_FILES = ["drivers/gpu/drm/gma500/sgxfive/sgxfive_owntask.c", "drivers/gpu/drm/gma500/sgxfive/sgxfive_owntask.h",
              "drivers/gpu/drm/gma500/sgxfive/sgx_fw.c", "drivers/gpu/drm/gma500/sgxfive/sgx_own_regs.h"]
DATA_FILES = ["render/closing-r3-geo/bins/p1139-green.bin"]
OFF6 = "cited/closing6/dpm/offline/"
OFF7 = "cited/closing7/b/offline/"
DATA_RULES = ([OFF6 + f for f in ("f5lib.py", "f5_stepmodel.py", "f4_phase.py", "f9_loss.py", "f7_replay.py", "r6lib.py",
                                  "FREEZE-f1.sha256", "FREEZE-f4.sha256", "FREEZE-f5.sha256", "FREEZE-f7.sha256", "FREEZE-f9.sha256")]
              + [OFF7 + f for f in ("olib.py", "g1_walk64.py", "g2_replay64.py", "g3_span.py", "FREEZE-g1.sha256", "FREEZE-g2.sha256",
                                    "FREEZE-g3.sha256", "g1_walk64.out", "g2_replay64.out", "g3_span.out", "g5_blocks.out")]
              + ["render/closing-r5-dpm/gen/hu1.py"])
UNTRACKED = ["tools/usse-asm/usse-asm"]


def git(repo, *a):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rev(repo, c):
    out = git(repo, "rev-parse", c)
    if out is None:
        raise SystemExit(f"{repo}: no commit {c}")
    return out.decode().strip()


def lines(set_):
    out = []
    head = rev(MAIN, MAIN_PIN)
    for p in MAIN_FILES:
        b = git(MAIN, "show", f"{head}:{p}")
        if b is None or b != (MAIN / p).read_bytes():
            raise SystemExit(f"resgx545:{p} in the working tree is not the committed file at main {MAIN_PIN}")
        out.append(f"{sha(b)}  {head}  resgx545:{p}")
    if set_ == "B":
        old = rev(MAIN, OLD_REGS)
        out.append(f"{sha(git(MAIN, 'show', f'{old}:tools/fwtask/regs.toml'))}  {old}  resgx545:tools/fwtask/regs.toml")
        fb = rev(LINUX, FORK_B)
        for p in FORK_FILES:
            b = git(LINUX, "show", f"{fb}:{p}")
            if b is None:
                raise SystemExit(f"linux:{p} not at {fb}")
            out.append(f"{sha(b)}  {fb}  linux:{p}")
        fa = rev(LINUX, FORK_A)
        p = FORK_FILES[-1]
        out.append(f"{sha(git(LINUX, 'show', f'{fa}:{p}'))}  {fa}  linux:{p}")
    dh = rev(DATA, DATA_PIN)
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


def header(set_):
    return (f"# FROZEN{'' if set_ == 'A' else '-B'}.commits (R7-dpm, set {set_}): the commit that holds each outside file the freeze pins or the\n"
            "# checks read.  Verify a line with `git -C REPO show COMMIT:PATH | shasum -a 256` (resgx545 = RESGX545_MAIN at main 1c64f3a,\n"
            "# linux = RESGX545_LINUX, data = resgx545-data at 830641e6).  Written by gen/frozen_commits.py; never rewritten after the first job.\n")


def main(argv):
    if len(argv) < 3 or argv[2] not in ("A", "B"):
        print("usage: frozen_commits.py write|verify A|B")
        return 2
    set_ = argv[2]
    f = KP / ("FROZEN.commits" if set_ == "A" else "FROZEN-B.commits")
    if argv[1] == "write":
        f.write_text(header(set_) + "\n".join(lines(set_)) + "\n")
        return 0
    if argv[1] == "verify":
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
                print(f"{f.name}: {rp} at {c} does not hash to {s[:12]}")
                bad = 1
        return bad
    print("usage: frozen_commits.py write|verify A|B")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
