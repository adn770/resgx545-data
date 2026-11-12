#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_k.sh [--set SET]: copy a freeze set's runner, tables and freeze file and the staged programs (bins/) to the laptop, all under
# ~/scratch/r6x/ (run: the runner directory, the tables and the freeze files; stage: the programs; out: the kept stages) and create
# ~/scratch/tmp (the runner's mktemp directory lives there, never in /tmp); then check that the laptop's copies are the frozen ones
# and that ~/sgxfive-test-rgn4 is the build the set's k.env names (a mismatch: STOP AND ASK, nothing is rebuilt).  No compile.
# NOT RUN while r6-render4x was prepared.  Copied from r5-render4x's (the ~/r5x-* directories became ~/scratch/r6x/*).
# Restaging is always safe: there is no gate state on the laptop to reset (gates come from the kept stage directories on the Mac), and
# the runner refuses a laptop freeze file that is not the Mac's.  A later set (B) is staged beside A's files, never over them.
# SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
SET=A
if [ "${1:-}" = "--set" ]; then SET=${2:?set}; shift 2; fi
[ -f "$KP/sets/$SET.env" ] || { echo "no sets/$SET.env"; exit 2; }
. "$KP/sets/$SET.env"
. "$KP/$SET_RUNDIR/k.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
LR=scratch/r6x
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/$SET_GUARD" "$KP" "$SET" || exit 1
"$KP/run/freeze_k.sh" verify "$SET" || exit 1
RFILES="$SET_RUNDIR/lib_k.sh $SET_RUNDIR/run_stage.sh $SET_RUNDIR/k.env"
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "mkdir -p $LR/run/$SET_RUNDIR $LR/run/tables $LR/stage $LR/out scratch/tmp"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $RFILES; do echo "$KP/$f"; done) "$T:$LR/run/$SET_RUNDIR/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $SET_TABLES; do echo "$KP/$f"; done) "$T:$LR/run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP/$SET_FREEZE" "$T:$LR/run/"
if [ -n "$SET_BINS" ]; then
	# shellcheck disable=SC2086
	run bounded 120 scp -q $SSHO $(for f in $SET_BINS; do echo "$KP/$f"; done) "$T:$LR/stage/"
fi
SBINS=""
for f in $SET_BINS; do SBINS="$SBINS ~/$LR/stage/${f##*/}"; done
CHK="cd $LR/run && sha256sum $RFILES $SET_TABLES $SET_FREEZE$SBINS ~/sgxfive-test-rgn4"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "bounded 120 ssh $SSHO $T '$CHK'   (compared with the Mac's)"
	exit 0
fi
# the laptop's copies must be the frozen ones, and the rgn4 tool must still be there
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" "$CHK")
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in $RFILES $SET_TABLES $SET_FREEZE; do
	want=$(shasum -a 256 "$KP/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
for f in $SET_BINS; do
	want=$(shasum -a 256 "$KP/$f" | cut -d' ' -f1)
	echo "$got" | grep -Eq "^$want  .*$LR/stage/$(basename "$f")\$" || { echo "STAGING FAILED: $(basename "$f") on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's tool is not the rgn4 build ($TOOL_SHA)"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged set $SET: runner, tables, programs under ~/$LR; tool $TOOL_SHA unchanged"
