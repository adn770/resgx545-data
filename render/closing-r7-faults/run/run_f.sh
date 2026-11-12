#!/bin/bash
# SPDX-License-Identifier: MIT
# run_f.sh STAGE FROZEN_SHA256 ATTEMPT: one r7-faults job table on the laptop, one row a line of tables/STAGE.txt in file order.
# FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (f.sh passes it): the laptop's copy must be that file, and the table and the
# runner files must be in it.  ATTEMPT names the output directory ~/scratch/r7f/out/ATTEMPT/STAGE, which must not exist or be empty.
# SIGPIPE and SIGHUP are ignored (a dropped ssh does not stop a stage half way); everything printed also goes to $KEEP/runner.log.
# From r6-held's run_h.sh (closing6/r6-held: E848's held cells on this module) with the plan's stages (closing7/c/exp-faults-r7.md
# 1.4, 1.5, 2.2) and stop rules (decision 3 (a): a -110 is a reading).
# Table header lines:  #stage NAME   #limit N (the fault-class events the stage may take: held faults, replays and hangs together)
# Line: name|set|risk|knobs|rt|args        (the tool is $T, the staged programs $S, the job's directory $W)
#   knobs  words (space separated), only these:
#            gate         s0's n0: no tool; CR_BIF_CTRL.CLEAR_FAULT flipped twice through debugfs kregnow (0x0c00^=0x10, set then
#                         cleared) with nothing held; the statuses kept (NAME.txt), the kernel's lines in the slice
#            probe        an L row: the probe fill runs plainly; a hang ("job hung") is a reading, followed by strict health
#            rgn:1        after the job's reset render_rgn_arrays is written 1 and read back (rc 19); after the job 0 (rc 19); the trap
#                         writes 0 at every exit
#            held         the job runs in the background with hold_recovery Y (read back Y, else rc 9); registers (debugfs regs) before
#                         it (snap 0), HOLD_READ s after the launch (snap 1, kept as NAME.regs) and HOLD_GAP s later (snap 2); [clr];
#                         [long]; then, the hold STILL Y, the kernel's own debugfs reset (the held recovery); hold_recovery N (read
#                         back, rc 11), snap 3; a fault still latched gets one more reset (snap 4), then the session stops (rc 10)
#            clr          (with held) after snap 2: kregnow 0x0c00^=0x10 (CLEAR_FAULT set), snap c1, kregnow 0x0c00^=0x10 (cleared),
#                         snap c2 (E826's write and its two reads)
#            long         (with held) after snap 2: LONG_EXTRA s more before the reset (about 9 s from the launch: E826 f2's 9.1 s)
#            cell:health  (with held) after the reset: health triangles (`tri`) one by one until one draws, THREE at most (no reset
#                         between them); each step keeps its output, its kernel-log slice (by its own marker) and its registers; the
#                         third failing one ends the session with the knobs restored and no further reset (rc 17: the lead decides)
#            ctl640       (with held) the stage's premise: if the first boot after this cell's held reset timed out, the stage stops
#                         after the cell's health (rc 24: the plan's stop rule 2, "a 640 x 480 control cell times out")
#            hypo:G:MAX   a held job's FAULT is the stated hypothesis of the group: measured; after MAX the rest of the group is skipped
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every `tri` row
#          any other word is refused: rc 7, nothing runs
#   rt     "-" only
# STOP RULES (plan 1.5 and 2.2; decision 3 (a)).  SESSION (exit, no resume): the second boot of one recovery fails or "SGX boot: BIF
# fault during reset" (rc 26, at once, no further reset); strict health after a cell or a hang fails (rc 16); a cell's third triangle
# fails (rc 17); the session's BUDGET_110-th timed-out boot (rc 25, after the cell's health); a fatal kernel message (rc 3), a job that
# did not return (rc 6).  STAGE (rc 24, after the row's health; the driver goes on with the next stage): a fault word other than
# 0x90004, a timed-out boot's dump with BIF_INT_STAT other than 0x000d0004 or BIF_FAULT outside the pages 0x10000-0x10fff and
# 0x20000-0x20fff, a fault through list 15 (word_problem); a ctl640 cell whose held reset timed out; a held job that faults with
# another shape (BIF_INT_STAT bits 15:0 not 4, or not page 0x2xxxx with SB 6); a probe that faults; the LIMIT-th fault-class event
# of the stage with rows left (l: the third hang).
# Exit status: 0 stage done; 1 preflight; 3 FATAL kernel message; 4 unexpected hang, fault or failure; 5 failed health recovery;
# 6 a job did not return; 7 a forbidden knob; 9 hold not Y; 10 a held fault still latched after two resets; 11 hold not back to N;
# 12 registers unreadable; 13 the reset before a job failed with no boot up after it; 14 a fault latched before a job; 16 strict
# health failed; 17 a cell's third triangle failed; 18 the laptop stopped answering a BIF read or write (E317); 19 a knob did not read
# back; 21 less than MIN_FREE_MB free on ~; 24 the stage stopped by its rule; 25 the session's budget of timed-out boots; 26 a dead
# boot (two failed boots in a row, or a BIF fault during the reset).
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours but the
# CLEAR_FAULT pair (through the kernel's kregnow), no loop that waits.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
FZ=$DIR/../FROZEN.sha256
S=$DIR/../bins
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
[ -f "$FZ" ] || { echo "no $FZ: run run/stage_f.sh again"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$FZ" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$FZ" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_f.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (f.sh passes it)"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|gate|probe|rgn:1|held|clr|long|ctl640|hypo:[a-z0-9]+:[0-9]+|cell:health)$/) { print $1 ": " k[i]; bad=1 } if ($5 != "-") { print $1 ": rt " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or rt that r7-faults does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $6 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without --keep-going"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $4 ~ /(^| )(clr|long|ctl640|cell:[a-z]+)( |$)/ && $4 !~ /(^| )held( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: clr, long, ctl640 or cell on a row that is not held"; exit 7; }
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-0}
. "$DIR/lib_f.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$FZ"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_f.sh run_f.sh f.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done
for b in $(awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^probe / { print $6 }' "$FILE" | sed -n 's#.*"\$S/\([a-z0-9-]*\.bin\)".*#\1#p'); do
	want=$(expect_sha "bins/$b"); got=$(sha "$S/$b" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "bins/$b is not the frozen one"; exit 1; }
done

# ---- one step of a cell: a plain tool call after the held job, with its own marker, slice, registers ----------------------------
# cell_step NAME STEP ARGS...: sets STEP_CLASS (ok, fault, hang, fail); stops: 3 fatal, 6 freeze, 12 registers, 26 a dead boot
STEP_CLASS=""
cell_step() {
	local nm=$1 st=$2 rc cls sw si
	shift 2
	echo "  step $st: $T $*"
	mark_case "$nm.$st"
	sudo -n timeout -k 10 "$STEP_TIMEOUT" "$T" "$@" > "$JW/$nm.$st.out" 2>&1 </dev/null
	rc=$?
	slice_since "resgx545 case $nm.$st $RUN" > "$JW/$nm.$st.dmesg"
	snap "$nm" "$st" || { echo "## STOP: registers unreadable after step $st of $nm"; exit 12; }
	keep "$nm.$st" "$JW/$nm.$st.out"
	keep "$nm.$st" "$JW/$nm.$st.dmesg" ".dmesg"
	keep "$nm.$st" "$JW/snap$st.regs" ".regs"
	if [ "$rc" -eq 124 ]; then echo "## STOP: step $st of $nm did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$nm.$st.dmesg" "$JW/$nm.$st.out" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG in step $st of $nm"; FATAL_STOP=1; exit 3
	fi
	dead_check "$JW/$nm.$st.dmesg" "step $st of $nm"
	cls=$(classify_plain "$JW/$nm.$st.out" "$JW/$nm.$st.dmesg" "$rc")
	if [ "$cls" = ok ] && ! grep -q '^diff: 0 of' "$JW/$nm.$st.out"; then cls=fail; fi
	echo "  step $st: rc $rc class $cls boots $(boots "$JW/$nm.$st.dmesg")"
	mark "class $nm.$st $cls"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$nm.$st" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$*" \
		"$rc" "$cls" step - - no >> "$KEEP/cases.tsv"
	STEP_CLASS=$cls
	if [ "$cls" = fault ]; then
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		sw=$(awk 'match($0, /BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+/) { s = substr($0, RSTART, RLENGTH); sub(/.* at /, "", s); print s; exit }' "$JW/$nm.$st.dmesg")
		si=$(awk 'match($0, /BIF fault 0x[0-9a-f]+ at/) { s = substr($0, RSTART + 12, RLENGTH - 15); print s; exit }' "$JW/$nm.$st.dmesg")
		echo "  step $st fault: BIF_INT_STAT ${si:-unread}, BIF_FAULT ${sw:-unread} (the job's ${JOBWORD:-unread}); events $FAULT_EVENTS of $FAULT_LIMIT"
		mark "fault $nm.$st ${si:-unread} ${sw:-unread}"
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
njob=0; SKIP_GRPS=""; FAULT_EVENTS=0
TOTAL=$(grep -v '^#' "$FILE" | grep -vc '^$')
for i in $(seq 1 "$TOTAL"); do
	line=$(grep -v '^#' "$FILE" | grep -v '^$' | sed -n "${i}p")
	IFS='|' read -r name sset risk knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0; mode=plain; rgn=0; cell=""; clr=0; long=0; ctl640=0
	for k in $knobs; do
		case "$k" in
		hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;;
		held) mode=held ;;
		gate) mode=gate ;;
		probe) mode=probe ;;
		rgn:1) rgn=1 ;;
		clr) clr=1 ;;
		long) long=1 ;;
		ctl640) ctl640=1 ;;
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
	mark "row $name"
	if ! reset_gpu; then
		# the reset before the job reported an error: a -110 is a reading if the boot after it came up (row_close counts it)
		slice_since "resgx545 r7f row $name $RUN" > "$JW/prereset.dmesg"
		dead_check "$JW/prereset.dmesg" "the reset before $name"
		case "$(boots "$JW/prereset.dmesg")" in
		*U) echo "  the reset before $name timed out a boot and the next came up: a -110, counted with the row" ;;
		*) echo "## STOP: the reset before $name failed (boots: $(boots "$JW/prereset.dmesg"))"; exit 13 ;;
		esac
	fi
	rgn_set "$rgn" || { echo "## STOP: render_rgn_arrays does not read back $rgn before $name ($(rgn_now))"; exit 19; }
	mark "rgn $name $rgn"
	knobs_ok "$rgn" || { echo "## STOP: a knob is not as the row asks before $name (hold_recovery $(hold_now), render_rgn_arrays $(rgn_now), render_pb_pages $(pb_now), render_tail_room $(room_now))"; exit 19; }
	mark "knobs-read $name hold_recovery=$(hold_now) render_rgn_arrays=$(rgn_now) render_pb_pages=$(pb_now) render_tail_room=$(room_now)"
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	eval "set -- $args"
	rrc=-; heldmsg=no; fr=-; JOBWORD=""; STOP24=""
	if [ "$mode" = gate ]; then
		echo "  gate: kregnow 0x0c00^=0x10 twice with nothing held (the fork: taken; BIF_CTRL 0x10, then back)"
		mark_case "$name"
		clr_write "$name" set; s1=$?
		snap "$name" c1 || { echo "## STOP: registers unreadable after the set in $name"; exit 12; }
		clr_write "$name" clear; s2=$?
		snap "$name" 1 || { echo "## STOP: registers unreadable after $name"; exit 12; }
		printf 'set rc %s\nclear rc %s\n' "$s1" "$s2" > "$JW/$name.out"
		rc=$(( s1 + s2 ))
	elif [ "$mode" = plain ] || [ "$mode" = probe ]; then
		echo "  cmd: $T $*"
		mark_case "$name"
		sudo -n timeout -k 10 "$JOB_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
		rc=$?
		snap "$name" 1 || { echo "## STOP: registers unreadable after $name"; exit 12; }
	else
		rb=$(set_hold Y); echo "  hold_recovery written Y, read back $rb"; mark "readback $name hold_recovery=$rb"
		[ "$rb" = Y ] || { echo "## STOP: hold_recovery read back $rb, wrote Y (the job did not start)"; exit 9; }
		echo "  cmd (held, background): $T $*"
		mark_case "$name"
		sudo -n timeout -k 10 "$HELD_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null &
		JOBPID=$!
		sleep "$HOLD_READ"
		snap "$name" 1 || { echo "## STOP: registers unreadable during $name"; exit 12; }
		sleep "$HOLD_GAP"
		snap "$name" 2
		if [ "$clr" = 1 ]; then
			# E826's write while the recovery is held: CLEAR_FAULT set, read, cleared, read (the kernel logs its reads too)
			mark "clr $name"
			clr_write "$name" set
			snap "$name" c1
			clr_write "$name" clear
			snap "$name" c2
		fi
		if [ "$long" = 1 ]; then
			mark "long $name $LONG_EXTRA"
			echo "  long hold: $LONG_EXTRA s more before the reset"
			sleep "$LONG_EXTRA"
			snap "$name" l
		fi
		# the reset while the hold is still Y: it becomes the held recovery and blames the held job
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
				for f in "$JW"/snap*.regs; do [ -f "$f" ] && keep "$name" "$f" ".${f##*/}"; done; keep "$name" "$JW/$name.out"
				echo "## STOP: the held fault of $name did not clear after two resets (bits 15:0 = ${f4:-unread}): no further reset (PREFLIGHT.md)"
				exit 10
			fi
		fi
		[ "$hold_back" = N ] || { echo "## STOP: hold_recovery read back $hold_back after $name"; exit 11; }
		wait "$JOBPID"; rc=$?; JOBPID=""
	fi
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*(failed|scratch \+)|rc |set rc|clear rc)' "$JW/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	heldmsg=no; grep -q "recovery held (debugfs hold_recovery)" "$JW/$name.dmesg" && heldmsg=yes
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	keep "$name" "$JW/snap1.regs" ".regs"
	for f in "$JW"/snap*.regs; do
		case "${f##*/}" in snap1.regs) ;; *) [ -f "$f" ] && keep "$name" "$f" ".${f##*/}" ;; esac
	done
	[ -f "$JW/$name.kw.txt" ] && keep "$name" "$JW/$name.kw.txt" ".kw.txt"
	if [ "$rgn" = 1 ]; then
		rgn_set 0 || { echo "## STOP: render_rgn_arrays does not read back 0 after $name ($(rgn_now))"; exit 19; }
		mark "rgn-back $name 0"
	fi
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$name.dmesg" "$JW/$name.out" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	dead_check "$JW/$name.dmesg" "$name"
	# classify
	if [ "$mode" = gate ]; then
		c0=$(regval "$JW/snap0.regs" 0x0c00); c1=$(regval "$JW/snapc1.regs" 0x0c00); c2=$(regval "$JW/snap1.regs" 0x0c00)
		if [ "$rc" -eq 0 ] && [ -n "$c0" ] && [ "$c0" = "$c2" ] && [ "$c1" != "$c0" ]; then class=ok; else class=fail; fi
	elif [ "$mode" = held ]; then
		fr=$(fault_req "$JW/snap1.regs")
		if [ "$fr" -ne 0 ]; then class=fault
		elif [ "$heldmsg" = yes ]; then class=hang
		elif [ "$rc" -eq 0 ]; then class=ok
		else class=fail; fi
	elif [ "$mode" = probe ]; then
		if bad_lines "$JW/$name.out" "$JW/$name.dmesg" | grep -Eq "BIF fault|faulted"; then class=fault
		elif [ "$rc" -eq 3 ] && grep -q 'failed: job hung' "$JW/$name.out" && grep -Eq 'job [0-9]+ hung' "$JW/$name.dmesg"; then class=hang
		elif [ "$rc" -eq 0 ] && grep -q 'scratch +0x000 ' "$JW/$name.out"; then class=ok
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
	echo "  class $class (fault bits 15:0 at snap 1: $fr, hold message: $heldmsg, boots in the job's slice: $(boots "$JW/$name.dmesg"))"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" \
		"$rc" "$class" "$mode" "$fr" "$rrc" "$heldmsg" >> "$KEEP/cases.tsv"
	case "$mode.$class" in
	gate.ok|plain.ok|probe.ok) ;;
	gate.*) echo "## STOP: the kregnow gate did not behave as the fork says (statuses $(tr '\n' ' ' < "$JW/$name.out"), BIF_CTRL $c0 -> $c1 -> $c2)"; reset_gpu; STOP24="the gate row"; health "$name" </dev/null ;;
	probe.hang)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		echo "  hang (a reading): events $FAULT_EVENTS of $FAULT_LIMIT; the kernel's recovery, then strict health"
		strict_health "$name" </dev/null ;;
	probe.fault) echo "## a probe faulted ($name): the stage stops after its health"; STOP24="a probe fault"; strict_health "$name" </dev/null ;;
	plain.fault|plain.hang) echo "## STOP: unexpected $class in $name"; reset_gpu; strict_health "$name" </dev/null; exit 4 ;;
	plain.*|probe.*|held.fail) echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	held.hang) echo "## STOP: unexpected hang in $name"; strict_health "$name" </dev/null; exit 4 ;;
	held.ok)
		echo "  $name did not fault, so there is no boot to read: one health check"
		strict_health "$name" </dev/null ;;
	held.fault)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		fr1=$(regval "$JW/snap1.regs" 0x0c04); fint=$(( ${fr1:-0} & 0xffff )); JOBWORD=$(regval "$JW/snap1.regs" 0x0c08)
		echo "  fault: BIF_INT_STAT bits 15:0 $fint, BIF_FAULT ${JOBWORD:-unread}, first boot after the held reset: $(boots "$JW/$name.dmesg" | cut -c1); fault-class events $FAULT_EVENTS of $FAULT_LIMIT"
		mark "fault $name $fint ${JOBWORD:-unread}"
		if [ -z "$grp" ]; then echo "## STOP: a held job outside a hypothesis group faulted ($name)"; strict_health "$name" </dev/null; exit 4; fi
		gv=$(printf '%s' "$grp" | tr -c 'A-Za-z0-9' '_'); eval "HYPO_$gv=\$(( \${HYPO_$gv:-0} + 1 ))"; eval "n=\$HYPO_$gv"
		[ "$n" -ge "$gmax" ] && SKIP_GRPS="$SKIP_GRPS $grp"
		if [ "$fint" != 4 ] || [ -z "$JOBWORD" ] || [ $(( (JOBWORD >> 4) & 0xf )) -ne 6 ] || [ $(( JOBWORD >> 28 )) -ne 2 ]; then
			echo "## the held fault of $name is not E848's shape (bits 15:0 $fint, BIF_FAULT ${JOBWORD:-unread}): the stage stops after its health"
			STOP24="a held fault of another shape"; strict_health "$name" </dev/null
		else
			if [ "$ctl640" = 1 ] && [ "$(boots "$JW/$name.dmesg" | cut -c1)" = T ]; then
				STOP24="the 640 x 480 control's held reset timed out (the premise of the stage is gone)"
			fi
			# the cell: the triangles; no reset of ours in between
			cell_tris "$name"
			strict_health "$name" </dev/null
		fi ;;
	esac
	row_close "$name"
	[ -n "$ROW_WORD" ] && STOP24="${STOP24:+$STOP24; }$ROW_WORD"
	if [ "$(used_110)" -ge "$BUDGET_110" ]; then
		echo "## STOP: the session's budget of $BUDGET_110 timed-out boots is reached after $name (its health ran): rc 25"; exit 25
	fi
	if [ -n "$STOP24" ]; then echo "## STOP (stage $STAGE): $STOP24, after $name: rc 24"; exit 24; fi
	if [ "$FAULT_EVENTS" -ge "$FAULT_LIMIT" ] && [ "$i" -lt "$TOTAL" ] && [ "$FAULT_LIMIT" -gt 0 ]; then
		echo "## STOP (stage $STAGE): $FAULT_EVENTS fault-class events ($FAULT_LIMIT is the limit) with rows left: stop after $name, rc 24"
		exit 24
	fi
	rm_work "$JW"
done
JW=$WROOT/end; mkdir -p "$JW"
mark "row end"
reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
health end </dev/null
row_close end
rm_work "$JW"
echo "## end: $njob rows of $STAGE"
