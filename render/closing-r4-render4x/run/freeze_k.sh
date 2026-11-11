#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_k.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a score:
#            generators and the values they extracted, scorers (scorekit.py a byte-for-byte copy of resgx545 main's), runner scripts,
#            env, tables, predictions, the staged programs (bins/), TABLES.md, TOOL.sha256 and TOOLSRC.sha256, and by absolute path:
#            the resgx545 files the session uses (tools/closing/scorekit.py, the source of the copy; tools/bringup/health.sh, run by
#            k.sh) and every file the generator read from outside this directory (gen/data/sources.lst: the resgx545-data records the
#            controls and predictions come from, the assembler, the program sources).  Run it after gen/rgen.py and BEFORE the first
#            job; k.sh and the scorer verify it.  Then gen/frozen_commits.py writes FROZEN.commits.
#   verify   check both, and that no file was added since (a new table is a change too)
# Writes only the two .sha256 files (and .verify.out scratch).
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
files() {
	ls gen/*.py gen/data/* score/*.py run/*.sh run/k.env stages.txt TABLES.md TOOL.sha256 TOOLSRC.sha256
	ls tables/*.txt predictions/*.tsv bins/*
	ls "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/bringup/health.sh"
	cat gen/data/sources.lst
}
case "$MODE" in
freeze)
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/k.env || { echo "run/k.env does not name the pinned tool ($pin)"; exit 1; }
	cmp -s score/scorekit.py "$MAIN/tools/closing/scorekit.py" || { echo "score/scorekit.py is not main's tools/closing/scorekit.py byte for byte"; exit 1; }
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
