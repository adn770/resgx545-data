#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r1.sh: copy what R1-events runs to the laptop (~/r1ev/, results in ~/r1ev-out/) and check it there.  NOT RUN while
# R1-events was prepared.  Builds nothing: the tool is the laptop's ~/sgxfive-test-s1b (built by S1b's staging; its sha256 is
# pinned in TOOL.sha256 and the runner refuses any other binary), ~/regtimeline is the one S1b built, and the task blob
# (ring_e1, 12 rungs in slot 3) and the loop programs were assembled and verified on the Mac (gen/gen_r1.py).
# Gate files: d0's file is (over)written with "GATE d0 NONE (staged)" on both sides, so that a gate of an earlier session can
# never open d1 (nothing is deleted).  SGX_DRY_RUN=1 prints the commands.  Host and ssh options: tools/bringup/local.env, or
# SGX_TARGET_HOST and SGX_TARGET_SSH_OPTS in the environment.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R1=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
BRINGUP=$R/tools/bringup
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=${R1_TOOL_NAME:-sgxfive-test-s1b}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging (each ssh bounded by a perl alarm)
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else perl -e 'alarm shift; exec @ARGV' 120 "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R1/run/guard_r1.sh" || exit 1
"$R1/run/freeze_r1.sh" verify || exit 1
GATES=${R1_GATES:-$R1/gates}
mkdir -p "$GATES"
echo "GATE d0 NONE (staged, not scored)" > "$GATES/d0.gate"
# shellcheck disable=SC2086
run ssh $SSHO "$T" 'mkdir -p r1ev/run r1ev/gen r1ev/tables r1ev/bins r1ev/gates r1ev-out'
# shellcheck disable=SC2086
run scp -q $SSHO "$R1"/run/r1_run.py "$R1"/run/health_remote.sh "$T:r1ev/run/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R/tools/fwtask/fwtask_run.py" "$T:r1ev/run/fwtask_run.py"
# shellcheck disable=SC2086
run scp -q $SSHO "$R1"/gen/r1layout.py "$T:r1ev/gen/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R1"/tables/*.json "$T:r1ev/tables/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R1"/bins/*.blob "$R1"/bins/*.bin "$T:r1ev/bins/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R1"/LAPTOP.sha256 "$R1"/TOOL.sha256 "$T:r1ev/"
# shellcheck disable=SC2086
run scp -q $SSHO "$GATES"/d0.gate "$T:r1ev/gates/"
# the laptop's copies are the frozen ones, and the pinned tool is there (its sha256 goes into every stage's env.json)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "cd ~/r1ev && sha256sum -c --quiet LAPTOP.sha256 && test -x ~/$TOOL && test \"\$(sha256sum ~/$TOOL | cut -d' ' -f1)\" = \"\$(cut -d' ' -f1 TOOL.sha256)\" && echo \"tool ok: \$(sha256sum ~/$TOOL | cut -c1-16)\""
# shellcheck disable=SC2086
run ssh $SSHO "$T" "test -x ~/regtimeline && sha256sum ~/regtimeline | cut -c1-16"
# what the runner needs as root: the landed cmd_gate's tool (it hardcodes /home/jtorra/sgxfive-test), the python that sudo
# runs, and an sgx debugfs directory found through dri/* (the device has three names: the first that holds own_res is used)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n test -x /home/jtorra/sgxfive-test || { echo 'no executable /home/jtorra/sgxfive-test (the landed gate tool)'; exit 1; }"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n python3 -c 'import sys; assert sys.version_info >= (3, 8), sys.version; print(sys.version.split()[0])'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ]; then echo \"debugfs \$d\"; fi; done'"
echo "staged: ~/r1ev on $T (tool ~/$TOOL)"
