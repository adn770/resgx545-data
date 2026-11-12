#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_k.sh [freeze | verify] [SET]   (SET: A, the default, or a later set with its sets/SET.env)
#   freeze   write the set's predictions hash file (SET_PREDS: every predictions file of the set) and its freeze file (SET_FREEZE: every
#            file the set's set_files names: generators and the values they extracted, scorers (scorekit.py a byte-for-byte copy of
#            resgx545 main's), runner scripts, env, the set file, tables, predictions, the staged programs, TABLES.md, TOOL.sha256 and
#            TOOLSRC.sha256, and by absolute path: the resgx545 files the session uses (tools/closing/scorekit.py, the source of the copy;
#            tools/bringup/health.sh, run by k.sh) and every file the generator read from outside this directory (gen/data/sources.lst:
#            the resgx545-data records the controls and predictions come from, the assembler, the program sources)).  Run it after
#            gen/rgen.py and BEFORE the first job; k.sh and the scorer verify it.  Then gen/frozen_commits.py writes FROZEN.commits.
#            A set's freeze is written once: `freeze` refuses to replace an existing freeze file (a refreeze before the first job:
#            remove the set's two hash files by hand first).
#   verify   check the set's two hash files, and that every file set_files names is in the freeze (a new file of the set is a change)
# Stage A is FROZEN.sha256 + PREDICTIONS.sha256 (the names round 5's tools read).  A later set (B) writes FROZEN-B.sha256 +
# PREDICTIONS-B.sha256 over ITS files; A's files are never rewritten, and A's verify never reads B's files (set_files lists names).
# Writes only the set's two .sha256 files (and .verify.out scratch).
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
SET=${2:-A}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
[ -f "sets/$SET.env" ] || { echo "no sets/$SET.env"; exit 2; }
. "sets/$SET.env"
files() {
	set_files | tr ' ' '\n' | grep -v '^$'
	ls "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/bringup/health.sh"
	cat gen/data/sources.lst
}
case "$MODE" in
freeze)
	[ -f "$SET_FREEZE" ] && { echo "$SET_FREEZE exists: a set's freeze is never rewritten"; exit 1; }
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" "$SET_RUNDIR/k.env" || { echo "$SET_RUNDIR/k.env does not name the pinned tool ($pin)"; exit 1; }
	cmp -s score/scorekit.py "$MAIN/tools/closing/scorekit.py" || { echo "score/scorekit.py is not main's tools/closing/scorekit.py byte for byte"; exit 1; }
	# shellcheck disable=SC2086
	shasum -a 256 $SET_PREDFILES > "$SET_PREDS" || exit 1
	files | xargs shasum -a 256 > "$SET_FREEZE" || exit 1
	echo "frozen set $SET: $(wc -l < "$SET_FREEZE" | tr -d ' ') files, $(wc -l < "$SET_PREDS" | tr -d ' ') predictions" ;;
verify)
	[ -f "$SET_FREEZE" ] && [ -f "$SET_PREDS" ] || { echo "set $SET not frozen: run run/freeze_k.sh freeze $SET"; exit 1; }
	shasum -a 256 -c "$SET_FREEZE" --quiet > .verify.out 2>&1; a=$?
	shasum -a 256 -c "$SET_PREDS" --quiet >> .verify.out 2>&1; b=$?
	extra=$(files | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' "$SET_FREEZE" -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 .verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified (set $SET)" ;;
*) echo "usage: freeze_k.sh [freeze|verify] [SET]"; exit 2 ;;
esac
