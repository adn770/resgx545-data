#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE: one S1b job table on the laptop, one job a line of tables/STAGE.txt in file order.
# Line: name|set|risk|P|knobs|rt|args      (the tool is $T, staged programs $S, work directory $W)
#   P      render_pb_pages for the job ("-": leave it); put back after the job and at exit
#   knobs  words (space separated):
#            alias_skip=MASK     debugfs alias_skip for the job (put back after)
#            noreset             no GPU reset before this job (default: a reset before every job)
#            stophang            a hang in this job ends the stage (the default for an unexpected hang anyway)
#            hypo:GROUP:MAX      a hang or fault is a stated HYPOTHESIS of the group (every expected hang or fault of
#                                S1b is one): it is measured (class and group recorded, reset + health, go on); after
#                                MAX events the rest of the group is skipped (MAX is below the group's row count),
#                                and after 3 events in the stage (STAGE_HYPO_MAX) every remaining hypothesis row is
#                                skipped; a skipped row is recorded in cases.tsv with rc - and class skipped.  A hang
#                                or fault in a job without hypo: stops the stage.  Rows with hypo: are the table's
#                                LAST rows (refused otherwise).
#            expectdiff          rc 1 WITH a `diff:` line (the tool's own one-triangle reference check) is not a failure
#   rt     "-", or a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only)
# Every job: kernel-log marker before the knob writes ("knobs"), after the read-back ("readback") and the
# case marker ("resgx545 case NAME RUN") right before the tool starts; the kernel log slice after the case
# marker is kept as NAME.dmesg.gz.  cases.tsv gets rc, class and the hypothesis group after every job.
# Exit status: 0 stage done; 1 preflight (also a table or program whose sha256 differs from FROZEN.sha256, a hypo row
# before a plain row, a multi-render tri row without --keep-going); 3 FATAL kernel message (watchdog, lockup, BUG ...);
# 4 an unexpected hang, fault or failure; 5 the first failed health recovery; 6 a job did not return (freeze); 7 a
# forbidden knob; 8 a staged program is missing; 9 a knob read-back differs from the value written.  On 3 and 6
# nothing but the knob restore touches the machine.
# No reboot, no GRUB, no kernel build, no clock-gate register, no trc_hazard, no loop that waits.
STAGE=${1:?stage name}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
NEED_RT=$(awk -F'|' '!/^#/ && NF>=7 && $6!="-" {f=1} END{print f+0}' "$FILE")
export NEED_RT
# hypothesis rows (expected hangs and faults) last; every multi-render tri job keeps going
awk -F'|' '!/^#/ && NF>=7 { if ($5 ~ /hypo:/) h=1; else if (h) { print "plain row " $1 " after a hypothesis row"; bad=1 } }
	END { exit bad }' "$FILE" || { echo "table $STAGE: hypothesis rows must be last"; exit 1; }
awk -F'|' '!/^#/ && NF>=7 && $7 ~ /^tri / && $7 ~ / -n [2-9]/ && $7 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' \
	"$FILE" || { echo "table $STAGE: a multi-render tri job without --keep-going"; exit 1; }
. "$DIR/lib_s1.sh"
# the table and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { grep -h "  $1\$" "$DIR/../FROZEN.sha256" 2>/dev/null | head -n 1 | cut -d' ' -f1; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
# "#need PATH" lines: staged programs that must exist and be the frozen ones ($S expands)
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run stage_s1.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
begin
njob=0; SKIP_GRPS=""; NEVENTS=0
# the stage's own gate: after this many hang/fault events in hypothesis rows, the remaining hypothesis rows are skipped
STAGE_HYPO_MAX=3
set -f
for line in $(grep -v '^#' "$FILE" | grep -v '^$' | tr ' ' '\001'); do
	set +f
	line=$(printf '%s' "$line" | tr '\001' ' ')
	IFS='|' read -r name sset risk P knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0
	for k in $knobs; do case "$k" in hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;; esac; done
	skip=""
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && skip="group $grp reached its $gmax events" ;; esac
	[ -n "$grp" ] && [ "$NEVENTS" -ge "$STAGE_HYPO_MAX" ] && skip="the stage reached $STAGE_HYPO_MAX hang/fault events"
	if [ -n "$skip" ]; then
		echo "== $name skipped: $skip"
		printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P" "$knobs" "$rt" "$args" "-" "skipped" "$grp" >> "$KEEP/cases.tsv"
		continue
	fi
	njob=$((njob + 1))
	echo "== $name set=$sset risk=$risk P=$P knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) echo "  no reset before (noreset)" ;; *) reset_gpu ;; esac
	mkdir -p "$W/dump" "$W/words" "$W/depth"; clean_w
	asmask=""
	for k in $knobs; do case "$k" in alias_skip=*) asmask=${k#alias_skip=} ;; esac; done
	mark "knobs $name render_pb_pages=$P alias_skip=${asmask:--}"
	if [ "$P" != "-" ]; then
		rb=$(set_knob render_pb_pages "$P"); echo "  render_pb_pages written $P, read back $rb"; mark "readback $name render_pb_pages=$rb"
		[ $((rb)) -eq $((P)) ] || { echo "## STOP: render_pb_pages read back $rb, wrote $P"; exit 9; }
	fi
	if [ -n "$asmask" ]; then
		rb=$(set_knob alias_skip "$asmask"); echo "  alias_skip written $asmask, read back $rb"; mark "readback $name alias_skip=$rb"
		[ $((rb)) -eq $((asmask)) ] || { echo "## STOP: alias_skip read back $rb, wrote $asmask"; exit 9; }
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
	# restore the knobs of the job before anything else touches the GPU
	[ -n "$asmask" ] && set_knob alias_skip "${AS_RESTORE:-0}" >/dev/null
	[ "$P" != "-" ] && [ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE" >/dev/null
	# 1. the kernel itself in trouble: stop at once, touch nothing
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return in ${JOB_TIMEOUT:-120} s (freeze)"; FATAL_STOP=1; exit 6; fi
	if grep -Eq "$FATAL_RE" "$W/$name.dmesg" "$W/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name:"; grep -E "$FATAL_RE" "$W/$name.dmesg" | head -3; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job
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
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P" "$knobs" "$rt" "$args" "$rc" "$class" "${grp:--}" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	hang|fault)
		if [ -n "$grp" ]; then
			gv=$(printf '%s' "$grp" | tr -c 'A-Za-z0-9' '_'); eval "HYPO_$gv=\$(( \${HYPO_$gv:-0} + 1 ))"; eval "n=\$HYPO_$gv"
			NEVENTS=$((NEVENTS + 1))
			echo "  $class $n of at most $gmax in group $grp, $NEVENTS of at most $STAGE_HYPO_MAX in the stage (a hypothesis: measured)"
			[ "$n" -ge "$gmax" ] && SKIP_GRPS="$SKIP_GRPS $grp"
		else echo "## STOP: unexpected $class in $name"; reset_gpu; health </dev/null; exit 4; fi
		reset_gpu; health </dev/null ;;
	fail) echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health </dev/null; exit 4 ;;
	esac
	clean_w
done
set +f
health </dev/null
echo "## end: $njob jobs of $STAGE"
