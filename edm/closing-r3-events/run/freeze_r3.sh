#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r3.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (predictions/*), LAPTOP.sha256 (the files as laid out on the laptop under ~/r3ev/: tables,
#            the three blobs and blobs.json, r3layout.py, the runner, health_remote.sh, TOOL.sha256 and the landed fwtask_run.py
#            as run/fwtask_run.py) and FROZEN.sha256 (every file that defines a case, a run or a score, LAPTOP.sha256 among them,
#            and what they import from the landed tree).  Run it after gen/gen_r3.py and BEFORE the first job; r3.sh and
#            score_r3.py verify it.
#   verify   check both
# Writes only the three .sha256 files.  The freeze is attested by file times and these hashes only, as in S1, S2b and R1.
set -o pipefail
cd "$(dirname "$0")/.." || exit 1
R=${RESGX545:-$HOME/src/resgx545}
MODE=${1:-freeze}
files() {
	ls gen/*.py asm/*.s bins/*.blob bins/blobs.json score/*.py run/*.sh run/*.py tables/*.json \
		predictions/* stages.txt TABLES.md LAPTOP.sha256 TOOL.sha256 tests/sim_r3.py &&
	ls "$R/tools/fwtask/fwtask_run.py" "$R/tools/fwtask/fwtask.py" "$R/tools/fwtask/regs.toml" \
		"$R/tools/fwtask/simrun.py" "$R/tools/usse-asm/usse-asm"
}
case "$MODE" in
freeze)
	shasum -a 256 predictions/* > PREDICTIONS.sha256 || exit 1
	shasum -a 256 tables/*.json bins/*.blob bins/blobs.json gen/r3layout.py run/r3_run.py run/health_remote.sh TOOL.sha256 \
		> LAPTOP.sha256 || exit 1
	h=$(shasum -a 256 "$R/tools/fwtask/fwtask_run.py" | cut -d' ' -f1)
	[ -n "$h" ] || { echo "no landed fwtask_run.py"; exit 1; }
	echo "$h  run/fwtask_run.py" >> LAPTOP.sha256
	list=$(files) || { echo "a frozen file is missing"; exit 1; }
	printf '%s\n' "$list" | xargs shasum -a 256 > FROZEN.sha256 || { echo "hashing failed"; exit 1; }
	echo "$(wc -l < FROZEN.sha256 | tr -d ' ') files frozen, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions files" ;;
verify)
	out=$(shasum -a 256 -c FROZEN.sha256 --quiet 2>&1)
	st=$?
	[ $st = 0 ] || { printf '%s\n' "$out" | head -3; echo "FROZEN FILES CHANGED"; exit 1; }
	out=$(shasum -a 256 -c PREDICTIONS.sha256 --quiet 2>&1)
	st=$?
	[ $st = 0 ] || { printf '%s\n' "$out" | head -3; echo "PREDICTIONS CHANGED"; exit 1; }
	echo "files verified" ;;
*) echo "usage: freeze_r3.sh [freeze|verify]"; exit 2 ;;
esac
