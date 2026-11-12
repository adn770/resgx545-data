#!/bin/bash
# SPDX-License-Identifier: MIT
# r6.sh [--from STAGE | --only STAGE... | --cell STAGE JOB] : the R6-dpm session driver, run from the Mac.  Built from R3-geo's r3.sh.
# NOT RUN while it was prepared.
#
# For each stage of stages.txt (r-a0, r-m, r-n, r-v, r-b, r-k): verify the frozen files, run the laptop-side stage runner over
# ssh (~/scratch/r6d/run/run/run_stage.sh), copy the stage's kept files to out/STAGE/ (copy only), the health script (tools/bringup/health.sh with
# the rgn4 tool) and its checks, then the frozen scorer (its SUMMARY line; the scorer never gates the run).  Stops on any non-zero stage,
# health failure, freeze (ssh does not answer) or watchdog.  The lead runs it; no wait loops; every ssh and scp bounded by a perl alarm:
# STAGE_ALARM (2400 s) a stage (r-b: 40 jobs), SSH_ALARM (150 s) health, a knob read and each copy.
# Stage exit codes (run_stage.sh): 0 done, 1 preflight, 3 kernel watchdog/BUG, 4 hang/fault/failure, 5 failed recovery, 6 freeze, 7 forbidden
# knob, 8 missing program, 9 knob read-back, 10 a premise or control failed (r-a0: the session stops before r-m), 11 a second EDM stall in
# r-k, 12 the own task could not be armed, 13 a capture not whole or the work filesystem short.  r6.sh adds 20 (frozen files changed), 22 (the attempt's stage directory exists), 30-37 (health: no answer, fill or triangle not exact,
# FAIL, watchdog, render_pb_pages not 0x422, hold_recovery not N, alias_skip not 0, the copy failed).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R6=$(dirname "$HERE")
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
BRINGUP=${RESGX545_BRINGUP:-$MAIN/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
export SGX_LOCAL_ENV="$LOCAL_ENV"
. "$HERE/lib_check.sh"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-rgn4
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$R6/stages.txt")
FROM=""; ONLY=""; CELL=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
if [ "${1:-}" = "--cell" ]; then ONLY=${2:?stage}; CELL=${3:?job}; fi
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
# ATTEMPT (R6_ATTEMPT, default a2 since freeze 2; a1 ran r-a0 only and stopped on the runner slip): every attempt keeps its files in out/ATTEMPT and laptop ~/scratch/r6d/out/ATTEMPT (state included),
# and an existing stage directory is never overwritten (rc 22)
ATT=${R6_ATTEMPT:-a2}
OUT=$R6/out/$ATT
mkdir -p "$OUT"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -f "$R6/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	envp=""; [ -n "$CELL" ] && envp="ONLY=$CELL "
	log=$st; [ -n "$CELL" ] && log="$st-cell-$CELL"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "$R6/run/freeze_r6.sh verify"
		echo "bounded ${STAGE_ALARM:-2400} ssh $SSHO $T '${envp}OUTROOT=\$HOME/scratch/r6d/out/$ATT bash ~/scratch/r6d/run/run/run_stage.sh $st' > $OUT/$log.log"
		echo "bounded ${SSH_ALARM:-150} scp -r $T:scratch/r6d/out/$ATT/$st $OUT/   (copy only)"
		echo "bounded ${SSH_ALARM:-150} $BRINGUP/health.sh $TOOL"
		echo "$PY $R6/score/score_r6.py $st $OUT/$st"
		continue
	fi
	[ -e "$OUT/$st" ] && [ -z "$CELL" ] && { echo "STOP: $OUT/$st exists (attempt $ATT): nothing is overwritten; set R6_ATTEMPT"; exit 22; }
	"$R6/run/freeze_r6.sh" verify
	vrc=$?
	[ $vrc -eq 0 ] || { echo "FROZEN FILES CHANGED (status $vrc): stop"; exit 20; }
	echo "#### $st $(date +%T)"
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-2400}" ssh $SSHO "$T" "${envp}OUTROOT=\$HOME/scratch/r6d/out/$ATT bash ~/scratch/r6d/run/run/run_stage.sh $st" > "$OUT/$log.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:|calibration|scene |EDM stall" "$OUT/$log.log" | tail -8
	# copy the kept files whatever the status; nothing is deleted on either side
	# shellcheck disable=SC2086
	bounded "${SSH_ALARM:-150}" scp -q -r $SSHO "$T:scratch/r6d/out/$ATT/$st" "$OUT/" > "$OUT/scp-$log.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then echo "STOP: stage $st exited $rc (see out/$log.log; 255 = ssh lost, 142 = alarm: a freeze)"; exit $rc; fi
	if [ $src -ne 0 ]; then echo "STOP: copying scratch/r6d/out/$ATT/$st failed (scp status $src, see out/scp-$log.log)"; exit 37; fi
	bounded "${SSH_ALARM:-150}" "$BRINGUP/health.sh" "$TOOL" > "$OUT/health-$log.txt" 2>&1
	hrc=$?
	cat "$OUT/health-$log.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health.sh exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$OUT/health-$log.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	grep -q 'FAIL' "$OUT/health-$log.txt" && { echo "STOP: health after $st: FAIL"; exit 32; }
	grep -Eq "$FATAL_RE" "$OUT/health-$log.txt" && { echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; }
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$OUT/health-$log.txt" || { echo "STOP: render_pb_pages not back at 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$OUT/health-$log.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# shellcheck disable=SC2086
	am=$(bounded "${SSH_ALARM:-150}" ssh $SSHO "$T" 'sudo -n sh -c "cat \$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1)/alias_skip"' 2>&1)
	arc=$?
	[ $arc -eq 0 ] || { echo "STOP: reading alias_skip after $st failed (status $arc)"; exit 36; }
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st (not numerically 0)"; exit 36; }
	[ -n "$CELL" ] || "$PY" "$R6/score/score_r6.py" "$st" "$OUT/$st" --out "$OUT" 2>&1 | grep -E '^SUMMARY' || echo "(scorer printed no SUMMARY for $st)"
	echo "stage $st done, health ok"
done
echo "R6-dpm done"
