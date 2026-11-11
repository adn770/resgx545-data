#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r4b.sh: copy what R4b runs to the laptop (~/r4b; results go to ~/r4b-out) and check it there.  Builds nothing: the task blob is
# R3k-events' frozen ring_exit.blob; the tool is the laptop's ~/sgxfive-test-s1b (TOOL.sha256: the health fill and triangle) and the
# landed cmd_gate's /home/jtorra/sgxfive-test.  The files are gen/laptop_files.py's; the laptop's LAPTOP.sha256 is this freeze's.
# Nothing is deleted on either side.  SGX_DRY_RUN=1 prints the commands.  Host and ssh options: tools/bringup/local.env, or
# SGX_TARGET_HOST and SGX_TARGET_SSH_OPTS in the environment.  The module must be fork a2788bd8's (srcversion loaded = installed = EXPECT).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R4=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$R/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-s1b
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
PYTHON=${PYTHON:-$R/.venv/bin/python}
EXPECT_SRCV=${SGX_EXPECT_SRCV:-99CD90DA26E3AFF9C450517}
LD=r4b
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else perl -e 'alarm shift; exec @ARGV' 120 "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R4/run/guard_r4b.sh" || exit 1
"$R4/run/freeze_r4b.sh" verify || exit 1
FILES=$("$PYTHON" "$R4/gen/laptop_files.py") || { echo "no file list"; exit 1; }
# shellcheck disable=SC2086
run ssh $SSHO "$T" "mkdir -p $LD/run $LD/gen $LD/tables $LD/bins $LD-out"
for f in $FILES; do
	# shellcheck disable=SC2086
	run scp -q $SSHO "$R4/$f" "$T:$LD/$f"
done
# shellcheck disable=SC2086
run scp -q $SSHO "$R/tools/fwtask/fwtask_run.py" "$T:$LD/run/fwtask_run.py"
# shellcheck disable=SC2086
run scp -q $SSHO "$R4/LAPTOP.sha256" "$T:$LD/LAPTOP.sha256"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "cd ~/$LD && sha256sum -c --quiet LAPTOP.sha256 && test -x ~/$TOOL && test \"\$(sha256sum ~/$TOOL | cut -d' ' -f1)\" = \"\$(cut -d' ' -f1 TOOL.sha256)\" && echo \"tool ok: \$(sha256sum ~/$TOOL | cut -c1-16)\""
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n test -x /home/jtorra/sgxfive-test || { echo 'no executable /home/jtorra/sgxfive-test (the landed gate tool)'; exit 1; }"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n python3 -c 'import sys; assert sys.version_info >= (3, 8), sys.version; print(sys.version.split()[0])'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ]; then for f in regs status miscinfo own_code own_arm own_res load boot reset kick_no_bump hold_recovery render_rgn_arrays render_pb_pages; do test -e \"\$d/\$f\" || { echo \"missing debugfs \$f\"; exit 1; }; done; echo \"files ok \$d\"; fi; done'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "l=\$(sudo -n cat /sys/module/gma500_gfx/srcversion); i=\$(modinfo -F srcversion gma500_gfx); echo \"srcversion loaded \$l installed \$i\"; test \"\$l\" = \"\$i\" && test \"\$l\" = $EXPECT_SRCV"
echo "staged: ~/$LD on $T (tool ~/$TOOL)"
