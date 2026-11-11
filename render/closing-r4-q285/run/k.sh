#!/bin/bash
# SPDX-License-Identifier: MIT
# k.sh [--from STAGE] [--only STAGE...] : the R4-A session driver (Q285 rerun), run from the Mac.  NOT RUN while it was prepared.  It
# runs on the gma500 module of fork a2788bd8 (srcversion 99CD90DA...) with ~/sgxfive-test-rgn4.  Built from R3K-regress's k.sh.
#
# For each stage of stages.txt (a-pb0, a-pb): verify the frozen files; the GATE (score/score_a.py gate: a-pb runs only if a-pb0's three
# controls passed, computed from the kept a-pb0 directories; else it is skipped CLEANLY with a message); the runner gets the sha256 of
# this side's FROZEN.sha256 and the attempt name; the laptop-side runner over ssh (run_stage.sh); copy the stage's kept files to
# out/ATT/STAGE (copy only); score the stage (out/ATT/score-STAGE.txt, one SUMMARY line); the health script (tools/bringup/health.sh:
# a fill and a triangle) and its checks, which include the knobs: hold_recovery N, alias_skip 0, render_pb_pages 0x422 and
# render_rgn_arrays 0 (the default of fork a2788bd8; the runner writes it 1 only around a row's job).  Every ssh and scp is bounded
# (perl alarm: STAGE_ALARM, default 900 s a stage; 300 s a copy; 150 s the health; 60 s a knob read).  Host and ssh options:
# SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops.
#
# GATES AND ATTEMPTS: there is no gate file on either side.  Gates are computed from the kept stage directories: this attempt's,
# then the earlier attempts' (newest first).  A rerun after a stop is a new attempt (`--from STAGE`).
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health recovery,
# 6 freeze, 7 forbidden knob, 12 registers unreadable, 13 reset failed, 14 fault latched before a job, 19 a knob did not read back;
# 142 the alarm: a freeze), 20 frozen files changed, 30-37 health after a stage, 38 no scorer SUMMARY, 39 the attempt's stage
# directory exists, 42 render_rgn_arrays is not 0 after a stage.
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
	num_eq "$rg" 0 || { echo "STOP: render_rgn_arrays is $rg after $st (not numerically 0: the runner did not put it back; the lead decides)"; exit 42; }
	echo "stage $st done, health ok, render_rgn_arrays $rg"
}

# one stage: gate, ssh, copy, score, health.  Returns 0 or exits with the code of the stop.
run_one() {
	local st=$1 g rc src sc kn
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (K_ATT) for a rerun"; exit 39; }
	"$KP/run/freeze_k.sh" verify || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_k.sh)"; exit 20; }
	case "$st" in
	a-pb)
		if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$PY $KP/score/score_a.py gate $st $ROOTS"
		else
			# shellcheck disable=SC2086
			"$PY" "$KP/score/score_a.py" gate "$st" $ROOTS > "$ROOT/gate-$st.txt" 2>&1; g=$?
			cat "$ROOT/gate-$st.txt"
			if [ "$g" != 0 ]; then
				echo "SKIPPED: $st (the gate is closed: a-pb0's controls did not all pass)"
				SKIPPED="$SKIPPED $st"; return 0
			fi
		fi ;;
	esac
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-900} ssh $SSHO $T 'bash ~/r4a-run/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:r4a-out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $KP/score/score_a.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-900}" ssh $SSHO "$T" "bash ~/r4a-run/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort|exit)|^  class|health:" "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even if ssh dropped)
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:r4a-out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		kn=$(knobs_read | tr '\n' ' ')
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "knobs after the stop (alias_skip, render_rgn_arrays; read only): ${kn:-unreadable}"
		echo "to continue after the lead's decision: run/k.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying r4a-out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$KP/score/score_a.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
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
echo "R4-A done${SKIPPED:+ (skipped:$SKIPPED)}: $PY $KP/score/score_a.py verdict $ROOTS"
