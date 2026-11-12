#!/bin/bash
# SPDX-License-Identifier: MIT
# freeze_f.sh [freeze | verify]: r7-faults' freeze.
#   freeze   write PREDICTIONS.sha256 (predictions/*.tsv) and FROZEN.sha256 (every file `files` lists: the generators, the scorer
#            (score/scorekit.py and score/sessioncheck.py byte for byte resgx545 main's), the runner, the driver, the tables, the five
#            programs and their listing, the predictions, TABLES.md, stages.txt, TOOL.sha256, TOOLSRC.sha256, the tests, and by
#            absolute path resgx545's tools/closing/scorekit.py, tools/closing/sessioncheck.py, tools/bringup/health.sh,
#            probes/usse/templates/counter.s, the usse-asm binary the programs were assembled with, and the kept records the
#            generator and the replays read (gen/data/sources.lst)).  Run after gen/fgen.py and gen/asm_l.py and BEFORE the first job;
#            then gen/frozen_commits.py writes FROZEN.commits.  Never rewrites a freeze.
#   verify   check both hash files, and that every file `files` names is in the freeze (a new file is a change)
cd "$(dirname "$0")/.." || exit 1
MODE=${1:-freeze}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
files() {
	echo gen/fgen.py gen/asm_l.py gen/frozen_commits.py gen/data/sources.lst score/score_f.py score/scorekit.py score/sessioncheck.py
	echo run/lib_f.sh run/run_f.sh run/f.env run/f.sh run/stage_f.sh run/freeze_f.sh run/guard_f.sh run/lib_check.sh
	echo tables/s0.txt tables/l.txt tables/d.txt tables/m.txt predictions/s0.tsv predictions/l.tsv predictions/d.tsv predictions/m.tsv
	echo bins/l0-lock-release.bin bins/l1-lock0-lock1.bin bins/l2-lock-lock-rel-rel.bin bins/l3-lock-lock-rel.bin bins/l4-lock-norel.bin bins/LISTING.txt
	echo TABLES.md stages.txt TOOL.sha256 TOOLSRC.sha256
	echo tests/run_all.sh tests/run_mock.sh tests/worlds.py tests/fake_tool.sh tests/test_gen.py tests/test_twin.py tests/test_replay.py
	echo tests/test_static.py tests/shims/sudo tests/shims/ssh tests/shims/scp tests/shims/df tests/shims/modinfo tests/shims/sha256sum tests/shims/timeout
	echo "$MAIN/tools/closing/scorekit.py" "$MAIN/tools/closing/sessioncheck.py" "$MAIN/tools/bringup/health.sh"
	echo "$MAIN/probes/usse/templates/counter.s" "$MAIN/tools/usse-asm/usse-asm"
	cat gen/data/sources.lst
}
case "$MODE" in
freeze)
	[ -f FROZEN.sha256 ] && { echo "FROZEN.sha256 exists: a freeze is never rewritten"; exit 1; }
	pin=$(cut -d' ' -f1 TOOL.sha256)
	grep -q "^TOOL_SHA=$pin\$" run/f.env || { echo "run/f.env does not name the pinned tool ($pin)"; exit 1; }
	cmp -s score/scorekit.py "$MAIN/tools/closing/scorekit.py" || { echo "score/scorekit.py is not main's byte for byte"; exit 1; }
	cmp -s score/sessioncheck.py "$MAIN/tools/closing/sessioncheck.py" || { echo "score/sessioncheck.py is not main's byte for byte"; exit 1; }
	shasum -a 256 predictions/s0.tsv predictions/l.tsv predictions/d.tsv predictions/m.tsv > PREDICTIONS.sha256 || exit 1
	files | tr ' ' '\n' | grep -v '^$' | xargs shasum -a 256 > FROZEN.sha256 || exit 1
	echo "frozen: $(wc -l < FROZEN.sha256 | tr -d ' ') files, $(wc -l < PREDICTIONS.sha256 | tr -d ' ') predictions" ;;
verify)
	mkdir -p debug
	[ -f FROZEN.sha256 ] && [ -f PREDICTIONS.sha256 ] || { echo "not frozen: run run/freeze_f.sh freeze"; exit 1; }
	shasum -a 256 -c FROZEN.sha256 --quiet > debug/.verify.out 2>&1; a=$?
	shasum -a 256 -c PREDICTIONS.sha256 --quiet >> debug/.verify.out 2>&1; b=$?
	extra=$(files | tr ' ' '\n' | grep -v '^$' | awk 'NR == FNR { f[$2] = 1; next } !($0 in f)' FROZEN.sha256 -)
	if [ "$a" != 0 ] || [ "$b" != 0 ] || [ -n "$extra" ]; then
		head -5 debug/.verify.out; [ -n "$extra" ] && echo "not frozen: $extra"
		echo "FROZEN FILES CHANGED"; exit 1
	fi
	echo "files verified" ;;
*) echo "usage: freeze_f.sh [freeze|verify]"; exit 2 ;;
esac
