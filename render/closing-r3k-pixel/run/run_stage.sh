#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT: one R3K-pixel job table on the laptop, one job a line of tables/STAGE.txt in
# file order.  FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (k.sh passes it): the laptop's copy must be that
# file.  ATTEMPT names the output directory ~/r3kpx-out/ATTEMPT/STAGE, which must not exist or be empty (one directory an
# attempt; nothing is merged).  SIGPIPE and SIGHUP are ignored (a dropped ssh does not stop a stage half way);
# everything printed also goes to $KEEP/runner.log.  Env K_FAULTS_PRIOR (0: the limit counts per stage here) and
# K_FAULT_LIMIT (default 5, k.env).  Built from R2-pixel's runner (held jobs, hypothesis groups, the fault limit).
# Line: name|set|risk|knobs|rt|args        (the tool is $T, staged programs $S, the job's directory $W)
#   knobs  words (space separated):
#            held           the job runs in the background with debugfs hold_recovery Y; the registers are read (debugfs
#                           regs) before it (snap 0), HOLD_READ s after the launch (snap 1) and HOLD_GAP s later (snap 2);
#                           then, the hold STILL Y, the kernel's own debugfs reset, which becomes the held recovery
#                           (writing N first would let the 50 ms watchdog recover and make the reset a second halt); then
#                           hold_recovery N (read back), snap 3; a fault still latched gets one more reset (snap 4), then
#                           the session stops (10)
#            noreset        no GPU reset before this job (default: a reset before every job)
#            stophang       a hang in this job ends the stage (the default for any hang anyway)
#            hypo:GROUP:MAX a FAULT is a stated hypothesis of the group: measured (class recorded, recovered, health),
#                           after MAX events the rest of the group is skipped; a fault in a job without it stops the
#                           stage.  A HANG always stops (an unexpected hang), hypothesis or not.
#            expectdiff     rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on
#                           every `tri` row (a row without it is refused before anything runs)
#            expectnopix    rc 3 with `failed: no pixel written` (a probe whose every pixel is the sentinel) is a result,
#                           class ok: S1b's d-L2e2-18 stopped its stage as a failure
#            rgn:N          debugfs render_rgn_arrays N (1 or 4) for this job: written after the job's reset, read back
#                           numerically (rc 19 if it does not read back); a row without it runs at 1 (written if a job left
#                           another value).  The stage restores 1 at every exit, a stop included.
#            idle           no tool: args "-" (a bif row with nothing held; the job is the writes alone)
#            bif            the four kregnow writes of the BIF rows with a regs read after each and a watch (lib_k.sh bif_seq):
#                           a held fault's hold stays Y during them; an idle row writes with nothing held.  Written files:
#                           NAME.snapb0..b5.regs.gz, NAME.kw.txt.gz; rc 18 when the laptop does not answer within BIF_ANSWER s
#   rt     "-", or a regtimeline register list: the job runs under it (read-only, /dev/mem)
# Every job: kernel-log markers (knobs, read-backs, snaps, reset, health tries, class) and the case marker ("resgx545 case
# NAME RUN") right before the job starts; the kernel log after the case marker, taken after the job's reset and before its
# health triangles, is kept as NAME.dmesg.gz.  cases.tsv gets rc and class.
# Classes: held jobs by snap 1 (fault: CR_BIF_INT_STAT bits 15:0 set; hang: the kernel's hold message and no fault bit; ok:
# rc 0; fail); other jobs by the kernel log and rc, a fault checked before a hang.
# Exit status: 0 stage done; 1 preflight (also a table or program that is not the frozen one, a tri row without
# expectdiff, a laptop FROZEN.sha256 that is not the Mac's); 3 FATAL kernel message; 4 an unexpected hang, fault or
# failure; 5 the first failed health recovery; 6 a job did not return (freeze); 7 a forbidden knob; 8 a staged program is
# missing; 9 the hold did not read back Y; 10 a held fault still latched after two resets; 11 hold_recovery did not read
# back N; 12 the registers could not be read during a held job; 13 the reset before a job failed; 14 a fault is latched
# before a job; 15 the fault-class event limit (the 5th event of the stage) was reached; 18 the laptop did not answer after a
# BIF write (E317); 19 render_rgn_arrays did not read back.  On 3, 6 and 18 nothing but the knob restore touches the machine;
# on 10 no further reset.  No reboot, no boot-loader change, no kernel build, no
# clock-gate register, no trc_hazard, no register write of ours, no loop that waits.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
# the laptop's freeze must be the Mac's, before anything else happens
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$DIR/../FROZEN.sha256" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$DIR/../FROZEN.sha256" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_k.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (k.sh passes it)"; exit 1; }
NEED_RT=$(awk -F'|' '!/^#/ && NF>=6 && $5!="-" {f=1} END{print f+0}' "$FILE")
export NEED_RT
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $6 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without --keep-going"; exit 1; }
. "$DIR/lib_k.sh"
# the table, the runner files and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$DIR/../FROZEN.sha256"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_k.sh run_stage.sh k.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run run/stage_k.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
begin
njob=0; SKIP_GRPS=""
FAULT_EVENTS=${K_FAULTS_PRIOR:-0}
TOTAL=$(grep -v '^#' "$FILE" | grep -vc '^$')
for i in $(seq 1 "$TOTAL"); do
	line=$(grep -v '^#' "$FILE" | grep -v '^$' | sed -n "${i}p")
	IFS='|' read -r name sset risk knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0; mode=plain; rgn=1; bif=0
	for k in $knobs; do
		case "$k" in
		hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;;
		held) mode=held ;;
		idle) mode=idle ;;
		bif) bif=1 ;;
		rgn:1|rgn:4) rgn=${k#rgn:} ;;
		noreset|stophang|expectdiff|expectnopix) ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp reached its $gmax events"; continue; } ;; esac
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; mkdir -p "$JW/dump"; W=$JW
	echo "== $name set=$sset risk=$risk mode=$mode knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) : ;; *) reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; } ;; esac
	mark "knobs $name mode=$mode [$knobs]"
	set_rgn "$rgn" || { echo "## STOP: render_rgn_arrays did not read back $rgn before $name (reads $(rgn_now))"; exit 19; }
	mark "rgn $name $rgn"
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	eval "set -- $args"
	rrc=-; heldmsg=no
	if [ "$mode" = idle ]; then
		# nothing runs: the BIF writes alone, with no job unfinished and nothing held
		echo "  (idle row: no tool)"
		mark_case "$name"
		: > "$JW/$name.out"
		[ "$bif" = 1 ] && bif_seq "$name"
		rc=0
	elif [ "$mode" = plain ]; then
		echo "  cmd: $T $*"
		mark_case "$name"
		if [ "$rt" = "-" ]; then
			sudo -n timeout -k 10 "$JOB_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
		else
			sudo -n timeout -k 10 "$JOB_TIMEOUT" "$RT" 0 "$RT_LEAD" "$rt" -- "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
		fi
		rc=$?
	else
		rb=$(set_hold Y); echo "  hold_recovery written Y, read back $rb"; mark "readback $name hold_recovery=$rb"
		[ "$rb" = Y ] || { echo "## STOP: hold_recovery read back $rb, wrote Y (the job did not start)"; exit 9; }
		echo "  cmd (held, background): $T $*"
		mark_case "$name"
		if [ "$rt" = "-" ]; then
			sudo -n timeout -k 10 "$HELD_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null &
		else
			sudo -n timeout -k 10 "$HELD_TIMEOUT" "$RT" 0 "$RT_LEAD" "$rt" -- "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null &
		fi
		JOBPID=$!
		sleep "$HOLD_READ"
		snap "$name" 1 || { echo "## STOP: registers unreadable during $name"; exit 12; }
		if [ "$bif" = 1 ]; then bif_seq "$name"; fi
		sleep "$HOLD_GAP"
		snap "$name" 2
		# the reset while the hold is still Y: it becomes the held recovery and blames the held job; with N written first
		# the watchdog would recover within 50 ms and this reset would be a second halt.
		mark "reset $name"
		reset_gpu; rrc=$?
		echo "  debugfs reset: status $rrc"
		hold_back=$(set_hold N); echo "  hold_recovery written N, read back $hold_back"; mark "readback $name hold_recovery=$hold_back"
		snap "$name" 3
		f3=$(fault_req "$JW/snap3.regs")
		if [ -z "$f3" ] || [ "$f3" -ne 0 ]; then
			echo "  the fault is still latched after the reset (bits 15:0 = ${f3:-unread}): one more reset"
			mark "reset2 $name"
			reset_gpu
			snap "$name" 4
			f4=$(fault_req "$JW/snap4.regs")
			if [ -z "$f4" ] || [ "$f4" -ne 0 ]; then
				NO_MORE_RESET=1
				for f in "$JW"/*.regs; do [ -f "$f" ] && keep "$name" "$f" ".${f##*/}"; done; keep "$name" "$JW/$name.out"
				echo "## STOP: the held fault of $name did not clear after two resets (bits 15:0 = ${f4:-unread}): no further reset (PREFLIGHT.md, recovery plan)"
				exit 10
			fi
		fi
		[ "$hold_back" = N ] || { echo "## STOP: hold_recovery read back $hold_back after $name"; exit 11; }
		wait "$JOBPID"; rc=$?; JOBPID=""
	fi
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: failed|BIF_INT_STAT)' "$JW/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	heldmsg=no; grep -q "recovery held (debugfs hold_recovery)" "$JW/$name.dmesg" && heldmsg=yes
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	# every kept file by an explicit loop over the globs (the globs are live: no `set -f` anywhere)
	for f in "$JW"/*.regs "$JW"/dump/*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	[ -f "$JW/kw.txt" ] && keep "$name" "$JW/kw.txt" ".kw.txt"
	# 1. the kernel itself in trouble: stop at once, touch nothing
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if grep -Eq "$FATAL_RE" "$JW/$name.dmesg" "$JW/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job
	fr=-
	if [ "$mode" = held ]; then
		fr=$(fault_req "$JW/snap1.regs")
		if [ "$fr" -ne 0 ]; then class=fault
		elif [ "$heldmsg" = yes ]; then class=hang
		elif [ "$rc" -eq 0 ]; then class=ok
		else class=fail; fi
	elif grep -Eq "BIF fault|faulted" "$JW/$name.out" "$JW/$name.dmesg"; then class=fault
	elif grep -Eq "job [0-9]+ hung|hung|timed out waiting" "$JW/$name.out" "$JW/$name.dmesg"; then class=hang
	elif [ "$rc" -eq 0 ]; then class=ok
	else class=fail; fi
	if [ "$class" = fail ]; then
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$JW/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:" "$JW/$name.out"; then class=ok; fi ;;
		esac
		case " $knobs " in *" expectnopix "*)
			if [ "$rc" -eq 3 ] && grep -q 'failed: no pixel written' "$JW/$name.out" && ! grep -Eq "BIF fault|faulted|hung|Segmentation|rejected|cancelled" "$JW/$name.out" "$JW/$name.dmesg"; then class=ok; fi ;;
		esac
	fi
	echo "  class $class (fault bits 15:0 at snap 1: $fr, hold message: $heldmsg)"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" \
		"$rc" "$class" "$mode" "$fr" "$rrc" "$heldmsg" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	fault)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		if [ -n "$grp" ]; then
			gv=$(printf '%s' "$grp" | tr -c 'A-Za-z0-9' '_'); eval "HYPO_$gv=\$(( \${HYPO_$gv:-0} + 1 ))"; eval "n=\$HYPO_$gv"
			echo "  fault $n of at most $gmax in group $grp (a hypothesis: measured); fault-class events of the session: $FAULT_EVENTS of $FAULT_LIMIT"
			[ "$n" -ge "$gmax" ] && SKIP_GRPS="$SKIP_GRPS $grp"
		else
			echo "## STOP: unexpected fault in $name"
			[ "$mode" = plain ] && reset_gpu
			health "$name" </dev/null; exit 4
		fi
		[ "$mode" = plain ] && reset_gpu
		health "$name" </dev/null
		if [ "$FAULT_EVENTS" -ge "$FAULT_LIMIT" ]; then
			echo "## STOP: the $FAULT_EVENTS-th fault-class event of the session ($FAULT_LIMIT is the limit): stop after $name (PREFLIGHT.md section 6)"
			exit 15
		fi ;;
	hang)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		echo "## STOP: unexpected hang in $name"
		[ "$mode" = plain ] && reset_gpu
		health "$name" </dev/null; exit 4 ;;
	fail) echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	esac
done
JW=$WROOT/end; mkdir -p "$JW"
health end </dev/null
echo "## end: $njob jobs of $STAGE"
