#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE: one R1 job table on the laptop, one job a line of tables/STAGE.txt in file order.
# Line: name|set|risk|P|knobs|rt|args      (the tool is $T, staged programs $S, work directory $W)
#   P      render_pb_pages for the job ("-": leave it); put back after the job and at exit
#   knobs  words (space separated):
#            noreset             no GPU reset before this job (default: a reset before every job)
#            stophang            a hang in this job ends the stage (every unexpected hang or fault does anyway)
#            expectdiff          rc 1 WITH a `diff:` line (the tool's own one-triangle reference check) is not a failure;
#                                REQUIRED on every `tri` row (a row without it is refused: a tri job whose scene differs
#                                from the reference prints diff: and exits 1, and would stop the stage)
#            trial072c:U         0x072c trial job: its timeline lists 0x0720-0x072c instead of 0x0720-0x0724 unless the
#                                gate state is fail; after the job the gate runs (U = the 0x0724 peak it must read)
#            s072c               the timeline lists 0x072c only if the gate state is pass (both trial jobs were clean)
#   rt     "-", or a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only); rows with a 072c knob
#          must list 0x0720-0x0724, which the runner widens
# There are no hypothesis rows in R1: EVERY hang, fault or failure stops the stage (rc 3 with "scene overflowed" is the
# normal class of the 4096 jobs and is ok).  Env: ONLY=NAME runs just that row of the table (the pause cells of g-c1f).
# Every job: kernel-log marker before the knob writes ("knobs"), after the read-back ("readback") and the case marker
# ("resgx545 case NAME RUN") right before the tool starts; the kernel log slice after the case marker is kept as
# NAME.dmesg.gz.  cases.tsv gets rc, class and a note (0x072c sampled or not) after every job.
# Exit status: 0 stage done; 1 preflight (also a table or program whose sha256 differs from FROZEN.sha256, a tri row
# without expectdiff, a multi-render tri row without --keep-going, ONLY naming no row); 3 FATAL kernel message (watchdog,
# lockup, BUG ...); 4 an unexpected hang, fault or failure; 5 the first failed health recovery; 6 a job did not return
# (freeze); 7 a forbidden knob; 8 a staged program is missing; 9 a knob read-back differs from the value written.  On 3
# and 6 nothing but the knob restore touches the machine.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no loop that waits.
STAGE=${1:?stage name}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
ONLY=${ONLY:-}
NEED_RT=$(awk -F'|' '!/^#/ && NF>=7 && $6!="-" {f=1} END{print f+0}' "$FILE")
export NEED_RT
awk -F'|' '!/^#/ && NF>=7 && $7 ~ /^tri / && $5 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=7 && $7 ~ /^tri / && $7 ~ / -n [2-9]/ && $7 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' \
	"$FILE" || { echo "table $STAGE: a multi-render tri job without --keep-going"; exit 1; }
