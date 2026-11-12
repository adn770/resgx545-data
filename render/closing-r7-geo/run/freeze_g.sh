#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_g.sh freeze | verify
#   freeze   write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a score:
#            generators, models and the byte copies they import, scorers (scorekit.py and sessioncheck.py byte copies of resgx545
#            main 1c64f3a's tools/closing), runner scripts, env, tables, predictions, the probe programs and their SHA256SUMS, the
#            templates, the controls list, TABLES.md, stages.txt, TOOL.sha256, TOOLSRC.sha256, TOOL6.sha256, TOOL6SRC.sha256, the
#            staged t6 binary, and by absolute path the resgx545 files the session uses and every file the generator read from
#            outside this directory (gen/data/sources.lst)).  Run after gen/g7gen.py and BEFORE the first job.
#   verify   check FROZEN.sha256 and PREDICTIONS.sha256, and that no file was added since.
# Writes only the .sha256 files (and .verify.out scratch).
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
files() {
	ls gen/*.py gen/data/* score/*.py run/*.sh run/g.env stages.txt TABLES.md TOOL.sha256 TOOLSRC.sha256 TOOL6.sha256 TOOL6SRC.sha256
	ls tables/*.txt predictions/*.tsv bins/* templates/* bin/t6/sgxfive-test
	ls "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/closing/sessioncheck.py" "$MAIN/tools/bringup/health.sh"
	cat gen/data/sources.lst
}
verify_files() {
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_g.sh freeze"; return 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> .verify.out 2>&1; b=$?
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; return 1
	fi
	return 0
}
case "$MODE" in
freeze)
	pin=$(cut -d' ' -f1 TOOL.sha256); pin6=$(cut -d' ' -f1 TOOL6.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/g.env || { echo "run/g.env does not name the pinned rgn4 tool ($pin)"; exit 1; }
	grep -q "^TOOL6_SHA=$pin6\$" run/g.env || { echo "run/g.env does not name the pinned t6 ($pin6)"; exit 1; }
	[ "$(shasum -a 256 bin/t6/sgxfive-test | cut -d' ' -f1)" = "$pin6" ] || { echo "bin/t6/sgxfive-test is not TOOL6.sha256's"; exit 1; }
	for f in scorekit.py sessioncheck.py; do
		cmp -s "score/$f" "$MAIN/tools/closing/$f" || { echo "score/$f is not main's tools/closing/$f byte for byte"; exit 1; }
	done
	(cd bins && shasum -a 256 -c SHA256SUMS --quiet) || { echo "bins/SHA256SUMS does not hold the programs"; exit 1; }
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	verify_files || exit 1
	echo "files verified" ;;
*) echo "usage: freeze_g.sh freeze | verify"; exit 2 ;;
esac
