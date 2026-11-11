#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r4e.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (predictions/*), LAPTOP.sha256 (the files as laid out on the laptop under ~/r4e-run: gen/laptop_files.py,
#            plus the landed fwtask_run.py as run/fwtask_run.py), FROZEN.sha256 (every file that defines a case, a run or a score, and the files
#            of the resgx545 tree they use, by absolute path) and FROZEN.commits (the resgx545 commit that holds each pinned file of the tree:
#            5a13042, verified with `git show`).  Run after gen/gen_r4.py and BEFORE the first job.
#   verify   check all of them
# The tree is $RESGX545 (default: the integration worktree closing4/lead/wt, branch r4-fold-rule at 5a13042).
cd "$(dirname "$0")/.." || exit 1
R=${RESGX545:-/Users/jtorra/src/scratch/resgx545/closing4/lead/wt}
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
PIN=5a13042a36972b37ae1e4c2338e0b7d0acd4da2c
MODE=${1:-freeze}
files() {
	ls gen/*.py asm/*.s bins/*.blob bins/blobs.json score/*.py run/*.sh run/*.py tables/*.json predictions/* stages.txt TABLES.md \
		LAPTOP.sha256 TOOL.sha256 tests/*.py tests/*.sh tests/mockfw/*.py tests/shims/* tests/fixtures/real/* &&
	ls "$R/tools/fwtask/fwtask_run.py" "$R/tools/fwtask/fwtask.py" "$R/tools/fwtask/regs.toml" "$R/tools/fwtask/simrun.py" \
		"$R/tools/usse-asm/usse-asm"
}
# FROZEN.commits: one `sha256  commit  path` line per pinned file of the tree (the path relative to it); a file the history never tracked
# (the built assembler) says `untracked`
commits() {
	R=$R PIN=$PIN "$PY" - <<'PYEOF'
import os, subprocess, sys
R, PIN = os.environ["R"], os.environ["PIN"]
print("""# FROZEN.commits: the resgx545 commit that holds each file of the resgx545 tree this session's FROZEN.sha256 pins by absolute
# path (the integration worktree of closing4, branch r4-fold-rule).  One line per pinned file: the sha256, the commit, the path
# relative to the tree.  Verify a pin with `git -C resgx545 show <commit>:<path> | sha256sum`.  "untracked" in the commit's place:
# a build product the history never held, verifiable only against the file itself.""")
for ln in open("FROZEN.sha256").read().splitlines():
    h, p = ln.split("  ", 1)
    if not p.startswith(R + "/"):
        continue
    rel = p[len(R) + 1:]
    tracked = subprocess.run(["git", "-C", R, "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0
    if not tracked:
        print(f"{h}  untracked  {rel}")
        continue
    blob = subprocess.run(["git", "-C", R, "show", f"{PIN}:{rel}"], capture_output=True).stdout
    import hashlib
    if hashlib.sha256(blob).hexdigest() != h:
        sys.exit(f"{rel}: commit {PIN[:7]} does not hold the file as pinned")
    print(f"{h}  {PIN}  {rel}")
PYEOF
}
case "$MODE" in
freeze)
	shasum -a 256 predictions/* > PREDICTIONS.sha256 || exit 1
	h=$(shasum -a 256 "$R/tools/fwtask/fwtask_run.py" | cut -d' ' -f1)
	[ -n "$h" ] || { echo "no landed fwtask_run.py"; exit 1; }
	list=$("$PY" gen/laptop_files.py) || { echo "no file list"; exit 1; }
	# shellcheck disable=SC2086
	shasum -a 256 $list > LAPTOP.sha256 || exit 1
	echo "$h  run/fwtask_run.py" >> LAPTOP.sha256
	list=$(files) || { echo "a frozen file is missing"; exit 1; }
	printf '%s\n' "$list" | xargs shasum -a 256 > FROZEN.sha256 || { echo "hashing failed"; exit 1; }
	commits > FROZEN.commits || { echo "FROZEN.commits not written"; exit 1; }
	echo "$(wc -l < FROZEN.sha256 | tr -d ' ') files frozen, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions files, $(grep -vc '^#' FROZEN.commits) pins" ;;
verify)
	out=$(shasum -a 256 -c FROZEN.sha256 --quiet 2>&1)
	st=$?
	[ $st = 0 ] || { printf '%s\n' "$out" | head -3; echo "FROZEN FILES CHANGED"; exit 1; }
	out=$(shasum -a 256 -c PREDICTIONS.sha256 --quiet 2>&1)
	st=$?
	[ $st = 0 ] || { printf '%s\n' "$out" | head -3; echo "PREDICTIONS CHANGED"; exit 1; }
	[ -f FROZEN.commits ] || { echo "no FROZEN.commits"; exit 1; }
	# every pin of FROZEN.sha256 under the tree has a FROZEN.commits line, and `git show COMMIT:PATH` hashes to it
	R=$R "$PY" - <<'PYEOF' || { echo "FROZEN.COMMITS DO NOT VERIFY"; exit 1; }
import hashlib, os, re, subprocess, sys
R = os.environ["R"]
pins = {}
for ln in open("FROZEN.sha256").read().splitlines():
    h, p = ln.split("  ", 1)
    if p.startswith(R + "/"):
        pins[p[len(R) + 1:]] = h
seen = {}
for ln in open("FROZEN.commits").read().splitlines():
    if ln.startswith("#"):
        continue
    m = re.fullmatch(r"([0-9a-f]{64})  ([0-9a-f]{40}|untracked)  (\S.*)", ln)
    if not m:
        sys.exit(f"bad FROZEN.commits line: {ln}")
    h, c, p = m.groups()
    if c != "untracked":
        blob = subprocess.run(["git", "-C", R, "show", f"{c}:{p}"], capture_output=True).stdout
        if hashlib.sha256(blob).hexdigest() != h:
            sys.exit(f"{p}: {c} does not hold {h[:16]}")
        if not c.startswith("5a13042"):
            sys.exit(f"{p}: pinned to {c[:7]}, not 5a13042")
    seen[p] = h
if seen != pins:
    sys.exit(f"FROZEN.commits does not cover the pins: {sorted(set(pins) ^ set(seen))}")
PYEOF
	echo "files verified" ;;
*) echo "usage: freeze_r4e.sh [freeze|verify]"; exit 2 ;;
esac
