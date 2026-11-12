#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT: one R5-pixel job table on the laptop, one job a line of tables/STAGE.txt in file
# order.  FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (r3.sh passes it): the laptop's copy must be that file.
# ATTEMPT names the output directory ~/r5p-out/ATTEMPT/STAGE, which must not exist or be empty (one directory an attempt;
# nothing is merged).  SIGPIPE and SIGHUP are ignored (a dropped ssh does not stop a stage half way); everything printed also
# goes to $KEEP/runner.log.  Built from R2-pixel's runner (round 2): attempts, frozen checks, classification over the WHOLE
# output, health per stage; without its held jobs (R5-pixel expects no fault: any fault or hang stops the stage).
# Line: name|set|risk|knobs|rt|args        (the tool is $T, staged programs $S, the job's directory $W)
#   knobs  words (space separated):
#            noreset        no GPU reset before this job (default: a reset before every job)
#            stophang       a hang in this job ends the stage (every hang, fault or failure does anyway)
#            expectdiff     rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on
#                           every `tri` row (a row without it is refused before anything runs)
#            expectnopix    rc 3 with `failed: no pixel written` is a result, class ok
#            s2             CR_EVENT_STATUS2 (0x0118) is read from the debugfs regs right after the job's reset (kept as
#                           NAME.pre.regs.txt.gz; a value other than 0x400 stops the stage, rc 16) and after the job
#                           (NAME.after.regs.txt.gz)
#            sweep:G:MASK   a sweep group: once a job of group G ends with a bit of MASK set in STATUS2, every later row of G
#                           that carries `sweep:G:MASK` is not run (class `skipped`); a row carrying `watch:G:MASK` is never
#                           skipped but sets the group like a sweep row (work inside what an earlier run proved intact)
#            proofstop:HEX:COUNT   the loop proof of the row: the tool output must contain `o0 HEX (COUNT of COUNT)`; if not,
#                           the stage stops after the health check (rc 17; a loop proof of a new shape or a bridge row)
#            want2:MASK:VAL   a BRIDGE control of the stage (R5-pixel: the rgn4 module must reproduce round 3's value): after the job
#                           (STATUS2 & MASK) must equal VAL (numbers, e.g. want2:0x40:0x40); else the stage stops after the health
#                           check (rc 18).  Needs the knob s2 on the same row.
#   rt     "-", or a regtimeline register list: the job runs under it (read-only, /dev/mem)
# Every job: kernel-log markers and the case marker ("resgx545 case NAME RUN") right before the job starts; the kernel log
# after the case marker, taken after the job's reset and before its health triangle, is kept as NAME.dmesg.gz.  cases.tsv
# gets rc, class and a note.  Classes: ok, fault, hang, fail, skipped (the output and the kernel log are searched whole).
# Exit status: 0 stage done; 1 preflight (also a table or program that is not the frozen one, a tri row without expectdiff,
# a laptop FROZEN.sha256 that is not the Mac's, a tool, regtimeline or kernel module that is not the pinned one); 3 FATAL
# kernel message; 4 an unexpected hang, fault or failure; 5 the first failed health recovery; 6 a job did not return
# (freeze); 7 a forbidden knob; 8 a staged program is missing; 12 the registers could not be read; 13 the reset before a job
# failed; 14 a fault is latched before a job; 16 STATUS2 is not 0x400 after the reset; 17 a loop proof failed; 18 a bridge
# control (knob want2) read otherwise.  On 3 and 6
# nothing but the knob restore touches the machine.  No reboot, no boot-loader change, no kernel build, no clock-gate
# register, no trc_hazard, no register write of ours, no loop that waits.
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
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_r5.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (r3.sh passes it)"; exit 1; }
NEED_RT=$(awk -F'|' '!/^#/ && NF>=6 && $5!="-" {f=1} END{print f+0}' "$FILE")
export NEED_RT
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
. "$DIR/lib_r5.sh"
# the table, the runner files and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$DIR/../FROZEN.sha256"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_r5.sh run_stage.sh r5.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run run/stage_r5.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
begin
njob=0; SWEEP_SET=" "
TOTAL=$(grep -v '^#' "$FILE" | grep -vc '^$')
for i in $(seq 1 "$TOTAL"); do
	line=$(grep -v '^#' "$FILE" | grep -v '^$' | sed -n "${i}p")
	IFS='|' read -r name sset risk knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	s2=0; sweepg=""; sweepm=0; swmode=""; proofv=""; proofn=0; want2m=""; want2v=""
	for k in $knobs; do
		case "$k" in
		noreset|stophang|expectdiff|expectnopix) ;;
		s2) s2=1 ;;
		sweep:*|watch:*) swmode=${k%%:*}; r=${k#*:}; sweepg=${r%%:*}; sweepm=$(( ${r#*:} )) ;;
		proofstop:*) r=${k#proofstop:}; proofv=${r%%:*}; proofn=${r#*:} ;;
		want2:*) r=${k#want2:}; want2m=${r%%:*}; want2v=${r#*:} ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	if [ "$swmode" = sweep ]; then
		case "$SWEEP_SET" in *" $sweepg "*)
			echo "== $name set=$sset: skipped (sweep $sweepg already set its bit)"
			printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" "-" "skipped" "sweep stopped" >> "$KEEP/cases.tsv"
			continue ;;
		esac
	fi
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; mkdir -p "$JW/dump"; W=$JW
	echo "== $name set=$sset risk=$risk knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) : ;; *) reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; } ;; esac
	mark "knobs $name [$knobs]"
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	pre2=""
	if [ "$s2" = 1 ]; then
		cp "$JW/snap0.regs" "$JW/pre.regs.txt"
		keep "$name" "$JW/pre.regs.txt" ".pre.regs.txt"
		pre2=$(status2_of "$JW/pre.regs.txt")
		echo "  STATUS2 before: ${pre2:-unreadable}"
		if [ -z "$pre2" ] || [ "$pre2" -ne $((0x400)) ]; then
			echo "## STOP: STATUS2 is ${pre2:-unreadable} after the reset before $name (not 0x400): the job did not run"
			printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" "-" "fail" "pre STATUS2 not 0x400" >> "$KEEP/cases.tsv"
			health "$name" </dev/null; exit 16
		fi
	fi
	eval "set -- $args"
	echo "  cmd: $T $*"
	mark_case "$name"
	if [ "$rt" = "-" ]; then
		sudo -n timeout -k 10 "$JOB_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
	else
		sudo -n timeout -k 10 "$JOB_TIMEOUT" "$RT" 0 "$RT_LEAD" "$rt" -- "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
	fi
	rc=$?
	post2=""
	if [ "$s2" = 1 ]; then
		sudo -n cat "$D/regs" > "$JW/after.regs.txt" 2>/dev/null && keep "$name" "$JW/after.regs.txt" ".after.regs.txt"
		post2=$(status2_of "$JW/after.regs.txt")
		echo "  STATUS2 after: ${post2:-unreadable}"
	fi
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: (o0|failed)|BIF_INT_STAT)' "$JW/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	# every kept file by an explicit loop over the globs (the globs are live: no `set -f` anywhere)
	for f in "$JW"/dump/*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	# 1. the kernel itself in trouble: stop at once, touch nothing
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if grep -Eq "$FATAL_RE" "$JW/$name.dmesg" "$JW/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job (the whole output and the whole kernel slice)
	if grep -Eq "BIF fault|faulted" "$JW/$name.out" "$JW/$name.dmesg"; then class=fault
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
	note="-"
	[ "$s2" = 1 ] && note="status2 ${pre2:-?} -> ${post2:-?}"
	# the loop proof of a proofstop row (the whole output is searched): a job that drew but did not carry the mark is `proof`
	if [ "$class" = ok ] && [ -n "$proofv" ] && ! grep -Eq "o0 $proofv \($proofn of $proofn\)" "$JW/$name.out"; then
		class=proof; note="$note; loop proof failed"
	fi
	echo "  class $class"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" "$rc" "$class" "$note" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	fault|hang|fail) echo "## STOP: unexpected $class in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	proof)
		echo "## STOP: the loop proof of $name failed (no 'o0 $proofv ($proofn of $proofn)' in the output): the backward branch did not loop in this task, or the job did not draw"
		reset_gpu; health "$name" </dev/null; exit 17 ;;
	esac
	# 3b. a bridge control (want2): the rgn4 module must reproduce round 3's STATUS2 bits; else the stage stops (rc 18)
	if [ -n "$want2m" ]; then
		if [ -z "$post2" ] || [ $(( post2 & want2m )) -ne $(( want2v )) ]; then
			echo "## STOP: bridge control $name: STATUS2 ${post2:-unreadable} & $want2m is not $want2v (the rgn4 module does not reproduce round 3's value)"
			reset_gpu; health "$name" </dev/null; exit 18
		fi
	fi
	# 4. a sweep or watch group: a job whose STATUS2 has a bit of the mask set ends the group
	if [ -n "$sweepg" ] && [ -n "$post2" ] && [ $(( post2 & sweepm )) -ne 0 ]; then
		SWEEP_SET="$SWEEP_SET$sweepg "
		echo "  sweep $sweepg: STATUS2 $post2 has a bit of $sweepm set: the later sweep rows of the group are not run"
	fi
done
JW=$WROOT/end; mkdir -p "$JW"
health end </dev/null
echo "## end: $njob jobs of $STAGE"
