#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE: one R5-dpm job table on the laptop, one job a line of tables/STAGE.txt in file order.  Built from R3-geo's
# run_stage.sh (closing3/r3-geo).
# Line: name|set|risk|P|knobs|rt|args      (the tool is $T = ~/sgxfive-test-rgn4, staged programs $S, work directory $W)
#   P      render_pb_pages for the job; restored after the job and at exit.  Or a cell the runner DERIVES from a calibration:
#            S:G:k:off   thr0 = S_k + off, S_k the step of global page k read from calibration G's OWN timeline (run/r5read.py, the
#                        rule of the plan's section 1: max(a, b - 1) for the step seen between pages a and b); P = thr0 + 0x22.
#                        Skipped when G was not calibrated, its steps were not monotone or it shows no step k; a derived thr0 below
#                        MIN_THR0 (0x48) or a P above 0x422 is skipped.
#   knobs  words (space separated):
#            noreset      no GPU reset before this job (default: a reset before every job; no R5 row uses it)
#            stophang     a hang in this job ends the stage (every unexpected hang or fault does anyway)
#            expectdiff   rc 1 WITH a `diff:` line is not a failure (the tri rows of stage d-b)
#            ctl:R|N      a control: its class (R raise / N none, run/r5read.py) must be the one written, else STOP (rc 10, state/CTLFAIL)
#            prem         a premise of A0: the job's own 0x0624 must be P - 0x22, and a calibration's steps must be monotone, else
#                         STOP (rc 10, state/CTLFAIL).  Every later stage is refused while state/CTLFAIL exists (CTL_OVERRIDE=1)
#            cal:G        a calibration: its steps go to state/G.steps (`k S a b`), its page need and partial renders to G.cal;
#                         non-monotone steps mark G.bad (the S:G cells are then skipped)
#            ucal:G:U     a scene calibration of stage d-b: the page need must be U (HU1, frozen) with no partial render, else G.void
#                         (the scene's cells are skipped: void); ok writes G.ucalok
#            uneed:G      run only when G.ucalok exists (and no G.void)
#            fw           stage A3: before the job the own task oomring is armed (reset, fwtask_run.py arm, ring cleared); after it the
#                         results page and the EDM status are kept (NAME.page.json, NAME.status.json).  A stalled EDM (ticks not
#                         advancing) is reset once and the stage goes on; a second stall ends the stage (rc 11).  A failed arm or
#                         clear ends the stage (rc 12).
#   rt     a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only)
# Every hang, fault or failure stops the stage (rc 3 with "scene overflowed" is the normal class of the DPM jobs and is ok).
# Env: ONLY=NAME runs just that row.  Exit: 0 done; 1 preflight (also a table or program not the frozen one); 3 FATAL kernel message;
# 4 a hang, fault or failure; 5 failed health recovery; 6 a job did not return; 7 a forbidden knob; 8 a staged program missing; 9 a
# knob read-back differs; 10 a control or premise failed; 11 a second EDM stall in A3; 12 the own task could not be armed or checked;
# 13 a job's capture is not whole (timeline cut, no control block or register dump, the work filesystem short of space) or the work
# filesystem is short of space before a job: a measurement failure, never read as a premise or a class (attempt 1's a0-cal-4096).
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no firmware str, no wait loop.
STAGE=${1:?stage name}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
ONLY=${ONLY:-}
HAS_FW=$(awk -F'|' '!/^#/ && NF>=7 && $5 ~ /(^| )fw( |$)/ {f=1} END{print f+0}' "$FILE")
export HAS_FW
awk -F'|' -v pat="--kp""oke" '!/^#/ && NF>=7 && (index($7, pat) || index($7, "--kr""eg") || index($7, "--po""ke")) { print $1; bad = 1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a poke option (R5-dpm has none)"; exit 1; }
. "$DIR/lib_r5.sh"
expect_sha() { grep -h "  $1\$" "$DIR/../FROZEN.sha256" 2>/dev/null | head -n 1 | cut -d' ' -f1; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run stage_r5.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
if [ -n "$ONLY" ] && ! grep -q "^$ONLY|" "$FILE"; then echo "ONLY=$ONLY names no row of $STAGE"; exit 1; fi
if [ "$STAGE" != d-a0 ] && [ -e "$STATE/CTLFAIL" ] && [ "${CTL_OVERRIDE:-0}" != 1 ]; then
	echo "a premise of A0 failed ($(cat "$STATE/CTLFAIL")): $STAGE is refused (CTL_OVERRIDE=1 to override)"; exit 1
fi
begin
if [ -z "$ONLY" ]; then
	# the groups this stage owns start empty; a group of an earlier stage (the calibrations of A0) is only read
	for g in $(awk -F'|' '!/^#/ && NF>=7 { n = split($5, k, " "); for (i = 1; i <= n; i++) if (k[i] ~ /^(cal|ucal):/) { split(k[i], p, ":"); print p[2] } }' "$FILE" | sort -u); do
		for x in steps cal bad void ucalok; do [ -e "$STATE/$g.$x" ] && rm -f -- "$STATE/$g.$x"; done
	done
	[ "$STAGE" = d-a0 ] && [ -e "$STATE/CTLFAIL" ] && rm -f -- "$STATE/CTLFAIL"
fi
STALLS=0
if [ "$HAS_FW" = 1 ] && [ -z "$ONLY" ]; then
	# A3's start: a fresh firmware load with the task armed, a fill and a triangle exact under it, and the task seen running
	reset_gpu
	a=$(fw_arm); echo "  arm: $(printf '%s' "$a" | cut -c1-200)"
	fw_ok "$a" || { echo "## STOP: the own task could not be armed"; exit 12; }
	fill_ok && tri_ok || { echo "## STOP: fill or triangle not exact with the own task armed"; exit 12; }
	pg=$(fw page) || { echo "## STOP: the results page cannot be read"; exit 12; }
	npass=$(printf '%s' "$pg" | "$PY3" -c 'import json,sys; p=json.load(sys.stdin)["page"]; print(sum(p[16:20]))' 2>/dev/null)
	echo "  passes of the four stubs after the arm, fill and triangle: ${npass:-?}"
	[ "${npass:-0}" -gt 0 ] || { echo "## STOP: the own task never ran (no pass counted)"; exit 12; }
	printf '%s\n' "$pg" > "$W/armcheck.page.json"; keep armcheck "$W/armcheck.page.json" "$(kept_name armcheck page)"
fi
njob=0
skip_row() { # NAME REASON
	echo "== $1 set=$sset: skipped ($2)"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$STAGE" "$sset" "$risk" "${P_RES:--}" "$knobs" "$rt" "$args" "-" "skipped" "$2" >> "$KEEP/cases.tsv"
}
stopctl() { echo "## STOP: $1: nothing after a failed premise is a reading"; echo "$1" > "$STATE/CTLFAIL"; exit 10; }
set -f
for line in $(grep -v '^#' "$FILE" | grep -v '^$' | tr ' ' '\001'); do
	set +f
	line=$(printf '%s' "$line" | tr '\001' ' ')
	IFS='|' read -r name sset risk P knobs rt args <<ROW
$line
ROW
	[ -z "$name" ] && continue
	[ -n "$ONLY" ] && [ "$name" != "$ONLY" ] && continue
	ctl=""; cal=""; ucal=""; uneed=""; prem=0; fwk=0
	for k in $knobs; do
		case "$k" in
		noreset|stophang|expectdiff) ;;
		prem) prem=1 ;;
		fw) fwk=1 ;;
		ctl:R|ctl:N) ctl=${k#ctl:} ;;
		cal:*) cal=${k#cal:} ;;
		ucal:*) ucal=${k#ucal:} ;;
		uneed:*) uneed=${k#uneed:} ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	# 0. the P of a derived row, from the steps of its calibration
	P_RES=$P
	case "$P" in
	S:*)
		IFS=: read -r _ grp kk off <<SREF
