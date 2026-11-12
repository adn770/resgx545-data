#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_f.sh: copy the runner, the tables, the five stage-L programs and the freeze file to the laptop, all under ~/scratch/r7f/
# (stage: run/, tables/, bins/ and FROZEN.sha256; out: the kept stages; run: the session's -110 ledger, written by the runner) and
# create ~/scratch/tmp (the runner's mktemp directory lives there, never in /tmp); then check that the laptop's copies are the frozen
# ones and that ~/sgxfive-test-rgn4 is the build f.env names (a mismatch: STOP AND ASK, nothing is rebuilt).  No compile.  NOT RUN
# while r7-faults was prepared.  From r6-held's stage_h.sh.  Restaging is always safe (the ledger is never touched by staging).
# The staged runner directory is exactly RFILES (tests/run_all.sh checks it with score/sessioncheck.py staged).
# SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$KP/run/f.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
LR=scratch/r7f
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/run/guard_f.sh" "$KP" || exit 1
"$KP/run/freeze_f.sh" verify || exit 1
RFILES="run/lib_f.sh run/run_f.sh run/f.env"
TFILES="tables/s0.txt tables/l.txt tables/d.txt tables/m.txt"
BFILES="bins/l0-lock-release.bin bins/l1-lock0-lock1.bin bins/l2-lock-lock-rel-rel.bin bins/l3-lock-lock-rel.bin bins/l4-lock-norel.bin"
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "mkdir -p $LR/stage/run $LR/stage/tables $LR/stage/bins $LR/out $LR/run scratch/tmp"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $RFILES; do echo "$KP/$f"; done) "$T:$LR/stage/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $TFILES; do echo "$KP/$f"; done) "$T:$LR/stage/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $BFILES; do echo "$KP/$f"; done) "$T:$LR/stage/bins/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP/FROZEN.sha256" "$T:$LR/stage/"
CHK="cd $LR/stage && sha256sum $RFILES $TFILES $BFILES FROZEN.sha256 ~/sgxfive-test-rgn4"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "bounded 120 ssh $SSHO $T '$CHK'   (compared with the Mac's)"
	exit 0
fi
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" "$CHK")
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in $RFILES $TFILES $BFILES FROZEN.sha256; do
	want=$(shasum -a 256 "$KP/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's tool is not the rgn4 build ($TOOL_SHA)"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged r7-faults: runner, tables, programs under ~/$LR/stage; tool $TOOL_SHA unchanged"
