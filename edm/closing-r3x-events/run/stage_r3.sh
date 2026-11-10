#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r3.sh: copy what R3x-events runs to the laptop (~/r3xev/, results in ~/r3xev-out/) and check it there.  NOT RUN while R3-events
# was prepared.  Builds nothing: the task blobs were assembled and verified on the Mac (gen/gen_r3.py); the tool is the
# laptop's ~/sgxfive-test-s1b (S1b's; sha256 pinned in TOOL.sha256; used by the health script only).
# There is NO gate state to reset: gates are computed from the kept stage directories (the stage.json of the previous stage in
# ~/r3xev-out/ on the laptop and out/ here), so restaging, rerunning or resuming never closes a gate (R1-events lesson).  Nothing is
# deleted on either side.  SGX_DRY_RUN=1 prints the commands.  Host and ssh options: tools/bringup/local.env, or SGX_TARGET_HOST
# and SGX_TARGET_SSH_OPTS in the environment.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R3=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
BRINGUP=$R/tools/bringup
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=${R3_TOOL_NAME:-sgxfive-test-s1b}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
PYTHON=${PYTHON:-python3}
EXPECT_SRCV=${SGX_EXPECT_SRCV:-B21FDA82BD5E5CB5A627E3B}      # the module this session is prepared for (kernel batch comes after it)
# every step must succeed: the first failure stops the staging (each ssh bounded by a perl alarm)
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else perl -e 'alarm shift; exec @ARGV' 120 "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R3/run/guard_r3.sh" || exit 1
"$R3/run/freeze_r3.sh" verify || exit 1
# shellcheck disable=SC2086
run ssh $SSHO "$T" 'mkdir -p r3xev/run r3xev/gen r3xev/tables r3xev/bins r3xev-out'
# shellcheck disable=SC2086
run scp -q $SSHO "$R3"/run/r3_run.py "$R3"/run/health_remote.sh "$T:r3xev/run/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R/tools/fwtask/fwtask_run.py" "$T:r3xev/run/fwtask_run.py"
# shellcheck disable=SC2086
run scp -q $SSHO "$R3"/gen/r3layout.py "$T:r3xev/gen/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R3"/tables/*.json "$T:r3xev/tables/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R3"/bins/*.blob "$R3"/bins/blobs.json "$T:r3xev/bins/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R3"/LAPTOP.sha256 "$R3"/TOOL.sha256 "$T:r3xev/"
# the laptop's copies are the frozen ones, and the pinned tool is there (its sha256 goes into every stage's env.json)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "cd ~/r3xev && sha256sum -c --quiet LAPTOP.sha256 && test -x ~/$TOOL && test \"\$(sha256sum ~/$TOOL | cut -d' ' -f1)\" = \"\$(cut -d' ' -f1 TOOL.sha256)\" && echo \"tool ok: \$(sha256sum ~/$TOOL | cut -c1-16)\""
# what the runner needs as root: the landed cmd_gate's tool (it hardcodes /home/jtorra/sgxfive-test), the python that sudo
# runs, and an sgx debugfs directory found through dri/* (the device has three names: the first that holds own_res is used)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n test -x /home/jtorra/sgxfive-test || { echo 'no executable /home/jtorra/sgxfive-test (the landed gate tool)'; exit 1; }"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n python3 -c 'import sys; assert sys.version_info >= (3, 8), sys.version; print(sys.version.split()[0])'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ]; then echo \"debugfs \$d\"; fi; done'"
# (the loaded module is the installed one: the runner compares /sys/module/gma500_gfx/srcversion with `modinfo -F srcversion
# gma500_gfx` in every stage's preflight, as root)
# the debugfs files the stages read (regs, status, miscinfo) and the module this session is prepared for
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ] && [ -e \"\$d/regs\" ] && [ -e \"\$d/status\" ] && [ -e \"\$d/miscinfo\" ]; then echo \"files ok \$d\"; fi; done'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "l=\$(sudo -n cat /sys/module/gma500_gfx/srcversion); i=\$(modinfo -F srcversion gma500_gfx); echo \"srcversion loaded \$l installed \$i\"; test \"\$l\" = \"\$i\" && test \"\$l\" = $EXPECT_SRCV"
echo "staged: ~/r3xev on $T (tool ~/$TOOL)"
