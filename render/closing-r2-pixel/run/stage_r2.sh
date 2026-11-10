#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r2.sh [--tables-only]: copy the runner, tables, frozen hashes and the staged programs to the laptop, then check
# that the laptop's copies are the frozen ones and that R1's tool and regtimeline are still the ones r2.env names.  No
# compile: R2 reuses ~/sgxfive-test-r1 (sha256 bf4f8be2...) and ~/regtimeline (079f6359...).  NOT RUN while R2 was prepared.
# Restaging is always safe: there is no gate state on the laptop to reset (gates come from the kept stage directories on
# the Mac), and the runner refuses a laptop FROZEN.sha256 that is not the Mac's.  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R2=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/r2.env"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R2/run/guard_r2.sh" || exit 1
"$R2/run/freeze_r2.sh" verify || exit 1
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" 'mkdir -p r2/run r2/tables r2-stage r2-out'
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R2"/run/lib_r2.sh "$R2"/run/run_stage.sh "$R2"/run/r2.env "$T:r2/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R2"/tables/*.txt "$T:r2/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R2"/FROZEN.sha256 "$T:r2/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$R2"/bins/*.bin "$T:r2-stage/"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "bounded 120 ssh $SSHO $T 'cd r2 && sha256sum run/lib_r2.sh run/run_stage.sh run/r2.env tables/*.txt FROZEN.sha256 ~/r2-stage/*.bin ~/sgxfive-test-r1 ~/regtimeline'   (compared with the Mac's)"
	exit 0
fi
# the laptop's copies must be the frozen ones, and R1's binaries must still be there
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" 'cd r2 && sha256sum run/lib_r2.sh run/run_stage.sh run/r2.env tables/*.txt FROZEN.sha256 ~/r2-stage/*.bin ~/sgxfive-test-r1 ~/regtimeline')
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in run/lib_r2.sh run/run_stage.sh run/r2.env tables/*.txt FROZEN.sha256; do
	case "$f" in tables/*) f=tables/$(basename "$f") ;; esac
	[ -f "$R2/$f" ] || continue
	want=$(shasum -a 256 "$R2/$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
for f in "$R2"/bins/*.bin; do
	want=$(shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  .*/r2-stage/$(basename "$f")\$" || { echo "STAGING FAILED: $(basename "$f") on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-r1\$" || { echo "STAGING FAILED: the laptop's tool is not R1's ($TOOL_SHA)"; bad=1; }
echo "$got" | grep -q "^$RT_SHA  .*regtimeline\$" || { echo "STAGING FAILED: the laptop's regtimeline is not $RT_SHA"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged: runner, tables, programs; tool $TOOL_SHA and regtimeline $RT_SHA unchanged"
