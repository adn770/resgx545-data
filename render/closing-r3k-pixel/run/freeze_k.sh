#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_k.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a
#            score: generators, scorers, runner scripts, env, tables, predictions, staged programs, the data the generators read,
#            TOOL.sha256 and TOOLSRC.sha256 (the pins, copied from closing3/r3-pixel) and the landed files the generators import
#            read-only).  Run it after gen/kgen.py and BEFORE the first job; k.sh and the scorer verify it.  The tool's source
#            must still be the pinned one (TOOLSRC.sha256) and k.env must name the pinned binary (TOOL.sha256).
#   verify   check both, and that no file was added since (a new table or program is a change too)
# Writes only the two .sha256 files (and .toolsrc.now / .verify.out scratch).  The freeze is attested by file times and these
# hashes only.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
. run/lib_check.sh
files() {
	ls gen/*.py gen/data/* score/*.py run/*.sh run/k.env stages.txt conditional.txt TABLES.md TOOL.sha256 TOOLSRC.sha256
	ls tables/*.txt predictions/*.tsv bins/*.bin
	# read-only imports of the generators and scorers: frozen by sha256 too (the tool's source is the one R1 built)
	ls "$MAIN/userspace/libsgxfive/tools/sgxfive-test.c"
}
case "$MODE" in
freeze)
	toolsrc "$MAIN" > .toolsrc.now
	cmp -s .toolsrc.now TOOLSRC.sha256 || { echo "the landed tool source differs from the pinned TOOLSRC.sha256: the mock would not be R1's tool"; exit 1; }
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/k.env || { echo "run/k.env does not name the pinned tool ($pin)"; exit 1; }
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_k.sh freeze"; exit 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> .verify.out 2>&1; b=$?
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_k.sh [freeze|verify]"; exit 2 ;;
esac
