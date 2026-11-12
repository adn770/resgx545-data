#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_h.sh [freeze | verify]: part H's freeze.
#   freeze   write PREDICTIONS.sha256 (predictions/*.tsv) and FROZEN.sha256 (every file `files` lists: generator, scorer (scorekit.py
#            byte for byte resgx545 main's), runner, driver, tables, predictions, TABLES.md, stages.txt, TOOL.sha256, TOOLSRC.sha256, the
#            tests, the O3 oracle files of private/o3 (by hash: data-private), and by absolute path resgx545's tools/closing/scorekit.py
#            and tools/bringup/health.sh and the E848 records the generator and the replays read (gen/data/sources.lst)).  Run after
#            gen/hgen.py and BEFORE the first job; then gen/frozen_commits.py writes FROZEN.commits.  Never rewrites a freeze.
#   verify   check both hash files, and that every file `files` names is in the freeze (a new file is a change)
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
files() {
	echo gen/hgen.py gen/frozen_commits.py gen/data/sources.lst score/score_h.py score/scorekit.py
	echo run/lib_h.sh run/run_h.sh run/h.env run/h.sh run/stage_h.sh run/freeze_h.sh run/guard_h.sh run/lib_check.sh
	echo tables/s0.txt tables/q.txt predictions/s0.tsv predictions/q.tsv TABLES.md stages.txt TOOL.sha256 TOOLSRC.sha256
	echo tests/run_all.sh tests/run_mock.sh tests/worlds.py tests/fake_tool.sh tests/test_gen.py tests/test_twin.py tests/test_replay.py
	echo tests/test_static.py tests/shims/sudo tests/shims/ssh tests/shims/scp tests/shims/df tests/shims/modinfo tests/shims/sha256sum tests/shims/timeout
	echo private/o3/PREDICTIONS.md private/o3/o3_oracle.py private/o3/o3_oracle.json private/o3/RESULT.md
	echo "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/bringup/health.sh"
	cat gen/data/sources.lst
}
case "$MODE" in
freeze)
	[ -f FROZEN.sha256 ] && { echo "FROZEN.sha256 exists: a freeze is never rewritten"; exit 1; }
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/h.env || { echo "run/h.env does not name the pinned tool ($pin)"; exit 1; }
	cmp -s score/scorekit.py "$MAIN/tools/closing/scorekit.py" || { echo "score/scorekit.py is not main's byte for byte"; exit 1; }
	shasum -a 256 predictions/s0.tsv predictions/q.tsv > PREDICTIONS.sha256 || exit 1
	files | tr ' ' '\n' | grep -v '^$' | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	mkdir -p debug
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_h.sh freeze"; exit 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > debug/.verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> debug/.verify.out 2>&1; b=$?
	extra=$(files | tr ' ' '\n' | grep -v '^$' | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 debug/.verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_h.sh [freeze|verify]"; exit 2 ;;
esac
