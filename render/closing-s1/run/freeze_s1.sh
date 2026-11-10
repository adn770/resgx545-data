#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_s1.sh [freeze | verify [STAGE] | e2b]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a
#            case, a run or a score: generators, scorers, runner scripts, tables, predictions, staged programs)
#            Run it after gen/s1gen.py and BEFORE the first job; the run script verifies it before each stage.
#   verify   check them (and, for the stage g-e2b, FROZEN-e2b.sha256)
#   e2b      after gen/gen_e2_boundary.py: freeze tables/g-e2b.txt, predictions/g-e2b.tsv and the U json it came from
# Writes only the .sha256 files in this directory.  The freeze is attested by file times and these hashes only
# (no external stamp), as in the earlier batches.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
files() {
	ls gen/*.py score/*.py run/*.sh stages.txt TABLES.md 2>/dev/null
	ls tables/*.txt 2>/dev/null | grep -v 'g-e2b.txt'
	ls predictions/* 2>/dev/null | grep -v 'g-e2b'
	ls bins/* 2>/dev/null
	# what the scorers and generators import from the landed tree (read-only): frozen by sha256 too
	ls "$HOME/src/resgx545/tools/usse-asm/pbdump.py" "$HOME/src/resgx545/tools/usse-asm/probe.py"
}
case "$MODE" in
freeze)
	shasum -a 256 predictions/*.tsv predictions/*.bits > PREDICTIONS.sha256
	files | grep -v '^gen/__pycache__' | xargs shasum -a 256 > FROZEN.sha256
	wc -l < FROZEN.sha256; cat PREDICTIONS.sha256 | wc -l ;;
e2b)
	[ -f tables/g-e2b.txt ] && [ -f predictions/g-e2b.tsv ] || { echo "run gen/gen_e2_boundary.py first"; exit 1; }
	shasum -a 256 tables/g-e2b.txt predictions/g-e2b.tsv out/g-e2b.generated-from.json > FROZEN-e2b.sha256
	cat FROZEN-e2b.sha256 ;;
verify)
	st=${2:-}
	shasum -a 256 -c FROZEN.sha256 --quiet 2>&1 | head -3
	[ "${PIPESTATUS[0]}" = 0 ] || { echo "FROZEN FILES CHANGED"; exit 1; }
	shasum -a 256 -c PREDICTIONS.sha256 --quiet 2>&1 | head -3
	[ "${PIPESTATUS[0]}" = 0 ] || { echo "PREDICTIONS CHANGED"; exit 1; }
	if [ "$st" = g-e2b ]; then
		[ -f FROZEN-e2b.sha256 ] || { echo "g-e2b is not frozen: run run/freeze_s1.sh e2b"; exit 1; }
		shasum -a 256 -c FROZEN-e2b.sha256 --quiet 2>&1 | head -3
		[ "${PIPESTATUS[0]}" = 0 ] || { echo "g-e2b FILES CHANGED"; exit 1; }
	fi
	echo "files verified" ;;
*) echo "usage: freeze_s1.sh [freeze|verify [STAGE]|e2b]"; exit 2 ;;
esac