$P
SREF
		r=$(s_cell "$grp" "$kk" "$off")
		case "$r" in
		SKIP*) P_RES="-"; skip_row "$name" "${r#SKIP }"; continue ;;
		*) thr=$r; P_RES=$(printf '0x%x' $((thr + 34)))
		   if [ "$thr" -lt "$MIN_THR0" ] || [ $((thr + 34)) -gt "$MAX_P" ]; then skip_row "$name" "thr0 $thr outside the allowed cells (0x48 .. P 0x422)"; continue; fi ;;
		esac ;;
	0x*) ;;
	*) echo "## STOP: P $P of $name is neither a number nor S:G:k:off"; exit 7 ;;
	esac
	if [ -n "$uneed" ]; then
		if [ -e "$STATE/$uneed.void" ] || [ ! -e "$STATE/$uneed.ucalok" ]; then skip_row "$name" "scene $uneed void: its calibration did not read its HU1 page need"; continue; fi
	fi
	space_ok || { echo "## STOP: less than $MIN_JOB_KB KB free in the work directory before $name"; exit 13; }
	njob=$((njob + 1))
	echo "== $name set=$sset risk=$risk P=$P_RES knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) echo "  no reset before (noreset)" ;; *) reset_gpu ;; esac
	if [ "$fwk" = 1 ]; then
		a=$(fw_arm); fw_ok "$a" || { echo "## STOP: the own task could not be armed before $name: $(printf '%s' "$a" | cut -c1-200)"; exit 12; }
		fw_clear || { echo "## STOP: the results page could not be cleared before $name"; exit 12; }
		echo "  own task armed, ring cleared"
	fi
	mkdir -p "$W/dump" "$W/words"; clean_w
	mark "knobs $name render_pb_pages=$P_RES"
	rb=$(set_knob render_pb_pages "$P_RES"); echo "  render_pb_pages written $P_RES, read back $rb"; mark "readback $name render_pb_pages=$rb"
	[ $((rb)) -eq $((P_RES)) ] || { echo "## STOP: render_pb_pages read back $rb, wrote $P_RES"; exit 9; }
	eval "set -- $args"
	echo "  cmd: $T $*"
	mark_case "$name"
	tmo=${JOB_TIMEOUT:-120}
	sudo -n timeout -k 10 "$tmo" "$RT" 0 "$RT_LEAD" "$rt" -- "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: failed)' "$W/$name.out" | head -2 | tr '\n' ' ' | cut -c1-150)"
	slice_since "resgx545 case $name $RUN" > "$W/$name.dmesg"
	keep "$name" "$W/$name.out" "$(kept_name "$name" out)"
	keep "$name" "$W/$name.dmesg" "$(kept_name "$name" dmesg)"
	sudo -n cat "$D/buf09" > "$W/after.buf09.bin" 2>/dev/null && keep "$name" "$W/after.buf09.bin" "$(kept_name "$name" buf09)"
	sudo -n cat "$D/regs" > "$W/after.regs.txt" 2>/dev/null && keep "$name" "$W/after.regs.txt" "$(kept_name "$name" regs)"
	for f in "$W"/dump/* "$W"/words/*; do
		[ -f "$f" ] && keep "$name" "$f" "$name.$(basename "$f").gz"
	done
	set_knob render_pb_pages "$PB_RESTORE" >/dev/null
	# 1. the kernel itself in trouble: stop at once, touch nothing
	if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
		echo "## STOP: $name did not return in $tmo s (freeze)"; FATAL_STOP=1; exit 6
	fi
	if grep -Eq "$FATAL_RE" "$W/$name.dmesg" "$W/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name:"; grep -E "$FATAL_RE" "$W/$name.dmesg" | head -3; FATAL_STOP=1; exit 3
	fi
	# 2. the own task's page and the EDM's ticks (A3)
	if [ "$fwk" = 1 ]; then
		fw page > "$W/$name.page.json"; keep "$name" "$W/$name.page.json" "$(kept_name "$name" page)"
		fw status > "$W/$name.status.json"; keep "$name" "$W/$name.status.json" "$(kept_name "$name" status)"
		if ! fw_alive "$(cat "$W/$name.status.json")"; then
			STALLS=$((STALLS + 1))
			if [ "$STALLS" -ge 2 ]; then echo "## STOP: a second EDM stall (after $name): A3 ends"; exit 11; fi
			echo "  EDM stall after $name (the first): reset once, the stage goes on"; reset_gpu
		fi
	fi
	# 3. classify the job: hang and fault first, searched in the WHOLE output (rc 3 with "scene overflowed" is the normal class)
	class=ok
	if grep -Eq "job [0-9]+ hung|hung|timed out waiting|Connection timed out" "$W/$name.out" "$W/$name.dmesg"; then class=hang
	elif grep -Eq "faulted|BIF fault|bif fault" "$W/$name.out" "$W/$name.dmesg"; then class=fault
	elif [ "$rc" -ne 0 ] && ! grep -q "scene overflowed" "$W/$name.out"; then
		class=fail
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$W/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:" "$W/$name.out"; then class=ok; fi ;;
		esac
	fi
	echo "  class $class"
	mark "class $name $class"
	if [ "$class" = ok ]; then
		why=$(capture_ok "$name") || {
			printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P_RES" "$knobs" "$rt" "$args" "$rc" "capture" "$why" >> "$KEEP/cases.tsv"
			echo "## STOP: the capture of $name is not whole ($why): nothing is read from it"; exit 13; }
	fi
	rd=$(dpm_read "$W/$name.out" "$W/after.buf09.bin")
	oc=$(field "$rd" cls)
	note="class $oc $rd"
	echo "  reading: $rd"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P_RES" "$knobs" "$rt" "$args" "$rc" "$class" "$note" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	hang|fault|fail) echo "## STOP: $class in $name (rc $rc)"; reset_gpu; health </dev/null; exit 4 ;;
	esac
	# 4. premises, calibrations, controls
	thr=$((P_RES - 34))
	if [ "$prem" = 1 ]; then
		kn=$(field "$rd" knob)
		[ -n "$kn" ] && [ "$kn" != - ] && [ $((kn)) -eq "$thr" ] || stopctl "$name: its own 0x0624 read ${kn:-?}, P - 0x22 is $(printf '0x%x' "$thr")"
	fi
	if [ -n "$cal" ]; then
		"$PY3" "$HERE_LIB/r5read.py" steps "$W/$name.out" > "$STATE/$cal.steps"
		echo "$(field "$rd" need) $(field "$rd" nparts) $name" > "$STATE/$cal.cal"
		echo "  calibration $cal: steps $(tr '\n' ';' < "$STATE/$cal.steps")"
		if [ "$(field "$rd" mono)" != 1 ]; then
			[ "$prem" = 1 ] && stopctl "calibration $name: steps not monotone"
			: > "$STATE/$cal.bad"; echo "  calibration $cal: steps not monotone, its cells will be skipped"
		fi
	fi
	if [ -n "$ucal" ]; then
		g=${ucal%%:*}; u=${ucal#*:}
		if [ "$(field "$rd" need)" = "$u" ] && [ "$(field "$rd" nparts)" = 0 ]; then : > "$STATE/$g.ucalok"; echo "  scene $g: page need $u as HU1"
		else : > "$STATE/$g.void"; echo "  scene $g: page need $(field "$rd" need) (HU1 $u), partial renders $(field "$rd" nparts): its cells are void"; fi
	fi
	if [ -n "$ctl" ] && [ "$oc" != "$ctl" ]; then
		stopctl "control $name read class ${oc:-?}, frozen $ctl"
	fi
	clean_w
done
set +f
if [ -n "$ONLY" ] && [ "$njob" -eq 0 ]; then echo "## abort: ONLY=$ONLY ran no job"; exit 1; fi
health </dev/null
echo "## end: $njob jobs of $STAGE"
