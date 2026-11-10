#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r3.sh [freeze | verify]  (R3)
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a
#            run or a score: generators, scorers, runner scripts, tables, predictions, staged programs, the vertex
#            templates, TOOL.sha256 and TOOLSRC.sha256, and what the scorers and generators import read-only from the
#            landed tree).  Run it after gen/r3gen.py and BEFORE the first job; the session driver verifies it before each
#            stage and the scorer refuses to run unless it verifies.  Refuses if the landed tool source no longer hashes as
#            the pinned TOOLSRC.sha256 (the source R1's laptop binary was built from: the Mac mock must be that tool).
#   verify   check both
# Writes only the .sha256 files in this directory.  The freeze is attested by file times and these hashes only
# (no external stamp), as in the earlier batches.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
files() {
	ls gen/*.py score/*.py run/*.sh run/*.awk stages.txt TABLES.md TOOLSRC.sha256 TOOL.sha256 2>/dev/null
	ls tables/*.txt predictions/* bins/* templates/*.s 2>/dev/null
	# read-only imports of the scorers and generators (and the templates the generators read): frozen by sha256 too
	ls "$MAIN/tools/usse-asm/pbdump.py" "$MAIN/tools/usse-asm/probe.py" "$MAIN/tools/sweep/counters.py" \
		"$MAIN/probes/mte/templates/vtx_zab.s" "$MAIN/probes/mte/templates/vtx_w.s" \
		"$MAIN/probes/mte/templates/vtx_wclip.s" "$MAIN/probes/mte/templates/pix_green.s" \
		"$MAIN/probes/usse/templates/pix_op.s" 2>/dev/null
}
case "$MODE" in
freeze)
	. run/lib_check.sh
	toolsrc "$MAIN" > .toolsrc.now
	cmp -s .toolsrc.now TOOLSRC.sha256 || { echo "the landed tool source differs from the pinned TOOLSRC.sha256: the mock would not be R1's tool"; exit 1; }
	[ -s TOOL.sha256 ] || { echo "no TOOL.sha256 (the laptop tool's pinned hash)"; exit 1; }
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
*) echo "usage: freeze_r3.sh [freeze|verify]"; exit 2 ;;
esac
