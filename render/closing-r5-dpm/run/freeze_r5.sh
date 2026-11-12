#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r5.sh [freeze | verify]  (R5-dpm; built from R3-geo's freeze_r3.sh)
#   freeze   write PREDICTIONS.sha256 (every predictions file), FROZEN.sha256 (every file that defines a case, a run or a score:
#            generators, scorers, runner scripts, the reader, tables, predictions, staged programs, the task source, TOOL.sha256 and
#            TOOLSRC.sha256, and what the generators, guard and tests import read-only from the landed tree) and FROZEN.commits (the
#            resgx545 commit, and the linux fork commit, that hold each landed file: gen/frozen_commits.py).  Run after gen/r5plan.py
#            and gen/gen_oomring.py and BEFORE the first job; the driver verifies before each stage and the scorer refuses to run
#            unless it verifies.
#   verify   check all three
# Writes only the .sha256 / .commits files in this directory.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
files() {
	ls gen/*.py score/*.py run/*.sh run/*.py run/r5.env asm/*.s stages.txt TABLES.md TOOLSRC.sha256 TOOL.sha256 2>/dev/null
	ls tables/*.txt predictions/* bins/* 2>/dev/null
	ls "$MAIN/tools/fwtask/fwtask.py" "$MAIN/tools/fwtask/regs.toml" "$MAIN/tools/fwtask/fwtask_run.py" "$MAIN/tools/fwtask/simrun.py" \
		"$MAIN/tools/fwtask/layout.py" "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/forkpin.py" 2>/dev/null
}
case "$MODE" in
freeze)
	[ -s TOOL.sha256 ] && [ -s TOOLSRC.sha256 ] || { echo "no TOOL.sha256 / TOOLSRC.sha256"; exit 1; }
	shasum -a 256 predictions/* > PREDICTIONS.sha256
	files | xargs shasum -a 256 > FROZEN.sha256
	PYTHONDONTWRITEBYTECODE=1 "$PY" gen/frozen_commits.py write || { echo "FROZEN.commits could not be written"; exit 1; }
	wc -l < FROZEN.sha256; wc -l < PREDICTIONS.sha256 ;;
verify)
	shasum -a 256 -c FROZEN.sha256 --quiet > debug/.verify.out 2>&1
	a=$?
	head -3 debug/.verify.out
	[ $a = 0 ] || { echo "FROZEN FILES CHANGED"; exit 1; }
	shasum -a 256 -c PREDICTIONS.sha256 --quiet > debug/.verify.out 2>&1
	b=$?
	head -3 debug/.verify.out
	[ $b = 0 ] || { echo "PREDICTIONS CHANGED"; exit 1; }
	PYTHONDONTWRITEBYTECODE=1 "$PY" gen/frozen_commits.py verify || { echo "FROZEN.commits does not verify"; exit 1; }
	echo "files verified" ;;
*) echo "usage: freeze_r5.sh [freeze|verify]"; exit 2 ;;
esac
