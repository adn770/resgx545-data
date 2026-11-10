#!/bin/bash
# SPDX-License-Identifier: MIT
# r1.sh [--from STAGE | --only STAGE]: the R1-events session driver, run from the Mac.  NOT RUN while it was prepared.
# R1-events lives on the laptop in ~/r1ev and ~/r1ev-out.
#
# Order: k (Q290), t (Q082), d0 (Q033 controls, gate), d1 (Q033, the 4096x4096 jobs).  Only d0 has a gate; k and t need only
# the previous stage's exit 0 and health.
# For each stage: verify the freeze; for d1, the gate file the SCORER wrote for d0 must say OPEN (it is copied to the laptop,
# whose runner refuses the stage without it); one ssh runs the stage (sudo -n python3 on the laptop, bounded by a perl alarm
# here); the stage's files are copied back whatever the status (copy only); the health script; the scorer, which prints the
# SUMMARY line and, for d0, writes GATES/d0.gate and exits 0 only when the gate is open.  Any stop, a failed health, a closed
# gate or a lost ssh ends the session.
# Exit: the stage's own code (1, 3, 4, 5, 6, 7, 9), 20 frozen files changed, 21 the laptop's LAPTOP.sha256 is not this
# freeze's, 30-35 health after a stage (no answer, fill or triangle not exact, FAIL, watchdog in the tail, render_pb_pages or
# hold_recovery not back), 33 also a watchdog line in the stage's kernel.log, 37 copy failed, 38 a hung/recovery/fault line in
# the stage's kernel.log that no job reported (or none kept), 40 a gate closed, 41 the scorer refused or failed, 255 or 142
# ssh lost or the alarm (a freeze: boot nothing, report).  A gated stage's own gate is set to NONE before its ssh.
# OUT (default out/) and GATES (default gates/) are where copies, logs, scores and gate files go (the mock tests point them
# elsewhere).  SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call, one scorer call.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R1=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
BRINGUP=$R/tools/bringup
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=${R1_TOOL_NAME:-sgxfive-test-s1b}
PY=${PY:-$R1/../../closing/pixel-faults/.venv/bin/python}
OUT=${R1_OUT:-$R1/out}
GATES=${R1_GATES:-$R1/gates}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$R1/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then ONLY=${2:?stage}; fi
prev_gate() { case "$1" in d1) echo d0 ;; esac; }
gated() { case "$1" in d0) return 0 ;; esac; return 1; }
alarm_of() { case "$1" in k) echo 600 ;; t) echo 900 ;; d0) echo 300 ;; d1) echo 1500 ;; esac; }
mkdir -p "$OUT" "$GATES"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ $go = 1 ] || continue
	"$R1/run/freeze_r1.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
	pg=$(prev_gate "$st")
	if [ -n "$pg" ]; then
		grep -q "^GATE $pg OPEN" "$GATES/$pg.gate" 2>/dev/null || { echo "GATE $pg is not open: $st does not run"; cat "$GATES/$pg.gate" 2>/dev/null; exit 40; }
	fi
	echo "#### $st $(date +%T)"
	RUNNER="sudo -n python3 ~/r1ev/run/r1_run.py $st --tool ~/$TOOL --rt ~/regtimeline --bins ~/r1ev/bins --out ~/r1ev-out"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		[ -n "$pg" ] && echo "scp $SSHO $GATES/$pg.gate $T:r1ev/gates/"
		echo "ssh $SSHO $T '$RUNNER' > $OUT/$st.log"
		echo "scp -r $SSHO $T:r1ev-out/$st $OUT/   (copy only)"
		echo "ssh $SSHO $T 'bash ~/r1ev/run/health_remote.sh $TOOL'"
		echo "$PY $R1/score/score_r1.py $st $OUT/$st --gates $GATES$(gated "$st" && echo ' --gate')"
		continue
	fi
	# the laptop's copies must be the frozen ones of this Mac (LAPTOP.sha256 compared byte for byte)
	# shellcheck disable=SC2086
	rl=$(perl -e 'alarm 60; exec @ARGV' ssh $SSHO "$T" 'cat ~/r1ev/LAPTOP.sha256')
	src=$?
	[ $src -eq 0 ] || { echo "STOP: cannot read ~/r1ev/LAPTOP.sha256 on the laptop (status $src)"; exit 21; }
	[ "$rl" = "$(cat "$R1/LAPTOP.sha256")" ] || { echo "STOP: the laptop's LAPTOP.sha256 is not this freeze's: run run/stage_r1.sh"; exit 21; }
	if [ -n "$pg" ]; then
		# shellcheck disable=SC2086
		perl -e 'alarm 60; exec @ARGV' scp -q $SSHO "$GATES/$pg.gate" "$T:r1ev/gates/" || { echo "STOP: the gate file did not reach the laptop"; exit 37; }
	fi
	# this stage's own gate is NONE until its scorer opens it: a stop here never leaves an older OPEN behind
	if gated "$st"; then echo "GATE $st NONE (running $(date +%T))" > "$GATES/$st.gate"; fi
	# shellcheck disable=SC2086
	perl -e 'alarm shift; exec @ARGV' "${STAGE_ALARM:-$(alarm_of "$st")}" ssh $SSHO "$T" "$RUNNER" > "$OUT/$st.log" 2>&1
	rc=$?
	grep -E '^## (STOP|preflight|arm|end|stop)|^== ' "$OUT/$st.log" | tail -8
	# copy the kept files whatever the status; nothing is deleted on either side
	# shellcheck disable=SC2086
	perl -e 'alarm 180; exec @ARGV' scp -q -r $SSHO "$T:r1ev-out/$st" "$OUT/" > "$OUT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		echo "STOP: stage $st exited $rc (see $OUT/$st.log; 255 or 142 = ssh lost or the alarm: a freeze, boot nothing)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying r1ev-out/$st failed (scp status $src)"; exit 37; fi
	# shellcheck disable=SC2086
	perl -e 'alarm 150; exec @ARGV' ssh $SSHO "$T" "bash ~/r1ev/run/health_remote.sh $TOOL" > "$OUT/health-$st.txt" 2>&1
	hrc=$?
	cat "$OUT/health-$st.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$OUT/health-$st.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	if grep -q 'FAIL' "$OUT/health-$st.txt"; then echo "STOP: health after $st: FAIL"; exit 32; fi
	if grep -Eq "$FATAL_RE" "$OUT/health-$st.txt"; then echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; fi
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$OUT/health-$st.txt" || { echo "STOP: render_pb_pages not back at 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$OUT/health-$st.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# the whole stage's kernel log (journalctl -k, not a per-job slice): a watchdog anywhere stops; a hung or fault line stops
	# unless the stage is t, whose last job (t6-hang, S3's held TA fault) logs one by design
	KL=$OUT/$st/kernel.log
	[ -s "$KL" ] || { echo "STOP: no kernel.log kept for $st"; exit 38; }
	if grep -Eq "$FATAL_RE" "$KL"; then echo "STOP: a watchdog/BUG line in $st's kernel.log"; exit 33; fi
	if grep -v 'resgx545 r1 ' "$KL" | grep -Eiq '\b(hung|recovering)\b|BIF fault|page fault'; then
		if [ "$st" = t ] && grep -q '"t6-hang"' "$OUT/$st/stage.json"; then
			echo "note: t's kernel.log has a fault/hung line after the held TA fault (expected)"
		else
			echo "STOP: a hung, recovery or fault line in $st's kernel.log that no job slice reported"; exit 38
		fi
	fi
	if gated "$st"; then
		"$PY" "$R1/score/score_r1.py" "$st" "$OUT/$st" --gates "$GATES" --gate > "$OUT/score-$st.txt" 2>&1
		grc=$?
	else
		"$PY" "$R1/score/score_r1.py" "$st" "$OUT/$st" --gates "$GATES" > "$OUT/score-$st.txt" 2>&1
		grc=$?
	fi
	grep -E '^(SUMMARY|GATE|REFUSING)' "$OUT/score-$st.txt"
	if grep -q '^REFUSING' "$OUT/score-$st.txt"; then echo "STOP: the scorer refused"; exit 41; fi
	if gated "$st" && [ $grc -ne 0 ]; then echo "STOP: the gate after $st is closed (see $OUT/score-$st.txt)"; exit 40; fi
	if ! gated "$st" && [ $grc -ne 0 ]; then echo "STOP: the scorer failed on $st (status $grc)"; exit 41; fi
	echo "stage $st done, health ok"
done
echo "R1 done"
