#!/bin/bash
# SPDX-License-Identifier: MIT
# r3.sh SESSION [--from STAGE | --only STAGE]: the R3k session driver (SESSION k0 or kev), run from the Mac.  NOT RUN while it was prepared.
# K0 lives on the laptop in ~/r3k0 and ~/r3k0-out, K1 in ~/r3kev and ~/r3kev-out (no collision with ~/r3g*, ~/r3p-*, ~/r3xev, ~/r3xc3).
#
# Order (stages-SESSION.txt, a line `stage alarm-seconds`): k0: k0f k0t k0c k0h; kev: f t kb e2b e3h e3a e3b.  K0 failing stops everything: the
# driver ends at the first K0 stage that exits non-zero, whose scorer reports a failed control (exit 9), or whose health is not exact; kev's
# first gate is K0's last stage (out/k0h/stage.json must say it finished), so K1 refuses to start after a failed K0.
# For each stage: verify the freeze; the gate (score_r3.py gate STAGE OUT: the previous stage's own kept stage.json must say it finished, exit 0,
# or exit 8 after the lead chose to go on with --from; derived from kept output only, so restaging and resuming never close a gate); the
# laptop's LAPTOP.sha256 compared byte for byte with this freeze's; one ssh runs the stage (sudo -n python3 on the laptop, bounded by a perl
# alarm here); the stage's files are copied back whatever the status (copy only); the health script; the scorer, which prints the SUMMARY line.
# Any stop, a failed health or a lost ssh ends the session; a stage that its stop budget ended (exit 8) is reset and healthy and is scored,
# and the session still ends: the lead decides whether to go on (`--from NEXT`).
# Exit: the stage's own code (1 preflight, 3 watchdog, 4 job or exception, 5 reset or gate not exact, 6 no return, 7 a table value outside the
# allow-list, 8 stop budget), 9 a K0 control failed, 20 frozen files changed, 21 the laptop's LAPTOP.sha256 is not this freeze's, 30-35 health
# after a stage (no answer, fill or triangle not exact, FAIL, watchdog in the tail, render_pb_pages or hold_recovery not as they were), 33 also
# a watchdog line in the stage's kernel.log, 37 copy failed, 38 a hung/recovery/fault line in the stage's kernel.log (e3b expects them: its own
# check), 40 a gate closed, 41 the scorer refused or failed, 255 or 142 ssh lost or the alarm (a freeze: boot nothing, report).
# OUT (default out/) is where copies, logs and scores go (the mock tests point it elsewhere).  SGX_DRY_RUN=1 prints the commands.
# No wait loops: one ssh a stage, one health call, one scorer call.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R3=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
BRINGUP=$R/tools/bringup
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=${R3_TOOL_NAME:-sgxfive-test-s1b}
PY=${PY:-$R3/../../closing/pixel-faults/.venv/bin/python}
OUT=${R3_OUT:-$R3/out}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
SESSION=${1:-}
case "$SESSION" in k0) LD=r3k0 ;; kev) LD=r3kev ;; *) echo "usage: r3.sh k0|kev [--from STAGE | --only STAGE]"; exit 2 ;; esac
shift
ALL=$(awk '{print $1}' "$R3/stages-$SESSION.txt" | tr '\n' ' ')
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then ONLY=${2:?stage}; fi
alarm_of() { awk -v s="$1" '$1 == s {print $2}' "$R3/stages-$SESSION.txt"; }
mkdir -p "$OUT"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ $go = 1 ] || continue
	"$R3/run/freeze_r3.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
	echo "#### $st $(date +%T)"
	RUNNER="sudo -n python3 ~/$LD/run/r3_run.py $st --tool ~/$TOOL --bins ~/$LD/bins --out ~/$LD-out"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "$PY $R3/score/score_r3.py gate $st $OUT"
		echo "ssh $SSHO $T '$RUNNER' > $OUT/$st.log"
		echo "scp -r $SSHO $T:$LD-out/$st $OUT/   (copy only)"
		echo "ssh $SSHO $T 'bash ~/$LD/run/health_remote.sh $TOOL'"
		echo "$PY $R3/score/score_r3.py $st $OUT/$st"
		continue
	fi
	"$PY" "$R3/score/score_r3.py" gate "$st" "$OUT" || { echo "STOP: the gate of $st is closed"; exit 40; }
	# the laptop's copies must be the frozen ones of this Mac (LAPTOP-SESSION.sha256 compared byte for byte)
	# shellcheck disable=SC2086
	rl=$(perl -e 'alarm 60; exec @ARGV' ssh $SSHO "$T" "cat ~/$LD/LAPTOP.sha256")
	src=$?
	[ $src -eq 0 ] || { echo "STOP: cannot read ~/$LD/LAPTOP.sha256 on the laptop (status $src)"; exit 21; }
	[ "$rl" = "$(cat "$R3/LAPTOP-$SESSION.sha256")" ] || { echo "STOP: the laptop's LAPTOP.sha256 is not this freeze's: run run/stage_r3.sh $SESSION"; exit 21; }
	# shellcheck disable=SC2086
	perl -e 'alarm shift; exec @ARGV' "${STAGE_ALARM:-$(alarm_of "$st")}" ssh $SSHO "$T" "$RUNNER" > "$OUT/$st.log" 2>&1
	rc=$?
	grep -E '^## (STOP|preflight|arm|end|stop)|^== ' "$OUT/$st.log" | tail -8
	# copy the kept files whatever the status; nothing is deleted on either side
	# shellcheck disable=SC2086
	perl -e 'alarm 180; exec @ARGV' scp -q -r $SSHO "$T:$LD-out/$st" "$OUT/" > "$OUT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ] && [ $rc -ne 8 ]; then
		echo "STOP: stage $st exited $rc (see $OUT/$st.log; 255 or 142 = ssh lost or the alarm: a freeze, boot nothing)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying $LD-out/$st failed (scp status $src)"; exit 37; fi
	# shellcheck disable=SC2086
	perl -e 'alarm 150; exec @ARGV' ssh $SSHO "$T" "bash ~/$LD/run/health_remote.sh $TOOL" > "$OUT/health-$st.txt" 2>&1
	hrc=$?
	cat "$OUT/health-$st.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$OUT/health-$st.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	if grep -q 'FAIL' "$OUT/health-$st.txt"; then echo "STOP: health after $st: FAIL"; exit 32; fi
	if grep -Eq "$FATAL_RE" "$OUT/health-$st.txt"; then echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; fi
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$OUT/health-$st.txt" || { echo "STOP: render_pb_pages is not 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$OUT/health-$st.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# the whole stage's kernel log (journalctl -k, not a per-job slice): a watchdog anywhere stops; a hung or fault line stops (e3b's b1 jobs
	# hold a fault on purpose: for that stage only the BIF-fault and page-fault lines stop, never a hung or recovering line)
	KL=$OUT/$st/kernel.log
	[ -s "$KL" ] || { echo "STOP: no kernel.log kept for $st"; exit 38; }
	if grep -Eq "$FATAL_RE" "$KL"; then echo "STOP: a watchdog/BUG line in $st's kernel.log"; exit 33; fi
	if [ "$st" = e3b ]; then BADRE='BIF fault|page fault'; else BADRE='\b(hung|recovering)\b|BIF fault|page fault'; fi
	if grep -v 'resgx545 r3k ' "$KL" | grep -Eiq "$BADRE"; then
		echo "STOP: a hung, recovery or fault line in $st's kernel.log"; exit 38
	fi
	"$PY" "$R3/score/score_r3.py" "$st" "$OUT/$st" > "$OUT/score-$st.txt" 2>&1
	grc=$?
	grep -E '^(SUMMARY|REFUSING|CONTROL FAILED)' "$OUT/score-$st.txt"
	if grep -q '^REFUSING' "$OUT/score-$st.txt"; then echo "STOP: the scorer refused"; exit 41; fi
	if [ $grc -eq 9 ]; then echo "STOP: a K0 control of $st read differently from its frozen outcome: K0 failing stops everything"; exit 9; fi
	if [ $grc -ne 0 ]; then echo "STOP: the scorer failed on $st (status $grc)"; exit 41; fi
	if [ $rc -eq 8 ]; then
		echo "STOP (by design): stage $st was ended by its stop budget; reset and gate are exact, health is fine, the stage is scored."
		echo "      The lead decides whether to go on: run/r3.sh $SESSION --from NEXT-STAGE (its gate accepts exit 8)."
		exit 8
	fi
	echo "stage $st done, health ok"
done
echo "R3k $SESSION done"
