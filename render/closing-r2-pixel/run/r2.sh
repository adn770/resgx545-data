#!/bin/bash
# SPDX-License-Identifier: MIT
# r2.sh [--from STAGE] [--only STAGE...] : the R2-pixel session driver, run from the Mac.  NOT RUN while it was prepared.
#
# For each stage of stages.txt (r2-d-safe, r2-d-fault, r2-a-safe, r2-a-fault): verify the frozen files; the GATE
# (score/score_r2.py gate: r2-d-fault runs only if d-ok-64 passed, r2-a-fault only if the a4 control passed); the
# runner gets the sha256 of this side's FROZEN.sha256 (it refuses a laptop copy that differs), the attempt name and the
# session's fault-class event count so far; the laptop-side runner over ssh (run_stage.sh); copy the stage's kept files
# to out/ATT/STAGE (copy only); score the stage (out/ATT/score-STAGE.txt, one SUMMARY line); the health script
# (tools/bringup/health.sh) and its checks.  After r2-a-fault the conditional stage r2-a-slack (the PRE-APPROVED slack pair,
# conditional.txt) runs when `score_r2.py gate r2-a-slack` says a5 cannot tell and the 5-event budget allows both of its
# faults (else it prints what to do).  Every ssh and scp is bounded (perl alarm: STAGE_ALARM, default 900 s a stage; 300 s a
# copy; 150 s the health; 60 s a knob read).  Host and ssh options: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS
# (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call between.
#
# GATES AND ATTEMPTS: there is no gate file on either side.  Gates are computed from the kept stage directories: this
# attempt's, then the earlier attempts' (newest first), so restaging or a new attempt (R2_ATT) never loses a gate; a gate
# that is closed says which stage to rerun (`run/r2.sh --only STAGE`, a new directory).  A rerun after a stop is a new attempt
# (`--from STAGE`); pass R2_FAULTS_PRIOR=N (the stop message prints it) to keep the session's fault count.
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health
# recovery, 6 freeze, 7 forbidden knob, 8 missing program, 9/11 hold_recovery read-back, 10 a held fault that did not clear,
# 12 registers unreadable, 13 reset failed, 14 fault latched before a job, 15 the 5th fault-class event; 142 the alarm: the
# laptop did not answer in time, a freeze), 20 frozen files changed, 30-37 health after a stage (no answer, fill or triangle
# not exact, FAIL, watchdog, render_pb_pages, hold_recovery, alias_skip, scp), 38 no scorer SUMMARY, 39 the attempt's stage
# directory exists, 40 a gate is closed, 41 the fault budget cannot hold the slack pair.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R2=$(dirname "$HERE")
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
LIMIT=${R2_FAULT_LIMIT:-5}
ALL=$(tr '\n' ' ' < "$R2/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${R2_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$R2/out/$ATT
FSHA=$(shasum -a 256 "$R2/FROZEN.sha256" | cut -d' ' -f1)
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
# the gate roots: this attempt, then the earlier ones, newest first
ROOTS="$ROOT"
for d in $(ls -1dt "$R2"/out/*/ 2>/dev/null); do
	d=${d%/}
	[ "$d" = "$ROOT" ] || ROOTS="$ROOTS $d"
done
PRIOR=${R2_FAULTS_PRIOR:-0}
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA; fault-class events before this attempt: $PRIOR (limit $LIMIT)"

# one stage: gate, ssh, copy, score, health.  Returns 0 or exits with the code of the stop.
run_one() {
	local st=$1 fe g rc src sc hrc n am arc
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (R2_ATT) for a rerun"; exit 39; }
	"$R2/run/freeze_r2.sh" verify || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_r2.sh)"; exit 20; }
	case "$st" in
	r2-d-fault|r2-a-fault|r2-a-slack)
		if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$PY $R2/score/score_r2.py gate $st $ROOTS"
		else
			# shellcheck disable=SC2086
			"$PY" "$R2/score/score_r2.py" gate "$st" $ROOTS > "$ROOT/gate-$st.txt" 2>&1; g=$?
			cat "$ROOT/gate-$st.txt"
			[ "$g" = 0 ] || { echo "STOP: the gate of $st is closed (status $g): its prerequisites failed; the SUMMARY line names the stage to rerun"; exit 40; }
		fi ;;
	esac
	fe=$((PRIOR + $(fault_events "$ROOT"/r2-*)))
	echo "#### $st $(date +%T) (fault-class events so far: $fe of $LIMIT)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-900} ssh $SSHO $T 'R2_FAULTS_PRIOR=$fe bash ~/r2/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:r2-out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $R2/score/score_r2.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-900}" ssh $SSHO "$T" "R2_FAULTS_PRIOR=$fe bash ~/r2/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:" "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:r2-out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		fe=$((PRIOR + $(fault_events "$ROOT"/r2-*)))
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "fault-class events so far: $fe; to continue after the lead's decision: R2_FAULTS_PRIOR=$fe run/r2.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying r2-out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$R2/score/score_r2.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
	grep '^SUMMARY:' "$ROOT/score-$st.txt" || { echo "STOP: no SUMMARY from the scorer of $st (status $sc)"; exit 38; }
	[ "$sc" = 0 ] || { echo "STOP: the scorer of $st exited $sc"; exit 38; }
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

go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ "$st" = r2-a-slack ] && continue          # conditional: handled below, by its gate
	[ -f "$R2/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	run_one "$st"
done
# the conditional slack pair, after the last stage of the normal order (not with --only of another stage)
if [ -z "$ONLY" ] || [ "$ONLY" = r2-a-slack ]; then
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "$PY $R2/score/score_r2.py gate r2-a-slack $ROOTS   (run r2-a-slack only if the gate is open: exit 0)"
		run_one r2-a-slack
	elif [ "$ONLY" = r2-a-slack ] || [ -f "$ROOT/r2-a-fault/cases.tsv" ]; then
		# (the gate is evaluated here; run_one evaluates it once more, which is the same answer)
		# shellcheck disable=SC2086
		"$PY" "$R2/score/score_r2.py" gate r2-a-slack $ROOTS > "$ROOT/gate-r2-a-slack.txt" 2>&1; g=$?
		cat "$ROOT/gate-r2-a-slack.txt"
		if [ "$g" = 0 ]; then
			fe=$((PRIOR + $(fault_events "$ROOT"/r2-*)))
			if [ $((fe + 2)) -gt "$LIMIT" ]; then
				echo "STOP: the slack pair needs two fault-class events and $fe of $LIMIT are used: lead's decision: R2_FAULT_LIMIT=$((fe + 2)) R2_FAULTS_PRIOR=$fe R2_ATT=$ATT-slack run/r2.sh --only r2-a-slack"
				exit 41
			fi
			run_one r2-a-slack
		else
			echo "the slack pair is not run (gate status $g: 3 not needed, 1 closed)"
		fi
	fi
fi
echo "R2 done: $PY $R2/score/score_r2.py verdict $ROOTS"
