#!/bin/bash
# SPDX-License-Identifier: MIT
# k.sh [--from STAGE] [--only STAGE...] : the R3K-pixel session driver (kernel-batch session K2, pixel and fault rows), run from the
# Mac.  NOT RUN while it was prepared.  It runs AFTER K0 and K1 on the new gma500 module (srcversion 230E0EF5...).
#
# For each stage of stages.txt (k-f4, k-pb0, k-pb, k-bif; fault rows are last in each stage and the riskiest stage, k-bif, is last
# of the session): verify the frozen files; the GATE (score/score_k.py gate: k-pb runs only if the controls of k-pb0 passed, else it
# is skipped CLEANLY with a message and the session goes on); the runner gets the sha256 of this side's FROZEN.sha256 (it refuses a
# laptop copy that differs), the attempt name and K_FAULTS_PRIOR=0 (the fault limit, 5, counts per stage); the laptop-side runner
# over ssh (run_stage.sh); copy the stage's kept files to out/ATT/STAGE (copy only); score the stage (out/ATT/score-STAGE.txt, one
# SUMMARY line); the health script (tools/bringup/health.sh) and its checks, which include the knobs: hold_recovery N,
# alias_skip 0, render_pb_pages 0x422 and render_rgn_arrays 1 (the knob of Q140 is restored to 1 at the end of its stage and
# after any stop: a stage that leaves another value stops the session, rc 42).  After a stop the driver tries to read the knob
# once (bounded) and prints it.  Every ssh and scp is bounded (perl alarm: STAGE_ALARM, default 900 s a stage; 300 s a copy; 150 s
# the health; 60 s a knob read).  Host and ssh options: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).
# SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call between.
#
# GATES AND ATTEMPTS: there is no gate file on either side.  Gates are computed from the kept stage directories: this attempt's,
# then the earlier attempts' (newest first), so restaging or a new attempt (K_ATT) never loses a gate.  A rerun after a stop is a
# new attempt (`--from STAGE`).
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health recovery,
# 6 freeze, 7 forbidden knob, 8 missing program, 9/11 hold_recovery read-back, 10 a held fault that did not clear, 12 registers
# unreadable, 13 reset failed, 14 fault latched before a job, 15 the 5th fault-class event of a stage, 18 no answer after a BIF write
# (E317), 19 render_rgn_arrays did not read back; 142 the alarm: a freeze), 20 frozen files changed, 30-37 health after a stage (no
# answer, fill or triangle not exact, FAIL, watchdog, render_pb_pages, hold_recovery, alias_skip, scp), 38 no scorer SUMMARY, 39 the
# attempt's stage directory exists, 42 render_rgn_arrays is not 1 after a stage.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
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
ALL=$(tr '\n' ' ' < "$KP/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${K_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$KP/out/$ATT
FSHA=$(shasum -a 256 "$KP/FROZEN.sha256" | cut -d' ' -f1)
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
# the gate roots: this attempt, then the earlier ones, newest first
ROOTS="$ROOT"
for d in $(ls -1dt "$KP"/out/*/ 2>/dev/null); do
	d=${d%/}
	[ "$d" = "$ROOT" ] || ROOTS="$ROOTS $d"
done
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA"
SKIPPED=""

# the knobs after a stage or a stop, read through sudo -n (the node has three names: the first sgx debugfs directory)
knobs_read() { # prints "alias_skip rgn" on two lines
	# shellcheck disable=SC2086
	bounded 60 ssh $SSHO "$T" 'sudo -n sh -c "d=\$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1); cat \$d/alias_skip; cat \$d/render_rgn_arrays"' 2>&1
}

# the health script and its checks after a stage
health_after() {
	local st=$1 hrc n am arc kn rg
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
	kn=$(knobs_read); arc=$?
	[ $arc -eq 0 ] || { echo "STOP: reading alias_skip and render_rgn_arrays after $st failed (status $arc): $kn"; exit 36; }
	am=$(echo "$kn" | sed -n 1p); rg=$(echo "$kn" | sed -n 2p)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	num_eq "$rg" 1 || { echo "STOP: render_rgn_arrays is $rg after $st (not numerically 1): the knob must be restored (write 1 to debugfs render_rgn_arrays before anything else)"; exit 42; }
	echo "stage $st done, health ok, render_rgn_arrays $rg"
}

# one stage: gate, ssh, copy, score, health.  Returns 0 or exits with the code of the stop.
run_one() {
	local st=$1 g rc src sc kn
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (K_ATT) for a rerun"; exit 39; }
	"$KP/run/freeze_k.sh" verify || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_k.sh)"; exit 20; }
	case "$st" in
	k-pb)
		if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$PY $KP/score/score_k.py gate $st $ROOTS"
		else
			# shellcheck disable=SC2086
			"$PY" "$KP/score/score_k.py" gate "$st" $ROOTS > "$ROOT/gate-$st.txt" 2>&1; g=$?
			cat "$ROOT/gate-$st.txt"
			if [ "$g" != 0 ]; then
				echo "SKIPPED: $st (the gate is closed: the controls of k-pb0 failed; the poke rows are not run unpoked-controlled)"
				SKIPPED="$SKIPPED $st"; return 0
			fi
		fi ;;
	esac
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-900} ssh $SSHO $T 'K_FAULTS_PRIOR=0 bash ~/r3kpx-run/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:r3kpx-out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $KP/score/score_k.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-900}" ssh $SSHO "$T" "K_FAULTS_PRIOR=0 bash ~/r3kpx-run/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort|exit)|^  class|health:" "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:r3kpx-out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		kn=$(knobs_read | tr '\n' ' ')
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze; 18 = no answer after a BIF write)"
		echo "knobs after the stop (alias_skip, render_rgn_arrays; the runner restores the knob at every exit): ${kn:-unreadable}"
		echo "to continue after the lead's decision: run/k.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying r3kpx-out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$KP/score/score_k.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
	grep '^SUMMARY:' "$ROOT/score-$st.txt" || { echo "STOP: no SUMMARY from the scorer of $st (status $sc)"; exit 38; }
	[ "$sc" = 0 ] || { echo "STOP: the scorer of $st exited $sc"; exit 38; }
	health_after "$st"
	return 0
}

go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -f "$KP/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	run_one "$st"
done
echo "R3K-pixel done${SKIPPED:+ (skipped:$SKIPPED)}: $PY $KP/score/score_k.py verdict $ROOTS"
