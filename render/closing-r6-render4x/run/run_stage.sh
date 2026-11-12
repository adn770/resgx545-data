#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT [FREEZE]: one r6-render4x job table on the laptop, one job a line of tables/STAGE.txt in file
# order.  FROZEN_SHA256 is the sha256 of the Mac's freeze file FREEZE (default FROZEN.sha256, stage A's; k.sh passes both): the laptop's
# copy must be that file and the table and runner files must be in it.  ATTEMPT names the output directory ~/scratch/r6x/out/ATTEMPT/
# STAGE, which must not exist or be empty (one directory an attempt; nothing is merged).  SIGPIPE and SIGHUP are ignored (a dropped
# ssh does not stop a stage half way); everything printed also goes to $KEEP/runner.log.
# Copied from r5-render4x's runner (closing5/r5-render4x/run/run_stage.sh: R4-G's with round 5's stop rules, DECISIONS-R5 R5-4 a) with
# round 6's files (lib_k.sh: ~/scratch/r6x, one mktemp directory under ~/scratch/tmp, each job's work directory removed once kept), a
# free-space check before each job (rc 21), debugfs kpoke read and kept after each job (t7 arms a --kpoke-render of the tool's) and
# the freeze file named by the driver (a later freeze, stage B, names its own).
# Table header lines:  #stage NAME   #limit N (the fault-class events the stage may take)   #need FILE (a staged program, $S/NAME.bin:
#   it must exist and be the frozen one, bins/NAME in FROZEN.sha256)
# Line: name|set|risk|knobs|rt|args        (the tool is $T, staged programs $S, the job's directory $W)
#   knobs  words (space separated), only these:
#            rgn:1        after the job's reset, debugfs render_rgn_arrays is written 1 and read back (rc 19 if it does not read 1);
#                         after the job it is written 0 and read back (rc 19); at every exit the trap writes 0
#            pb:0xNN      debugfs render_pb_pages written 0xNN (0x23 to 0x422) after the reset and read back numerically (rc 19);
#                         back to 0x422 after the job (rc 19) and at every exit; a row without it runs at 0x422
#            held         the job runs in the background with hold_recovery Y (written, read back Y: rc 9); the registers are read
#                         (debugfs regs) before it (snap 0), HOLD_READ s after the launch (snap 1) and HOLD_GAP s later (snap 2); then,
#                         the hold STILL Y, the kernel's own debugfs reset, which becomes the held recovery; then hold_recovery N
#                         (read back, rc 11), snap 3; a fault still latched gets one more reset (snap 4), then the session stops (10)
#            dumpheld     (with held) debugfs render_param and render_tadata READ during the hold (after snap 1) and kept
#            strict       after a fault-class event the FIRST health fill and triangle must draw (no reset of ours before): else the
#                         usual recovery, then the stage stops (rc 16).  Every row of this session carries it.
#            hypo:G:MAX   a FAULT is a stated hypothesis of the group: measured (class recorded, recovered, health); after MAX events
#                         the rest of the group is skipped; a fault in a job without it stops the stage (rc 4, after strict health)
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every `tri` row
#          any other word is refused: rc 7, nothing runs
#   rt     "-" only (no regtimeline in this session)
# STOP RULES: an unexpected fault, hang or failure ends the stage (strict health, rc 4); a fault whose BIF_INT_STAT bits 15:0 are not
# 0x0100 or whose BIF_FAULT is not 0x10000011 (a TA-side fault, another word), or a "recovery failed: -110" line, ends it (strict
# health, rc 18); the LIMIT-th fault-class event of the stage ends it when rows remain (rc 15: the limit is the number the stage may
# take); a fatal kernel message is rc 3 and a job that did not return rc 6 (nothing but the knob restore and the exit log touch the
# machine).
# Every job: a reset, the knobs, kernel-log markers and the case marker ("resgx545 case NAME RUN") right before the job starts; the
# kernel log after the case marker is kept as NAME.dmesg.gz (the slice is by the marker, not by a line count); the registers after
# the job (snap 9) are kept; cases.tsv gets rc and class.  The reset information lines are not bad lines.  After the last job a reset
# comes before the end health.
# Exit status: 0 stage done; 1 preflight (also a table that is not the frozen one, a tri row without expectdiff or --keep-going, a
# staged program that is not the frozen one, a laptop FROZEN.sha256 that is not the Mac's); 3 FATAL kernel message; 4 an unexpected
# hang, fault or failure; 5 the first failed health recovery; 6 a job did not return (freeze); 7 a forbidden knob; 8 a staged program
# is missing; 9 the hold did not read back Y; 10 a held fault still latched after two resets; 11 hold_recovery did not read back N;
# 12 the registers could not be read; 13 the reset before a job failed; 14 a fault is latched before a job; 15 the fault-class event
# limit of the stage with rows left; 16 strict: a health triangle failed after a fault-class event; 18 a fault that is not E845's
# 3D-side word, or a -110; 19 a knob did not read back; 21 less than MIN_FREE_MB free on ~ (before a job, or at the preflight).
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours, no loop that
# waits.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
FREEZE=${4:-FROZEN.sha256}
case "$FREEZE" in FROZEN.sha256|FROZEN-[A-Z].sha256) ;; *) echo "the freeze file $FREEZE is not FROZEN.sha256 or FROZEN-X.sha256"; exit 1 ;; esac
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
FZ=$DIR/../$FREEZE
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
[ -f "$FZ" ] || { echo "no $FZ: run run/stage_k.sh again"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$FZ" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$FZ" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's $FREEZE is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_k.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (k.sh passes it)"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|rgn:1|held|dumpheld|strict|pb:0x[0-9a-f][0-9a-f][0-9a-f]?|hypo:[a-z0-9]+:[0-9]+)$/) { print $1 ": " k[i]; bad=1 } if ($5 != "-") { print $1 ": rt " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or rt that r6-render4x does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $6 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without --keep-going"; exit 1; }
for v in $(grep -v '^#' "$FILE" | grep -oE 'pb:0x[0-9a-f]+' | cut -d: -f2); do
	[ $((v)) -ge $((0x23)) ] && [ $((v)) -le $((0x422)) ] || { echo "table $STAGE: pb:$v is outside 0x23 to 0x422"; exit 7; }
done
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-1}
. "$DIR/lib_k.sh"
# the table, the runner files and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$FZ"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
RD=$(basename "$DIR")
for f in lib_k.sh run_stage.sh k.env; do
	want=$(expect_sha "$RD/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "$RD/$f is not the frozen one"; exit 1; }
done
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run run/stage_k.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done

# ---- the rows ---------------------------------------------------------------------------------------------------------------
begin
njob=0; SKIP_GRPS=""
FAULT_EVENTS=0
TOTAL=$(grep -v '^#' "$FILE" | grep -vc '^$')
for i in $(seq 1 "$TOTAL"); do
	line=$(grep -v '^#' "$FILE" | grep -v '^$' | sed -n "${i}p")
	IFS='|' read -r name sset risk knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0; mode=plain; rgn=0; pbv=0x422; strict=0; dumpheld=0
	for k in $knobs; do
		case "$k" in
		hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;;
		held) mode=held ;;
		rgn:1) rgn=1 ;;
		pb:*) pbv=${k#pb:} ;;
		strict) strict=1 ;;
		dumpheld) dumpheld=1 ;;
		expectdiff|-) ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp reached its $gmax events"; continue; } ;; esac
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; mkdir -p "$JW/dump"; W=$JW
	echo "== $name set=$sset risk=$risk mode=$mode knobs=[$knobs]"
	space_ok || { echo "## STOP: less than $MIN_FREE_MB MiB free on ~ before $name ($(free_kb) KiB)"; exit 21; }
	echo "  free on ~: $(free_kb) KiB"
	reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; }
	rgn_set "$rgn" || { echo "## STOP: render_rgn_arrays does not read back $rgn before $name ($(rgn_now))"; exit 19; }
	mark "rgn $name $rgn"
	pb_set "$pbv" || { echo "## STOP: render_pb_pages does not read back $pbv before $name ($(pb_now))"; exit 19; }
	mark "pb $name $pbv"
	knobs_ok "$rgn" "$pbv" || { echo "## STOP: a knob is not as the row asks before $name (hold_recovery $(hold_now), render_rgn_arrays $(rgn_now), render_pb_pages $(pb_now))"; exit 19; }
	mark "knobs-read $name hold_recovery=$(hold_now) render_rgn_arrays=$(rgn_now) render_pb_pages=$(pb_now)"
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	eval "set -- $args"
	rrc=-; heldmsg=no; fr=-
	if [ "$mode" = plain ]; then
		echo "  cmd: $T $*"
		mark_case "$name"
		sudo -n timeout -k 10 "$JOB_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
		rc=$?
		snap "$name" 9 || { echo "## STOP: registers unreadable after $name"; exit 12; }
	else
		rb=$(set_hold Y); echo "  hold_recovery written Y, read back $rb"; mark "readback $name hold_recovery=$rb"
		[ "$rb" = Y ] || { echo "## STOP: hold_recovery read back $rb, wrote Y (the job did not start)"; exit 9; }
		echo "  cmd (held, background): $T $*"
		mark_case "$name"
		sudo -n timeout -k 10 "$HELD_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null &
		JOBPID=$!
		sleep "$HOLD_READ"
		snap "$name" 1 || { echo "## STOP: registers unreadable during $name"; exit 12; }
		if [ "$dumpheld" = 1 ]; then
			sudo -n timeout -k 5 30 cat "$D/render_param" > "$JW/heldparam.bin" 2>&1; sudo -n timeout -k 5 30 cat "$D/render_tadata" > "$JW/heldtadata.bin" 2>&1
		fi
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
	echo "  rc $rc $(grep -E '^(job|tri:|BIF_INT_STAT)' "$JW/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	# what is still armed (a --kpoke-render the tool armed and the kernel did not apply; the next reset disarms it): read, kept
	dbg_cat kpoke > "$JW/$name.kpoke" 2>&1
	heldmsg=no; grep -q "recovery held (debugfs hold_recovery)" "$JW/$name.dmesg" && heldmsg=yes
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	keep "$name" "$JW/$name.kpoke" ".kpoke.txt"
	# every kept file by an explicit loop over the globs (the globs are live: no `set -f` anywhere)
	for f in "$JW"/*.regs "$JW"/dump/*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	[ -f "$JW/heldparam.bin" ] && keep "$name" "$JW/heldparam.bin" ".heldparam.bin"
	[ -f "$JW/heldtadata.bin" ] && keep "$name" "$JW/heldtadata.bin" ".heldtadata.bin"
	# the knobs back to the defaults before anything else (health, the next reset, a stop)
	if [ "$rgn" = 1 ]; then
		rgn_set 0 || { echo "## STOP: render_rgn_arrays does not read back 0 after $name ($(rgn_now))"; exit 19; }
		mark "rgn-back $name 0"
	fi
	if [ "$pbv" != 0x422 ]; then
		pb_set 0x422 || { echo "## STOP: render_pb_pages does not read back 0x422 after $name ($(pb_now))"; exit 19; }
		mark "pb-back $name 0x422"
	fi
	# 1. the kernel itself in trouble: stop at once, touch nothing more
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$name.dmesg" "$JW/$name.out" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job
	if [ "$mode" = held ]; then
		fr=$(fault_req "$JW/snap1.regs")
		if [ "$fr" -ne 0 ]; then class=fault
		elif [ "$heldmsg" = yes ]; then class=hang
		elif [ "$rc" -eq 0 ]; then class=ok
		else class=fail; fi
	else
		class=$(classify_plain "$JW/$name.out" "$JW/$name.dmesg" "$rc")
	fi
	if [ "$class" = fail ]; then
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$JW/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:|^sgxfive-test: " "$JW/$name.out"; then class=ok; fi ;;
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
		# the fault's word: the kernel's line of the job's slice (plain) or the held snap 1 (held)
		if [ "$mode" = held ]; then fr1=$(regval "$JW/snap1.regs" 0x0c04); fint=$(( ${fr1:-0} & 0xffff )); fword=$(regval "$JW/snap1.regs" 0x0c08)
		else fint=$(fault_int "$JW/$name.dmesg"); fword=$(fault_word "$JW/$name.dmesg"); fi
		echo "  fault: BIF_INT_STAT bits 15:0 ${fint:-unread}, BIF_FAULT ${fword:-unread}"
		mark "fault $name ${fint:-unread} ${fword:-unread}"
		if [ -z "$grp" ]; then
			echo "## STOP: unexpected fault in $name"
			[ "$mode" = plain ] && reset_gpu
			strict_health "$name" </dev/null; exit 4
		fi
		gv=$(printf '%s' "$grp" | tr -c 'A-Za-z0-9' '_'); eval "HYPO_$gv=\$(( \${HYPO_$gv:-0} + 1 ))"; eval "n=\$HYPO_$gv"
		echo "  fault $n of at most $gmax in group $grp (a hypothesis: measured); fault-class events of the stage: $FAULT_EVENTS of $FAULT_LIMIT"
		[ "$n" -ge "$gmax" ] && SKIP_GRPS="$SKIP_GRPS $grp"
		strict_health "$name" </dev/null
		if [ "${fint:-x}" != 256 ] || ! num_word "${fword:-x}" 0x10000011 || grep -q 'recovery failed: -110' "$JW/$name.dmesg"; then
			echo "## STOP: the fault of $name is not E845's 3D-side word (bits 15:0 ${fint:-unread}, BIF_FAULT ${fword:-unread}) or a -110: stop (rc 18)"
			exit 18
		fi
		if [ "$FAULT_EVENTS" -ge "$FAULT_LIMIT" ] && [ "$i" -lt "$TOTAL" ]; then
			echo "## STOP: the $FAULT_EVENTS-th fault-class event of the stage ($FAULT_LIMIT is the limit) with rows left: stop after $name"
			exit 15
		fi ;;
	hang)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		echo "## STOP: unexpected hang in $name"
		[ "$mode" = plain ] && reset_gpu
		strict_health "$name" </dev/null; exit 4 ;;
	fail) echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	esac
	# the job's files are kept (and its health pair, if any): its work directory goes
	rm_work "$JW"
done
JW=$WROOT/end; mkdir -p "$JW"
reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
health end </dev/null
rm_work "$JW"
echo "## end: $njob jobs of $STAGE"
