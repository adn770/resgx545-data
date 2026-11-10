#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r2.sh [freeze | verify]
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or
#            a score: generators, scorers, runner scripts, env, tables, predictions, staged programs, templates, the
#            data the generators read, and the landed files the generators import read-only).  Run it after
#            gen/r2gen.py and BEFORE the first job; r2.sh and the scorer verify it.
#   verify   check both, and that no file was added since (a new table or program is a change too)
# Writes only the two .sha256 files.  The freeze is attested by file times and these hashes only.
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
files() {
	ls gen/*.py gen/data/* score/*.py run/*.sh run/r2.env stages.txt conditional.txt TABLES.md
	ls tables/*.txt predictions/*.tsv bins/*.bin templates/*.s
	# read-only imports of the generators: frozen by sha256 too (the tool's source is the one R1 built, TOOL.sha256)
	ls "$MAIN/tools/usse-asm/probe.py" "$MAIN/probes/texture/templates/tx_map.s" \
		"$MAIN/userspace/libsgxfive/tools/sgxfive-test.c" "$HOME/src/resgx545-data/texture/p1141/probes/p1141-addr.toml"
}
case "$MODE" in
freeze)
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_r2.sh freeze"; exit 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> .verify.out 2>&1; b=$?
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_r2.sh [freeze|verify]"; exit 2 ;;
esac
