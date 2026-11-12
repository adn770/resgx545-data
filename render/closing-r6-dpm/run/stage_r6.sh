#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r6.sh [--tables-only | --local DIR]: copy the runner, the reader, the landed fwtask_run.py, tables, FROZEN.sha256 and the staged programs
# (p1139-green.bin, oomring.blob) to ~/scratch/r6d/run and ~/scratch/r6d/stage on the laptop (round 6's rule: every laptop file under
# ~/scratch/<prefix>/, work directories under ~/scratch/tmp).  NOTHING IS BUILT: the tool is round 4's ~/sgxfive-test-rgn4 and
# ~/regtimeline is S1's (both pinned in run/r6.env); the staging checks both hashes, python3 and the free space of ~ on the laptop and
# refuses a mismatch (STOP AND ASK).  NOT RUN while R6-dpm was prepared.  Every ssh/scp is bounded by a perl alarm (SSH_ALARM, 150 s).
# SGX_DRY_RUN=1 prints the commands.  R5-dpm's stage_r5.sh with the new directories.
# Freeze 2 (after attempt a1): the files staged are ONE list (RUNNER, below) used by both modes; --local DIR copies exactly that list
# into DIR/scratch/r6d/... (the laptop layout, nothing else) for tests/run_mock.sh, which runs the runner from there.  Attempt a1's
# tree lacked run/lib_check.sh (num_eq), because this script's scp line did not name it while the mock ran the source tree.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R6=$(dirname "$HERE")
TABLES_ONLY=0
LOCAL=""
case "${1:-}" in "") ;; --tables-only) TABLES_ONLY=1 ;; --local) LOCAL=${2:?--local DIR} ;; *) echo "usage: stage_r6.sh [--tables-only | --local DIR]"; exit 2 ;; esac
# the runner tree the laptop gets: every file run_stage.sh reads or sources (tests/test_staged.sh checks the list is complete)
RUNNER="lib_r6.sh lib_check.sh run_stage.sh r6read.py r6.env fwtask_run.py"
PROGS="p1139-green.bin oomring.blob"
if [ -n "$LOCAL" ]; then
	L=$LOCAL/scratch/r6d
	mkdir -p "$L/run/run" "$L/run/tables" "$L/stage" "$L/out" "$LOCAL/scratch/tmp" || exit 1
	for f in $RUNNER; do cp "$R6/run/$f" "$L/run/run/" || exit 1; done
	cp "$R6"/tables/*.txt "$L/run/tables/" && cp "$R6/FROZEN.sha256" "$L/run/" || exit 1
	for f in $PROGS; do cp "$R6/bins/$f" "$L/stage/" || exit 1; done
	echo "staged locally in $L"
	exit 0
fi
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
. "$HERE/r6.env"
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
run() {
	if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; return 0; fi
	bounded "${SSH_ALARM:-150}" "$@"
	st=$?
	[ $st -eq 0 ] || { echo "STAGING FAILED (status $st) at: $*"; exit 1; }
}
"$R6/run/guard_r6.sh"; g=$?
[ $g -eq 0 ] || { echo "guard failed"; exit 1; }
"$R6/run/freeze_r6.sh" verify; v=$?
[ $v -eq 0 ] || { echo "frozen files do not verify"; exit 1; }
# shellcheck disable=SC2086
run ssh -o BatchMode=yes -o ConnectTimeout=10 $OPTS "$T" 'mkdir -p scratch/r6d/run/run scratch/r6d/run/tables scratch/r6d/stage scratch/r6d/out scratch/tmp'
# shellcheck disable=SC2086
run scp -q $OPTS $(for f in $RUNNER; do printf '%s ' "$R6/run/$f"; done) "$T:scratch/r6d/run/run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R6"/tables/*.txt "$T:scratch/r6d/run/tables/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R6"/FROZEN.sha256 "$T:scratch/r6d/run/"
# shellcheck disable=SC2086
run scp -q $OPTS $(for f in $PROGS; do printf '%s ' "$R6/bins/$f"; done) "$T:scratch/r6d/stage/"
[ "$TABLES_ONLY" = 1 ] && exit 0
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "ssh $T sha256sum ~/sgxfive-test-rgn4 ~/regtimeline ~/scratch/r6d/stage/oomring.blob; python3 -V; df -Pk ~/scratch   (tool $TOOL_SHA, regtimeline $RT_SHA)"
	exit 0
fi
# shellcheck disable=SC2086
got=$(bounded "${SSH_ALARM:-150}" ssh -o BatchMode=yes $OPTS "$T" 'sha256sum ~/sgxfive-test-rgn4 ~/regtimeline ~/scratch/r6d/stage/oomring.blob; python3 -V; df -Pk ~/scratch | awk "NR==2 {print \"free \" \$4}"' 2>&1)
st=$?
echo "$got"
[ $st -eq 0 ] || { echo "STAGING FAILED: cannot read the hashes (status $st)"; exit 1; }
echo "$got" | grep -q "^$TOOL_SHA " || { echo "STAGING REFUSED: ~/sgxfive-test-rgn4 is not the pinned rgn4 tool ($TOOL_SHA): STOP AND ASK"; exit 1; }
echo "$got" | grep -q "^$RT_SHA " || { echo "STAGING REFUSED: ~/regtimeline is not the pinned one ($RT_SHA): STOP AND ASK"; exit 1; }
echo "$got" | grep -q "^$OOMRING_SHA " || { echo "STAGING REFUSED: oomring.blob did not arrive intact"; exit 1; }
echo "$got" | grep -q "^Python 3" || { echo "STAGING REFUSED: no python3 on the laptop (the reader and fwtask_run.py need it)"; exit 1; }
fr=$(echo "$got" | awk '/^free / {print $2}')
[ "${fr:-0}" -ge 600000 ] || { echo "STAGING REFUSED: ${fr:-?} KB free on ~/scratch (600 MB needed)"; exit 1; }
echo "staged: the rgn4 tool $TOOL_SHA (nothing built), runner, reader, tables and programs in ~/scratch/r6d/run and ~/scratch/r6d/stage"
