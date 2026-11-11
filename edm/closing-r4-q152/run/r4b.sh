#!/bin/bash
# SPDX-License-Identifier: MIT
# r4b.sh [ATTEMPT]: the R4b session driver (stage fr, Q152: a replicate of E817's FCF), run from the Mac.  NOT RUN while it was prepared.
# The laptop directories are ~/r4b (inputs, staged by run/stage_r4b.sh) and ~/r4b-out/ATTEMPT (results); the Mac keeps out/ATTEMPT.
# ATTEMPT defaults to the date and time; an existing attempt directory is refused on either side (nothing is overwritten or deleted).
# Order: freeze verify; the laptop's LAPTOP.sha256 compared with this freeze's; the LOAD step (after a fresh boot the firmware is loaded by
# a health fill and triangle: both must print diff: 0, and the knobs must read their defaults); one ssh runs the stage (sudo -n python3 on
# the laptop, bounded by a perl alarm); the stage's files are copied back whatever the status (copy only); the health script again; the
# stage's kernel.log; the scorer, which prints the SUMMARY line.
# Exit: the stage's own code (1 preflight, 3 watchdog, 4 job or exception, 5 reset or gate not exact, 6 no return, 7 a table value outside
# the allow-list, 8 the stage ended by its stop rule: a control stopped, or a stop past the budget), 20 frozen files changed, 21 the laptop's
# LAPTOP.sha256 is not this freeze's, 22 the attempt directory exists, 30-36 health at the load step or after the stage (no answer, fill or
# triangle not diff: 0, FAIL, watchdog, a knob not at its default), 37 copy failed, 38 a hung/recovery/fault line in the kernel.log,
# 41 the scorer failed, 255 or 142 ssh lost or the alarm (a freeze: boot nothing, report).  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R4=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$R/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-s1b
PY=${PY:-$R/.venv/bin/python}
OUTROOT=${R4B_OUT:-$R4/out}
ATT=${1:-$(date +%Y%m%d-%H%M%S)}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
RESET_INFO_RE='\] SGX reset: after the fault clear BIF_FAULT 0x[0-9a-f]+ BIF_INT_STAT 0x[0-9a-f]+$'
LD=r4b
st=fr
OUT=$OUTROOT/$ATT
ALARM=720
"$R4/run/freeze_r4b.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
RUNNER="sudo -n python3 ~/$LD/run/r4b_run.py $st --tool ~/$TOOL --bins ~/$LD/bins --out ~/$LD-out/$ATT"
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "ssh $SSHO $T 'cat ~/$LD/LAPTOP.sha256'   (compared with LAPTOP.sha256)"
	echo "ssh $SSHO $T 'bash ~/$LD/run/health_remote.sh $TOOL' > $OUT/health-load.txt   (the load step)"
	echo "ssh $SSHO $T '$RUNNER' > $OUT/$st.log"
	echo "scp -r $SSHO $T:$LD-out/$ATT/$st $OUT/   (copy only)"
	echo "ssh $SSHO $T 'bash ~/$LD/run/health_remote.sh $TOOL' > $OUT/health-$st.txt"
	echo "$PY $R4/score/score_r4b.py $st $OUT/$st > $OUT/score-$st.txt"
	exit 0
fi
[ -e "$OUT" ] && { echo "STOP: $OUT exists (an attempt is never overwritten): give another ATTEMPT"; exit 22; }
mkdir -p "$OUT"
echo "#### r4b attempt $ATT $(date +%T)"
# shellcheck disable=SC2086
rl=$(perl -e 'alarm 60; exec @ARGV' ssh $SSHO "$T" "cat ~/$LD/LAPTOP.sha256; test ! -e ~/$LD-out/$ATT || echo ATTEMPT-EXISTS")
src=$?
[ $src -eq 0 ] || { echo "STOP: cannot read ~/$LD/LAPTOP.sha256 on the laptop (status $src)"; exit 21; }
case "$rl" in *ATTEMPT-EXISTS*) echo "STOP: ~/$LD-out/$ATT exists on the laptop"; exit 22 ;; esac
[ "$rl" = "$(cat "$R4/LAPTOP.sha256")" ] || { echo "STOP: the laptop's LAPTOP.sha256 is not this freeze's: run run/stage_r4b.sh"; exit 21; }
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
}
# the LOAD step: after a fresh boot the firmware is not loaded until a client job (attempt1-nofw of R3k: ENODEV); a fill and a triangle load it
health load
# shellcheck disable=SC2086
perl -e 'alarm shift; exec @ARGV' "$ALARM" ssh $SSHO "$T" "$RUNNER" > "$OUT/$st.log" 2>&1
rc=$?
grep -E '^## (STOP|preflight|arm|end|stop)|^== ' "$OUT/$st.log" | tail -14
# shellcheck disable=SC2086
perl -e 'alarm 180; exec @ARGV' scp -q -r $SSHO "$T:$LD-out/$ATT/$st" "$OUT/" > "$OUT/scp-$st.log" 2>&1
src=$?
if [ $rc -ne 0 ] && [ $rc -ne 8 ]; then
	echo "STOP: stage $st exited $rc (see $OUT/$st.log; 255 or 142 = ssh lost or the alarm: a freeze, boot nothing)"
	exit $rc
fi
if [ $src -ne 0 ]; then echo "STOP: copying $LD-out/$ATT/$st failed (scp status $src)"; exit 37; fi
health "$st"
KL=$OUT/$st/kernel.log
[ -s "$KL" ] || { echo "STOP: no kernel.log kept for $st"; exit 38; }
if grep -Eq "$FATAL_RE" "$KL"; then echo "STOP: a watchdog/BUG line in $st's kernel.log"; exit 33; fi
if grep -v 'resgx545 r4b ' "$KL" | grep -vE "$RESET_INFO_RE" | grep -Eiq '\b(hung|recovering)\b|BIF fault|page fault'; then
	echo "STOP: a hung, recovery or fault line in $st's kernel.log"; exit 38
fi
"$PY" "$R4/score/score_r4b.py" "$st" "$OUT/$st" > "$OUT/score-$st.txt" 2>&1
grc=$?
grep -E '^SUMMARY' "$OUT/score-$st.txt"
[ $grc -eq 0 ] || { echo "STOP: the scorer failed (status $grc)"; exit 41; }
if [ $rc -eq 8 ]; then
	echo "STOP (by its rule): stage $st ended early (a control stopped, or a stop past the budget); reset and gate exact, health fine, scored."
	exit 8
fi
echo "R4b $ATT done"
