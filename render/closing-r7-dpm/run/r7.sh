#!/bin/bash
# SPDX-License-Identifier: MIT
# r7.sh [--from STAGE | --only STAGE... | --cell STAGE JOB] : the R7-dpm session driver, run from the Mac (R6-dpm's r6.sh).
# NOT RUN while it was prepared.  R7_SET=A (default) runs set A (stages.txt: s-a0, s-m, s-b, s-v) on the test module 41E2F5C7;
# R7_SET=B runs set B (stagesB.txt: s-k) after the lead's one-shot boot of module 37EC97AB.  Each set verifies its own freeze.
#
# For each stage of the set: verify the set's frozen files, run the laptop-side stage runner over
# ssh (~/scratch/r7d/run/run/run_stage.sh), copy the stage's kept files to out/STAGE/ (copy only), the health script (tools/bringup/health.sh with
# the rgn4 tool) and its checks, then the frozen scorer (its SUMMARY line; the scorer never gates the run).  Stops on any non-zero stage,
# health failure, freeze (ssh does not answer) or watchdog.  The lead runs it; no wait loops; every ssh and scp bounded by a perl alarm:
# STAGE_ALARM (2400 s) a stage (s-m: 50 jobs), SSH_ALARM (150 s) health, a knob read and each copy.
# Stage exit codes (run_stage.sh): 0 done, 1 preflight, 3 kernel watchdog/BUG, 4 hang/fault/failure, 5 failed recovery, 6 freeze, 7 forbidden
# knob, 8 missing program, 9 knob read-back, 10 a premise or control failed or had no reading (s-a0: set A stops before s-m; s-k's k-b6:
# set B stops), 11 a second EDM stall in s-k, 12 the own task could not be armed, 13 a capture not whole or the work filesystem short.  r7.sh adds 20 (frozen files changed), 22 (the attempt's stage directory exists), 23 (a kept file the scorer
# reads is missing: sessioncheck.py kept against score_r7.py's REQUIRED, over the rows that ran), 30-37 (health: no answer, fill or triangle not exact,
# FAIL, watchdog, render_pb_pages not 0x422, hold_recovery not N, alias_skip not 0, the copy failed).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R7=$(dirname "$HERE")
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
SET=${R7_SET:-A}
case "$SET" in A) ALL=$(tr '\n' ' ' < "$R7/stages.txt") ;; B) ALL=$(tr '\n' ' ' < "$R7/stagesB.txt") ;; *) echo "R7_SET is A or B"; exit 2 ;; esac
FROM=""; ONLY=""; CELL=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
if [ "${1:-}" = "--cell" ]; then ONLY=${2:?stage}; CELL=${3:?job}; fi
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
# ATTEMPT (R7_ATTEMPT, default a1 for set A and b1 for set B): every attempt keeps its files in out/ATTEMPT and laptop
# ~/scratch/r7d/out/ATTEMPT (state included), and an existing stage directory is never overwritten (rc 22)
if [ "$SET" = A ]; then ATT=${R7_ATTEMPT:-a1}; else ATT=${R7_ATTEMPT:-b1}; fi
OUT=$R7/out/$ATT
mkdir -p "$OUT"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ -n "$ONLY" ] && go=1
	[ $go = 1 ] || continue
	[ -f "$R7/tables/$st.txt" ] || { echo "STOP: no tables/$st.txt"; exit 20; }
	envp=""; [ -n "$CELL" ] && envp="ONLY=$CELL "
	log=$st; [ -n "$CELL" ] && log="$st-cell-$CELL"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "$R7/run/freeze_r7.sh verify $SET"
		echo "bounded ${STAGE_ALARM:-2400} ssh $SSHO $T '${envp}OUTROOT=\$HOME/scratch/r7d/out/$ATT bash ~/scratch/r7d/run/run/run_stage.sh $st' > $OUT/$log.log"
		echo "bounded ${SSH_ALARM:-150} scp -r $T:scratch/r7d/out/$ATT/$st $OUT/   (copy only)"
		echo "$PY $R7/run/sessioncheck.py kept $R7/score/score_r7.py $st $OUT/$st --rows $OUT/$st.rows"
		echo "bounded ${SSH_ALARM:-150} $BRINGUP/health.sh $TOOL"
		echo "$PY $R7/score/score_r7.py $st $OUT/$st"
		continue
	fi
	[ -e "$OUT/$st" ] && [ -z "$CELL" ] && { echo "STOP: $OUT/$st exists (attempt $ATT): nothing is overwritten; set R7_ATTEMPT"; exit 22; }
	"$R7/run/freeze_r7.sh" verify "$SET"
	vrc=$?
	[ $vrc -eq 0 ] || { echo "FROZEN FILES CHANGED (status $vrc): stop"; exit 20; }
	echo "#### $st $(date +%T)"
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-2400}" ssh $SSHO "$T" "${envp}OUTROOT=\$HOME/scratch/r7d/out/$ATT bash ~/scratch/r7d/run/run/run_stage.sh $st" > "$OUT/$log.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort)|^  class|health:|calibration|scene |EDM stall" "$OUT/$log.log" | tail -8
	# copy the kept files whatever the status; nothing is deleted on either side
	# shellcheck disable=SC2086
	bounded "${SSH_ALARM:-150}" scp -q -r $SSHO "$T:scratch/r7d/out/$ATT/$st" "$OUT/" > "$OUT/scp-$log.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then echo "STOP: stage $st exited $rc (see out/$log.log; 255 = ssh lost, 142 = alarm: a freeze)"; exit $rc; fi
	if [ $src -ne 0 ]; then echo "STOP: copying scratch/r7d/out/$ATT/$st failed (scp status $src, see out/scp-$log.log)"; exit 37; fi
	# every file the scorer reads is kept, for every row that ran (round 6's design-out; HACKING "Session build rules")
	awk -F'\t' 'NR > 1 && $10 == "ok" {print $1}' "$OUT/$st/cases.tsv" > "$OUT/$st.rows" 2>/dev/null
	R7_SCORE_NOFREEZE=1 "$PY" "$R7/run/sessioncheck.py" kept "$R7/score/score_r7.py" "$st" "$OUT/$st" --rows "$OUT/$st.rows" \
		|| { echo "STOP: a file the scorer reads is not kept in $OUT/$st"; exit 23; }
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
	[ -n "$CELL" ] || "$PY" "$R7/score/score_r7.py" "$st" "$OUT/$st" --out "$OUT" 2>&1 | grep -E '^SUMMARY' || echo "(scorer printed no SUMMARY for $st)"
	echo "stage $st done, health ok"
done
echo "R7-dpm set $SET done"
