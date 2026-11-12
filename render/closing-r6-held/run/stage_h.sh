#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_h.sh: copy part H's runner, tables and freeze file to the laptop, all under ~/scratch/r6h/ (run: the runner directory run/, the
# tables and FROZEN.sha256; out: the kept stages) and create ~/scratch/tmp (the runner's mktemp directory lives there, never in /tmp);
# then check that the laptop's copies are the frozen ones and that ~/sgxfive-test-rgn4 is the build h.env names (a mismatch: STOP AND
# ASK, nothing is rebuilt).  No compile.  NOT RUN while r6-held was prepared.  From r6-render4x's stage_k.sh.  Restaging is always
# safe (no gate state on the laptop).  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$KP/run/h.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
LR=scratch/r6h
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/run/guard_h.sh" "$KP" || exit 1
"$KP/run/freeze_h.sh" verify || exit 1
RFILES="run/lib_h.sh run/run_h.sh run/h.env"
TFILES="tables/s0.txt tables/q.txt"
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "mkdir -p $LR/run/run $LR/run/tables $LR/out scratch/tmp"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $RFILES; do echo "$KP/$f"; done) "$T:$LR/run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $TFILES; do echo "$KP/$f"; done) "$T:$LR/run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP/FROZEN.sha256" "$T:$LR/run/"
CHK="cd $LR/run && sha256sum $RFILES $TFILES FROZEN.sha256 ~/sgxfive-test-rgn4"
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
for f in $RFILES $TFILES FROZEN.sha256; do
	want=$(shasum -a 256 "$KP/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's tool is not the rgn4 build ($TOOL_SHA)"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged part H: runner, tables under ~/$LR; tool $TOOL_SHA unchanged"
