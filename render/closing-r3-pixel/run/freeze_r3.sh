#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r3.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a score:
#            generators, scorers, runner scripts, env, tables, predictions, staged programs, templates, TOOL.sha256 and TOOLSRC.sha256
#            (R1's pins), and the landed files the generators import read-only).  Run it after gen/r3gen.py and BEFORE the first
#            job; r3.sh and the scorer verify it.  The tool's source must still be the pinned one (TOOLSRC.sha256) and r3.env must
#            name the pinned binary (TOOL.sha256): the mock would not be R1's tool otherwise.
#   verify   check both, and that no file was added since (a new table or program is a change too)
# Writes only the two .sha256 files (and .toolsrc.now / .verify.out scratch).  The freeze is attested by file times and these
# hashes only.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
. run/lib_check.sh
files() {
	ls gen/*.py score/*.py run/*.sh run/r3.env stages.txt conditional.txt TABLES.md TOOL.sha256 TOOLSRC.sha256
	ls tables/*.txt predictions/*.tsv bins/*.bin bins/*.tsv templates/*.s
	# read-only imports of the generators and scorers: frozen by sha256 too
	ls "$MAIN/tools/usse-asm/probe.py" "$MAIN/tools/usse-asm/pbdump.py" "$MAIN/tools/usse-asm/usse-asm" \
		"$MAIN/probes/mte/templates/vtx_zab.s" "$MAIN/probes/usse/templates/pds_iter_xy.s" "$MAIN/probes/usse/templates/vtx_coords.s" \
		"$MAIN/userspace/libsgxfive/tools/sgxfive-test.c" "$HOME/src/resgx545-data/vdm/verification-1141ta/programs/o4g-3-x.s" \
		"$HOME/src/resgx545-data/vdm/verification-1141ta/programs/o4g-3-y.s"
}
case "$MODE" in
freeze)
	toolsrc "$MAIN" > .toolsrc.now
	cmp -s .toolsrc.now TOOLSRC.sha256 || { echo "the landed tool source differs from the pinned TOOLSRC.sha256: the mock would not be R1's tool"; exit 1; }
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/r3.env || { echo "run/r3.env does not name the pinned tool ($pin)"; exit 1; }
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_r3.sh freeze"; exit 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> .verify.out 2>&1; b=$?
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_r3.sh [freeze|verify]"; exit 2 ;;
esac
