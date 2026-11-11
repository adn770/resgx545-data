#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE: one R3GC job table on the laptop, one job a line of tables/STAGE.txt in file order.
# Line: name|set|risk|P|knobs|rt|args      (the tool is $T = ~/sgxfive-test-r1, staged programs $S, work directory $W)
#   P      render_pb_pages for the job ("-": leave it); put back after the job and at exit
#   knobs  words (space separated):
#            noreset             no GPU reset before this job (default: a reset before every job)
#            stophang            a hang in this job ends the stage (every unexpected hang or fault does anyway)
#            expectdiff          rc 1 WITH a `diff:` line (the tool's own one-triangle reference check) is not a failure;
#                                REQUIRED on every `tri` row
#            s2                  CR_EVENT_STATUS2 (0x0118) is read from the debugfs regs right after the reset (kept as
#                                NAME.pre.regs.txt.gz) and after the job (NAME.after.regs.txt.gz)
#            sweep:G             a sweep group: once a job of group G ends with bit 7 (0x80) of STATUS2 set, every later row
#                                of G is not run (recorded as class `skipped`)
#            kpoke               the row pokes pb:11 (only that: --kpoke / --kpoke-render with exactly pb:11=0xHEX); the
#                                tool writes the poke, never this script; REQUIRES wd:S
#            wd:S                watchdog: S seconds after the tool started, if it is still running, the KERNEL'S OWN debugfs
#                                reset is written (from a background subshell; killed when the tool returns first); the job
#                                then ends as a hang and the stage stops with a reset and a health triangle
#   rt     "-", or a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only)
# There are no hypothesis rows in R3GC: EVERY hang, fault or failure stops the stage (rc 3 with "scene overflowed" is the
# normal class of the DPM jobs and is ok).  Env: ONLY=NAME runs just that row of the table.
# Every job: kernel-log marker before the knob writes ("knobs"), after the read-back ("readback") and the case marker
# ("resgx545 case NAME RUN") right before the tool starts; the kernel log slice after the case marker is kept as NAME.dmesg.gz.
# cases.tsv gets rc, class and a note after every job.
# Exit status: 0 stage done; 1 preflight (also a table or program whose sha256 differs from FROZEN.sha256, a tri row without
# expectdiff, a multi-render tri row without --keep-going, ONLY naming no row, a poke row that is not exactly pb:11 with
# kpoke and wd:S); 3 FATAL kernel message (watchdog, lockup, BUG ...); 4 an unexpected hang, fault or failure; 5 the first
# failed health recovery; 6 a job did not return (freeze; for a wd row the kernel's reset and a health triangle first); 7 a
# forbidden knob; 8 a staged program is missing; 9 a knob read-back differs from the value written.  On 3 and 6 (no wd) nothing
# but the knob restore touches the machine.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no loop that waits.
STAGE=${1:?stage name}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
ONLY=${ONLY:-}
NEED_RT=$(awk -F'|' '!/^#/ && NF>=7 && $6!="-" {f=1} END{print f+0}' "$FILE")
NEED_KPOKE=$(awk -F'|' '!/^#/ && NF>=7 && $5 ~ /(^| )kpoke( |$)/ {f=1} END{print f+0}' "$FILE")
export NEED_RT NEED_KPOKE
awk -F'|' '!/^#/ && NF>=7 && $7 ~ /^tri / && $5 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=7 && $7 ~ /^tri / && $7 ~ / -n [2-9]/ && $7 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' \
	"$FILE" || { echo "table $STAGE: a multi-render tri job without --keep-going"; exit 1; }
# the pokes: every --kpoke* value of a row is exactly pb:11=0xHEX, and a row with one has the kpoke knob and a wd:S watchdog
awk -F'|' '!/^#/ && NF>=7 && $7 ~ /--kpoke/ {
		n = split($7, a, " "); ok = 1
		for (i = 1; i <= n; i++) if (a[i] ~ /^--kpoke/) { v = a[i + 1]; sub(/^[0-9]+:/, "", v); if (v !~ /^pb:11=0x[0-9a-fA-F]+$/) ok = 0 }
		if (!ok || $5 !~ /(^| )kpoke( |$)/ || $5 !~ /(^| )wd:[0-9]+( |$)/) { print $1; bad = 1 } }
	!/^#/ && NF>=7 && $5 ~ /(^| )kpoke( |$)/ && $7 !~ /--kpoke/ { print $1; bad = 1 }
	END { exit bad }' "$FILE" || { echo "table $STAGE: a poke that is not exactly pb:11 with the kpoke and wd:S knobs"; exit 1; }
