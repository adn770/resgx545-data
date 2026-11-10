#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_s3.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a
#            case, a run or a score: scorers, runner scripts, env, tables, predictions, staged programs).
#            Run it after the last change and BEFORE the first job; s3.sh and the scorer verify it.
#   verify   check both
# Writes only the two .sha256 files.  The freeze is attested by file times and these hashes only.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
files() {
	ls score/*.py run/*.sh run/s3.env stages.txt tables/*.txt predictions/*.tsv bins/*
}
case "$MODE" in
freeze)
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_s3.sh freeze"; exit 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> .verify.out 2>&1; b=$?
	# a file added since the freeze is a change too
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		cat .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_s3.sh [freeze|verify]"; exit 2 ;;
esac
