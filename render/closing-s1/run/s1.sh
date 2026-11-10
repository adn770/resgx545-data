#!/bin/bash
# SPDX-License-Identifier: MIT
# s1.sh [--from STAGE] [--only STAGE...] : the S1 session driver, run from the Mac.  NOT RUN while it was prepared.
#
# For each stage: verify the frozen files, run the laptop-side stage runner over ssh (run_stage.sh), copy the
# stage's kept files to out/STAGE/ (copy only), then the health script (tools/bringup/health.sh) and stop on
# any health failure, freeze (ssh does not answer) or watchdog.  The PAUSE of S1: after g-e2a the driver stops
# with status 10 unless tables/g-e2b.txt exists; then
#     python gen/gen_e2_boundary.py U.json   (U from: score/score_s1.py g-e2a out/g-e2a --emit-u U.json)
#     run/freeze_s1.sh e2b ; run/stage_s1.sh --tables-only ; run/s1.sh --from g-e2b
# Host and ssh options as the bringup scripts: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).
# SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call between stages.
# Stage exit codes (run_stage.sh): 0 done, 1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure,
# 5 three failed recoveries, 6 freeze, 7 forbidden knob, 8 missing program.  Any of them stops the session.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S1=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-s1
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$S1/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; return 0; fi; "$@"; }
mkdir -p "$S1/out"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	if [ ! -f "$S1/tables/$st.txt" ]; then
		echo "PAUSE: tables/$st.txt does not exist yet (generated after g-e2a: see the header of this script)"; exit 10
	fi
	run "$S1/run/freeze_s1.sh" verify "$st" || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "ssh $SSHO $T 'bash ~/s1/run/run_stage.sh $st' > $S1/out/$st.log"
		echo "scp -r $T:s1-out/$st $S1/out/   (copy only)"
		echo "$BRINGUP/health.sh $TOOL"
		continue
	fi
	# shellcheck disable=SC2086
	# a live session is bounded on the Mac too (a stuck GPU job keeps ssh alive): perl alarm, default 30 minutes a stage
	perl -e 'alarm shift; exec @ARGV' "${STAGE_ALARM:-1800}" ssh $SSHO "$T" "bash ~/s1/run/run_stage.sh $st" > "$S1/out/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:" "$S1/out/$st.log" | tail -5
	# copy the kept files whatever the status (analysis needs them); nothing is deleted on either side
	# shellcheck disable=SC2086
	scp -q -r $SSHO "$T:s1-out/$st" "$S1/out/" > "$S1/out/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then echo "STOP: stage $st exited $rc (see out/$st.log; 255 = ssh lost: a freeze)"; exit $rc; fi
	if [ $src -ne 0 ]; then echo "STOP: copying s1-out/$st failed (scp status $src, see out/scp-$st.log)"; exit 37; fi
	# health.sh has no timeout of its own (a stuck GPU process keeps the ssh session alive): a perl alarm of 150 s
	perl -e 'alarm 150; exec @ARGV' "$BRINGUP/health.sh" "$TOOL" > "$S1/out/health-$st.txt" 2>&1
	hrc=$?
	cat "$S1/out/health-$st.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health.sh exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$S1/out/health-$st.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	grep -q 'FAIL' "$S1/out/health-$st.txt" && { echo "STOP: health after $st: FAIL"; exit 32; }
	grep -Eq "$FATAL_RE" "$S1/out/health-$st.txt" && { echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; }
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$S1/out/health-$st.txt" || { echo "STOP: render_pb_pages not back at 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$S1/out/health-$st.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# shellcheck disable=SC2086
	am=$(ssh $SSHO "$T" 'sudo -n sh -c "cat \$(ls -d /sys/kernel/debug/dri/*/sgx | head -1)/alias_skip"' 2>&1)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	echo "stage $st done, health ok"
done
echo "S1 done"
