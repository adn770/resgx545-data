#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r5.sh: copy the runner, tables, frozen hashes and the staged programs to the laptop (directories ~/r5p-run,
# ~/r5p-stage, ~/r5p-out: no other session's), then check that the laptop's copies are the frozen ones and that
# the tool is still the one r5.env names (a mismatch: STOP AND ASK, nothing is rebuilt).  No compile: R5-pixel uses
# ~/sgxfive-test-rgn4 (sha256 e6951558...), no regtimeline.  NOT RUN while R5-pixel was prepared.
# Restaging is always safe: there is no gate state on the laptop to reset (gates come from the kept stage directories on
# the Mac), and the runner refuses a laptop FROZEN.sha256 that is not the Mac's.  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R5=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/r5.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R5/run/guard_r5.sh" || exit 1
"$R5/run/freeze_r5.sh" verify || exit 1
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" 'mkdir -p r5p-run/run r5p-run/tables r5p-stage r5p-out'
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R5"/run/lib_r5.sh "$R5"/run/run_stage.sh "$R5"/run/r5.env "$T:r5p-run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R5"/tables/*.txt "$T:r5p-run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R5"/FROZEN.sha256 "$T:r5p-run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R5"/bins/*.bin "$T:r5p-stage/"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "bounded 120 ssh $SSHO $T 'cd r5p-run && sha256sum run/lib_r5.sh run/run_stage.sh run/r5.env tables/*.txt FROZEN.sha256 ~/r5p-stage/*.bin ~/sgxfive-test-rgn4'   (compared with the Mac's)"
	exit 0
fi
# the laptop's copies must be the frozen ones, and the rgn4 tool must still be there (R5-pixel uses no regtimeline)
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" 'cd r5p-run && sha256sum run/lib_r5.sh run/run_stage.sh run/r5.env tables/*.txt FROZEN.sha256 ~/r5p-stage/*.bin ~/sgxfive-test-rgn4')
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in run/lib_r5.sh run/run_stage.sh run/r5.env tables/*.txt FROZEN.sha256; do
	case "$f" in tables/*) f=tables/$(basename "$f") ;; esac
	[ -f "$R5/$f" ] || continue
	want=$(shasum -a 256 "$R5/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
for f in "$R5"/bins/*.bin; do
	want=$(shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  .*/r5p-stage/$(basename "$f")\$" || { echo "STAGING FAILED: $(basename "$f") on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's tool is not the pinned rgn4 tool ($TOOL_SHA)"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged: runner, tables, programs; tool $TOOL_SHA unchanged"
