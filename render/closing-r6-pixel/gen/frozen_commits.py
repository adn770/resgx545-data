#!/usr/bin/env python3
"""frozen_commits.py: write FROZEN.commits beside this session's FROZEN.sha256: for every pin of a file of the resgx545 tree (an absolute
path under /Users/jtorra/src/resgx545) the pinned commit COMMIT (default: the HEAD of RESGX545_REPO's main checkout at the freeze) whose blob of that path
has exactly the pinned sha256, in the format HACKING.md gives (`sha256  commit  path`); a pin the history never tracked (a build product:
tools/usse-asm/usse-asm) says `untracked`.  Refuses to write when a tracked pin's blob at the commit differs.  The freeze itself is never
rewritten.  Pins of resgx545-data (not a resgx545 path component) are not part of this file.
  PY gen/frozen_commits.py [COMMIT]      (the repository: RESGX545_REPO, default /Users/jtorra/src/resgx545)
"""
import hashlib
import os
import pathlib
import re
import subprocess
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
REPO = pathlib.Path(os.environ.get("RESGX545_REPO", "/Users/jtorra/src/resgx545"))
COMMIT = sys.argv[1] if len(sys.argv) > 1 else subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
HEADER = """\
# FROZEN.commits: the resgx545 commit that holds each file of the resgx545 tree this session's
# FROZEN*.sha256 pin by absolute path. One line per pinned file and hash: the sha256, the
# commit, the path relative to the resgx545 tree. Verify a pin with
# `git -C resgx545 show <commit>:<path> | sha256sum`. "untracked" in the commit's place: a file
# resgx545 never tracked (a build product), verifiable only against the file itself. Written by
# gen/frozen_commits.py (this session's own, the format of tools/records/frozen.py); the freezes
# themselves are never rewritten.
"""


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True)


full = git("rev-parse", "--verify", COMMIT + "^{commit}").stdout.decode().strip()
if not full:
    sys.exit(f"no commit {COMMIT} in {REPO}")
lines, bad = [], []
for ln in (KP / "FROZEN.sha256").read_text().splitlines():
    m = re.fullmatch(r"([0-9a-f]{64}) [ *](/.+)", ln)
    if not m:
        continue
    parts = pathlib.PurePosixPath(m[2]).parts
    if "resgx545" not in parts[1:]:
        continue
    i = parts.index("resgx545")
    rel = "/".join(parts[i + 1:])
    blob = git("cat-file", "blob", f"{full}:{rel}")
    if blob.returncode == 0:
        if hashlib.sha256(blob.stdout).hexdigest() == m[1]:
            lines.append(f"{m[1]}  {full}  {rel}\n")
        else:
            bad.append(f"{rel}: the blob at {COMMIT} is not the pinned {m[1]}")
    elif not git("log", "--full-history", "--format=%H", "--", rel).stdout.strip():
        lines.append(f"{m[1]}  untracked  {rel}\n")
    else:
        bad.append(f"{rel}: not in {COMMIT}")
if bad:
    sys.exit("\n".join(bad))
text = HEADER + "".join(sorted(set(lines), key=lambda x: x.split()[2]))
out = KP / "FROZEN.commits"
if out.exists() and out.read_text() != text:
    sys.exit(f"{out} exists and differs: not replaced")
out.write_text(text)
print(f"{out}: {len(lines)} pins at {full}")
