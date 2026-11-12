#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_p.sh: copy what r6-held part P runs to the laptop (~/scratch/r6h/p/stage; results go to ~/scratch/r6h/p/out/ATTEMPT; the runner's
# work directories under ~/scratch/tmp) and check it there.  R5-events' stage_r5e.sh with round 6's directories.  Builds nothing: the
# task blob is R4-events' ring_skip3p, verified on the Mac (run/guard_blobs.py); the tool is the laptop's ~/sgxfive-test-s1b (TOOL.sha256:
# the health fill and triangle, the jobs' fill) and the landed cmd_gate's /home/jtorra/sgxfive-test.  The files are gen/laptop_files.py's;
# the laptop's LAPTOP.sha256 is this freeze's.  Nothing is deleted on either side.  SGX_DRY_RUN=1 prints the commands.  Host and ssh
# options: tools/bringup/local.env, or SGX_TARGET_HOST and SGX_TARGET_SSH_OPTS in the environment.  The module must be fork r6-kernel
# 3f0b3e74's (srcversion loaded = installed = 41E2F5C756F96D20F7109A4, SGX_EXPECT_SRCV overrides in tests), with debugfs peek and
# render_tail_room; at least 300 MiB free on ~.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R5=$(dirname "$HERE")
R=${RESGX545:-/Users/jtorra/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$HOME/src/resgx545/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-s1b
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
PYTHON=${PYTHON:-python3}
EXPECT_SRCV=${SGX_EXPECT_SRCV:-41E2F5C756F96D20F7109A4}
LD=scratch/r6h/p/stage
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else perl -e 'alarm shift; exec @ARGV' 120 "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R5/run/guard_p.sh" || exit 1
"$R5/run/freeze_p.sh" verify || exit 1
FILES=$("$PYTHON" "$R5/gen/laptop_files.py") || { echo "no file list"; exit 1; }
# shellcheck disable=SC2086
run ssh $SSHO "$T" "mkdir -p $LD/run $LD/gen $LD/tables $LD/bins scratch/r6h/p/out scratch/tmp"
for f in $FILES; do
	# shellcheck disable=SC2086
	run scp -q $SSHO "$R5/$f" "$T:$LD/$f"
done
# shellcheck disable=SC2086
run scp -q $SSHO "$R/tools/fwtask/fwtask_run.py" "$T:$LD/run/fwtask_run.py"
# shellcheck disable=SC2086
run scp -q $SSHO "$R5/LAPTOP.sha256" "$T:$LD/LAPTOP.sha256"
# the laptop's copies are the frozen ones, and the pinned tool is there
# shellcheck disable=SC2086
run ssh $SSHO "$T" "cd ~/$LD && sha256sum -c --quiet LAPTOP.sha256 && test -x ~/$TOOL && test \"\$(sha256sum ~/$TOOL | cut -d' ' -f1)\" = \"\$(cut -d' ' -f1 TOOL.sha256)\" && echo \"tool ok: \$(sha256sum ~/$TOOL | cut -c1-16)\""
# what the runner needs as root: the landed cmd_gate's tool (it hardcodes /home/jtorra/sgxfive-test), the python that sudo runs
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n test -x /home/jtorra/sgxfive-test || { echo 'no executable /home/jtorra/sgxfive-test (the landed gate tool)'; exit 1; }"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n python3 -c 'import sys; assert sys.version_info >= (3, 8), sys.version; print(sys.version.split()[0])'"
# the debugfs files every stage reads in its preflight, and the module this session is prepared for
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ]; then for f in regs status miscinfo own_code own_arm own_res load boot reset kick_no_bump kregnow hold_recovery render_rgn_arrays render_pb_pages timer_clock render_tail_room peek; do test -e \"\$d/\$f\" || { echo \"missing debugfs \$f\"; exit 1; }; done; echo \"files ok \$d\"; fi; done'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "l=\$(sudo -n cat /sys/module/gma500_gfx/srcversion); i=\$(modinfo -F srcversion gma500_gfx); echo \"srcversion loaded \$l installed \$i\"; test \"\$l\" = \"\$i\" && test \"\$l\" = $EXPECT_SRCV"
# the free space on ~ (at least 300 MiB: round 6's rule) and the work root
# shellcheck disable=SC2086
run ssh $SSHO "$T" "test -d ~/scratch/tmp && kb=\$(df -Pk ~ | tail -1 | awk '{print \$4}') && echo \"free on ~: \$kb KiB\" && test \"\$kb\" -ge 307200"
echo "staged: ~/$LD on $T (tool ~/$TOOL)"
