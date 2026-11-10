#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_k.sh: copy the runner, tables, frozen hashes and the staged programs to the laptop (directories ~/r3kreg-run,
# ~/r3kreg-stage, ~/r3kreg-out: no other session's), then check that the laptop's copies are the frozen ones and that R1's tool is still the one k.env names (a mismatch: STOP AND ASK, nothing is rebuilt).  No compile: R3K-regress (module regression) reuses
# ~/sgxfive-test-r1 (sha256 bf4f8be2...).  NOT RUN while R3K-regress (module regression) was prepared.
# Restaging is always safe: there is no gate state on the laptop to reset (gates come from the kept stage directories on
# the Mac), and the runner refuses a laptop FROZEN.sha256 that is not the Mac's.  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/k.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/run/guard_k.sh" || exit 1
"$KP/run/freeze_k.sh" verify || exit 1
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" 'mkdir -p r3kreg-run/run r3kreg-run/tables r3kreg-stage r3kreg-out'
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/run/lib_k.sh "$KP"/run/run_stage.sh "$KP"/run/k.env "$T:r3kreg-run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/tables/*.txt "$T:r3kreg-run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/FROZEN.sha256 "$T:r3kreg-run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/bins/*.bin "$T:r3kreg-stage/"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "bounded 120 ssh $SSHO $T 'cd r3kreg-run && sha256sum run/lib_k.sh run/run_stage.sh run/k.env tables/*.txt FROZEN.sha256 ~/r3kreg-stage/*.bin ~/sgxfive-test-r1'   (compared with the Mac's)"
	exit 0
fi
# the laptop's copies must be the frozen ones, and R1's binaries must still be there
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" 'cd r3kreg-run && sha256sum run/lib_k.sh run/run_stage.sh run/k.env tables/*.txt FROZEN.sha256 ~/r3kreg-stage/*.bin ~/sgxfive-test-r1')
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in run/lib_k.sh run/run_stage.sh run/k.env tables/*.txt FROZEN.sha256; do
	case "$f" in tables/*) f=tables/$(basename "$f") ;; esac
	[ -f "$KP/$f" ] || continue
	want=$(shasum -a 256 "$KP/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
for f in "$KP"/bins/*.bin; do
	want=$(shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  .*/r3kreg-stage/$(basename "$f")\$" || { echo "STAGING FAILED: $(basename "$f") on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-r1\$" || { echo "STAGING FAILED: the laptop's tool is not R1's ($TOOL_SHA)"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged: runner, tables, programs; tool $TOOL_SHA unchanged"
