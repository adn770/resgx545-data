#!/bin/bash
# SPDX-License-Identifier: MIT
# p.sh [ATTEMPT] [--from STAGE]: the driver of r6-held part P (one stage, p1: Q111's CR_DPM_TASK_STATE read at E855's lockup stop on the
# new kernel), run from the Mac.  NOT RUN while it was prepared.  R5-events' driver (closing5/r5-events/run/r5e.sh) with round 6's laptop
# files: the staged tree ~/scratch/r6h/p/stage (run/stage_p.sh), the results ~/scratch/r6h/p/out/ATTEMPT, the runner's work directories
# under ~/scratch/tmp (one mktemp -d r6hp.XXXXXX a job, removed once kept; never /tmp), and a free-space check on ~ (at least 300 MiB)
# before the load step and the stage.  The Mac keeps out/ATTEMPT.  ATTEMPT defaults to the date and time; an existing attempt directory is
# refused on either side (nothing is overwritten or deleted) unless --from names the stage to resume with.
# Order: freeze verify; the laptop's LAPTOP.sha256 compared with this freeze's; the free space; the LOAD step (a health fill and triangle
# load the firmware after a boot: both must print diff: 0, the knobs must read their defaults, the peek must print one `reg 0x0694` line);
# then the stage: one ssh runs it (sudo -n python3 on the laptop, bounded by a perl alarm here), its files are copied back whatever the
# status (copy only), the health script, the stage's kernel.log, the scorer, which prints the SUMMARY line.  Any stop, a failed health or
# a lost ssh ends the session; a stage that its stop rule ended (exit 8) is reset and healthy and is scored, and the session ends: the
# lead decides.
# Exit: the stage's own code (1 preflight, 3 watchdog, 4 job or exception, 5 reset or gate not exact, 6 no return, 7 a table value outside
# the allow-list, 8 the stage ended by its stop rule, 9 the clock did not come back, 21 less than 300 MiB free on ~), 20 frozen files
# changed, 21 the laptop's LAPTOP.sha256 is not this freeze's or too little free space, 22 the attempt directory exists, 30-36 health at
# the load step or after the stage (no answer, fill or triangle not diff: 0, FAIL, watchdog, a knob not at its default, no peek line),
# 37 copy failed, 38 a fault line in the kernel.log, 40 a gate closed, 41 the scorer refused or failed, 255 or 142 ssh lost or the alarm
# (a freeze: boot nothing, report).  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R5=$(dirname "$HERE")
R=${RESGX545:-/Users/jtorra/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$HOME/src/resgx545/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-s1b
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
OUTROOT=${R3_OUT:-$R5/out}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
RESET_INFO_RE='\] SGX reset: after the fault clear BIF_FAULT 0x[0-9a-f]+ BIF_INT_STAT 0x[0-9a-f]+$'
LD=scratch/r6h/p/stage
OD=scratch/r6h/p/out
WK=scratch/tmp
MIN_FREE_MB=300
ATT=""; FROM=""
if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then ATT=$1; shift; fi
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
[ -n "$ATT" ] || ATT=$(date +%Y%m%d-%H%M%S)
ALL=$(awk '{print $1}' "$R5/stages.txt" | tr '\n' ' ')
alarm_of() { awk -v s="$1" '$1 == s {print $2}' "$R5/stages.txt"; }
OUT=$OUTROOT/$ATT
"$R5/run/freeze_p.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "ssh $SSHO $T 'cat ~/$LD/LAPTOP.sha256'   (compared with LAPTOP.sha256)"
	echo "ssh $SSHO $T 'df -Pk ~ | tail -1'   (at least $MIN_FREE_MB MiB free)"
	echo "ssh $SSHO $T 'bash ~/$LD/run/health_remote.sh $TOOL' > $OUT/health-load.txt   (the load step)"
	for st in $ALL; do
		echo "$PY $R5/score/score_p.py gate $st $OUT"
		echo "ssh $SSHO $T 'sudo -n python3 ~/$LD/run/r6hp_run.py $st --tool ~/$TOOL --bins ~/$LD/bins --out ~/$OD/$ATT --work ~/$WK' > $OUT/$st.log"
		echo "scp -r $SSHO $T:$OD/$ATT/$st $OUT/   (copy only)"
		echo "ssh $SSHO $T 'bash ~/$LD/run/health_remote.sh $TOOL' > $OUT/health-$st.txt"
		echo "$PY $R5/score/score_p.py $st $OUT/$st > $OUT/score-$st.txt"
	done
	exit 0
fi
if [ -z "$FROM" ]; then
	[ -e "$OUT" ] && { echo "STOP: $OUT exists (an attempt is never overwritten): give another ATTEMPT, or --from STAGE to resume"; exit 22; }
else
	[ -d "$OUT" ] || { echo "STOP: --from needs the attempt directory $OUT"; exit 22; }
fi
mkdir -p "$OUT"
echo "#### r6hp attempt $ATT $(date +%T)"
# shellcheck disable=SC2086
rl=$(perl -e 'alarm 60; exec @ARGV' ssh $SSHO "$T" "cat ~/$LD/LAPTOP.sha256")
src=$?
[ $src -eq 0 ] || { echo "STOP: cannot read ~/$LD/LAPTOP.sha256 on the laptop (status $src)"; exit 21; }
[ "$rl" = "$(cat "$R5/LAPTOP.sha256")" ] || { echo "STOP: the laptop's LAPTOP.sha256 is not this freeze's: run run/stage_p.sh"; exit 21; }
health() {      # health TAG: the fill and the triangle through the pinned tool, the knobs; exit codes 30-36
	local tag=$1 f="$OUT/health-$1.txt" hrc n
	# shellcheck disable=SC2086
	perl -e 'alarm 150; exec @ARGV' ssh $SSHO "$T" "bash ~/$LD/run/health_remote.sh $TOOL" > "$f" 2>&1
	hrc=$?
	cat "$f"
	[ $hrc -eq 0 ] || { echo "STOP: health ($tag) exited $hrc (no answer = freeze)"; exit 30; }
	n=$(grep -c '^diff: 0' "$f")
	[ "$n" -ge 2 ] || { echo "STOP: health ($tag): the fill and the triangle did not both print diff: 0"; exit 31; }
	if grep -q 'FAIL' "$f"; then echo "STOP: health ($tag): FAIL"; exit 32; fi
	if grep -Eq "$FATAL_RE" "$f"; then echo "STOP: kernel watchdog/BUG in the health tail ($tag)"; exit 33; fi
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$f" || { echo "STOP: render_pb_pages is not 0x422 ($tag)"; exit 34; }
	grep -q 'hold_recovery=N' "$f" || { echo "STOP: hold_recovery is not N ($tag)"; exit 35; }
	grep -Eq 'render_rgn_arrays=0x0*0( |$)' "$f" || { echo "STOP: render_rgn_arrays is not 0, the new default ($tag)"; exit 36; }
	grep -q 'kick_no_bump=N' "$f" || { echo "STOP: kick_no_bump is not N ($tag)"; exit 36; }
	grep -Eq 'render_tail_room=0x0*0( |$)' "$f" || { echo "STOP: render_tail_room is not 0, the default ($tag)"; exit 36; }
	grep -Eq '^peek: reg 0x0694 0x[0-9a-f]{8}$' "$f" || { echo "STOP: the peek did not print one reg 0x0694 line ($tag)"; exit 36; }
	grep -Eq 'timer_clock=0x0*0( |$)' "$f" || { echo "STOP: timer_clock is not 0 ($tag): the firmware's next boot would run at another clock"; exit 36; }
}
# free space on ~ (KiB, df -P): at least MIN_FREE_MB, before the load step and the stage
space() {
	local kb
	# shellcheck disable=SC2086
	kb=$(perl -e 'alarm 60; exec @ARGV' ssh $SSHO "$T" "df -Pk ~ | tail -1" | awk '{print $4}')
	echo "free on ~: ${kb:-unread} KiB ($1)"
	[ -n "$kb" ] && [ "$kb" -ge $((MIN_FREE_MB * 1024)) ] || { echo "STOP: less than $MIN_FREE_MB MiB free on ~ ($1)"; exit 21; }
}
space load
# the LOAD step: after a boot the firmware is not loaded until a client job (R3k's attempt1-nofw: ENODEV); a fill and a triangle load it
[ -z "$FROM" ] && health load
go=0; [ -z "$FROM" ] && go=1
for st in $ALL; do
	[ "$st" = "$FROM" ] && go=1
	[ $go = 1 ] || continue
	"$R5/run/freeze_p.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
	echo "#### $st $(date +%T)"
	space "$st"
	"$PY" "$R5/score/score_p.py" gate "$st" "$OUT" || { echo "STOP: the gate of $st is closed"; exit 40; }
	RUNNER="sudo -n python3 ~/$LD/run/r6hp_run.py $st --tool ~/$TOOL --bins ~/$LD/bins --out ~/$OD/$ATT --work ~/$WK"
	# shellcheck disable=SC2086
	perl -e 'alarm shift; exec @ARGV' "$(alarm_of "$st")" ssh $SSHO "$T" "$RUNNER" > "$OUT/$st.log" 2>&1
	rc=$?
	grep -E '^## (STOP|preflight|arm|end|stop)|^== ' "$OUT/$st.log" | tail -14
	# copy the kept files whatever the status; nothing is deleted on either side
	# shellcheck disable=SC2086
	perl -e 'alarm 180; exec @ARGV' scp -q -r $SSHO "$T:$OD/$ATT/$st" "$OUT/" > "$OUT/scp-$st.log" 2>&1
	cprc=$?
	if [ $rc -ne 0 ] && [ $rc -ne 8 ]; then
		echo "STOP: stage $st exited $rc (see $OUT/$st.log; 255 or 142 = ssh lost or the alarm: a freeze, boot nothing)"
		exit $rc
	fi
	if [ $cprc -ne 0 ]; then echo "STOP: copying $OD/$ATT/$st failed (scp status $cprc)"; exit 37; fi
	health "$st"
	KL=$OUT/$st/kernel.log
	[ -s "$KL" ] || { echo "STOP: no kernel.log kept for $st"; exit 38; }
	if grep -Eq "$FATAL_RE" "$KL"; then echo "STOP: a watchdog/BUG line in $st's kernel.log"; exit 33; fi
	# the B1P / B1E jobs of every stage are held on purpose (hung / recovering lines are the design): only BIF-fault and page-fault
	# lines stop it
	BADRE='BIF fault|page fault'
	if grep -v 'resgx545 r6hp ' "$KL" | grep -vE "$RESET_INFO_RE" | grep -Eiq "$BADRE"; then
		echo "STOP: a hung, recovery or fault line in $st's kernel.log"; exit 38
	fi
	"$PY" "$R5/score/score_p.py" "$st" "$OUT/$st" > "$OUT/score-$st.txt" 2>&1
	grc=$?
	grep -E '^(SUMMARY|REFUSING)' "$OUT/score-$st.txt"
	if grep -q '^REFUSING' "$OUT/score-$st.txt"; then echo "STOP: the scorer refused"; exit 41; fi
	if [ $grc -ne 0 ]; then echo "STOP: the scorer failed on $st (status $grc)"; exit 41; fi
	if [ $rc -eq 8 ]; then
		echo "STOP: stage $st was ended by its stop rule (a control stopped, an unexplained stop, or the budget): reset and gate are"
		echo "      exact, health is fine, the stage is scored.  R5-4 (a): such a stop ends the session; the lead decides"
		echo "      (run/p.sh $ATT --from NEXT-STAGE resumes; its gate accepts exit 8).  $(grep -o 'timer_clock=[^ ]*' "$OUT/health-$st.txt")"
		exit 8
	fi
	echo "stage $st done, health ok"
done
echo "timer_clock at the end: $(grep -o 'timer_clock=[^ ]*' "$OUT/health-$st.txt") (the knob each stage's clock_back read back: \
$(grep -ho '"knob": "[^"]*"' "$OUT"/*/clock-back.json | tr '\n' ' '))"
echo "R6hp $ATT done (r6-held part P)"
