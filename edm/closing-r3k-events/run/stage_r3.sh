#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_r3.sh SESSION: copy what a R3k session runs to the laptop (K0: ~/r3k0/, results in ~/r3k0-out/; K1: ~/r3kev/, ~/r3kev-out/) and check it
# there.  NOT RUN while R3k was prepared.  Builds nothing: the task blobs were assembled and verified on the Mac (gen/gen_r3.py); the tool is the
# laptop's ~/sgxfive-test-s1b (sha256 pinned in TOOL.sha256; the health script, e3's loop fills and e3b's fill) and, for K0's k0t, ~/sgxfive-test-r1
# (L1's and L2's tool, TOOLR1.sha256).  The files are those of gen/laptop_files.py; the laptop's LAPTOP.sha256 is this freeze's LAPTOP-SESSION.sha256.
# There is NO gate state to reset: gates are computed from the kept stage directories, so restaging, rerunning or resuming never closes a gate.
# Nothing is deleted on either side.  SGX_DRY_RUN=1 prints the commands.  Host and ssh options: tools/bringup/local.env, or SGX_TARGET_HOST and
# SGX_TARGET_SSH_OPTS in the environment.  The module must be the NEW one (srcversion loaded = installed = EXPECT, SGX_EXPECT_SRCV overrides in tests).
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
EXPECT_SRCV=${SGX_EXPECT_SRCV:-230E0EF50FFFD606C53AE3C}      # the new module (fork resgx545-r3 8fc748b0)
SESSION=${1:-}
case "$SESSION" in k0) LD=r3k0 ;; kev) LD=r3kev ;; *) echo "usage: stage_r3.sh k0|kev"; exit 2 ;; esac
# every step must succeed: the first failure stops the staging (each ssh bounded by a perl alarm)
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else perl -e 'alarm shift; exec @ARGV' 120 "$@" || { echo "STAGING FAILED at: $*"; exit 1; }; fi; }
"$R3/run/guard_r3.sh" || exit 1
"$R3/run/freeze_r3.sh" verify || exit 1
FILES=$("$PYTHON" "$R3/gen/laptop_files.py" "$SESSION") || { echo "no file list"; exit 1; }
# shellcheck disable=SC2086
run ssh $SSHO "$T" "mkdir -p $LD/run $LD/gen $LD/tables $LD/bins/progs $LD-out"
for f in $FILES; do
	# shellcheck disable=SC2086
	run scp -q $SSHO "$R3/$f" "$T:$LD/$f"
done
# shellcheck disable=SC2086
run scp -q $SSHO "$R/tools/fwtask/fwtask_run.py" "$T:$LD/run/fwtask_run.py"
# shellcheck disable=SC2086
run scp -q $SSHO "$R3/LAPTOP-$SESSION.sha256" "$T:$LD/LAPTOP.sha256"
# the laptop's copies are the frozen ones, and the pinned tools are there
# shellcheck disable=SC2086
run ssh $SSHO "$T" "cd ~/$LD && sha256sum -c --quiet LAPTOP.sha256 && test -x ~/$TOOL && test \"\$(sha256sum ~/$TOOL | cut -d' ' -f1)\" = \"\$(cut -d' ' -f1 TOOL.sha256)\" && echo \"tool ok: \$(sha256sum ~/$TOOL | cut -c1-16)\""
if [ "$SESSION" = k0 ]; then
	# shellcheck disable=SC2086
	run scp -q $SSHO "$R3/TOOLR1.sha256" "$T:$LD/TOOLR1.sha256"
	# shellcheck disable=SC2086
	run ssh $SSHO "$T" "cd ~/$LD && test -x ~/sgxfive-test-r1 && test \"\$(sha256sum ~/sgxfive-test-r1 | cut -d' ' -f1)\" = \"\$(cut -d' ' -f1 TOOLR1.sha256)\" && echo \"tool r1 ok: \$(sha256sum ~/sgxfive-test-r1 | cut -c1-16)\""
fi
# what the runner needs as root: the landed cmd_gate's tool (it hardcodes /home/jtorra/sgxfive-test), the python that sudo runs, and an sgx
# debugfs directory found through dri/* (the device has three names: the first that holds own_res is used)
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n test -x /home/jtorra/sgxfive-test || { echo 'no executable /home/jtorra/sgxfive-test (the landed gate tool)'; exit 1; }"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n python3 -c 'import sys; assert sys.version_info >= (3, 8), sys.version; print(sys.version.split()[0])'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ]; then echo \"debugfs \$d\"; fi; done'"
# the NEW module's debugfs files (every stage reads them in its preflight) and the module this session is prepared for
# shellcheck disable=SC2086
run ssh $SSHO "$T" "sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e \"\$d/own_res\" ]; then for f in regs status miscinfo kicker kick_no_bump kregnow hold_recovery render_rgn_arrays render_pb_pages; do test -e \"\$d/\$f\" || { echo \"missing debugfs \$f\"; exit 1; }; done; echo \"files ok \$d\"; fi; done'"
# shellcheck disable=SC2086
run ssh $SSHO "$T" "l=\$(sudo -n cat /sys/module/gma500_gfx/srcversion); i=\$(modinfo -F srcversion gma500_gfx); echo \"srcversion loaded \$l installed \$i\"; test \"\$l\" = \"\$i\" && test \"\$l\" = $EXPECT_SRCV"
echo "staged: ~/$LD on $T (tool ~/$TOOL)"
