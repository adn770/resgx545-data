#!/bin/bash
# SPDX-License-Identifier: MIT
# r3.sh [--from STAGE] [--only STAGE...] : the R3-pixel session driver, run from the Mac.  NOT RUN while it was prepared.
#
# For each stage of stages.txt (p-c3, q-f0, q-f1a, q-f1b, q-t, q-v): verify the frozen files; the GATE (score/score_r3.py gate
# STAGE ROOTS: q-f1a, q-f1b and q-t run only if q-f0's relative-branch loop proofs passed); the runner gets the sha256 of this
# side's FROZEN.sha256 (it refuses a laptop copy that differs) and the attempt name; the laptop-side runner over ssh
# (run_stage.sh); copy the stage's kept files to out/ATT/STAGE (copy only); score the stage (out/ATT/score-STAGE.txt, one
# SUMMARY line); the health script (tools/bringup/health.sh) and its checks.  Every ssh and scp is bounded (perl alarm:
# STAGE_ALARM, default 900 s a stage; 300 s a copy; 150 s the health; 60 s a knob read).  Host and ssh options:
# SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops.
#
# THE LOOP GATE (decision R3-P1: the backward `br` in a pixel task is unproven on hardware).  q-f0 starts with the relative
# loop at 53; a failed proof (the runner's rc 17, or the scorer's loop gate closed) ends the Q082 PIXEL loop stages CLEANLY:
# q-f1a, q-f1b and q-t are skipped with a message, the health check runs, q-v (the vertex loop, proven by E784, with its own
# depth-word proof) still runs, and the session ends with exit 0 and a line naming what was skipped.  Abs and rel loops
# disagreeing on the bit at q-f0 (gate exit 3) is not decided here: the driver stops with exit 41 and the lead's options.
#
# GATES AND ATTEMPTS: there is no gate file on either side.  Gates are computed from the kept stage directories: this
# attempt's, then the earlier attempts' (newest first), so restaging or a new attempt (R3_ATT) never loses a gate.  A rerun
# after a stop is a new attempt (`--from STAGE`).
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health
# recovery, 6 freeze, 7 forbidden knob, 8 missing program, 12 registers unreadable, 13 reset failed, 14 fault latched before a
# job, 16 STATUS2 not 0x400 after a reset, 17 loop proof failed [handled for q-f0, see above]; 142 the alarm: a freeze), 20
# frozen files changed, 30-37 health after a stage (no answer, fill or triangle not exact, FAIL, watchdog, render_pb_pages,
# hold_recovery, alias_skip, scp), 38 no scorer SUMMARY, 39 the attempt's stage directory exists, 40 a gate is closed
# for a stage that has no clean skip, 41 q-f0's abs and rel loops disagree.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R3=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-r1
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$R3/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${R3_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$R3/out/$ATT
FSHA=$(shasum -a 256 "$R3/FROZEN.sha256" | cut -d' ' -f1)
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
# the gate roots: this attempt, then the earlier ones, newest first
ROOTS="$ROOT"
for d in $(ls -1dt "$R3"/out/*/ 2>/dev/null); do
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

# one stage: gate, ssh, copy, score, health.  Returns 0, 17 (q-f0 only: the loop proof failed, handled by the caller) or
# exits with the code of the stop.
run_one() {
	local st=$1 g rc src sc
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (R3_ATT) for a rerun"; exit 39; }
	"$R3/run/freeze_r3.sh" verify || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_r3.sh)"; exit 20; }
	case "$st" in
	q-f1a|q-f1b|q-t)
		if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$PY $R3/score/score_r3.py gate $st $ROOTS"
		else
			# shellcheck disable=SC2086
			"$PY" "$R3/score/score_r3.py" gate "$st" $ROOTS > "$ROOT/gate-$st.txt" 2>&1; g=$?
			cat "$ROOT/gate-$st.txt"
			case $g in
			0) ;;
			3) echo "STOP: q-f0's abs and rel loops disagree on the bit (lead's decision: PREFLIGHT.md section 5)"; exit 41 ;;
			*) echo "SKIPPED: $st (the loop gate is closed: the backward br did not prove itself in a pixel task)"
			   SKIPPED="$SKIPPED $st"; return 0 ;;
			esac
		fi ;;
	esac
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-900} ssh $SSHO $T 'bash ~/r3p-run/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:r3p-out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $R3/score/score_r3.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-900}" ssh $SSHO "$T" "bash ~/r3p-run/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:|sweep " "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:r3p-out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ] && { [ "$st" != q-f0 ] || [ $rc -ne 17 ]; }; then
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "to continue after the lead's decision: run/r3.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying r3p-out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$R3/score/score_r3.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
	grep '^SUMMARY:' "$ROOT/score-$st.txt" || { echo "STOP: no SUMMARY from the scorer of $st (status $sc)"; exit 38; }
	[ "$sc" = 0 ] || { echo "STOP: the scorer of $st exited $sc"; exit 38; }
	health_after "$st"
	[ $rc -eq 17 ] && return 17
	return 0
}

go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -f "$R3/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	run_one "$st"; r=$?
	if [ $r -eq 17 ]; then
		echo "LOOP GATE CLOSED: q-f0's relative-branch proof failed in a pixel task: the pixel loop stages (q-f1a, q-f1b, q-t) are skipped (their gates are closed); the session goes on with q-v"
	fi
done
echo "R3-pixel done${SKIPPED:+ (skipped:$SKIPPED)}: $PY $R3/score/score_r3.py verdict $ROOTS"
