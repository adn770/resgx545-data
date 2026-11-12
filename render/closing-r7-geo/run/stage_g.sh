#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_g.sh: copy the runner (with sessioncheck.py and scorekit.py, which the controls' premise check runs), the tables, the controls
# list, the frozen hashes, the probe programs and round 6's t6 to the laptop (~/scratch/r7g/run, ~/scratch/r7g/stage,
# ~/scratch/r7g/bin; ~/scratch/r7g/out and ~/scratch/tmp are created; no other session's directories), then check that the laptop's
# copies are the frozen ones, that ~/scratch/r7g/bin/sgxfive-test is TOOL6.sha256's t6 and ~/sgxfive-test-rgn4 the build g.env
# names (a mismatch: STOP AND ASK, nothing is rebuilt).  No compile on the laptop.  Restaging is always safe.  SGX_DRY_RUN=1 prints
# the commands.  The staged list is exactly RUNNER_FILES (tests/run_all.sh checks it with sessioncheck.py staged).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/g.env"
TOOL_SHA=${G_TOOL_SHA:-$TOOL_SHA}
TOOL6_SHA=${G_TOOL6_SHA:-$TOOL6_SHA}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
T6L=${T6_LOCAL:-$KP/bin/t6/sgxfive-test}
R=scratch/$PREFIX
RUNNER_FILES="run/run_stage.sh run/lib_g.sh run/g.env score/sessioncheck.py score/scorekit.py"
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$KP/run/guard_g.sh" || exit 1
"$KP/run/freeze_g.sh" verify || exit 1
if [ -z "${SGX_DRY_RUN:-}" ]; then
	[ -f "$T6L" ] || { echo "no $T6L"; exit 1; }
	[ "$(shasum -a 256 "$T6L" | cut -d' ' -f1)" = "$TOOL6_SHA" ] || { echo "$T6L is not the t6 build $TOOL6_SHA"; exit 1; }
fi
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "mkdir -p $R/run/run $R/run/tables $R/bin $R/stage $R/out scratch/tmp && df -Pk ~ | awk 'NR == 2'"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO $(for f in $RUNNER_FILES; do printf '%s ' "$KP/$f"; done) "$T:$R/run/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/tables/*.txt "$T:$R/run/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/FROZEN.sha256 "$KP"/TOOL6.sha256 "$KP"/gen/data/controls.tsv "$KP"/bins/SHA256SUMS "$T:$R/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$KP"/bins/*.bin "$T:$R/stage/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$T6L" "$T:$R/bin/sgxfive-test"
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" "chmod 755 $R/bin/sgxfive-test"
CHK="cd $R/run && sha256sum run/run_stage.sh run/lib_g.sh run/g.env run/sessioncheck.py run/scorekit.py tables/*.txt FROZEN.sha256 TOOL6.sha256 controls.tsv SHA256SUMS ~/$R/bin/sgxfive-test ~/sgxfive-test-rgn4 && cd ~/$R/stage && sha256sum -c ~/$R/run/SHA256SUMS --quiet && echo programs-ok"
if [ -n "${SGX_DRY_RUN:-}" ]; then echo "bounded 120 ssh $SSHO $T '$CHK'   (compared with the Mac's)"; exit 0; fi
# shellcheck disable=SC2086
got=$(bounded 120 ssh $SSHO "$T" "$CHK")
rc=$?
[ $rc -eq 0 ] || { echo "STAGING FAILED: the check of the laptop's copies exited $rc"; exit 1; }
echo "$got"
bad=0
for f in run/run_stage.sh run/lib_g.sh run/g.env score/sessioncheck.py score/scorekit.py tables/*.txt FROZEN.sha256 TOOL6.sha256 gen/data/controls.tsv bins/SHA256SUMS; do
	want=$(cd "$KP" && shasum -a 256 "$f" | cut -d' ' -f1)
	case "$f" in score/*) lf=run/${f#score/} ;; gen/data/*|bins/*) lf=${f##*/} ;; *) lf=$f ;; esac
	echo "$got" | grep -q "^$want  $lf\$" || { echo "STAGING FAILED: $f (laptop $lf) is not the Mac's"; bad=1; }
done
echo "$got" | grep -q '^programs-ok$' || { echo "STAGING FAILED: the staged programs are not bins/SHA256SUMS's"; bad=1; }
echo "$got" | grep -Eq "^$TOOL6_SHA  .*$R/bin/sgxfive-test\$" || { echo "STAGING FAILED: the laptop's t6 is not $TOOL6_SHA"; bad=1; }
echo "$got" | grep -q "^$TOOL_SHA  .*sgxfive-test-rgn4\$" || { echo "STAGING FAILED: the laptop's rgn4 tool is not $TOOL_SHA"; bad=1; }
[ $bad = 0 ] || exit 1
echo "staged under ~/$R: runner, tables, controls, programs, t6 $TOOL6_SHA; rgn4 tool $TOOL_SHA unchanged"
