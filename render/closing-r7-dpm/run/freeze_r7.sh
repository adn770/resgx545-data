#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r7.sh [freeze | verify] [A | B | AB]  (R7-dpm; R6-dpm's freeze_r6.sh with two sets)
#   Two freezes (README.md): set A (s-a0, s-m, s-b, s-v on module 41E2F5C7) is FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits;
#   set B (s-k on module 37EC97AB, after the one-shot boot) is FROZEN-B.sha256, PREDICTIONS-B.sha256, FROZEN-B.commits.
#   freeze   write the set's three files: every file that defines a case, a run or a score (generators, scorers, runner scripts, the
#            reader, the landed sessioncheck.py and scorekit.py copies, the set's tables and predictions, its staged programs, its task
#            source and blob for B, TOOL.sha256 and TOOLSRC.sha256, and what the generators, guard and tests import read-only from the
#            landed tree and the published data) and the commits that hold each outside file (gen/frozen_commits.py).  Run after
#            gen/r7plan.py and gen/gen_oomring2.py and BEFORE the set's first job; the driver verifies before each stage and the
#            scorer refuses to run unless its set verifies.
#   verify   check the set's three files (default AB: both)
# Writes only the .sha256 / .commits files in this directory.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
SETS=${2:-AB}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
DATA=${RESGX545_DATA:-$HOME/src/resgx545-data}
code() {
	ls gen/*.py score/*.py run/*.sh run/*.py run/r7.env TOOLSRC.sha256 TOOL.sha256 2>/dev/null
	ls "$MAIN/tools/fwtask/fwtask.py" "$MAIN/tools/fwtask/regs.toml" "$MAIN/tools/fwtask/fwtask_run.py" "$MAIN/tools/fwtask/simrun.py" \
		"$MAIN/tools/fwtask/layout.py" "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/closing/sessioncheck.py" "$MAIN/tools/forkpin.py" \
		"$MAIN/tools/usse-asm/dpm_words.py" 2>/dev/null
	# the frozen offline rules the predictions start from (gen/r7model.py imports them; E873-E875, E899 and E900 cite them)
	ls "$DATA"/cited/closing6/dpm/offline/{f5lib,f5_stepmodel,f4_phase,f9_loss,f7_replay,r6lib}.py \
		"$DATA"/cited/closing6/dpm/offline/FREEZE-f{1,4,5,7,9}.sha256 "$DATA"/render/closing-r5-dpm/gen/hu1.py \
		"$DATA"/cited/closing7/b/offline/{olib,g1_walk64,g2_replay64,g3_span}.py "$DATA"/cited/closing7/b/offline/FREEZE-g{1,2,3}.sha256 2>/dev/null
}
files() {
	code
	if [ "$1" = A ]; then
		ls stages.txt tables/s-a0.txt tables/s-m.txt tables/s-b.txt tables/s-v.txt predictions/s-a0.tsv predictions/s-m.tsv \
			predictions/s-b.tsv predictions/s-v.tsv bins/p1139-green.bin
	else
		ls stagesB.txt tables/s-k.txt predictions/s-k.tsv bins/p1139-green.bin bins/oomring2.blob bins/blobs.json asm/oomring2.s asm/oomring.s
	fi
}
sfx() { [ "$1" = A ] && echo "" || echo "-B"; }
for set_ in $(echo "$SETS" | fold -w1); do
	case "$set_" in A|B) ;; *) echo "usage: freeze_r7.sh [freeze|verify] [A|B|AB]"; exit 2 ;; esac
	s=$(sfx "$set_")
	case "$MODE" in
	freeze)
		[ -s TOOL.sha256 ] && [ -s TOOLSRC.sha256 ] || { echo "no TOOL.sha256 / TOOLSRC.sha256"; exit 1; }
		if [ "$set_" = A ]; then shasum -a 256 predictions/s-a0.tsv predictions/s-m.tsv predictions/s-b.tsv predictions/s-v.tsv > PREDICTIONS.sha256
		else shasum -a 256 predictions/s-k.tsv > PREDICTIONS-B.sha256; fi
		files "$set_" | xargs shasum -a 256 > "FROZEN$s.sha256"
		PYTHONDONTWRITEBYTECODE=1 "$PY" gen/frozen_commits.py write "$set_" || { echo "FROZEN$s.commits could not be written"; exit 1; }
		echo "set $set_: $(wc -l < "FROZEN$s.sha256" | tr -d ' ') files, $(wc -l < "PREDICTIONS$s.sha256" | tr -d ' ') predictions files" ;;
	verify)
		mkdir -p debug
		shasum -a 256 -c "FROZEN$s.sha256" --quiet > debug/.verify.out 2>&1
		a=$?
		head -3 debug/.verify.out
		[ $a = 0 ] || { echo "SET $set_: FROZEN FILES CHANGED"; exit 1; }
		shasum -a 256 -c "PREDICTIONS$s.sha256" --quiet > debug/.verify.out 2>&1
		b=$?
		head -3 debug/.verify.out
		[ $b = 0 ] || { echo "SET $set_: PREDICTIONS CHANGED"; exit 1; }
		PYTHONDONTWRITEBYTECODE=1 "$PY" gen/frozen_commits.py verify "$set_" || { echo "FROZEN$s.commits does not verify"; exit 1; }
		echo "set $set_: files verified" ;;
	*) echo "usage: freeze_r7.sh [freeze|verify] [A|B|AB]"; exit 2 ;;
	esac
done
