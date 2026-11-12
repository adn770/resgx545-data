#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_m.sh TOOL6_SHA256: copy the runner, tables, frozen hashes and the t6 build to the laptop (~/scratch/r6m/run, ~/scratch/r6m/bin;
# ~/scratch/r6m/stage and out are created; no other session's directories), then check that the laptop's copies are the frozen ones,
# that ~/scratch/r6m/bin/sgxfive-test is the t6 build TOOL6_SHA256 names and ~/sgxfive-test-rgn4 the build m.env names (a mismatch:
# STOP AND ASK, nothing is rebuilt).  No compile on the laptop.  The t6 binary comes from debug/tool6-i686/sgxfive-test
# (lead/build_tool6.sh; T6_LOCAL overrides) and must have TOOL6_SHA256 here first.  Restaging is always safe.  SGX_DRY_RUN=1 prints
# the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/m.env"
TOOL_SHA=${M_TOOL_SHA:-$TOOL_SHA}
S6=${1:-}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
T6L=${T6_LOCAL:-$KP/debug/tool6-i686/sgxfive-test}
R=scratch/$PREFIX
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/run/guard_m.sh" || exit 1
"$KP/run/freeze_m.sh" verify "$S6" || exit 1
if [ -z "${SGX_DRY_RUN:-}" ]; then
	[ -f "$T6L" ] || { echo "no $T6L: lead/build_tool6.sh first"; exit 1; }
	[ "$(shasum -a 256 "$T6L" | cut -d' ' -f1)" = "$S6" ] || { echo "$T6L is not the t6 build $S6"; exit 1; }
fi
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "mkdir -p $R/run/run $R/run/tables $R/bin $R/stage $R/out scratch/tmp && df -Pk ~ | awk 'NR == 2'"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/run/lib_m.sh "$KP"/run/run_stage.sh "$KP"/run/m.env "$T:$R/run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/tables/*.txt "$T:$R/run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/FROZEN.sha256 "$KP"/TOOL6.sha256 "$T:$R/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$T6L" "$T:$R/bin/sgxfive-test"
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "chmod 755 $R/bin/sgxfive-test"
CHK="cd $R/run && sha256sum run/lib_m.sh run/run_stage.sh run/m.env tables/*.txt FROZEN.sha256 TOOL6.sha256 ~/$R/bin/sgxfive-test ~/sgxfive-test-rgn4"
if [ -n "${SGX_DRY_RUN:-}" ]; then echo "bounded 120 ssh $SSHO $T '$CHK'   (compared with the Mac's)"; exit 0; fi
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" "$CHK")
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in run/lib_m.sh run/run_stage.sh run/m.env tables/*.txt FROZEN.sha256 TOOL6.sha256; do
	want=$(cd "$KP" && shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -Eq "^$S6  .*$R/bin/sgxfive-test\$" || { echo "STAGING FAILED: the laptop's t6 is not $S6"; bad=1; }
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's rgn4 tool is not $TOOL_SHA"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged under ~/$R: runner, tables, TOOL6.sha256, t6 $S6; rgn4 tool $TOOL_SHA unchanged"