. "$DIR/lib_r3.sh"
# the table and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { grep -h "  $1\$" "$DIR/../FROZEN.sha256" 2>/dev/null | head -n 1 | cut -d' ' -f1; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
# "#need PATH" lines: staged programs that must exist and be the frozen ones ($S expands)
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run stage_r3.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
if [ -n "$ONLY" ] && ! grep -q "^$ONLY|" "$FILE"; then echo "ONLY=$ONLY names no row of $STAGE"; exit 1; fi
begin
echo "stage $STAGE: no gate (R1's 0x072c trial passed: every DPM timeline reads 0x0720-0x072c)" > "$KEEP/notes.txt"
njob=0
SWEEP_DONE=" "
set -f
for line in $(grep -v '^#' "$FILE" | grep -v '^$' | tr ' ' '\001'); do
	set +f
	line=$(printf '%s' "$line" | tr '\001' ' ')
	IFS='|' read -r name sset risk P knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	[ -n "$ONLY" ] && [ "$name" != "$ONLY" ] && continue
	s2=0; sweep=""; wd=""
	for k in $knobs; do
		case "$k" in
		noreset|stophang|expectdiff|kpoke) ;;
		s2) s2=1 ;;
		sweep:*) sweep=${k#sweep:} ;;
		wd:*) wd=${k#wd:} ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	if [ -n "$sweep" ]; then
		case "$SWEEP_DONE" in
		*" $sweep "*)
			echo "== $name set=$sset: skipped (sweep $sweep already set bit 7)"
			printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P" "$knobs" "$rt" "$args" "-" "skipped" "sweep stopped" >> "$KEEP/cases.tsv"
			continue ;;
		esac
	fi
	njob=$((njob + 1))
	echo "== $name set=$sset risk=$risk P=$P knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) echo "  no reset before (noreset)" ;; *) reset_gpu ;; esac
	mkdir -p "$W/dump" "$W/words" "$W/depth"; clean_w
	if [ "$s2" = 1 ]; then
		# the job's own pre read, after its reset and before the tool (the debugfs regs file, through sudo -n)
		sudo -n cat "$D/regs" > "$W/pre.regs.txt" 2>/dev/null && keep "$name" "$W/pre.regs.txt" ".pre.regs.txt"
		echo "  STATUS2 before: $(status2_of "$W/pre.regs.txt")"
	fi
	mark "knobs $name render_pb_pages=$P"
	if [ "$P" != "-" ]; then
		rb=$(set_knob render_pb_pages "$P"); echo "  render_pb_pages written $P, read back $rb"; mark "readback $name render_pb_pages=$rb"
		[ $((rb)) -eq $((P)) ] || { echo "## STOP: render_pb_pages read back $rb, wrote $P"; exit 9; }
	fi
	eval "set -- $args"
	echo "  cmd: $T $*"
	mark_case "$name"
	tmo=${JOB_TIMEOUT:-120}
	WDPID=""
	if [ -n "$wd" ]; then
		# the stuck-job watchdog: the kernel's own debugfs reset after $wd seconds if the tool has not returned
		( sleep "$wd"; echo 1 | sudo -n tee "$D/reset" >/dev/null 2>&1; echo fired > "$W/$name.wd" ) >/dev/null 2>&1 </dev/null &
		WDPID=$!
		tmo=$((wd + 40))
	fi
	if [ "$rt" = "-" ]; then
		sudo -n timeout "$tmo" "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	else
		sudo -n timeout "$tmo" "$RT" 0 0.3 "$rt" -- "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	fi
	rc=$?
	wdfired=0
	if [ -n "$WDPID" ]; then
		kill "$WDPID" 2>/dev/null; wait "$WDPID" 2>/dev/null
		[ -f "$W/$name.wd" ] && wdfired=1
	fi
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: failed)' "$W/$name.out" | head -2 | tr '\n' ' ' | cut -c1-150)"
	[ "$wdfired" = 1 ] && echo "  WATCHDOG: the tool had not returned after ${wd} s: the kernel's debugfs reset was written"
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
	# 1. the kernel itself in trouble: stop at once, touch nothing (a wd row: the kernel's own reset and a health triangle)
	if [ "$rc" -eq 124 ]; then
		if [ -n "$wd" ]; then
			echo "## STOP: $name did not return in $tmo s even after the watchdog's reset: reset and health first"
			printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P" "$knobs" "$rt" "$args" "$rc" "hang" "no return" >> "$KEEP/cases.tsv"
			reset_gpu; health </dev/null; exit 6
		fi
		echo "## STOP: $name did not return in $tmo s (freeze)"; FATAL_STOP=1; exit 6
	fi
	if grep -Eq "$FATAL_RE" "$W/$name.dmesg" "$W/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name:"; grep -E "$FATAL_RE" "$W/$name.dmesg" | head -3; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job: hang and fault first (rc 3 with "scene overflowed" is the normal overflow class)
	class=ok
	if [ "$wdfired" = 1 ] || grep -Eq "job [0-9]+ hung|hung|timed out waiting" "$W/$name.out" "$W/$name.dmesg"; then class=hang
	elif grep -Eq "faulted|BIF fault|bif fault" "$W/$name.out" "$W/$name.dmesg"; then class=fault
	elif [ "$rc" -ne 0 ] && ! grep -q "scene overflowed" "$W/$name.out"; then
		class=fail
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$W/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:" "$W/$name.out"; then class=ok; fi ;;
		esac
	fi
	echo "  class $class"
	mark "class $name $class"
	note="-"
	[ "$s2" = 1 ] && note="status2 $(status2_of "$W/pre.regs.txt") -> $(status2_of "$W/after.regs.txt")"
	[ "$wdfired" = 1 ] && note="watchdog fired"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P" "$knobs" "$rt" "$args" "$rc" "$class" "$note" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	hang|fault|fail) echo "## STOP: $class in $name (rc $rc)"; reset_gpu; health </dev/null; exit 4 ;;
	esac
	# 3. a sweep: the first job whose STATUS2 has bit 7 set ends it
	if [ -n "$sweep" ]; then
		post=$(status2_of "$W/after.regs.txt")
		if [ -n "$post" ] && [ $(( post & 128 )) -ne 0 ]; then
			SWEEP_DONE="$SWEEP_DONE$sweep "
			echo "  sweep $sweep: STATUS2 $post has bit 7 set: the rest of the sweep is not run"
		fi
	fi
	clean_w
done
set +f
if [ -n "$ONLY" ] && [ "$njob" -eq 0 ]; then echo "## abort: ONLY=$ONLY ran no job"; exit 1; fi
health </dev/null
echo "## end: $njob jobs of $STAGE"
