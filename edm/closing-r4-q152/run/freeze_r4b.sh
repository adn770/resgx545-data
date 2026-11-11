#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r4b.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (predictions/*), LAPTOP.sha256 (the files as laid out on the laptop under ~/r4b: gen/laptop_files.py,
#            plus the landed fwtask_run.py as run/fwtask_run.py) and FROZEN.sha256 (every file that defines a case, a run or a score, and the
#            files of the resgx545 tree they use, by absolute path).  Run after gen/gen_r4b.py and BEFORE the first job.
#   verify   check both
cd "$(dirname "$0")/.." || exit 1
R=${RESGX545:-$HOME/src/resgx545}
PY=${PY:-$R/.venv/bin/python}
MODE=${1:-freeze}
files() {
	ls asm/ring_exit.s bins/ring_exit.blob bins/blobs.json gen/*.py score/*.py run/*.sh run/*.py tables/*.json predictions/* \
		TABLES.md LAPTOP.sha256 TOOL.sha256 tests/test_gen_r4b.py &&
	ls "$R/tools/fwtask/fwtask_run.py" "$R/tools/fwtask/fwtask.py" "$R/tools/fwtask/regs.toml"
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
	# FROZEN.commits (HACKING.md): the resgx545 commit that holds each pinned file of the tree, by tools/records/frozen.py's own finder
	"$PY" - "$R" > FROZEN.commits <<'PYEOF' || { echo "FROZEN.commits not written"; exit 1; }
import pathlib, sys
R = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(R / "tools" / "records"))
import frozen
text, bad = frozen.commits_for(pathlib.Path("."), frozen.Finder(R), "2026-11-11")
if bad:
    sys.exit("pins no commit holds: " + "; ".join(bad))
sys.stdout.write(text)
PYEOF
	echo "$(wc -l < FROZEN.sha256 | tr -d ' ') files frozen, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions files" ;;
verify)
	out=$(shasum -a 256 -c FROZEN.sha256 --quiet 2>&1)
	st=$?
	[ $st = 0 ] || { printf '%s\n' "$out" | head -3; echo "FROZEN FILES CHANGED"; exit 1; }
	out=$(shasum -a 256 -c PREDICTIONS.sha256 --quiet 2>&1)
	st=$?
	[ $st = 0 ] || { printf '%s\n' "$out" | head -3; echo "PREDICTIONS CHANGED"; exit 1; }
	# every FROZEN.commits line: git show COMMIT:PATH hashes to the pinned sha256
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
    h, c, p = re.fullmatch(r"([0-9a-f]{64})  ([0-9a-f]{7,40})  (\S.*)", ln).groups()
    blob = subprocess.run(["git", "-C", R, "show", f"{c}:{p}"], capture_output=True).stdout
    if hashlib.sha256(blob).hexdigest() != h:
        sys.exit(f"{p}: {c} does not hold {h[:16]}")
    seen[p] = h
if seen != pins:
    sys.exit(f"FROZEN.commits does not cover the pins: {sorted(set(pins) ^ set(seen))}")
PYEOF
	echo "files verified" ;;
*) echo "usage: freeze_r4b.sh [freeze|verify]"; exit 2 ;;
esac
