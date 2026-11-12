#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_m.sh freeze | tool6 SHA | verify SHA
#   freeze       write PREDICTIONS.sha256 (every predictions file) and FROZEN.sha256 (every file that defines a case, a run or a
#                score: generators, models and the byte copies they import, scorers (scorekit.py a byte copy of resgx545 main's),
#                runner scripts, env, tables, predictions, TABLES.md, stages.txt, TOOL.sha256, TOOLSRC.sha256, TOOL6SRC.sha256,
#                lead/build_tool6.sh, and by absolute path the resgx545 files the session uses and every file the generator read
#                from outside this directory (gen/data/sources.lst)).  Run after gen/m6gen.py and BEFORE the first job.
#                TOOL6.sha256 is NOT in FROZEN.sha256: it is the slot of the t6 build's sha256, which only exists once the lead has
#                built the tool on cachix (lead/build_tool6.sh).
#   tool6 SHA    write TOOL6.sha256 (the t6 build's sha256 and its laptop path) once: refused if it already holds another hash,
#                and if the frozen files do not verify.  The predictions do not depend on it (no row's prediction names a tool hash).
#   verify SHA   check FROZEN.sha256 and PREDICTIONS.sha256, that no file was added since, and that TOOL6.sha256 holds SHA (the
#                lead's t6 hash, given on every verify: m.sh, stage_m.sh and the scorers pass it).  No SHA, or the slot: refused.
# Writes only the .sha256 files (and .verify.out scratch).
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
SLOT=SLOT-the-lead-writes-the-t6-sha256-here-with-run/freeze_m.sh-tool6
files() {
	ls gen/*.py gen/data/* score/*.py run/*.sh run/m.env lead/*.sh stages.txt TABLES.md TOOL.sha256 TOOLSRC.sha256 TOOL6SRC.sha256
	ls tables/*.txt predictions/*.tsv
	ls "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/bringup/health.sh"
	cat gen/data/sources.lst
}
is_sha() { [ ${#1} -eq 64 ] && case "$1" in *[!0-9a-f]*) return 1 ;; *) return 0 ;; esac; }
verify_files() {
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_m.sh freeze"; return 1; }
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
	grep -q "^TOOL_SHA=$pin\$" run/m.env || { echo "run/m.env does not name the pinned rgn4 tool ($pin)"; exit 1; }
	cmp -s score/scorekit.py "$MAIN/tools/closing/scorekit.py" || { echo "score/scorekit.py is not main's tools/closing/scorekit.py byte for byte"; exit 1; }
	[ -f TOOL6.sha256 ] || printf '%s  /home/jtorra/scratch/r6m/bin/sgxfive-test\n' "$SLOT" > TOOL6.sha256
	shasum -a 256 predictions/*.tsv > PREDICTIONS.sha256 || exit 1
	files | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions; TOOL6.sha256: $(cut -d' ' -f1 TOOL6.sha256)" ;;
tool6)
	s=${2:-}
	is_sha "$s" || { echo "usage: freeze_m.sh tool6 SHA256 (64 hex digits, the t6 build's: lead/build_tool6.sh prints it)"; exit 2; }
	verify_files || exit 1
	cur=$(cut -d' ' -f1 TOOL6.sha256 2>/dev/null)
	if is_sha "$cur" && [ "$cur" != "$s" ]; then echo "TOOL6.sha256 already holds $cur: not replaced (a new build is a new freeze; the lead decides)"; exit 1; fi
	printf '%s  /home/jtorra/scratch/r6m/bin/sgxfive-test\n' "$s" > TOOL6.sha256
	echo "TOOL6.sha256: $s" ;;
verify)
	s=${2:-}
	is_sha "$s" || { echo "verify needs the t6 sha256 (TOOL6.sha256 holds $(cut -d' ' -f1 TOOL6.sha256 2>/dev/null)): run/freeze_m.sh verify SHA256"; exit 1; }
	verify_files || exit 1
	[ "$(cut -d' ' -f1 TOOL6.sha256 2>/dev/null)" = "$s" ] || { echo "TOOL6.sha256 does not hold $s (the slot is filled by run/freeze_m.sh tool6 SHA)"; exit 1; }
	echo "files verified; t6 $s" ;;
*) echo "usage: freeze_m.sh freeze | tool6 SHA | verify SHA"; exit 2 ;;
esac
