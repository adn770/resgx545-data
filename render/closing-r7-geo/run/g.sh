#!/bin/bash
# SPDX-License-Identifier: MIT
# g.sh [--from STAGE] [--only STAGE...] : the r7-geo session driver, run from the Mac.  NOT RUN while it was prepared.
# It runs on the gma500 module of fork 3f0b3e74 (srcversion 41E2F5C7...) with ~/sgxfive-test-rgn4 (t4) and round 6's t6
# (~/scratch/r7g/bin/sgxfive-test, sha256 97df5c0e..., the zf odd-height rows only).  Built from round 6's r6-misc m.sh.
#
# For each stage of stages.txt (xf tx zd zf zs): verify the frozen files; the laptop-side runner over ssh (run_stage.sh, with the
# sha256 of this side's FROZEN.sha256 and the attempt name); copy the stage's kept files to out/ATT/STAGE (copy only); the kept-files
# check (sessioncheck.py kept: every file score_g.REQUIRED names); score the stage (out/ATT/score-STAGE.txt, SUMMARY lines); the
# health script (tools/bringup/health.sh with the rgn4 tool: a fill and a triangle) and its checks, including the knobs at their
# defaults (hold_recovery N, alias_skip 0, render_pb_pages 0x422, render_rgn_arrays 0, render_tail_room 0: this session writes
# none of them).  Every ssh and scp is bounded (perl alarm).  Host and ssh options: SGX_TARGET_HOST, SGX_TARGET_SSH_OPTS
# (tools/bringup/local.env).  SGX_DRY_RUN=1 prints the commands.  No wait loops.  A rerun after a stop is a new attempt
# (`--from STAGE`, a new out/ATT).
# Exit: the stage runner's status (1 preflight, 3 kernel watchdog/BUG, 4 unexpected hang/fault/failure, 5 failed health recovery,
# 6 freeze, 7 forbidden knob or tool, 12 registers unreadable, 13 reset failed, 14 fault latched before a job, 16 strict health
# failed, 17 two rows without a hash, 22 free space, 23 a scorer's file not kept, 24 two soft failures in a row, 25 a control
# without its reading; 142 the alarm: a freeze), 2 usage, 20 frozen files changed, 30-37 health after a stage, 38 no scorer
# SUMMARY, 39 the attempt's stage directory exists, 40 a kept file the scorer reads is missing on the Mac, 42 a knob not at its
# default after a stage.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
KP=$(dirname "$HERE")
BRINGUP=${RESGX545_BRINGUP:-$HOME/src/resgx545/tools/bringup}
LOCAL_ENV=${SGX_LOCAL_ENV:-$BRINGUP/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
. "$HERE/lib_check.sh"
. "$HERE/g.env"
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
TOOL=sgxfive-test-rgn4
R=scratch/$PREFIX
SSHO="-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 $OPTS"
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|psb.*watchdog'
ALL=$(tr '\n' ' ' < "$KP/stages.txt")
# a per-stage alarm (s): xf 10 fills; tx 18 probes with a health check after each; zd 127 jobs up to 4096 x 4096 with depth dumps;
# zf 242 small depth jobs; zs 230 jobs at 512 x 256 with every pixel
alarm_of() { case "$1" in xf) echo 900 ;; tx) echo 1800 ;; zd) echo 4800 ;; zf) echo 4200 ;; zs) echo 4200 ;; *) echo 900 ;; esac; }
FROM=""; ONLY=""
if [ "${1:-}" = "--from" ]; then FROM=${2:?stage}; shift 2; fi
if [ "${1:-}" = "--only" ]; then shift; ONLY="$*"; fi
ATT=${G_ATT:-$(date +%Y%m%d-%H%M%S)}
ROOT=$KP/out/$ATT
FSHA=$(shasum -a 256 "$KP/FROZEN.sha256" | cut -d' ' -f1)
"$KP/run/freeze_g.sh" verify > /dev/null || { "$KP/run/freeze_g.sh" verify; echo "FROZEN FILES CHANGED: stop"; exit 20; }
[ -n "${SGX_DRY_RUN:-}" ] || mkdir -p "$ROOT"
echo "attempt $ATT: $ROOT; FROZEN.sha256 $FSHA"

