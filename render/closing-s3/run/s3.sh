#!/bin/bash
# SPDX-License-Identifier: MIT
# s3.sh [--from STAGE] [--only STAGE...] : the S3 session driver, run from the Mac.  NOT RUN while it was prepared.
#
# For each stage of stages.txt (s3-a-safe, s3-e1-ctl, s3-e1, s3-a-fault, s3-xfer): verify the frozen files; the
# GATE (score/score_s3.py gate: s3-e1 and s3-xfer run only if the E444 controls passed, s3-a-fault only if the
# a4 control and the E444 controls passed); the runner gets the sha256 of this side's FROZEN.sha256 (it
# refuses a laptop copy that differs) and the attempt name (exit 39 here: the stage's directory exists); the laptop-side runner over ssh (run_stage.sh); copy the stage's kept files to
# out/STAGE/ (copy only); score the stage (out/score-STAGE.txt, one SUMMARY line); the health script
# (tools/bringup/health.sh) and its checks.  Every ssh and scp is bounded (perl alarm: STAGE_ALARM, default
# 900 s a stage; 300 s a copy; 150 s the health; 60 s a knob read).
# Host and ssh options as the bringup scripts: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).
# SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call between stages.
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed
# health recovery, 6 freeze, 7 forbidden knob, 8 missing program, 9/11 hold_recovery read-back, 10 a held fault
# that did not clear, 12 registers unreadable; 142 the alarm: the laptop did not answer in time, a freeze),
# 20 frozen files changed, 30-37 health after a stage (no answer, the fill or triangle not exact, FAIL,
# watchdog, render_pb_pages, hold_recovery, alias_skip, scp), 38 the scorer did not run, 40 a gate is closed.
# Any of them stops the session; the recovery plan for 10 and 142 is in PREFLIGHT.md (nothing more is done).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S3=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-s1
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$S3/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
# one directory an attempt, on both sides: out/ATT/STAGE here, ~/s3-out/ATT/STAGE on the laptop; a stage
# directory that exists is never written again (exit 39).  S3_ATT names the attempt (default: the clock);
# S3_PRIOR_ROOTS lists earlier attempts' out/ATT directories the gates and the verdict may read
# (e.g. after --from in a new attempt).
ATT=${S3_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$S3/out/$ATT
ROOTS="$ROOT ${S3_PRIOR_ROOTS:-}"
FSHA=$(shasum -a 256 "$S3/FROZEN.sha256" | cut -d' ' -f1)
mkdir -p "$ROOT"
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (S3_ATT) for a rerun"; exit 39; }
	"$S3/run/freeze_s3.sh" verify || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
	if [ "$st" = s3-e1 ] || [ "$st" = s3-a-fault ] || [ "$st" = s3-xfer ]; then
		if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$PY $S3/score/score_s3.py gate $st $ROOTS"
		else
			# shellcheck disable=SC2086
			"$PY" "$S3/score/score_s3.py" gate "$st" $ROOTS > "$ROOT/gate-$st.txt" 2>&1; g=$?
			cat "$ROOT/gate-$st.txt"
			[ "$g" = 0 ] || { echo "STOP: the gate of $st is closed (status $g): its prerequisites failed"; exit 40; }
		fi
	fi
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-900} ssh $SSHO $T 'bash ~/s3/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:s3-out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $S3/score/score_s3.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		continue
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-900}" ssh $SSHO "$T" "bash ~/s3/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:" "$ROOT/$st.log"
	# copy the kept files whatever the status (analysis needs them; runner.log has the whole output even
	# if ssh dropped); nothing is deleted on either side
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:s3-out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"; exit $rc; fi
	if [ $src -ne 0 ]; then echo "STOP: copying s3-out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$S3/score/score_s3.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
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
	# shellcheck disable=SC2086
	am=$(bounded 60 ssh $SSHO "$T" 'sudo -n cat /sys/kernel/debug/dri/0/sgx/alias_skip' 2>&1)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	echo "stage $st done, health ok"
done
echo "S3 done: $PY $S3/score/score_s3.py verdict $ROOTS"
