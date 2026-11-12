#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_r7.sh freeze | tool7 SHA | verify SHA
#   freeze       write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a
#                score: generators, models and the byte copies they import, scorers (scorekit.py and sessioncheck.py byte copies of
#                resgx545 main's tools/closing/), runner scripts, env, tables, predictions, staged programs (bins/), templates,
#                TABLES.md, stages.txt, TOOL.sha256, TOOL6.sha256, TOOLSRC.sha256, TOOL6SRC.sha256, TOOL7SRC.sha256,
#                lead/build_tool7.sh, and by absolute path the resgx545 files the session uses and every file a generator read from
#                outside this directory (gen/data/sources-*.lst)).  Run after gen/r7gen.py and BEFORE the first job.
#                TOOL7.sha256 is NOT in FROZEN.sha256: it is the slot of the t7 build's sha256, which only exists once the lead has
#                built the tool on cachix (lead/build_tool7.sh).
#   tool7 SHA    write TOOL7.sha256 (the t7 build's sha256 and its laptop path) once: refused if it already holds another hash, and
#                if the frozen files do not verify.  The predictions do not depend on it (no row's prediction names a tool hash).
#   verify SHA   check FROZEN.sha256 and PREDICTIONS.sha256, that no file was added since, and that TOOL7.sha256 holds SHA (the
#                lead's t7 hash, given on every verify: r7.sh, stage_r7.sh and the scorers pass it).  No SHA, or the slot: refused.
# Writes only the .sha256 files (and .verify.out scratch).
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
SLOT=SLOT-the-lead-writes-the-t7-sha256-here-with-run/freeze_r7.sh-tool7
files() {
	ls gen/*.py gen/data/* score/*.py run/*.sh run/r7.env lead/*.sh stages.txt TABLES.md TOOL.sha256 TOOL6.sha256 TOOLSRC.sha256 \
		TOOL6SRC.sha256 TOOL7SRC.sha256
	ls tables/*.txt predictions/*.tsv bins/* templates/*
	ls "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/closing/sessioncheck.py" "$MAIN/tools/bringup/health.sh"
	cat gen/data/sources-*.lst | sort -u
}
is_sha() { [ ${#1} -eq 64 ] && case "$1" in *[!0-9a-f]*) return 1 ;; *) return 0 ;; esac; }
verify_files() {
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_r7.sh freeze"; return 1; }
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
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/r7.env || { echo "run/r7.env does not name the pinned rgn4 tool ($pin)"; exit 1; }
	pin6=$(cut -d' ' -f1 TOOL6.sha256)
	grep -q "^TOOL6_SHA=$pin6\$" run/r7.env || { echo "run/r7.env does not name round 6's t6 ($pin6)"; exit 1; }
	for f in scorekit.py sessioncheck.py; do
		cmp -s "score/$f" "$MAIN/tools/closing/$f" || { echo "score/$f is not main's tools/closing/$f byte for byte"; exit 1; }
	done
	[ -f TOOL7.sha256 ] || printf '%s  /home/jtorra/scratch/r7r/bin/sgxfive-test-t7\n' "$SLOT" > TOOL7.sha256
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions; TOOL7.sha256: $(cut -d' ' -f1 TOOL7.sha256)" ;;
tool7)
	s=${2:-}
	is_sha "$s" || { echo "usage: freeze_r7.sh tool7 SHA256 (64 hex digits, the t7 build's: lead/build_tool7.sh prints it)"; exit 2; }
	verify_files || exit 1
	cur=$(cut -d' ' -f1 TOOL7.sha256 2>/dev/null)
	if is_sha "$cur" && [ "$cur" != "$s" ]; then echo "TOOL7.sha256 already holds $cur: not replaced (a new build is a new freeze; the lead decides)"; exit 1; fi
	printf '%s  /home/jtorra/scratch/r7r/bin/sgxfive-test-t7\n' "$s" > TOOL7.sha256
	echo "TOOL7.sha256: $s" ;;
verify)
	s=${2:-}
	is_sha "$s" || { echo "verify needs the t7 sha256 (TOOL7.sha256 holds $(cut -d' ' -f1 TOOL7.sha256 2>/dev/null)): run/freeze_r7.sh verify SHA256"; exit 1; }
	verify_files || exit 1
	[ "$(cut -d' ' -f1 TOOL7.sha256 2>/dev/null)" = "$s" ] || { echo "TOOL7.sha256 does not hold $s (the slot is filled by run/freeze_r7.sh tool7 SHA)"; exit 1; }
	echo "files verified; t7 $s" ;;
*) echo "usage: freeze_r7.sh freeze | tool7 SHA | verify SHA"; exit 2 ;;
esac
