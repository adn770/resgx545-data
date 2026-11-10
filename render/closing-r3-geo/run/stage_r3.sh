#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r3.sh [--tables-only]: copy the runner, tables and staged programs to the laptop.  NOTHING IS BUILT: the tool is
# R1's ~/sgxfive-test-r1 (sha256 pinned in TOOL.sha256: bf4f8be2...) and ~/regtimeline is R1's; the staging checks both hashes
# on the laptop (ssh sha256sum) and stops if the tool differs from the pin or the regtimeline is missing.  NOT RUN while R3 was
# prepared.  The vertex templates (vtx_zw, vtx_wzclip) are probe programs assembled on the Mac into bins/ and staged
# as files, as in R1.  Every ssh/scp is bounded by a perl alarm (SSH_ALARM, 150 s).  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R3=$(dirname "$HERE")
TABLES_ONLY=0
case "${1:-}" in "") ;; --tables-only) TABLES_ONLY=1 ;; *) echo "usage: stage_r3.sh [--tables-only]"; exit 2 ;; esac
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
export SGX_LOCAL_ENV="$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
# every step must succeed: the first failure stops the staging
run() {
	if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; return 0; fi
	bounded "${SSH_ALARM:-150}" "$@"
	st=$?
	[ $st -eq 0 ] || { echo "STAGING FAILED (status $st) at: $*"; exit 1; }
}
"$R3/run/guard_r3.sh"; g=$?
[ $g -eq 0 ] || { echo "guard failed"; exit 1; }
"$R3/run/freeze_r3.sh" verify; v=$?
[ $v -eq 0 ] || { echo "frozen files do not verify"; exit 1; }
want=$(cut -d' ' -f1 "$R3/TOOL.sha256")
# shellcheck disable=SC2086
run ssh -o BatchMode=yes -o ConnectTimeout=10 $OPTS "$T" 'mkdir -p r3g/run r3g/tables r3g-stage r3g-out/state'
# shellcheck disable=SC2086
run scp -q $OPTS "$R3"/run/lib_r3.sh "$R3"/run/run_stage.sh "$R3"/run/dpm_read.awk "$R3"/run/bis.awk "$T:r3g/run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R3"/tables/*.txt "$T:r3g/tables/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R3"/FROZEN.sha256 "$R3"/TOOL.sha256 "$T:r3g/"
# shellcheck disable=SC2086
run scp -q $OPTS "$R3"/bins/*.bin "$T:r3g-stage/"
[ "$TABLES_ONLY" = 1 ] && exit 0
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "ssh $T sha256sum ~/sgxfive-test-r1 ~/regtimeline   (the tool must be $want)"
	exit 0
fi
# shellcheck disable=SC2086
got=$(bounded "${SSH_ALARM:-150}" ssh -o BatchMode=yes $OPTS "$T" 'sha256sum ~/sgxfive-test-r1 ~/regtimeline' 2>&1)
st=$?
echo "$got"
[ $st -eq 0 ] || { echo "STAGING FAILED: cannot read the tool and regtimeline hashes (status $st)"; exit 1; }
[ "$(echo "$got" | grep -c "^$want ")" = 1 ] || { echo "STAGING REFUSED: ~/sgxfive-test-r1 is not the pinned R1 tool ($want): STOP AND ASK (user decision R3-G8: no rebuild)"; exit 1; }
echo "$got" | grep -q 'regtimeline' || { echo "STAGING REFUSED: no ~/regtimeline"; exit 1; }
echo "staged: R1's tool $want (nothing built), runner, tables and programs in ~/r3g and ~/r3g-stage"
