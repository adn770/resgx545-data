#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r1.sh [freeze | verify]  (R1)
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a
#            run or a score: generators, scorers, runner scripts, tables, predictions, staged programs, the vertex
#            templates, and what the scorers and generators import read-only from the landed tree).  Run it after
#            gen/r1gen.py and BEFORE the first job; the session driver verifies it before each stage and the scorer
#            refuses to run unless it verifies.  TOOLSRC.sha256 (the deploy inputs of the tool) is written first.
#   verify   check both
# Writes only the .sha256 files in this directory.  The freeze is attested by file times and these hashes only
# (no external stamp), as in the earlier batches.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
files() {
	ls gen/*.py score/*.py run/*.sh stages.txt TABLES.md TOOLSRC.sha256 2>/dev/null
	ls tables/*.txt predictions/* bins/* templates/*.s 2>/dev/null
	# read-only imports of the scorers and generators (and the templates the generators read): frozen by sha256 too
	ls "$MAIN/tools/usse-asm/pbdump.py" "$MAIN/tools/usse-asm/probe.py" "$MAIN/tools/sweep/counters.py" \
		"$MAIN/probes/mte/templates/vtx_zab.s" "$MAIN/probes/mte/templates/vtx_w.s" \
		"$MAIN/probes/mte/templates/vtx_wclip.s" "$MAIN/probes/mte/templates/pix_green.s" \
		"$MAIN/probes/usse/templates/pix_op.s" "$MAIN/probes/usse/templates/pds_iter_xy.s" \
		"$MAIN/probes/usse/templates/vtx_coords.s" 2>/dev/null
}
case "$MODE" in
freeze)
	# the tool's source: the deploy inputs of TOOL_SRC (default main: its libsgxfive carries the S1b --index-width
	# change); stage_r1.sh refuses a --src that differs
	. run/lib_check.sh
	TOOL_SRC=${TOOL_SRC:-$MAIN}
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
*) echo "usage: freeze_r1.sh [freeze|verify]"; exit 2 ;;
esac