awk -F'|' '!/^#/ && NF>=7 && $5 ~ /072c/ && $6 !~ /0x0720-0x0724/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a 072c row that does not list 0x0720-0x0724"; exit 1; }
. "$DIR/lib_r1.sh"
# the table and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { grep -h "  $1\$" "$DIR/../FROZEN.sha256" 2>/dev/null | head -n 1 | cut -d' ' -f1; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
# "#need PATH" lines: staged programs that must exist and be the frozen ones ($S expands)
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run stage_r1.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
if [ -n "$ONLY" ] && ! grep -q "^$ONLY|" "$FILE"; then echo "ONLY=$ONLY names no row of $STAGE"; exit 1; fi
HAS_TRIAL=$(awk -F'|' '!/^#/ && NF>=7 && $5 ~ /trial072c/ {f=1} END{print f+0}' "$FILE")
begin
[ "$HAS_TRIAL" = 1 ] && gate_set untested
echo "gate state at stage start: $(gate_state)" > "$KEEP/gate072c.txt"
njob=0
set -f
for line in $(grep -v '^#' "$FILE" | grep -v '^$' | tr ' ' '\001'); do
	set +f
	line=$(printf '%s' "$line" | tr '\001' ' ')
	IFS='|' read -r name sset risk P knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	[ -n "$ONLY" ] && [ "$name" != "$ONLY" ] && continue
	trial=""; sample=0
	for k in $knobs; do
		case "$k" in
		noreset|stophang|expectdiff|s072c) ;;
		trial072c:*) trial=${k#trial072c:} ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	gst=$(gate_state)
	if [ -n "$trial" ]; then case "$gst" in untested|pass1) sample=1 ;; esac; fi
	case " $knobs " in *" s072c "*) [ "$gst" = pass ] && sample=1 ;; esac
	if [ "$sample" = 1 ]; then rt=${rt//0x0720-0x0724/0x0720-0x072c}; note="072c=sampled"; else note="072c=no"; fi
	njob=$((njob + 1))
	echo "== $name set=$sset risk=$risk P=$P knobs=[$knobs] rt=$rt gate=$gst ($note)"
	case " $knobs " in *" noreset "*) echo "  no reset before (noreset)" ;; *) reset_gpu ;; esac
	mkdir -p "$W/dump" "$W/words" "$W/depth"; clean_w
	mark "knobs $name render_pb_pages=$P"
	if [ "$P" != "-" ]; then
		rb=$(set_knob render_pb_pages "$P"); echo "  render_pb_pages written $P, read back $rb"; mark "readback $name render_pb_pages=$rb"
		[ $((rb)) -eq $((P)) ] || { echo "## STOP: render_pb_pages read back $rb, wrote $P"; exit 9; }
	fi
	eval "set -- $args"
	echo "  cmd: $T $*"
	mark_case "$name"
	if [ "$rt" = "-" ]; then
		sudo -n timeout "${JOB_TIMEOUT:-120}" "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	else
		sudo -n timeout "${JOB_TIMEOUT:-120}" "$RT" 0 0.3 "$rt" -- "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	fi
	rc=$?
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: failed)' "$W/$name.out" | head -2 | tr '\n' ' ' | cut -c1-150)"
	grep -E '^tri [0-9]+x[0-9]+ #[0-9]+:' "$W/$name.out" | cut -c1-150 | head -4
	slice_since "resgx545 case $name $RUN" > "$W/$name.dmesg"
	keep "$name" "$W/$name.out"
	keep "$name" "$W/$name.dmesg" ".dmesg"
	sudo -n cat "$D/buf09" > "$W/after.buf09.bin" 2>/dev/null && keep "$name" "$W/after.buf09.bin" ".after.buf09.bin"
	sudo -n cat "$D/regs" > "$W/after.regs.txt" 2>/dev/null && keep "$name" "$W/after.regs.txt" ".after.regs.txt"
	for f in "$W"/dump/* "$W"/words/* "$W"/depth/*; do
		[ -f "$f" ] && keep "$name" "$f" ".$(basename "$f")"
	done
	# restore the knob of the job before anything else touches the GPU
	[ "$P" != "-" ] && [ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE" >/dev/null
	# 1. the kernel itself in trouble: stop at once, touch nothing
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return in ${JOB_TIMEOUT:-120} s (freeze)"; FATAL_STOP=1; exit 6; fi
	if grep -Eq "$FATAL_RE" "$W/$name.dmesg" "$W/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name:"; grep -E "$FATAL_RE" "$W/$name.dmesg" | head -3; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job: hang and fault first (rc 3 with "scene overflowed" is the normal overflow class)
	class=ok
	if grep -Eq "job [0-9]+ hung|hung|timed out waiting" "$W/$name.out" "$W/$name.dmesg"; then class=hang
	elif grep -Eq "faulted|BIF fault|bif fault" "$W/$name.out" "$W/$name.dmesg"; then class=fault
	elif [ "$rc" -ne 0 ] && ! grep -q "scene overflowed" "$W/$name.out"; then
		class=fail
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$W/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:" "$W/$name.out"; then class=ok; fi ;;
		esac
	fi
	echo "  class $class"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P" "$knobs" "$rt" "$args" "$rc" "$class" "$note" >> "$KEEP/cases.tsv"
	# 3. the 0x072c gate of a trial job: evaluated before the next job's reset; a failed job fails the gate and stops
	if [ -n "$trial" ]; then
		gh=0; if [ "$class" = ok ] && tri_ok; then gh=1; fi
		if [ "$sample" = 1 ] && gate_check "$name" "$class" "$trial" "$gh"; then
			if [ "$gst" = untested ]; then gate_set pass1; else gate_set pass; fi
			echo "$name CLEAN -> $(gate_state)" >> "$KEEP/gate072c.txt"
		else
			gate_set fail
			echo "$name NOT clean:${GATE_WHY:- not sampled (gate state was $gst)} -> fail" >> "$KEEP/gate072c.txt"
			echo "  0x072c gate FAILED:${GATE_WHY:- not sampled}: the remaining DPM jobs run without 0x072c"
		fi
	fi
	case "$class" in
	ok) ;;
	hang|fault|fail) echo "## STOP: $class in $name (rc $rc)"; reset_gpu; health </dev/null; exit 4 ;;
	esac
	clean_w
done
set +f
if [ -n "$ONLY" ] && [ "$njob" -eq 0 ]; then echo "## abort: ONLY=$ONLY ran no job"; exit 1; fi
echo "gate state at stage end: $(gate_state)" >> "$KEEP/gate072c.txt"
health </dev/null
echo "## end: $njob jobs of $STAGE"
