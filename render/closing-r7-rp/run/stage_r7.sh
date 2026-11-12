#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r7.sh TOOL7_SHA256: copy the runner, tables, frozen hashes, the staged programs and the t6 and t7 builds to the laptop
# (~/scratch/r7r/run, ~/scratch/r7r/stage, ~/scratch/r7r/bin; ~/scratch/r7r/out and ~/scratch/tmp are created; no other session's
# directories), then check that the laptop's copies are the frozen ones, that ~/scratch/r7r/bin/sgxfive-test-t7 is the t7 build
# TOOL7_SHA256 names, -t6 round 6's build (r7.env TOOL6_SHA) and ~/sgxfive-test-rgn4 the rgn4 build (a mismatch: STOP AND ASK, nothing
# is rebuilt).  No compile on the laptop.  t7 comes from debug/tool7-i686/sgxfive-test (lead/build_tool7.sh; T7_LOCAL overrides) and
# must have TOOL7_SHA256 here first; t6 from debug/tool6-i686/sgxfive-test, a copy of round 6's Mac build closing6/r6-misc/debug/tool6-i686 (T6_LOCAL overrides).
# Restaging is always safe.  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/r7.env"
TOOL_SHA=${R7_TOOL_SHA:-$TOOL_SHA}
TOOL6_SHA=${R7_TOOL6_SHA:-$TOOL6_SHA}
S7=${1:-}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
T7L=${T7_LOCAL:-$KP/debug/tool7-i686/sgxfive-test}
T6L=${T6_LOCAL:-$KP/debug/tool6-i686/sgxfive-test}
R=scratch/$PREFIX
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/run/guard_r7.sh" || exit 1
"$KP/run/freeze_r7.sh" verify "$S7" || exit 1
if [ -z "${SGX_DRY_RUN:-}" ]; then
	[ -f "$T7L" ] || { echo "no $T7L: lead/build_tool7.sh first"; exit 1; }
	[ "$(shasum -a 256 "$T7L" | cut -d' ' -f1)" = "$S7" ] || { echo "$T7L is not the t7 build $S7"; exit 1; }
	[ -f "$T6L" ] || { echo "no $T6L (round 6's t6 build)"; exit 1; }
	[ "$(shasum -a 256 "$T6L" | cut -d' ' -f1)" = "$TOOL6_SHA" ] || { echo "$T6L is not round 6's t6 $TOOL6_SHA"; exit 1; }
fi
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "mkdir -p $R/run/run $R/run/tables $R/bin $R/stage $R/out scratch/tmp && df -Pk ~ | awk 'NR == 2'"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/run/lib_r7.sh "$KP"/run/run_stage.sh "$KP"/run/r7.env "$T:$R/run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/tables/*.txt "$T:$R/run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/FROZEN.sha256 "$KP"/TOOL7.sha256 "$T:$R/run/"
# shellcheck disable=SC2086
run bounded 300 scp -q $SSHO "$KP"/bins/* "$T:$R/stage/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$T6L" "$T:$R/bin/sgxfive-test-t6"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$T7L" "$T:$R/bin/sgxfive-test-t7"
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "chmod 755 $R/bin/sgxfive-test-t6 $R/bin/sgxfive-test-t7"
CHK="cd $R/run && sha256sum run/lib_r7.sh run/run_stage.sh run/r7.env tables/*.txt FROZEN.sha256 TOOL7.sha256 ~/$R/stage/* ~/$R/bin/sgxfive-test-t6 ~/$R/bin/sgxfive-test-t7 ~/sgxfive-test-rgn4"
if [ -n "${SGX_DRY_RUN:-}" ]; then echo "bounded 120 ssh $SSHO $T '$CHK'   (compared with the Mac's)"; exit 0; fi
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" "$CHK")
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
bad=0
for f in run/lib_r7.sh run/run_stage.sh run/r7.env tables/*.txt FROZEN.sha256 TOOL7.sha256; do
	want=$(cd "$KP" && shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -q "^$want  $f\$" || { echo "STAGING FAILED: $f on the laptop is not the Mac's"; bad=1; }
done
for f in "$KP"/bins/*; do
	want=$(shasum -a 256 "$f" | cut -d' ' -f1)
	echo "$got" | grep -Eq "^$want  .*$R/stage/${f##*/}\$" || { echo "STAGING FAILED: stage/${f##*/} on the laptop is not the Mac's"; bad=1; }
done
echo "$got" | grep -Eq "^$S7  .*$R/bin/sgxfive-test-t7\$" || { echo "STAGING FAILED: the laptop's t7 is not $S7"; bad=1; }
echo "$got" | grep -Eq "^$TOOL6_SHA  .*$R/bin/sgxfive-test-t6\$" || { echo "STAGING FAILED: the laptop's t6 is not $TOOL6_SHA"; bad=1; }
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's rgn4 tool is not $TOOL_SHA"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged under ~/$R: runner, tables, programs ($(ls "$KP"/bins | wc -l | tr -d ' ')), TOOL7.sha256, t6 $TOOL6_SHA, t7 $S7; rgn4 tool $TOOL_SHA unchanged"
