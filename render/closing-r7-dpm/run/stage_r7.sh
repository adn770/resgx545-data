#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r7.sh [--tables-only | --local DIR]: copy the runner, the reader, the landed fwtask_run.py, tables, FROZEN.sha256 and the staged programs
# (p1139-green.bin, oomring2.blob) to ~/scratch/r7d/run and ~/scratch/r7d/stage on the laptop (round 6's rule: every laptop file under
# ~/scratch/<prefix>/, work directories under ~/scratch/tmp).  NOTHING IS BUILT: the tool is round 4's ~/sgxfive-test-rgn4 and
# ~/regtimeline is S1's (both pinned in run/r7.env); the staging checks both hashes, python3 and the free space of ~ on the laptop and
# refuses a mismatch (STOP AND ASK).  NOT RUN while R7-dpm was prepared.  Every ssh/scp is bounded by a perl alarm (SSH_ALARM, 150 s).
# SGX_DRY_RUN=1 prints the commands.  R6-dpm's stage_r6.sh (freeze 2: ONE file list, RUNNER, used by both modes; --local DIR copies
# exactly that list into DIR/scratch/r7d/... for tests/run_mock.sh, which runs the runner from there under env -i) with round 7's
# files: the landed sessioncheck.py and scorekit.py (the premise check), both sets' freezes, oomring2.blob (set B).  Staged once, for
# both sets; set B's runner refuses to start unless the module 37EC97AB is loaded.  tests/run_all.sh checks the list with
# sessioncheck.py staged.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R7=$(dirname "$HERE")
TABLES_ONLY=0
LOCAL=""
case "${1:-}" in "") ;; --tables-only) TABLES_ONLY=1 ;; --local) LOCAL=${2:?--local DIR} ;; *) echo "usage: stage_r7.sh [--tables-only | --local DIR]"; exit 2 ;; esac
# the runner tree the laptop gets: every file run_stage.sh reads or sources (tests/test_staged.sh checks the list is complete)
RUNNER="lib_r7.sh lib_check.sh run_stage.sh r7read.py r7.env fwtask_run.py sessioncheck.py scorekit.py"
PROGS="p1139-green.bin oomring2.blob"
FREEZES="FROZEN.sha256 FROZEN-B.sha256"
if [ -n "$LOCAL" ]; then
	L=$LOCAL/scratch/r7d
	mkdir -p "$L/run/run" "$L/run/tables" "$L/stage" "$L/out" "$LOCAL/scratch/tmp" || exit 1
	for f in $RUNNER; do cp "$R7/run/$f" "$L/run/run/" || exit 1; done
	cp "$R7"/tables/*.txt "$L/run/tables/" || exit 1
	for f in $FREEZES; do cp "$R7/$f" "$L/run/" || exit 1; done
	for f in $PROGS; do cp "$R7/bins/$f" "$L/stage/" || exit 1; done
	echo "staged locally in $L"
	exit 0
fi
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
. "$HERE/r7.env"
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
run() {
	if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; return 0; fi
	bounded "${SSH_ALARM:-150}" "$@"
	st=$?
	[ $st -eq 0 ] || { echo "STAGING FAILED (status $st) at: $*"; exit 1; }
}
"$R7/run/guard_r7.sh"; g=$?
[ $g -eq 0 ] || { echo "guard failed"; exit 1; }
"$R7/run/freeze_r7.sh" verify AB; v=$?
[ $v -eq 0 ] || { echo "frozen files do not verify"; exit 1; }
# shellcheck disable=SC2086
run ssh -o BatchMode=yes -o ConnectTimeout=10 $OPTS "$T" 'mkdir -p scratch/r7d/run/run scratch/r7d/run/tables scratch/r7d/stage scratch/r7d/out scratch/tmp'
# shellcheck disable=SC2086
run scp -q $OPTS $(for f in $RUNNER; do printf '%s ' "$R7/run/$f"; done) "$T:scratch/r7d/run/run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R7"/tables/*.txt "$T:scratch/r7d/run/tables/"
# shellcheck disable=SC2086
run scp -q $OPTS $(for f in $FREEZES; do printf '%s ' "$R7/$f"; done) "$T:scratch/r7d/run/"
# shellcheck disable=SC2086
run scp -q $OPTS $(for f in $PROGS; do printf '%s ' "$R7/bins/$f"; done) "$T:scratch/r7d/stage/"
[ "$TABLES_ONLY" = 1 ] && exit 0
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "ssh $T sha256sum ~/sgxfive-test-rgn4 ~/regtimeline ~/scratch/r7d/stage/oomring2.blob; python3 -V; df -Pk ~/scratch   (tool $TOOL_SHA, regtimeline $RT_SHA)"
	exit 0
fi
# shellcheck disable=SC2086
got=$(bounded "${SSH_ALARM:-150}" ssh -o BatchMode=yes $OPTS "$T" 'sha256sum ~/sgxfive-test-rgn4 ~/regtimeline ~/scratch/r7d/stage/oomring2.blob; python3 -V; df -Pk ~/scratch | awk "NR==2 {print \"free \" \$4}"' 2>&1)
st=$?
echo "$got"
[ $st -eq 0 ] || { echo "STAGING FAILED: cannot read the hashes (status $st)"; exit 1; }
echo "$got" | grep -q "^$TOOL_SHA " || { echo "STAGING REFUSED: ~/sgxfive-test-rgn4 is not the pinned rgn4 tool ($TOOL_SHA): STOP AND ASK"; exit 1; }
echo "$got" | grep -q "^$RT_SHA " || { echo "STAGING REFUSED: ~/regtimeline is not the pinned one ($RT_SHA): STOP AND ASK"; exit 1; }
echo "$got" | grep -q "^$OOMRING2_SHA " || { echo "STAGING REFUSED: oomring2.blob did not arrive intact"; exit 1; }
echo "$got" | grep -qE "^Python 3\.(1[0-9]|[2-9][0-9])" || { echo "STAGING REFUSED: no python3 >= 3.10 on the laptop (the reader, fwtask_run.py and the landed scorekit.py need it)"; exit 1; }
fr=$(echo "$got" | awk '/^free / {print $2}')
[ "${fr:-0}" -ge 600000 ] || { echo "STAGING REFUSED: ${fr:-?} KB free on ~/scratch (600 MB needed)"; exit 1; }
echo "staged: the rgn4 tool $TOOL_SHA (nothing built), runner, reader, tables and programs in ~/scratch/r7d/run and ~/scratch/r7d/stage"
