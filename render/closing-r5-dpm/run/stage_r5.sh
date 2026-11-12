#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r5.sh [--tables-only]: copy the runner, the reader, the landed fwtask_run.py, tables, FROZEN.sha256 and the staged programs
# (p1139-green.bin, oomring.blob) to ~/r5d-run and ~/r5d-stage on the laptop.  NOTHING IS BUILT: the tool is round 4's
# ~/sgxfive-test-rgn4 and ~/regtimeline is S1's (both pinned in run/r5.env); the staging checks both hashes and python3 on the laptop
# and refuses a mismatch (STOP AND ASK).  NOT RUN while R5-dpm was prepared.  Every ssh/scp is bounded by a perl alarm (SSH_ALARM,
# 150 s).  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R5=$(dirname "$HERE")
TABLES_ONLY=0
case "${1:-}" in "") ;; --tables-only) TABLES_ONLY=1 ;; *) echo "usage: stage_r5.sh [--tables-only]"; exit 2 ;; esac
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
. "$HERE/r5.env"
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
run() {
	if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; return 0; fi
	bounded "${SSH_ALARM:-150}" "$@"
	st=$?
	[ $st -eq 0 ] || { echo "STAGING FAILED (status $st) at: $*"; exit 1; }
}
"$R5/run/guard_r5.sh"; g=$?
[ $g -eq 0 ] || { echo "guard failed"; exit 1; }
"$R5/run/freeze_r5.sh" verify; v=$?
[ $v -eq 0 ] || { echo "frozen files do not verify"; exit 1; }
# shellcheck disable=SC2086
run ssh -o BatchMode=yes -o ConnectTimeout=10 $OPTS "$T" 'mkdir -p r5d-run/run r5d-run/tables r5d-stage r5d-out/state'
# shellcheck disable=SC2086
run scp -q $OPTS "$R5"/run/lib_r5.sh "$R5"/run/run_stage.sh "$R5"/run/r5read.py "$R5"/run/r5.env "$R5"/run/fwtask_run.py "$T:r5d-run/run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R5"/tables/*.txt "$T:r5d-run/tables/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R5"/FROZEN.sha256 "$T:r5d-run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R5"/bins/p1139-green.bin "$R5"/bins/oomring.blob "$T:r5d-stage/"
[ "$TABLES_ONLY" = 1 ] && exit 0
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "ssh $T sha256sum ~/sgxfive-test-rgn4 ~/regtimeline ~/r5d-stage/oomring.blob; python3 -V   (tool $TOOL_SHA, regtimeline $RT_SHA)"
	exit 0
fi
# shellcheck disable=SC2086
got=$(bounded "${SSH_ALARM:-150}" ssh -o BatchMode=yes $OPTS "$T" 'sha256sum ~/sgxfive-test-rgn4 ~/regtimeline ~/r5d-stage/oomring.blob; python3 -V' 2>&1)
st=$?
echo "$got"
[ $st -eq 0 ] || { echo "STAGING FAILED: cannot read the hashes (status $st)"; exit 1; }
echo "$got" | grep -q "^$TOOL_SHA " || { echo "STAGING REFUSED: ~/sgxfive-test-rgn4 is not the pinned rgn4 tool ($TOOL_SHA): STOP AND ASK"; exit 1; }
echo "$got" | grep -q "^$RT_SHA " || { echo "STAGING REFUSED: ~/regtimeline is not the pinned one ($RT_SHA): STOP AND ASK"; exit 1; }
echo "$got" | grep -q "^$OOMRING_SHA " || { echo "STAGING REFUSED: oomring.blob did not arrive intact"; exit 1; }
echo "$got" | grep -q "^Python 3" || { echo "STAGING REFUSED: no python3 on the laptop (the reader and fwtask_run.py need it)"; exit 1; }
echo "staged: the rgn4 tool $TOOL_SHA (nothing built), runner, reader, tables and programs in ~/r5d-run and ~/r5d-stage"
