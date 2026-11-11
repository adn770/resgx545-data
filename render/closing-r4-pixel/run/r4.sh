#!/bin/bash
# SPDX-License-Identifier: MIT
# r4.sh [--from STAGE] [--only STAGE...] : the R4-pixel session driver, run from the Mac.  NOT RUN while it was prepared.
#
# For each stage of stages.txt (p4-o4, q4-v, q4-f, q4-t, g4-rw): verify the frozen files; the laptop-side runner over ssh
# (run_stage.sh; it gets the sha256 of this side's FROZEN.sha256 and refuses a laptop copy that differs, and the attempt name);
# copy the stage's kept files to out/ATT/STAGE (copy only); score the stage (out/ATT/score-STAGE.txt, one SUMMARY line); the
# health script (tools/bringup/health.sh) and its checks; then the BRIDGE GATE: `score_r4.py gate STAGE KEPT` (exit 0 every bridge
# control of the stage passed, 1 a control FAILED, 2 a control cannot tell) stops the session with exit 42 unless it is 0, so the
# lead decides before the next stage (decision: tool a, each stage's bridge controls are the gate).  Every ssh and scp is bounded
# (perl alarm: STAGE_ALARM, default 900 s a stage; 300 s a copy; 150 s the health; 60 s a knob read).  Host and ssh options:
# SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops.
#
# The runner's own stops: rc 17 (a loop proof of a stage's first loop row failed): the stage ends after its health check, is scored
# and the session goes on with the next stage (a nested or load loop that does not prove itself costs that stage only); rc 18 (a
# runner-side bridge control, knob want2, read otherwise): the stage ends after its health check, is scored and the session STOPS
# (exit 42): the rgn4 module does not reproduce round 3's value.  Every other non-zero rc stops the session.
#
# GATES AND ATTEMPTS: there is no gate file on either side; gates are computed from the kept stage directory.  A rerun after a
# stop is a new attempt (`--from STAGE`).
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health
# recovery, 6 freeze, 7 forbidden knob, 8 missing program, 12 registers unreadable, 13 reset failed, 14 fault latched before a
# job, 16 STATUS2 not 0x400 after a reset; 142 the alarm: a freeze), 20 frozen files changed, 30-37 health after a stage (no
# answer, fill or triangle not exact, FAIL, watchdog, render_pb_pages, hold_recovery, alias_skip, scp), 38 no scorer SUMMARY, 39
# the attempt's stage directory exists, 42 a bridge control failed or could not tell (runner rc 18 or the scorer's gate).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R4=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-rgn4
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$R4/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${R4_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$R4/out/$ATT
FSHA=$(shasum -a 256 "$R4/FROZEN.sha256" | cut -d' ' -f1)
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
# the gate roots: this attempt, then the earlier ones, newest first
ROOTS="$ROOT"
for d in $(ls -1dt "$R4"/out/*/ 2>/dev/null); do
	d=${d%/}
	[ "$d" = "$ROOT" ] || ROOTS="$ROOTS $d"
done
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA"
SKIPPED=""

# the health script and its checks after a stage (also after a stage that stopped on a loop proof)
health_after() {
	local st=$1 hrc n am arc
	bounded 150 "$BRINGUP/health.sh" "$TOOL" > "$ROOT/health-$st.txt" 2>&1
	hrc=$?
	cat "$ROOT/health-$st.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health.sh exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$ROOT/health-$st.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	grep -q 'FAIL' "$ROOT/health-$st.txt" && { echo "STOP: health after $st: FAIL"; exit 32; }
	grep -Eq "$FATAL_RE" "$ROOT/health-$st.txt" && { echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; }
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$ROOT/health-$st.txt" || { echo "STOP: render_pb_pages not 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$ROOT/health-$st.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# the first sgx debugfs directory (the node has three names), through sudo -n
	# shellcheck disable=SC2086
	am=$(bounded 60 ssh $SSHO "$T" 'sudo -n sh -c "cat \$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1)/alias_skip"' 2>&1)
	arc=$?
	[ $arc -eq 0 ] || { echo "STOP: reading alias_skip after $st failed (status $arc): $am"; exit 36; }
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	echo "stage $st done, health ok"
}

# one stage: ssh, copy, score, health, bridge gate.  Returns 0, 17 (the loop proof failed), 18 (a bridge control, runner side) or
# exits with the code of the stop.
run_one() {
	local st=$1 g rc src sc
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (R4_ATT) for a rerun"; exit 39; }
	"$R4/run/freeze_r4.sh" verify || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_r4.sh)"; exit 20; }
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-900} ssh $SSHO $T 'bash ~/r4p-run/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:r4p-out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $R4/score/score_r4.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-900}" ssh $SSHO "$T" "bash ~/r4p-run/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:|sweep " "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:r4p-out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ] && [ $rc -ne 17 ] && [ $rc -ne 18 ]; then
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "to continue after the lead's decision: run/r4.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying r4p-out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$R4/score/score_r4.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
	grep '^SUMMARY:' "$ROOT/score-$st.txt" || { echo "STOP: no SUMMARY from the scorer of $st (status $sc)"; exit 38; }
	[ "$sc" = 0 ] || { echo "STOP: the scorer of $st exited $sc"; exit 38; }
	health_after "$st"
	[ $rc -eq 17 ] && return 17
	[ $rc -eq 18 ] && return 18
	# the bridge gate of the stage (from the kept files)
	"$PY" "$R4/score/score_r4.py" gate "$st" "$ROOT/$st" > "$ROOT/gate-$st.txt" 2>&1; g=$?
	cat "$ROOT/gate-$st.txt"
	if [ $g -ne 0 ]; then echo "STOP: the bridge controls of $st did not pass (gate exit $g): the lead decides (PREFLIGHT.md section 5)"; exit 42; fi
	return 0
}

go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -f "$R4/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	run_one "$st"; r=$?
	if [ $r -eq 17 ]; then
		echo "LOOP PROOF FAILED in $st (the stage ended after its health check and was scored); the session goes on with the next stage"
		SKIPPED="$SKIPPED $st(proof)"
	fi
	if [ $r -eq 18 ]; then
		echo "STOP: a bridge control of $st read otherwise (runner rc 18): the rgn4 module does not reproduce round 3's value; the lead decides"
		exit 42
	fi
done
echo "R4-pixel done${SKIPPED:+ (ended early:$SKIPPED)}: $PY $R4/score/score_r4.py verdict $ROOT"
