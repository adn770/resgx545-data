#!/bin/bash
# SPDX-License-Identifier: MIT
# m.sh TOOL6_SHA256 [--from STAGE] [--only STAGE...] : the r6-misc session driver, run from the Mac.  NOT RUN while it was prepared.
# It runs on the gma500 module of fork a2788bd8 (rgn4, srcversion 99CD90DA...) with ~/sgxfive-test-rgn4 (t4) and the t6 build the
# lead froze (~/scratch/r6m/bin/sgxfive-test, TOOL6_SHA256 = TOOL6.sha256's).  Built from round 5's r5-render4x k.sh.
#
# For each stage of stages.txt (q289 q287 q086): verify the frozen files with the t6 hash; the laptop-side runner over ssh
# (run_stage.sh, with the sha256 of this side's FROZEN.sha256, the attempt name and the t6 hash); copy the stage's kept files to
# out/ATT/STAGE (copy only); score the stage (out/ATT/score-STAGE.txt, SUMMARY lines); the health script (tools/bringup/health.sh
# with the rgn4 tool: a fill and a triangle) and its checks, including the knobs at their defaults (hold_recovery N, alias_skip 0,
# render_pb_pages 0x422, render_rgn_arrays 0: this session writes none of them).  q287's rc 21 (gateodd: the odd height refused,
# a clean end) is scored, checked and the driver goes on.  Every ssh and scp is bounded (perl alarm).  Host and ssh options:
# SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops.
# A rerun after a stop is a new attempt (`--from STAGE`, a new out/ATT).
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health recovery,
# 6 freeze, 7 forbidden knob or tool, 12 registers unreadable, 13 reset failed, 14 fault latched before a job, 15 the stage's
# fault limit with rows left, 16 strict health failed, 17 two rows without a hash, 18 a fault that is not the 3D-side class or a
# -110, 22 free space; 142 the alarm: a freeze), 2 usage, 20 frozen files changed, 30-37 health after a stage, 38 no scorer
# SUMMARY, 39 the attempt's stage directory exists, 42 a knob not at its default after a stage.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/m.env"
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
S6=${1:-}
case "$S6" in ""|-*) echo "usage: m.sh TOOL6_SHA256 [--from STAGE] [--only STAGE...]"; exit 2 ;; esac
shift
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-rgn4
R=scratch/$PREFIX
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$KP/stages.txt")
# a per-stage alarm (s): q289 23 fills; q287 20 small depth jobs; q086 21 4x jobs up to 1024 x 768 with every pixel, 3 faults
alarm_of() { case "$1" in q289) echo 900 ;; q287) echo 1200 ;; q086) echo 2400 ;; *) echo 900 ;; esac; }
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${M_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$KP/out/$ATT
FSHA=$(shasum -a 256 "$KP/FROZEN.sha256" | cut -d' ' -f1)
"$KP/run/freeze_m.sh" verify "$S6" > /dev/null || { "$KP/run/freeze_m.sh" verify "$S6"; echo "FROZEN FILES CHANGED or no t6 hash: stop"; exit 20; }
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA; t6 $S6"

knobs_read() { # alias_skip, render_rgn_arrays, render_pb_pages, hold_recovery on four lines
	# shellcheck disable=SC2086
	bounded 60 ssh $SSHO "$T" 'sudo -n sh -c "d=\$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1); cat \$d/alias_skip; cat \$d/render_rgn_arrays; cat \$d/render_pb_pages; cat \$d/hold_recovery"' 2>&1
}
health_after() {
	local st=$1 hrc n am arc kn rg pbn ho
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
	[ $arc -eq 0 ] || { echo "STOP: reading the knobs after $st failed (status $arc): $kn"; exit 36; }
	am=$(echo "$kn" | sed -n 1p); rg=$(echo "$kn" | sed -n 2p); pbn=$(echo "$kn" | sed -n 3p); ho=$(echo "$kn" | sed -n 4p)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st"; exit 42; }
	num_eq "$rg" 0 || { echo "STOP: render_rgn_arrays is $rg after $st (r6-misc writes no knob: the lead decides)"; exit 42; }
	num_eq "$pbn" 0x422 || { echo "STOP: render_pb_pages is $pbn after $st (r6-misc writes no knob: the lead decides)"; exit 42; }
	[ "$ho" = N ] || { echo "STOP: hold_recovery is $ho after $st"; exit 42; }
	echo "stage $st done, health ok, knobs at their defaults"
}

run_one() {
	local st=$1 rc src sc
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (M_ATT) for a rerun"; exit 39; }
	"$KP/run/freeze_m.sh" verify "$S6" > /dev/null || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_m.sh)"; exit 20; }
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-$(alarm_of "$st")} ssh $SSHO $T 'bash ~/$R/run/run/run_stage.sh $st $FSHA $ATT $S6' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:$R/out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $KP/score/score_m.py $st $ROOT/$st $S6 > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-$(alarm_of "$st")}" ssh $SSHO "$T" "bash ~/$R/run/run/run_stage.sh $st $FSHA $ATT $S6" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort|exit|gateodd)|^  class|health:" "$ROOT/$st.log"
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:$R/out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ] && [ $rc -ne 21 ]; then
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "knobs after the stop (read only): $(knobs_read | tr '\n' ' ')"
		echo "to continue after the lead's decision: run/m.sh $S6 --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying $R/out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	[ $rc -eq 21 ] && echo "$st: gateodd, the odd height was refused: the stage ended cleanly (scored as such)"
	"$PY" "$KP/score/score_m.py" "$st" "$ROOT/$st" "$S6" > "$ROOT/score-$st.txt" 2>&1; sc=$?
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
echo "r6-misc done: $PY $KP/score/score_m.py verdict $ROOT $S6"
