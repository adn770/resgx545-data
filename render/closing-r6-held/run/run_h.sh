#!/bin/bash
# SPDX-License-Identifier: MIT
# run_h.sh STAGE FROZEN_SHA256 ATTEMPT: one r6-held part H job table on the laptop, one row a line of tables/STAGE.txt in file order.
# FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (h.sh passes it): the laptop's copy must be that file, and the table and the
# runner files must be in it.  ATTEMPT names the output directory ~/scratch/r6h/out/ATTEMPT/STAGE, which must not exist or be empty.
# SIGPIPE and SIGHUP are ignored (a dropped ssh does not stop a stage half way); everything printed also goes to $KEEP/runner.log.
# From r6-render4x's run_stage.sh (round 6's files, free space, strict health) and round 4's stage h cells (closing4/r4-render4x,
# E848), with the new kernel's bif_flush (fork r6-kernel 3f0b3e74) and the stop rules of rank-round6.md R6-5 / DECISIONS-R6 R6-5 (a).
# Table header lines:  #stage NAME   #limit N (the fault-class events the stage may take: held faults and replays together)
# Line: name|set|risk|knobs|rt|args        (the tool is $T, the job's directory $W)
#   knobs  words (space separated), only these:
#            gate         s0's n0: no tool; `1` written to debugfs bif_flush with nothing held: it must be refused (status not 0, the
#                         message "busy"), BIF_CTRL the same in the registers before and after, no "bif_flush:" kernel line; else rc 23
#            rgn:1        after the job's reset render_rgn_arrays is written 1 and read back (rc 19); after the job 0 (rc 19); the trap
#                         writes 0 at every exit
#            held         the job runs in the background with hold_recovery Y (read back Y, else rc 9); registers (debugfs regs) before
#                         it (snap 0), HOLD_READ s after the launch (snap 1) and HOLD_GAP s later (snap 2); [flush]; then, the hold STILL
#                         Y, the kernel's own debugfs reset (the held recovery); hold_recovery N (read back, rc 11), snap 3; a fault still
#                         latched gets one more reset (snap 4), then the session stops (rc 10)
#            flush        (with held) after snap 2, `1` written to debugfs bif_flush while the recovery is held, its status and message
#                         kept (NAME.flush.txt), then the registers (snap f); a refused flush voids the K2 rows: the cell goes on to
#                         its end and health, then the stage stops (rc 23)
#            cell:KIND    (with held) after the reset: the follow-up KIND (fill: one fill; health: none), then health triangles (`tri`)
#                         one by one until one draws, THREE at most (no reset between them); each step keeps its output, its kernel-log
#                         slice (by its own marker) and its registers; the third failing one ends the session with the knobs restored
#                         and no further reset (rc 17: the lead decides)
#            hypo:G:MAX   a held job's FAULT is the stated hypothesis of the group: measured; after MAX the rest of the group is skipped
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every `tri` row
#          any other word is refused: rc 7, nothing runs
#   rt     "-" only
# Peek (CR_DPM_TASK_STATE, explore only): read before each job (peek0), during the hold (peek1), after the reset (peek3), kept.
# STOP RULES (R6-5 a, rank-round6.md R6-5): a fault, hang or failure outside a held job or a cell step ends the stage (strict health,
# rc 4); a held job's fault whose BIF_INT_STAT bits 15:0 are not 0x0004 or whose BIF_FAULT is not a 0x2xxxx page with SB 6 (E848's
# shape), or a step's fault that is not the held job's page and SB (any list), ends it (strict health, rc 18); two cells IN A ROW each
# with an "SGX recovery failed: -110" in their kernel-log slices end it after the second's health (rc 22); the LIMIT-th fault-class
# event of the stage with rows left ends it (rc 15: with 6 cells, 6 held faults, one replay a cell and three more); the third failing
# triangle of a cell (rc 17); a fatal kernel message rc 3, a job that did not return rc 6 (nothing but the knob restore and the exit
# log touch the machine after either).  After every cell: strict health (the first fill and triangle must draw, else rc 16).
# Exit status: 0 stage done; 1 preflight; 3 FATAL kernel message; 4 unexpected hang, fault or failure; 5 failed health recovery;
# 6 a job did not return; 7 a forbidden knob; 9 hold not Y; 10 a held fault still latched after two resets; 11 hold not back to N;
# 12 registers unreadable; 13 the reset before a job failed; 14 a fault latched before a job; 15 the stage's fault-class limit with rows
# left; 16 strict health failed; 17 a cell's third triangle failed; 18 a fault of another shape; 19 a knob did not read back; 21 less
# than MIN_FREE_MB free on ~; 22 two cells in a row with a -110; 23 the bif_flush gate or a held flush did not behave as the fork says.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours (bif_flush is the
# kernel's own sequence), no loop that waits.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
FZ=$DIR/../FROZEN.sha256
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
[ -f "$FZ" ] || { echo "no $FZ: run run/stage_h.sh again"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$FZ" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$FZ" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_h.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (h.sh passes it)"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|gate|rgn:1|held|flush|hypo:[a-z0-9]+:[0-9]+|cell:(fill|health))$/) { print $1 ": " k[i]; bad=1 } if ($5 != "-") { print $1 ": rt " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or rt that r6-held does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $6 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without --keep-going"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $4 ~ /(^| )(flush|cell:[a-z]+)( |$)/ && $4 !~ /(^| )held( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: flush or cell on a row that is not held"; exit 7; }
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-0}
. "$DIR/lib_h.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$FZ"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_h.sh run_h.sh h.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done

# ---- one step of a cell: a plain tool call after the held job, with its own marker, slice, registers ----------------------------
# cell_step NAME STEP ARGS...: prints the step's class (ok, fault, hang, fail); stops: 3 fatal, 6 freeze, 12 registers
STEP_CLASS=""
cell_step() {
	local nm=$1 st=$2 rc cls
	shift 2
	echo "  step $st: $T $*"
	mark_case "$nm.$st"
	sudo -n timeout -k 10 "$STEP_TIMEOUT" "$T" "$@" > "$JW/$nm.$st.out" 2>&1 </dev/null
	rc=$?
	slice_since "resgx545 case $nm.$st $RUN" > "$JW/$nm.$st.dmesg"
	snap "$nm" "$st" || { echo "## STOP: registers unreadable after step $st of $nm"; exit 12; }
	keep "$nm.$st" "$JW/$nm.$st.out"
	keep "$nm.$st" "$JW/$nm.$st.dmesg" ".dmesg"
	keep "$nm" "$JW/snap$st.regs" ".snap$st.regs"
	if [ "$rc" -eq 124 ]; then echo "## STOP: step $st of $nm did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$nm.$st.dmesg" "$JW/$nm.$st.out" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG in step $st of $nm"; FATAL_STOP=1; exit 3
	fi
	cls=$(classify_plain "$JW/$nm.$st.out" "$JW/$nm.$st.dmesg" "$rc")
	if [ "$cls" = ok ] && ! grep -q '^diff: 0 of' "$JW/$nm.$st.out"; then cls=fail; fi
	echo "  step $st: rc $rc class $cls"
	mark "class $nm.$st $cls"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$nm.$st" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$*" \
		"$rc" "$cls" step - - no >> "$KEEP/cases.tsv"
	STEP_CLASS=$cls
	[ "$(minus110 "$JW/$nm.$st.dmesg")" = 1 ] && CELL110=1
	if [ "$cls" = fault ]; then
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		sw=$(fault_word "$JW/$nm.$st.dmesg"); si=$(fault_int "$JW/$nm.$st.dmesg")
		echo "  step $st fault: BIF_INT_STAT bits 15:0 ${si:-unread}, BIF_FAULT ${sw:-unread} (the job's ${JOBWORD:-unread}); events $FAULT_EVENTS of $FAULT_LIMIT"
		mark "fault $nm.$st ${si:-unread} ${sw:-unread}"
		# a replay is the held job's page and SB through any list: bits 31:4 equal, requestor bit 2
		if [ "${si:-x}" != 4 ] || [ -z "${sw:-}" ] || [ -z "${JOBWORD:-}" ] || [ $(( sw >> 4 )) -ne $(( JOBWORD >> 4 )) ]; then
			echo "## STOP: step $st of $nm faulted with another shape (bits 15:0 ${si:-unread}, BIF_FAULT ${sw:-unread}, the job's ${JOBWORD:-unread}): rc 18"
			strict_health "$nm" </dev/null; exit 18
		fi
	elif [ "$cls" != ok ]; then
		echo "## STOP: step $st of $nm ended $cls (rc $rc): neither a draw nor a replay"
		reset_gpu; strict_health "$nm" </dev/null; exit 4
	fi
	return 0
}
# cell_tris NAME: health triangles one by one until one draws, three at most (written out, no loop)
cell_tris() {
	local nm=$1
	cell_step "$nm" t1 tri; [ "$STEP_CLASS" = ok ] && return 0
	cell_step "$nm" t2 tri; [ "$STEP_CLASS" = ok ] && return 0
	cell_step "$nm" t3 tri; [ "$STEP_CLASS" = ok ] && return 0
	echo "## STOP: the third triangle failed after $nm: the knobs are restored, no further reset (the lead decides what next)"
	NO_MORE_RESET=1; FATAL_STOP=1; exit 17
}

# ---- the rows ---------------------------------------------------------------------------------------------------------------
begin
njob=0; SKIP_GRPS=""; FAULT_EVENTS=0; PREV110=0
TOTAL=$(grep -v '^#' "$FILE" | grep -vc '^$')
for i in $(seq 1 "$TOTAL"); do
	line=$(grep -v '^#' "$FILE" | grep -v '^$' | sed -n "${i}p")
	IFS='|' read -r name sset risk knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0; mode=plain; rgn=0; cell=""; flush=0
	for k in $knobs; do
		case "$k" in
		hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;;
		held) mode=held ;;
		gate) mode=gate ;;
		rgn:1) rgn=1 ;;
		flush) flush=1 ;;
		cell:*) cell=${k#cell:} ;;
		expectdiff|-) ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp reached its $gmax events"; continue; } ;; esac
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; mkdir -p "$JW"; W=$JW
	echo "== $name set=$sset risk=$risk mode=$mode knobs=[$knobs]"
	space_ok || { echo "## STOP: less than $MIN_FREE_MB MiB free on ~ before $name ($(free_kb) KiB)"; exit 21; }
	echo "  free on ~: $(free_kb) KiB"
	reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; }
	rgn_set "$rgn" || { echo "## STOP: render_rgn_arrays does not read back $rgn before $name ($(rgn_now))"; exit 19; }
	mark "rgn $name $rgn"
	knobs_ok "$rgn" || { echo "## STOP: a knob is not as the row asks before $name (hold_recovery $(hold_now), render_rgn_arrays $(rgn_now), render_pb_pages $(pb_now), render_tail_room $(room_now))"; exit 19; }
	mark "knobs-read $name hold_recovery=$(hold_now) render_rgn_arrays=$(rgn_now) render_pb_pages=$(pb_now) render_tail_room=$(room_now)"
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	peek "$name" 0
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	eval "set -- $args"
	rrc=-; heldmsg=no; fr=-; CELL110=0; JOBWORD=""; FLUSH_BAD=0
	if [ "$mode" = gate ]; then
		echo "  gate: bif_flush 1 with nothing held (the fork: -EBUSY)"
		mark_case "$name"
		flush_write "$JW/flush.err"; frc=$?
		printf 'rc %s\n%s\n' "$frc" "$(cat "$JW/flush.err")" > "$JW/$name.out"
		snap "$name" 1 || { echo "## STOP: registers unreadable after $name"; exit 12; }
		peek "$name" 1
		rc=$frc
	elif [ "$mode" = plain ]; then
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
		peek "$name" 1
		sleep "$HOLD_GAP"
		snap "$name" 2
		f2=$(fault_req "$JW/snap2.regs")
		if [ "$flush" = 1 ] && [ "${f2:-0}" = 0 ]; then
			echo "  no fault latched at snap 2: no flush (nothing is held; the cell has nothing to measure)"
			mark "noflush $name"
		elif [ "$flush" = 1 ]; then
			# K2: the BIF invalidate while the recovery is held (the kernel's own sequence; the hold stays)
			mark "flush $name"
			flush_write "$JW/flush.err"; frc=$?
			printf 'rc %s\n%s\n' "$frc" "$(cat "$JW/flush.err")" > "$JW/$name.flush.txt"
			echo "  bif_flush 1: status $frc $(head -c 120 "$JW/flush.err")"
			[ "$frc" = 0 ] || FLUSH_BAD=1
			snap "$name" f
		fi
		# the reset while the hold is still Y: it becomes the held recovery and blames the held job
		mark "reset $name"
		reset_gpu; rrc=$?
		echo "  debugfs reset: status $rrc"
		hold_back=$(set_hold N); echo "  hold_recovery written N, read back $hold_back"; mark "readback $name hold_recovery=$hold_back"
		snap "$name" 3
		peek "$name" 3
		f3=$(fault_req "$JW/snap3.regs")
		if [ -z "$f3" ] || [ "$f3" -ne 0 ]; then
			echo "  the fault is still latched after the reset (bits 15:0 = ${f3:-unread}): one more reset"
			mark "reset2 $name"
			reset_gpu
			snap "$name" 4
			f4=$(fault_req "$JW/snap4.regs")
			if [ -z "$f4" ] || [ "$f4" -ne 0 ]; then
				NO_MORE_RESET=1
				for f in "$JW"/*.regs "$JW"/peek*.txt; do [ -f "$f" ] && keep "$name" "$f" ".${f##*/}"; done; keep "$name" "$JW/$name.out"
				echo "## STOP: the held fault of $name did not clear after two resets (bits 15:0 = ${f4:-unread}): no further reset (PREFLIGHT.md)"
				exit 10
			fi
		fi
		[ "$hold_back" = N ] || { echo "## STOP: hold_recovery read back $hold_back after $name"; exit 11; }
		wait "$JOBPID"; rc=$?; JOBPID=""
	fi
	echo "  rc $rc $(grep -E '^(job|tri:|BIF_INT_STAT|rc )' "$JW/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	heldmsg=no; grep -q "recovery held (debugfs hold_recovery)" "$JW/$name.dmesg" && heldmsg=yes
	[ "$(minus110 "$JW/$name.dmesg")" = 1 ] && CELL110=1
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	[ -f "$JW/$name.flush.txt" ] && keep "$name" "$JW/$name.flush.txt" ".flush.txt"
	for f in "$JW"/*.regs "$JW"/peek*.txt; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	if [ "$rgn" = 1 ]; then
		rgn_set 0 || { echo "## STOP: render_rgn_arrays does not read back 0 after $name ($(rgn_now))"; exit 19; }
		mark "rgn-back $name 0"
	fi
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$name.dmesg" "$JW/$name.out" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# classify
	if [ "$mode" = gate ]; then
		c0=$(regval "$JW/snap0.regs" 0x0c00); c1=$(regval "$JW/snap1.regs" 0x0c00)
		if [ "$rc" -ne 0 ] && grep -qi 'busy' "$JW/flush.err" && [ -n "$c0" ] && [ "$c0" = "$c1" ] && ! grep -q 'bif_flush:' "$JW/$name.dmesg"; then
			class=ok
		else
			class=fail
		fi
	elif [ "$mode" = held ]; then
		fr=$(fault_req "$JW/snap1.regs")
		if [ "$fr" -ne 0 ]; then class=fault
		elif [ "$heldmsg" = yes ]; then class=hang
		elif [ "$rc" -eq 0 ]; then class=ok
		else class=fail; fi
	else
		class=$(classify_plain "$JW/$name.out" "$JW/$name.dmesg" "$rc")
		if [ "$class" = fail ]; then
			case " $knobs " in *" expectdiff "*)
				if [ "$rc" -eq 1 ] && grep -q '^diff:' "$JW/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:|^sgxfive-test: " "$JW/$name.out"; then class=ok; fi ;;
			esac
		fi
		[ "$class" = ok ] && ! grep -q '^diff: 0 of' "$JW/$name.out" && class=fail
	fi
	echo "  class $class (fault bits 15:0 at snap 1: $fr, hold message: $heldmsg)"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" \
		"$rc" "$class" "$mode" "$fr" "$rrc" "$heldmsg" >> "$KEEP/cases.tsv"
	case "$mode.$class" in
	gate.ok) ;;
	gate.*) echo "## STOP: the bif_flush gate did not behave as the fork says (status $rc, BIF_CTRL $c0 -> $c1): rc 23"; reset_gpu; strict_health "$name" </dev/null; exit 23 ;;
	plain.ok) ;;
	plain.fault|plain.hang) echo "## STOP: unexpected $class in $name"; reset_gpu; strict_health "$name" </dev/null; exit 4 ;;
	plain.*|held.fail) echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	held.hang) echo "## STOP: unexpected hang in $name"; strict_health "$name" </dev/null; exit 4 ;;
	held.ok)
		echo "  $name did not fault, so there is no replay to measure: one health check"
		strict_health "$name" </dev/null ;;
	held.fault)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		fr1=$(regval "$JW/snap1.regs" 0x0c04); fint=$(( ${fr1:-0} & 0xffff )); JOBWORD=$(regval "$JW/snap1.regs" 0x0c08)
		echo "  fault: BIF_INT_STAT bits 15:0 $fint, BIF_FAULT ${JOBWORD:-unread}; fault-class events $FAULT_EVENTS of $FAULT_LIMIT"
		mark "fault $name $fint ${JOBWORD:-unread}"
		if [ -z "$grp" ]; then echo "## STOP: a held job outside a hypothesis group faulted ($name)"; strict_health "$name" </dev/null; exit 4; fi
		gv=$(printf '%s' "$grp" | tr -c 'A-Za-z0-9' '_'); eval "HYPO_$gv=\$(( \${HYPO_$gv:-0} + 1 ))"; eval "n=\$HYPO_$gv"
		[ "$n" -ge "$gmax" ] && SKIP_GRPS="$SKIP_GRPS $grp"
		if [ "$fint" != 4 ] || [ -z "$JOBWORD" ] || [ $(( (JOBWORD >> 4) & 0xf )) -ne 6 ] || [ $(( JOBWORD >> 28 )) -ne 2 ]; then
			echo "## STOP: the held fault of $name is not E848's shape (bits 15:0 $fint, BIF_FAULT ${JOBWORD:-unread}): rc 18"
			strict_health "$name" </dev/null; exit 18
		fi
		# the cell: its follow-up, then the triangles; no reset of ours in between
		if [ "$cell" = fill ]; then
			cell_step "$name" fill fill
		fi
		cell_tris "$name"
		strict_health "$name" </dev/null ;;
	esac
	# the stage's limits after the cell's health
	if [ "$FLUSH_BAD" = 1 ]; then echo "## STOP: bif_flush was refused with $name held (see $name.flush.txt): the K2 rows are void, rc 23"; exit 23; fi
	if [ "$CELL110" = 1 ] && [ "$PREV110" = 1 ]; then
		echo "## STOP: a -110 in two cells in a row (the boot after a reset timed out): rc 22"; exit 22
	fi
	PREV110=$CELL110
	echo "  -110 in this row: $CELL110"
	mark "minus110 $name $CELL110"
	if [ "$FAULT_EVENTS" -ge "$FAULT_LIMIT" ] && [ "$i" -lt "$TOTAL" ] && [ "$FAULT_LIMIT" -gt 0 ]; then
		echo "## STOP: $FAULT_EVENTS fault-class events of the stage ($FAULT_LIMIT is the limit) with rows left: stop after $name"
		exit 15
	fi
	rm_work "$JW"
done
JW=$WROOT/end; mkdir -p "$JW"
reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
health end </dev/null
rm_work "$JW"
echo "## end: $njob rows of $STAGE"