knobs_read() { # alias_skip, render_rgn_arrays, render_pb_pages, hold_recovery, render_tail_room on five lines
	# shellcheck disable=SC2086
	bounded 60 ssh $SSHO "$T" 'sudo -n sh -c "d=\$(ls -d /sys/kernel/debug/dri/*/sgx | head -n 1); cat \$d/alias_skip; cat \$d/render_rgn_arrays; cat \$d/render_pb_pages; cat \$d/hold_recovery; cat \$d/render_tail_room"' 2>&1
}
health_after() {
	local st=$1 hrc n am arc kn rg pbn ho tr
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
	am=$(echo "$kn" | sed -n 1p); rg=$(echo "$kn" | sed -n 2p); pbn=$(echo "$kn" | sed -n 3p); ho=$(echo "$kn" | sed -n 4p); tr=$(echo "$kn" | sed -n 5p)
	num_eq "$am" 0 || { echo "STOP: alias_skip is $am after $st"; exit 42; }
	num_eq "$rg" 0 || { echo "STOP: render_rgn_arrays is $rg after $st (r7-geo writes no knob: the lead decides)"; exit 42; }
	num_eq "$pbn" 0x422 || { echo "STOP: render_pb_pages is $pbn after $st (r7-geo writes no knob: the lead decides)"; exit 42; }
	num_eq "$tr" 0 || { echo "STOP: render_tail_room is $tr after $st (r7-geo writes no knob: the lead decides)"; exit 42; }
	[ "$ho" = N ] || { echo "STOP: hold_recovery is $ho after $st"; exit 42; }
	echo "stage $st done, health ok, knobs at their defaults"
}

run_one() {
	local st=$1 rc src sc
	[ -e "$ROOT/$st" ] && { echo "STOP: $ROOT/$st exists: a new attempt (G_ATT) for a rerun"; exit 39; }
	"$KP/run/freeze_g.sh" verify > /dev/null || { echo "FROZEN FILES CHANGED: stop (restage after a regenerated freeze: run/stage_g.sh)"; exit 20; }
	echo "#### $st $(date +%T)"
	if [ -n "${SGX_DRY_RUN:-}" ]; then
		echo "bounded ${STAGE_ALARM:-$(alarm_of "$st")} ssh $SSHO $T 'bash ~/$R/run/run/run_stage.sh $st $FSHA $ATT' > $ROOT/$st.log"
		echo "bounded 300 scp -q -r $SSHO $T:$R/out/$ATT/$st $ROOT/$st   (copy only)"
		echo "$PY $KP/score/sessioncheck.py kept $KP/score/score_g.py $st $ROOT/$st --call read_files"
		echo "$PY $KP/score/score_g.py $st $ROOT/$st > $ROOT/score-$st.txt"
		echo "bounded 150 $BRINGUP/health.sh $TOOL"
		return 0
	fi
	# shellcheck disable=SC2086
	bounded "${STAGE_ALARM:-$(alarm_of "$st")}" ssh $SSHO "$T" "bash ~/$R/run/run/run_stage.sh $st $FSHA $ATT" > "$ROOT/$st.log" 2>&1
	rc=$?
	grep -E "^## (STOP|abort|exit|gate)|^  class [^o]|soft failure|health:" "$ROOT/$st.log"
	# shellcheck disable=SC2086
	bounded 300 scp -q -r $SSHO "$T:$R/out/$ATT/$st" "$ROOT/$st" > "$ROOT/scp-$st.log" 2>&1
	src=$?
	if [ $rc -ne 0 ]; then
		echo "STOP: stage $st exited $rc (see $ROOT/$st.log and $st/runner.log; 255 = ssh lost, 142 = the alarm: a freeze)"
		echo "knobs after the stop (read only): $(knobs_read | tr '\n' ' ')"
		echo "to continue after the lead's decision: run/g.sh --from $st (a new attempt directory)"
		exit $rc
	fi
	if [ $src -ne 0 ]; then echo "STOP: copying $R/out/$ATT/$st failed (status $src, see scp-$st.log)"; exit 37; fi
	"$PY" "$KP/score/sessioncheck.py" kept "$KP/score/score_g.py" "$st" "$ROOT/$st" --call read_files > "$ROOT/kept-$st.txt" 2>&1 \
		|| { cat "$ROOT/kept-$st.txt"; echo "STOP: a file the scorer of $st reads is not in the kept output"; exit 40; }
	"$PY" "$KP/score/score_g.py" "$st" "$ROOT/$st" > "$ROOT/score-$st.txt" 2>&1; sc=$?
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
echo "r7-geo done: $PY $KP/score/score_g.py verdict $ROOT"
