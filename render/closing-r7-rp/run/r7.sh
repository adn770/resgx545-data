#!/bin/bash
# SPDX-License-Identifier: MIT
# r7.sh TOOL7_SHA256 [--from STAGE] [--only STAGE...]: the r7-rp session driver, run from the Mac.  NOT RUN while it was prepared.
# r6-misc's m.sh with r6-pixel's bridge gates.  For each stage of stages.txt (s0, q287, q291g, q291, p7-rdc, p7-rd, q293, q139, q086):
# verify the frozen files (and the t7 hash, TOOL7.sha256); the laptop-side runner over ssh (~/scratch/r7r/run/run/run_stage.sh; it gets
# the sha256 of this side's FROZEN.sha256, the attempt name and the t7 hash, and refuses a laptop copy that differs); copy the stage's
# kept files from ~/scratch/r7r/out/ATT/STAGE to out/ATT/STAGE (copy only); score it (out/ATT/score-STAGE.txt, one SUMMARY line);
# the health script (tools/bringup/health.sh with the rgn4 tool) and the knobs read back at their defaults; then the stage's GATE
# (`score/score_r7.py gate STAGE KEPT S7`, from the kept files; exit 0 passed, 1 failed, 2 cannot tell):
#   s0      the session gate (t4, t6, t7 draw the default triangle exactly; E831's 34 x 18 depth row stores 924): not 0 -> exit 40
#   q291g   q291's gate row (512 slots as frozen): not 0 -> stage q291 is skipped (Q291 cannot tell), the session goes on (plan rc 24)
#   p7-rdc  R6's bridge controls: not 0 -> stage p7-rd is skipped (Q276 cannot tell), the session goes on
#   others  none (their controls void their own verdicts only)
# The runner's rc 21 (q287 gateodd: odd widths refused, the even-width rows ran) goes on; every other non-zero runner status stops the
# session.  Every ssh and scp is bounded (perl alarm: a stage's alarm below, 300 s a copy, 150 s the health, 60 s a knob read).  Host and
# ssh options: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops.
# Exit: the stage runner's status (see run/run_stage.sh), 20 frozen files changed or no t7 hash, 30-36 health after a stage (no answer,
# not exact, FAIL, watchdog, render_pb_pages, hold_recovery, a knob read), 37 a copy failed, 38 no scorer SUMMARY, 39 the attempt's
# stage directory exists, 40 the s0 gate did not pass, 42 a knob not at its default after a stage.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/r7.env"
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
S7=${1:-}
case "$S7" in ""|-*) echo "usage: r7.sh TOOL7_SHA256 [--from STAGE] [--only STAGE...]"; exit 2 ;; esac
shift
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-rgn4
R=scratch/$PREFIX
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$KP/stages.txt")
alarm_of() { case "$1" in s0|q291g|q293) echo 600 ;; q139|q086) echo 2400 ;; *) echo 1500 ;; esac; }
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${R7_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$KP/out/$ATT
FSHA=$(shasum -a 256 "$KP/FROZEN.sha256" | cut -d' ' -f1)
"$KP/run/freeze_r7.sh" verify "$S7" > /dev/null || { "$KP/run/freeze_r7.sh" verify "$S7"; echo "FROZEN FILES CHANGED or no t7 hash: stop"; exit 20; }
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA; t7 $S7"
SKIP=""

knobs_read() { # alias_skip, render_rgn_arrays, render_pb_pages, hold_recovery, render_tail_room on five lines
	# shellcheck disable=SC2086
	bounded 60 ssh $SSHO "$T" 'sudo -n sh -c "d=\$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1); cat \$d/alias_skip; cat \$d/render_rgn_arrays; cat \$d/render_pb_pages; cat \$d/hold_recovery; cat \$d/render_tail_room"' 2>&1
}
health_after() {
	local st=$1 hrc n am arc kn rg pbn ho tr
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
	[ $arc -eq 0 ] || { echo "STOP: reading the knobs after $st failed (status $arc): $kn"; exit 36; }
	am=$(echo "$kn" | sed -n 1p); rg=$(echo "$kn" | sed -n 2p); pbn=$(echo "$kn" | sed -n 3p); ho=$(echo "$kn" | sed -n 4p); tr=$(echo "$kn" | sed -n 5p)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st"; exit 42; }
	num_eq "$rg" 0 || { echo "STOP: render_rgn_arrays is $rg after $st (the runner puts it back to 0: the lead decides)"; exit 42; }
	num_eq "$pbn" 0x422 || { echo "STOP: render_pb_pages is $pbn after $st (r7-rp writes no such knob: the lead decides)"; exit 42; }
	[ "$ho" = N ] || { echo "STOP: hold_recovery is $ho after $st"; exit 42; }
	num_eq "$tr" 0 || { echo "STOP: render_tail_room is $tr after $st (r7-rp writes no such knob: the lead decides)"; exit 42; }
	echo "stage $st done, health ok, knobs at their defaults"
}

run_one() {
	local st=$1 rc src sc g
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (R7_ATT) for a rerun"; exit 39; }
	"$KP/run/freeze_r7.sh" verify "$S7" > /dev/null || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_r7.sh)"; exit 20; }
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-$(alarm_of "$st")} ssh $SSHO $T 'bash ~/$R/run/run/run_stage.sh $st $FSHA $ATT $S7' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:$R/out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $KP/score/score_r7.py $st $ROOT/$st $S7 > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		echo "$PY $KP/score/score_r7.py gate $st $ROOT/$st $S7"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-$(alarm_of "$st")}" ssh $SSHO "$T" "bash ~/$R/run/run/run_stage.sh $st $FSHA $ATT $S7" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort|exit|gateodd)|^  class|health:" "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:$R/out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ] && [ $rc -ne 21 ]; then
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "knobs after the stop (read only): $(knobs_read | tr '\n' ' ')"
		echo "to continue after the lead's decision: run/r7.sh $S7 --from STAGE (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying $R/out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	[ $rc -eq 21 ] && echo "$st: gateodd, the odd width was refused: the even-width rows ran (scored as such)"
	"$PY" "$KP/score/score_r7.py" "$st" "$ROOT/$st" "$S7" > "$ROOT/score-$st.txt" 2>&1; sc=$?
	grep '^SUMMARY:' "$ROOT/score-$st.txt" || { echo "STOP: no SUMMARY from the scorer of $st (status $sc)"; exit 38; }
	[ "$sc" = 0 ] || { echo "STOP: the scorer of $st exited $sc"; exit 38; }
	health_after "$st"
	"$PY" "$KP/score/score_r7.py" gate "$st" "$ROOT/$st" "$S7" > "$ROOT/gate-$st.txt" 2>&1; g=$?
	cat "$ROOT/gate-$st.txt"
	if [ $g -ne 0 ]; then
		case "$st" in
		s0) echo "STOP: the s0 gate did not pass (exit $g): the tools or the module do not reproduce the precedents; the lead decides"; exit 40 ;;
		q291g) echo "GATE: q291g did not pass (exit $g): stage q291 is skipped (Q291 cannot tell), the session goes on"; SKIP="$SKIP q291" ;;
		p7-rdc) echo "GATE: p7-rdc did not pass (exit $g): stage p7-rd is skipped (Q276 cannot tell), the session goes on"; SKIP="$SKIP p7-rd" ;;
		*) echo "STOP: stage $st has no gate but the gate exited $g"; exit 38 ;;
		esac
	fi
	return 0
}

go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	case " $SKIP " in *" $st "*) echo "#### $st skipped by its gate"; continue ;; esac
	[ -f "$KP/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	run_one "$st"
done
echo "r7-rp done${SKIP:+ (skipped by gates:$SKIP)}: $PY $KP/score/score_r7.py verdict $ROOT $S7"
