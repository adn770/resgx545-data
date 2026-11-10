#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_s1.sh [freeze | verify [STAGE]]  (S1b)
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a
#            run or a score: generators, scorers, runner scripts, tables, predictions, staged programs, and what the
#            scorers and generators import read-only from the landed tree and the data repo).  Run it after
#            gen/s1gen.py and BEFORE the first job; the session driver verifies it before each stage and the scorer
#            refuses to run unless it verifies.
#   verify   check both
# Writes only the .sha256 files in this directory.  The freeze is attested by file times and these hashes only
# (no external stamp), as in the earlier batches.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
DATA=${RESGX545_DATA:-$HOME/src/resgx545-data}
files() {
	ls gen/*.py score/*.py run/*.sh stages.txt TABLES.md TOOLSRC.sha256 2>/dev/null
	ls tables/*.txt predictions/* bins/* 2>/dev/null
	# read-only imports of the scorers and generators: frozen by sha256 too
	ls "$MAIN/tools/usse-asm/pbdump.py" "$MAIN/tools/usse-asm/probe.py" \
		"$DATA/vdm/verification-1141ta/recompute/q164_fate.py" \
		"$DATA/vdm/vtask-capacity/analysis/recompute_p1131.py" \
		"$DATA/texture/p1141/recompute/tex2.py" "$DATA/texture/p1141/support/texmodel.py"
}
case "$MODE" in
freeze)
	# the tool's source: the deploy inputs of TOOL_SRC (default the agent worktree whose libsgxfive carries the S1b
	# change; the same files committed to main hash the same); stage_s1.sh refuses a --src that differs
	. run/lib_check.sh
	TOOL_SRC=${TOOL_SRC:-$HOME/src/resgx545/.claude/worktrees/agent-aed0242cfe8ab4e23}
	toolsrc "$TOOL_SRC" > TOOLSRC.sha256
	[ -s TOOLSRC.sha256 ] || { echo "no deploy inputs under $TOOL_SRC"; exit 1; }
	shasum -a 256 predictions/* > PREDICTIONS.sha256
	files | xargs shasum -a 256 > FROZEN.sha256
	wc -l < FROZEN.sha256; wc -l < PREDICTIONS.sha256 ;;
verify)
	shasum -a 256 -c FROZEN.sha256 --quiet > .verify.out 2>&1
	a=$?
	head -3 .verify.out
	[ $a = 0 ] || { echo "FROZEN FILES CHANGED"; exit 1; }
	shasum -a 256 -c PREDICTIONS.sha256 --quiet > .verify.out 2>&1
	b=$?
	head -3 .verify.out
	[ $b = 0 ] || { echo "PREDICTIONS CHANGED"; exit 1; }
	echo "files verified" ;;
*) echo "usage: freeze_s1.sh [freeze|verify [STAGE]]"; exit 2 ;;
esac
