#!/bin/bash
# SPDX-License-Identifier: MIT
# r1.sh [--from STAGE | --only STAGE... | --cell STAGE JOB] : the R1 session driver, run from the Mac.  NOT RUN while it
# was prepared.
#
# For each stage of stages.txt: verify the frozen files, run the laptop-side stage runner over ssh (run_stage.sh), copy
# the stage's kept files to out/STAGE/ (copy only), then the health script (tools/bringup/health.sh) and stop on any
# health failure, freeze (ssh does not answer) or watchdog.  No pause: every table is frozen up front.  --cell runs ONE
# row of a table (the pause cell of g-c1f: `r1.sh --cell g-c1f f-1500-0x373`).
# Host and ssh options: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env of the main checkout, or the
# environment).  SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call between stages.
# Every ssh and scp is bounded by a perl alarm (a stuck GPU job keeps an ssh session alive): STAGE_ALARM (1800 s) for
# the stage, SSH_ALARM (150 s) for health, the knob check and each copy.  Every exit status is read right after its
# command (no status hidden behind a pipe).
# Stage exit codes (run_stage.sh): 0 done, 1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure,
# 5 failed recovery, 6 freeze, 7 forbidden knob, 8 missing program, 9 knob read-back.  Any of them stops the session;
# r1.sh adds 20 (frozen files changed), 30-37 (health: no answer, a failed fill or triangle, FAIL, watchdog in the
# dmesg tail, render_pb_pages not 0x422, hold_recovery not N, alias_skip not 0, the copy failed).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R1=$(dirname "$HERE")
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
BRINGUP=${RESGX545_BRINGUP:-$MAIN/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
export SGX_LOCAL_ENV="$LOCAL_ENV"
. "$HERE/lib_check.sh"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-r1
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$R1/stages.txt")
FROM=""; ONLY=""; CELL=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
if [ "${1:-}" = "--cell" ]; then ONLY=${2:?stage}; CELL=${3:?job}; fi
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
mkdir -p "$R1/out"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -f "$R1/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	envp=""; [ -n "$CELL" ] && envp="ONLY=$CELL "
	log=$st; [ -n "$CELL" ] && log="$st-cell-$CELL"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "$R1/run/freeze_r1.sh verify"
		echo "bounded ${STAGE_ALARM:-1800} ssh $SSHO $T '${envp}bash ~/r1/run/run_stage.sh $st' > $R1/out/$log.log"
		echo "bounded ${SSH_ALARM:-150} scp -r $T:r1-out/$st $R1/out/   (copy only)"
		echo "bounded ${SSH_ALARM:-150} $BRINGUP/health.sh $TOOL"
		continue
	fi
	"$R1/run/freeze_r1.sh" verify
	vrc=$?
	[ $vrc -eq 0 ] || { echo "FROZEN FILES CHANGED (status $vrc): stop"; exit 20; }
	echo "#### $st $(date +%T)"
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-1800}" ssh $SSHO "$T" "${envp}bash ~/r1/run/run_stage.sh $st" > "$R1/out/$log.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:|0x072c gate" "$R1/out/$log.log" | tail -8
	# copy the kept files whatever the status (analysis needs them); nothing is deleted on either side
	# shellcheck disable=SC2086
	bounded "${SSH_ALARM:-150}" scp -q -r $SSHO "$T:r1-out/$st" "$R1/out/" > "$R1/out/scp-$log.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then echo "STOP: stage $st exited $rc (see out/$log.log; 255 = ssh lost, 142 = alarm: a freeze)"; exit $rc; fi
	if [ $src -ne 0 ]; then echo "STOP: copying r1-out/$st failed (scp status $src, see out/scp-$log.log)"; exit 37; fi
	[ -f "$R1/out/$st/gate072c.txt" ] && cat "$R1/out/$st/gate072c.txt"
	bounded "${SSH_ALARM:-150}" "$BRINGUP/health.sh" "$TOOL" > "$R1/out/health-$log.txt" 2>&1
	hrc=$?
	cat "$R1/out/health-$log.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health.sh exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$R1/out/health-$log.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	grep -q 'FAIL' "$R1/out/health-$log.txt" && { echo "STOP: health after $st: FAIL"; exit 32; }
	grep -Eq "$FATAL_RE" "$R1/out/health-$log.txt" && { echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; }
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$R1/out/health-$log.txt" || { echo "STOP: render_pb_pages not back at 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$R1/out/health-$log.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# shellcheck disable=SC2086
	am=$(bounded "${SSH_ALARM:-150}" ssh $SSHO "$T" 'sudo -n sh -c "cat \$(ls -d /sys/kernel/debug/dri/*/sgx | head -1)/alias_skip"' 2>&1)
	arc=$?
	[ $arc -eq 0 ] || { echo "STOP: reading alias_skip after $st failed (status $arc)"; exit 36; }
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	echo "stage $st done, health ok"
done
echo "R1 done"
