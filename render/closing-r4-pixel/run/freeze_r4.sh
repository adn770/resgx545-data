#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r4.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a score:
#            generators, scorers (score/scorekit.py a byte-for-byte copy of tools/closing/scorekit.py at the pinned commit), runner
#            scripts, env, tables, predictions, staged programs, templates, TOOL.sha256, TABLES.md, and by ABSOLUTE path the resgx545 and
#            resgx545-data files the session reads (the lines of gen/pins_*.txt)).  Run it after gen/r4gen.py and BEFORE the first job;
#            r4.sh and the scorers verify it.  Then gen/frozen_commits.py writes FROZEN.commits (the pinned resgx545 commit 5a13042).
#   verify   check both, and that no file was added since (a new table or program is a change too)
# The resgx545 pins are written under /Users/jtorra/src/resgx545 (the tree FROZEN.commits names).  RESGX545_MAIN (default that path) is
# the tree the files are READ from: the offline build read the lead's worktree of 5a13042 (RESGX545_MAIN=.../closing4/lead/wt) because
# the main checkout had not yet merged it; the hashes are those of 5a13042, so verify works with either tree once the files agree.
# RESGX545_DATA likewise for /Users/jtorra/src/resgx545-data.  Writes only the two .sha256 files (and .verify.out scratch).
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
CANON_MAIN=/Users/jtorra/src/resgx545
CANON_DATA=/Users/jtorra/src/resgx545-data
MAIN=${RESGX545_MAIN:-$CANON_MAIN}
DATA=${RESGX545_DATA:-$CANON_DATA}
. run/lib_check.sh
pins() { # the absolute pins, read from the tree in use
	cat gen/pins_*.txt | sed -e "s#^/Users/jtorra/src/scratch/resgx545/closing4/lead/wt/#$CANON_MAIN/#" | sort -u |
		sed -e "s#^$CANON_MAIN/#$MAIN/#" -e "s#^$CANON_DATA/#$DATA/#"
}
files() {
	ls gen/*.py score/*.py run/*.sh run/r4.env stages.txt TABLES.md TOOL.sha256 gen/pins_*.txt
	ls tables/*.txt predictions/*.tsv bins/*.bin bins/*.tsv templates/*.s
	pins
}
canon() { sed -e "s#$MAIN/#$CANON_MAIN/#" -e "s#$DATA/#$CANON_DATA/#"; }
uncanon() { sed -e "s#$CANON_MAIN/#$MAIN/#" -e "s#$CANON_DATA/#$DATA/#"; }
case "$MODE" in
freeze)
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/r4.env || { echo "run/r4.env does not name the pinned tool ($pin)"; exit 1; }
	cmp -s score/scorekit.py "$MAIN/tools/closing/scorekit.py" || { echo "score/scorekit.py is not tools/closing/scorekit.py byte for byte"; exit 1; }
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 | canon > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_r4.sh freeze"; exit 1; }
	uncanon < FROZEN.sha256 > .frozen.now
	shasum -a 256 -c .frozen.now --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> .verify.out 2>&1; b=$?
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' .frozen.now -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_r4.sh [freeze|verify]"; exit 2 ;;
esac
