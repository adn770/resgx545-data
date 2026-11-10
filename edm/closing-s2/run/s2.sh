#!/bin/bash
# SPDX-License-Identifier: MIT
# s2.sh [--from STAGE] [--only STAGE]: the S2 session driver, run from the Mac.  NOT RUN while it was prepared.
#
# Order (decided by the user): e1c e1j | e2r [gate] e2w | e4c [gate] e4h [gate] e4l [gate] e5c [gate] e5t.
# For each stage: verify the freeze; for a stage behind a gate, the gate file the SCORER wrote must say OPEN (it is
# copied to the laptop, whose runner refuses the stage without it); one ssh runs the stage (sudo -n python3 on the
# laptop, bounded by a perl alarm here); the stage's files are copied back whatever the status (copy only); the
# health script; the scorer, which prints the SUMMARY line and, for a gated stage, writes GATES/STAGE.gate and exits
# 0 only when it is open.  Any stop, a failed health, a closed gate or a lost ssh ends the session.
# Gates:  e1c -> e1j: the three E1 controls held (quiet 50 ms logs nothing, 8 ms logs the ticks, the kick E538's word)
#         e2r -> e2w: sa66 = 0x01061a70 in 3 of 3 valid read passes (the ONLY way the sa67/sa68 writer is armed)
#         e4c -> e4h: 16 tick entries on the 25000 grid in 3 of 3;  e4h -> e4l: every hold up to 20 ms valid, done,
#         the knob in its band, tick and health fine;  e4l -> e5c: the same for the 100 ms holds;  e5c -> e5t: the
#         100 ms control reproduced e4l and the three kicks were valid (a stop in e5c ends S2 before the triangle)
# e1j -> e2r and e2w -> e4c need only the stage's exit 0 and the health (no result gate: they are independent).
# Exit: the stage's own code (1, 3, 4, 5, 6, 7, 9), 20 frozen files changed, 21 the laptop's LAPTOP.sha256 is not
# this freeze's, 30-35 health after a stage (no answer, fill or triangle not exact, FAIL, watchdog in the tail,
# render_pb_pages or hold_recovery not back), 33 also a watchdog line in the stage's kernel.log, 37 copy failed,
# 38 a hung/recovery/fault line in the stage's kernel.log (or none kept), 40 a gate closed, 41 the scorer refused or
# failed, 255 or 142 ssh lost or the alarm (a freeze: boot nothing, report).  A gated stage's own gate file is set
# to NONE before its ssh; gate lines carry the run id, which the laptop runner checks against its stage.json.
# OUT (default out/) and GATES (default gates/) are where the copies, logs, scores and gate files go (the mock tests
# point them elsewhere).  SGX_DRY_RUN=1 prints the commands.  No wait loops: one ssh a stage, one health call, one
# scorer call.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S2=$(dirname "$HERE")
R=${RESGX545:-$HOME/src/resgx545}
BRINGUP=$R/tools/bringup
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=${S2_TOOL_NAME:-sgxfive-test-s1}
PY=${PY:-$S2/../pixel-faults/.venv/bin/python}
HEALTH=${S2_HEALTH:-$BRINGUP/health.sh}
OUT=${S2_OUT:-$S2/out}
GATES=${S2_GATES:-$S2/gates}
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$S2/stages.txt")
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then ONLY=${2:?stage}; fi
prev_gate() { case "$1" in e1j) echo e1c ;; e2w) echo e2r ;; e4h) echo e4c ;; e4l) echo e4h ;; e5c) echo e4l ;; e5t) echo e5c ;; esac; }
gated() { case "$1" in e1c|e2r|e4c|e4h|e4l|e5c) return 0 ;; esac; return 1; }
mkdir -p "$OUT" "$GATES"
go=0; [ -z "$FROM" ] && go=1
for st in ${ONLY:-$ALL}; do
	[ "$st" = "$FROM" ] && go=1
	[ $go = 1 ] || continue
	"$S2/run/freeze_s2.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop"; exit 20; }
	pg=$(prev_gate "$st")
	if [ -n "$pg" ]; then
		grep -q "^GATE $pg OPEN" "$GATES/$pg.gate" 2>/dev/null || { echo "GATE $pg is not open: $st does not run"; cat "$GATES/$pg.gate" 2>/dev/null; exit 40; }
	fi
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		[ -n "$pg" ] && echo "scp $SSHO $GATES/$pg.gate $T:s2/gates/"
		echo "ssh $SSHO $T 'sudo -n python3 ~/s2/run/s2_run.py $st --tool ~/$TOOL --out ~/s2-out' > $OUT/$st.log"
		echo "scp -r $SSHO $T:s2-out/$st $OUT/   (copy only)"
		echo "$HEALTH $TOOL"
		echo "$PY $S2/score/score_s2.py $st $OUT/$st --gates $GATES$(gated "$st" && echo ' --gate')"
		continue
	fi
	# the laptop's copies must be the frozen ones of this Mac (LAPTOP.sha256 compared byte for byte)
	# shellcheck disable=SC2086
	rl=$(perl -e 'alarm 60; exec @ARGV' ssh $SSHO "$T" 'cat ~/s2/LAPTOP.sha256')
	src=$?
	[ $src -eq 0 ] || { echo "STOP: cannot read ~/s2/LAPTOP.sha256 on the laptop (status $src)"; exit 21; }
	[ "$rl" = "$(cat "$S2/LAPTOP.sha256")" ] || { echo "STOP: the laptop's LAPTOP.sha256 is not this freeze's: run run/stage_s2.sh"; exit 21; }
	if [ -n "$pg" ]; then
		# shellcheck disable=SC2086
		perl -e 'alarm 60; exec @ARGV' scp -q $SSHO "$GATES/$pg.gate" "$T:s2/gates/" || { echo "STOP: the gate file did not reach the laptop"; exit 37; }
	fi
	# this stage's own gate is NONE until its scorer opens it: a stop here never leaves an older OPEN behind
	if gated "$st"; then echo "GATE $st NONE (running $(date +%T))" > "$GATES/$st.gate"; fi
	# shellcheck disable=SC2086
	perl -e 'alarm shift; exec @ARGV' "${STAGE_ALARM:-900}" ssh $SSHO "$T" "sudo -n python3 ~/s2/run/s2_run.py $st --tool ~/$TOOL --out ~/s2-out" > "$OUT/$st.log" 2>&1
	rc=$?
	grep -E '^## (STOP|preflight|arm|end|stop|stuck)|^== ' "$OUT/$st.log" | tail -8
	# copy the kept files whatever the status; nothing is deleted on either side
	# shellcheck disable=SC2086
	perl -e 'alarm 120; exec @ARGV' scp -q -r $SSHO "$T:s2-out/$st" "$OUT/" > "$OUT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		echo "STOP: stage $st exited $rc (see $OUT/$st.log; 255 or 142 = ssh lost or the alarm: a freeze, boot nothing)"
		if [ "$st" = e2w ]; then
			echo "WARNING: e2w stopped before its restores were verified: sa67 and sa68 may still hold the S2 marker"
			echo "WARNING: (0xb2a067xx / 0xb2a068xx) through resets (E536: sa survived a reset); see $OUT/e2w/*.json"
		fi
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying s2-out/$st failed (scp status $src)"; exit 37; fi
	perl -e 'alarm 150; exec @ARGV' "$HEALTH" "$TOOL" > "$OUT/health-$st.txt" 2>&1
	hrc=$?
	cat "$OUT/health-$st.txt"
	if [ $hrc -ne 0 ]; then echo "STOP: health exited $hrc after $st (no answer = freeze)"; exit 30; fi
	n=$(grep -c '^diff: 0' "$OUT/health-$st.txt")
	[ "$n" -ge 2 ] || { echo "STOP: health after $st: the fill and the triangle did not both print diff: 0"; exit 31; }
	if grep -q 'FAIL' "$OUT/health-$st.txt"; then echo "STOP: health after $st: FAIL"; exit 32; fi
	if grep -Eq "$FATAL_RE" "$OUT/health-$st.txt"; then echo "STOP: kernel watchdog/BUG in the health tail after $st"; exit 33; fi
	grep -Eq 'render_pb_pages=0x0*422( |$)' "$OUT/health-$st.txt" || { echo "STOP: render_pb_pages not back at 0x422 after $st"; exit 34; }
	grep -q 'hold_recovery=N' "$OUT/health-$st.txt" || { echo "STOP: hold_recovery is not N after $st"; exit 35; }
	# the whole stage's kernel log (journalctl -k, not a per-job slice): a watchdog anywhere stops; a hung or fault
	# line stops unless the stage ended on the stuck triangle (whose recovery logs one by design)
	KL=$OUT/$st/kernel.log
	[ -s "$KL" ] || { echo "STOP: no kernel.log kept for $st"; exit 38; }
	if grep -Eq "$FATAL_RE" "$KL"; then echo "STOP: a watchdog/BUG line in $st's kernel.log"; exit 33; fi
	if grep -v 'resgx545 s2 ' "$KL" | grep -Eiq '\b(hung|recovering)\b|BIF fault|page fault'; then
		if grep -q '"stuck"' "$OUT/$st/stage.json"; then
			echo "note: $st's kernel.log has a hung/recovery line after the stuck triangle (expected)"
		else
			echo "STOP: a hung, recovery or fault line in $st's kernel.log that no job slice reported"; exit 38
		fi
	fi
	if gated "$st"; then
		"$PY" "$S2/score/score_s2.py" "$st" "$OUT/$st" --gates "$GATES" --gate > "$OUT/score-$st.txt" 2>&1
		grc=$?
	else
		"$PY" "$S2/score/score_s2.py" "$st" "$OUT/$st" --gates "$GATES" > "$OUT/score-$st.txt" 2>&1
		grc=$?
	fi
	grep -E '^(SUMMARY|GATE|REFUSING)' "$OUT/score-$st.txt"
	if grep -q '^REFUSING' "$OUT/score-$st.txt"; then echo "STOP: the scorer refused"; exit 41; fi
	if gated "$st" && [ $grc -ne 0 ]; then echo "STOP: the gate after $st is closed (see $OUT/score-$st.txt)"; exit 40; fi
	if ! gated "$st" && [ $grc -ne 0 ]; then echo "STOP: the scorer failed on $st (status $grc)"; exit 41; fi
	echo "stage $st done, health ok"
done
echo "S2 done"
