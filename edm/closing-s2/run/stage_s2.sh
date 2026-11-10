#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_s2.sh: copy what S2 runs to the laptop (~/s2/) and check it there.  NOT RUN while S2 was prepared.
# No build of anything: the tool is S1's ~/sgxfive-test-s1 (built by S1's stage_s1.sh), checked to exist; the task
# blobs were assembled and verified on the Mac (gen/gen_s2.py) and the kernel verifies them again at own_code.
# Gate files: every gated stage's file is (over)written with "GATE X NONE (staged)" on both sides, so that a gate
# of an earlier session can never open a stage of this one (nothing is deleted).
# SGX_DRY_RUN=1 prints the commands.  Host and ssh options: tools/bringup/local.env, as S1.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S2=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
BRINGUP=$R/tools/bringup
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=${S2_TOOL_NAME:-sgxfive-test-s1}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
# every step must succeed: the first failure stops the staging (each ssh bounded by a perl alarm)
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else perl -e 'alarm shift; exec @ARGV' 120 "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$S2/run/guard_s2.sh" || exit 1
"$S2/run/freeze_s2.sh" verify || exit 1
GATES=${S2_GATES:-$S2/gates}
mkdir -p "$GATES"
for g in e1c e2r e4c e4h e4l e5c; do echo "GATE $g NONE (staged, not scored)" > "$GATES/$g.gate"; done
# shellcheck disable=SC2086
run ssh $SSHO "$T" 'mkdir -p s2/run s2/gen s2/tables s2/bins s2/gates s2-out'
# shellcheck disable=SC2086
run scp -q $SSHO "$S2"/run/s2_run.py "$T:s2/run/"
# shellcheck disable=SC2086
run scp -q $SSHO "$R/tools/fwtask/fwtask_run.py" "$T:s2/run/fwtask_run.py"
# shellcheck disable=SC2086
run scp -q $SSHO "$S2"/gen/s2layout.py "$T:s2/gen/"
# shellcheck disable=SC2086
run scp -q $SSHO "$S2"/tables/*.json "$T:s2/tables/"
# shellcheck disable=SC2086
run scp -q $SSHO "$S2"/bins/*.blob "$T:s2/bins/"
# shellcheck disable=SC2086
run scp -q $SSHO "$S2"/LAPTOP.sha256 "$T:s2/"
# shellcheck disable=SC2086
run scp -q $SSHO "$GATES"/*.gate "$T:s2/gates/"
# the laptop's copies are the frozen ones, and the tool is there (its sha256 goes into every stage's env.json)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "cd ~/s2 && sha256sum -c --quiet LAPTOP.sha256 && test -x ~/$TOOL && sha256sum ~/$TOOL"
# what the runner needs as root: the landed cmd_gate's tool (it hardcodes /home/jtorra/sgxfive-test), the python
# that sudo runs, and an sgx debugfs directory found through dri/* (not only dri/0)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n test -x /home/jtorra/sgxfive-test || { echo 'no executable /home/jtorra/sgxfive-test (the landed gate tool)'; exit 1; }"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n python3 -c 'import sys; assert sys.version_info >= (3, 8), sys.version; print(sys.version.split()[0])'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'd=\$(ls -d /sys/kernel/debug/dri/*/sgx 2>/dev/null | head -n 1); test -n \"\$d\" && test -d \"\$d\" && echo \"debugfs \$d\"'"
echo "staged: ~/s2 on $T (tool ~/$TOOL)"
