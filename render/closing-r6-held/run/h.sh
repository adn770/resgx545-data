#!/bin/bash
# SPDX-License-Identifier: MIT
# h.sh [--from STAGE] [--only STAGE...]: the r6-held part H session driver, run from the Mac.  NOT RUN while it was prepared.  The new
# kernel (fork r6-kernel 3f0b3e74, srcversion 41E2F5C756F96D20F7109A4) with ~/sgxfive-test-rgn4.  From r6-render4x's k.sh (R4-G's,
# round 5's), one freeze (FROZEN.sha256), laptop directories ~/scratch/r6h/{run,out}.
#
# For each stage of stages.txt (s0 q): verify the frozen files; the GATE (score_h.py gate: q runs only if s0's controls passed, read
# from this attempt or the earlier ones; a closed gate skips q CLEANLY with a message) written to out/ATT/gate-q.txt; the laptop-side
# runner over ssh (run/run_h.sh STAGE FROZEN_SHA ATT); copy the stage's kept files to out/ATT/STAGE (copy only); score the stage
# (out/ATT/score-STAGE.txt, SUMMARY lines); the health script (tools/bringup/health.sh) and its checks, which include the knobs
# (hold_recovery N, alias_skip 0, render_pb_pages 0x422, render_rgn_arrays 0).  Every ssh and scp is bounded (perl alarm: STAGE_ALARM or
# the stage's default from stages.txt's second column; 300 s a copy; 150 s the health; 60 s a knob read).  SGX_DRY_RUN=1 prints the
# commands.  No wait loops.
# Exit: the stage runner's status (run/run_h.sh's header: 1 preflight ... 23 bif_flush; 142 the alarm), 20 frozen files changed,
# 30-37 health after a stage, 38 no scorer SUMMARY, 39 the attempt's stage directory exists, 42 a knob not back at its default.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
PY=${PY:-/Users/jtorra/src/resgx545/.venv/bin/python}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-rgn4
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(awk '{print $1}' "$KP/stages.txt" | tr '\n' ' ')
LR=scratch/r6h
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${K_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$KP/out/$ATT
[ -f "$KP/FROZEN.sha256" ] || { echo "not frozen (run/freeze_h.sh freeze)"; exit 20; }
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
knobs_read() { # prints alias_skip, render_rgn_arrays and render_pb_pages on three lines
	# shellcheck disable=SC2086
	bounded 60 ssh $SSHO "$T" 'sudo -n sh -c "d=\$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1); cat \$d/alias_skip; cat \$d/render_rgn_arrays; cat \$d/render_pb_pages"' 2>&1
}

# the health script and its checks after a stage
health_after() {
	local st=$1 hrc n am arc kn rg pbn
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
	[ $arc -eq 0 ] || { echo "STOP: reading alias_skip, render_rgn_arrays and render_pb_pages after $st failed (status $arc): $kn"; exit 36; }
	am=$(echo "$kn" | sed -n 1p); rg=$(echo "$kn" | sed -n 2p); pbn=$(echo "$kn" | sed -n 3p)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	num_eq "$rg" 0 || { echo "STOP: render_rgn_arrays is $rg after $st (not numerically 0: the runner did not put it back; the lead decides)"; exit 42; }
	num_eq "$pbn" 0x422 || { echo "STOP: render_pb_pages is $pbn after $st (not numerically 0x422: the runner did not put it back; the lead decides)"; exit 42; }
	echo "stage $st done, health ok, render_rgn_arrays $rg, render_pb_pages $pbn"
}

# one stage: gate, ssh, copy, score, health.  Returns 0 or exits with the code of the stop.
run_one() {
	local st=$1 g rc src sc kn
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (K_ATT) for a rerun"; exit 39; }
	"$KP/run/freeze_h.sh" verify || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_h.sh)"; exit 20; }
	case "$st" in
	s0) ;;
	*)
		if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$PY $KP/score/score_h.py gate $st $ROOTS"
		else
			# shellcheck disable=SC2086
			"$PY" "$KP/score/score_h.py" gate "$st" $ROOTS > "$ROOT/gate-$st.txt" 2>&1; g=$?
			cat "$ROOT/gate-$st.txt"
			if [ "$g" != 0 ]; then
				echo "SKIPPED: $st (the gate is closed: see gate-$st.txt; for s0 the session is void, the lead decides)"
				SKIPPED="$SKIPPED $st"; return 0
			fi
		fi ;;
	esac
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-$(awk -v s="$st" '$1 == s { print $2 }' "$KP/stages.txt")} ssh $SSHO $T 'bash ~/$LR/run/run/run_h.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:$LR/out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $KP/score/score_h.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-$(awk -v s="$st" '$1 == s { print $2 }' "$KP/stages.txt")}" ssh $SSHO "$T" "bash ~/$LR/run/run/run_h.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort|exit)|^  class|health:" "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:$LR/out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		kn=$(knobs_read | tr '\n' ' ')
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "knobs after the stop (alias_skip, render_rgn_arrays; read only): ${kn:-unreadable}"
		echo "to continue after the lead's decision: run/h.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying $LR/out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$KP/score/score_h.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
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
echo "r6-held part H done${SKIPPED:+ (skipped:$SKIPPED)}: $PY $KP/score/score_h.py verdict $ROOTS"
