#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_s1.sh: copy the runner, tables and staged programs to the laptop and build the tool and regtimeline
# there (userspace compiles only; no kernel build, no git on the laptop).  NOT RUN while S1 was prepared.
# usage: stage_s1.sh [--tables-only]   (SGX_DRY_RUN=1 prints the commands; --tables-only after the PAUSE: only the new
#        table goes over, no rebuild of the tool)
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S1=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$S1/run/guard_s1.sh" || exit 1
"$S1/run/freeze_s1.sh" verify || exit 1
# shellcheck disable=SC2086
run ssh -o BatchMode=yes $OPTS "$T" 'mkdir -p s1/run s1/tables s1-stage'
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/run/lib_s1.sh "$S1"/run/run_stage.sh "$T:s1/run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/tables/*.txt "$T:s1/tables/"
# the frozen hashes: the runner's preflight compares its table and programs with them
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/FROZEN.sha256 "$T:s1/"
[ -f "$S1/FROZEN-e2b.sha256" ] && run scp -q $OPTS "$S1"/FROZEN-e2b.sha256 "$T:s1/"
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/bins/*.bin "$T:s1-stage/"
[ "${1:-}" = "--tables-only" ] && exit 0
run "$BRINGUP/deploy-tool.sh" s1
# regtimeline: one C file, userspace; built beside the tool
# shellcheck disable=SC2086
run scp -q $OPTS "$HOME/src/resgx545/tools/sweep/regtimeline.c" "$T:s1/regtimeline.c"
# shellcheck disable=SC2086
run ssh -o BatchMode=yes $OPTS "$T" 'cc -O2 -o ~/regtimeline ~/s1/regtimeline.c && sha256sum ~/regtimeline'
