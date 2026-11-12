#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r6.sh: copy the runner, tables, frozen hashes and the staged programs to the laptop (directories ~/scratch/r6p/run,
# ~/scratch/r6p/stage, ~/scratch/r6p/out: no other session's), then check that the laptop's copies are the frozen ones and that
# the tool is still the one r6.env names (a mismatch: STOP AND ASK, nothing is rebuilt).  No compile: R6-pixel uses
# ~/sgxfive-test-rgn4 (sha256 e6951558...), no regtimeline.  NOT RUN while R6-pixel was prepared.
# Restaging is always safe: there is no gate state on the laptop to reset (gates come from the kept stage directories on
# the Mac), and the runner refuses a laptop FROZEN.sha256 that is not the Mac's.  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R6=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/r6.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R6/run/guard_r6.sh" || exit 1
"$R6/run/freeze_r6.sh" verify || exit 1
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" 'mkdir -p scratch/r6p/run/run scratch/r6p/run/tables scratch/r6p/stage scratch/r6p/out scratch/tmp && df -Pk scratch/tmp'
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R6"/run/lib_r6.sh "$R6"/run/run_stage.sh "$R6"/run/r6.env "$T:scratch/r6p/run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R6"/tables/*.txt "$T:scratch/r6p/run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R6"/FROZEN.sha256 "$T:scratch/r6p/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R6"/bins/*.bin "$T:scratch/r6p/stage/"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "bounded 120 ssh $SSHO $T 'cd scratch/r6p/run && sha256sum run/lib_r6.sh run/run_stage.sh run/r6.env tables/*.txt FROZEN.sha256 ~/scratch/r6p/stage/*.bin ~/sgxfive-test-rgn4'   (compared with the Mac's)"
	exit 0
fi
# the laptop's copies must be the frozen ones, and the rgn4 tool must still be there (R6-pixel uses no regtimeline)
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" 'cd scratch/r6p/run && sha256sum run/lib_r6.sh run/run_stage.sh run/r6.env tables/*.txt FROZEN.sha256 ~/scratch/r6p/stage/*.bin ~/sgxfive-test-rgn4')
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in run/lib_r6.sh run/run_stage.sh run/r6.env tables/*.txt FROZEN.sha256; do
	case "$f" in tables/*) f=tables/$(basename "$f") ;; esac
	[ -f "$R6/$f" ] || continue
	want=$(shasum -a 256 "$R6/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
for f in "$R6"/bins/*.bin; do
	want=$(shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  .*/scratch/r6p/stage/$(basename "$f")\$" || { echo "STAGING FAILED: $(basename "$f") on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's tool is not the pinned rgn4 tool ($TOOL_SHA)"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged: runner, tables, programs; tool $TOOL_SHA unchanged"
