#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r3.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (predictions/*), LAPTOP-k0.sha256 and LAPTOP-kev.sha256 (the files as laid out on the laptop under ~/r3k0
#            and ~/r3kev: gen/laptop_files.py lists them, plus the landed fwtask_run.py as run/fwtask_run.py) and FROZEN.sha256 (every file that
#            defines a case, a run or a score, the LAPTOP files among them, and what they import from the landed tree).  Run it after
#            gen/gen_r3.py and BEFORE the first job; r3.sh and score_r3.py verify it.
#   verify   check both
# Writes only the .sha256 files.  The freeze is attested by file times and these hashes only, as in S1, S2b, R1 and L3.
set -o pipefail
cd "$(dirname "$0")/.." || exit 1
R=${RESGX545:-$HOME/src/resgx545}
PY=${PY:-../../closing/pixel-faults/.venv/bin/python}
MODE=${1:-freeze}
files() {
	ls gen/*.py asm/*.s bins/*.blob bins/blobs.json bins/progs/* score/*.py run/*.sh run/*.py tables/*.json \
		predictions/* stages-*.txt TABLES.md LAPTOP-*.sha256 TOOL.sha256 TOOLR1.sha256 tests/sim_r3.py &&
	ls "$R/tools/fwtask/fwtask_run.py" "$R/tools/fwtask/fwtask.py" "$R/tools/fwtask/regs.toml" \
		"$R/tools/fwtask/simrun.py" "$R/tools/usse-asm/usse-asm"
}
case "$MODE" in
freeze)
	shasum -a 256 predictions/* > PREDICTIONS.sha256 || exit 1
	h=$(shasum -a 256 "$R/tools/fwtask/fwtask_run.py" | cut -d' ' -f1)
	[ -n "$h" ] || { echo "no landed fwtask_run.py"; exit 1; }
	for s in k0 kev; do
		list=$("$PY" gen/laptop_files.py $s) || { echo "no file list for $s"; exit 1; }
		# shellcheck disable=SC2086
		shasum -a 256 $list > "LAPTOP-$s.sha256" || exit 1
		echo "$h  run/fwtask_run.py" >> "LAPTOP-$s.sha256"
	done
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
