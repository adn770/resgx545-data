#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_s3.sh: copy the runner, tables, frozen hashes and the one staged program to the laptop.  No compile:
# S3 reuses S1's ~/sgxfive-test-s1 and ~/regtimeline (their sha256 are in run/s3.env; the runner's preflight
# refuses others).  NOT RUN while S3 was prepared.  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S3=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$S3/run/guard_s3.sh" || exit 1
"$S3/run/freeze_s3.sh" verify || exit 1
# shellcheck disable=SC2086
run bounded 60 ssh $SSHO "$T" 'mkdir -p s3/run s3/tables s3-stage s3-out'
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$S3"/run/lib_s3.sh "$S3"/run/run_stage.sh "$S3"/run/s3.env "$T:s3/run/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$S3"/tables/*.txt "$T:s3/tables/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$S3"/FROZEN.sha256 "$T:s3/"
# shellcheck disable=SC2086
run bounded 120 scp -q $SSHO "$S3"/bins/*.bin "$T:s3-stage/"
# the laptop's copies must be the frozen ones, and S1's binaries must still be there
# shellcheck disable=SC2086
run bounded 120 ssh $SSHO "$T" 'cd s3 && sha256sum run/lib_s3.sh run/run_stage.sh run/s3.env tables/*.txt && sha256sum ~/s3-stage/*.bin ~/sgxfive-test-s1 ~/regtimeline'
