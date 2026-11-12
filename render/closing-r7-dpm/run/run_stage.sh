#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE: one R7-dpm job table on the laptop, one job a line of tables/STAGE.txt in file order.  R6-dpm's runner (freeze 2)
# with round 7's additions: two sets on two modules (the table's #set and #module lines, lib_r7.sh), the premise check of every control
# that declares its readings (reads:, the landed sessioncheck.py premise: a control WITHOUT a reading stops, it never reaches a gate),
# the value controls ctlneed and ctlpeaks, the re-pick rule of M: cells from a calibration's own steps, the tri dump (tdump) and the own
# task oomring2 with its premise (fwprem).
# Line: name|set|risk|P|knobs|rt|args      (the tool is $T = ~/sgxfive-test-rgn4, staged programs $S, work directory $W)
#   P      render_pb_pages for the job; restored after the job and at exit.  Or a cell the runner DERIVES from a calibration:
#            M:G:k:d:0xP  P = 0xP, the frozen model's cell, when G's steps lie in the model's brackets (G.modelok); else (G.modeloff)
#                        thr0 = G's own S_k + d (r7read.py steps: the point rule max(a, b - 1)), marked "repicked" in cases.tsv (the
#                        scorer then scores it for H-SPAN only).  Skipped when G was not calibrated or its steps were not monotone.
#            S:G:k:off   thr0 = S_k + off from calibration G's own timeline (no R7 row uses it; kept from R6)
#                        Each P = thr0 + 0x22; a derived thr0 below MIN_THR0 (0x20) or a P above 0x422 is skipped.
#   knobs  words (space separated):
#            noreset      no GPU reset before this job (default: a reset before every job; no R7 row uses it)
#            stophang     a hang in this job ends the stage (every unexpected hang or fault does anyway)
#            expectdiff   rc 1 WITH a `diff:` line is not a failure (the tri rows)
#            reads:K,...  a control's readings: each must be read (sessioncheck.py premise), else STOP (rc 10, state/CTLFAIL)
#            ctl:R|N      a control: its class must be the one written, else STOP (rc 10)
#            ctlleft:N    a control: the global pages left by its first partial render must be N, else STOP (rc 10)
#            ctlcnt:N     a control: its partial renders must be N, else STOP (rc 10)
#            ctlneed:0xU  a control: its page need (a complete job) must be U, else STOP (rc 10)
#            ctlpeaks:L   a control: its runs' peaks (0xA,0xB,...) must be L, else STOP (rc 10)
#            model:L      with cal:G, L = the frozen model's steps 0xS2,0xS3,... below the clamp: each step the first run passed
#                         must lie in the job's bracket (r7read model) -> G.modelok, else G.modeloff (G's M cells are re-picked);
#                         with prem, off the model STOPS (rc 10)
#            vprem        with cal:G (s-v): a job that is not a 1500-vertex scene marks G.bad (nothing depends on it)
#            prem         a premise: the job's own 0x0624 must be P - 0x22 and a calibration's steps monotone, else STOP (rc 10,
#                         state/CTLFAIL).  Every later stage of set A is refused while state/CTLFAIL exists (CTL_OVERRIDE=1)
#            cal:G        a calibration: its steps go to state/G.steps (`k S a b`), its page need and partial renders to G.cal
#            ucal:G:U     a scene calibration of s-b: the page need must be U (HU1) with no partial render, else G.void; ok: G.ucalok
#            uneed:G      run only when G.ucalok exists (and no G.void)
#            tdump        the tri dump is kept and must be whole (rc 13 otherwise): H-WALK64 reads its region headers
#            fw           stage s-k: the own task oomring2 armed before the job (reset, fwtask_run.py arm, ring cleared); after it the
#                         results page and the EDM status are kept.  An EDM stall is reset once; a second ends the stage (rc 11); a
#                         failed arm or clear ends it (rc 12)
#            fwprem       with fw: the premise of s-k: the rungs hold non-zero page counts inside the host samples' bracket
#                         (r7read.py ring: ring_counts=1), else STOP (rc 10)
#   rt     a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only)
# Every hang, fault or failure stops the stage (rc 3 with "scene overflowed" is the normal class of the DPM jobs and is ok).
# Env: ONLY=NAME runs just that row.  Exit: 0 done; 1 preflight (also a table or program not the frozen one, or the module not the set's);
# 3 FATAL kernel message; 4 a hang, fault or failure; 5 failed health recovery; 6 a job did not return; 7 a forbidden knob; 8 a staged
# program missing; 9 a knob read-back differs; 10 a control or premise failed or had no reading; 11 a second EDM stall in s-k; 12 the own
# task could not be armed or checked; 13 a job's capture is not whole or the work filesystem is short of space.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no firmware str, no wait loop.
STAGE=${1:?stage name}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
ONLY=${ONLY:-}
HAS_FW=$(awk -F'|' '!/^#/ && NF>=7 && $5 ~ /(^| )fw( |$)/ {f=1} END{print f+0}' "$FILE")
export HAS_FW
awk -F'|' -v pat="--kp""oke" '!/^#/ && NF>=7 && (index($7, pat) || index($7, "--kr""eg") || index($7, "--po""ke")) { print $1; bad = 1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a poke option (R7-dpm has none)"; exit 1; }
. "$DIR/lib_r7.sh"
# set A's freeze is FROZEN.sha256, set B's FROZEN-B.sha256 (two freezes: README.md)
FZ=$DIR/../FROZEN.sha256; [ "$SET" = B ] && FZ=$DIR/../FROZEN-B.sha256
expect_sha() { grep -h "  $1\$" "$FZ" 2>/dev/null | head -n 1 | cut -d' ' -f1; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run stage_r7.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
if [ -n "$ONLY" ] && ! grep -q "^$ONLY|" "$FILE"; then echo "ONLY=$ONLY names no row of $STAGE"; exit 1; fi
if [ "$SET" = A ] && [ "$STAGE" != s-a0 ] && [ -e "$STATE/CTLFAIL" ] && [ "${CTL_OVERRIDE:-0}" != 1 ]; then
	echo "a premise of s-a0 failed ($(cat "$STATE/CTLFAIL")): $STAGE is refused (CTL_OVERRIDE=1 to override)"; exit 1
fi
begin
if [ -z "$ONLY" ]; then
	# the groups this stage owns start empty; a group of an earlier stage is only read
	for g in $(awk -F'|' '!/^#/ && NF>=7 { n = split($5, k, " "); for (i = 1; i <= n; i++) if (k[i] ~ /^(cal|ucal):/) { split(k[i], p, ":"); print p[2] } }' "$FILE" | sort -u); do
		for x in steps cal bad void ucalok modelok modeloff; do [ -e "$STATE/$g.$x" ] && rm -f -- "$STATE/$g.$x"; done
	done
	{ [ "$STAGE" = s-a0 ] || [ "$STAGE" = s-k ]; } && [ -e "$STATE/CTLFAIL" ] && rm -f -- "$STATE/CTLFAIL"
fi
STALLS=0
if [ "$HAS_FW" = 1 ] && [ -z "$ONLY" ]; then
	# s-k's start: a fresh firmware load with the task armed, a fill and a triangle exact under it, and the task seen running
	reset_gpu
	new_w || { echo "## STOP: no work directory under $TMPROOT"; exit 13; }
	a=$(fw_arm); echo "  arm: $(printf '%s' "$a" | cut -c1-200)"
	fw_ok "$a" || { echo "## STOP: the own task could not be armed"; exit 12; }
	fill_ok && tri_ok || { echo "## STOP: fill or triangle not exact with the own task armed"; exit 12; }
	pg=$(fw page) || { echo "## STOP: the results page cannot be read"; exit 12; }
	npass=$(printf '%s' "$pg" | "$PY3" -c 'import json,sys; p=json.load(sys.stdin)["page"]; print(sum(p[16:20]))' 2>/dev/null)
	echo "  passes of the four stubs after the arm, fill and triangle: ${npass:-?}"
	[ "${npass:-0}" -gt 0 ] || { echo "## STOP: the own task never ran (no pass counted)"; exit 12; }
	printf '%s\n' "$pg" > "$W/armcheck.page.json"; keep armcheck "$W/armcheck.page.json" "$(kept_name armcheck page)"
	drop_w
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
	ctl=""; cal=""; ucal=""; uneed=""; prem=0; fwk=0; fwprem=0; cleft=""; ccnt=""; cneed=""; cpeaks=""; rkeys=""; tdump=0; mdl=""; vprem=0; pnote=""
	for k in $knobs; do
		case "$k" in
		noreset|stophang|expectdiff) ;;
		prem) prem=1 ;;
		fw) fwk=1 ;;
		fwprem) fwprem=1 ;;
		tdump) tdump=1 ;;
		reads:*) rkeys=${k#reads:} ;;
		ctl:R|ctl:N) ctl=${k#ctl:} ;;
		ctlleft:[0-9]) cleft=${k#ctlleft:} ;;
		ctlcnt:[0-9]) ccnt=${k#ctlcnt:} ;;
		ctlneed:0x*) cneed=${k#ctlneed:} ;;
		ctlpeaks:0x*) cpeaks=${k#ctlpeaks:} ;;
		model:*) mdl=${k#model:} ;;
		vprem) vprem=1 ;;
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
		   if [ "$thr" -lt "$MIN_THR0" ] || [ $((thr + 34)) -gt "$MAX_P" ]; then skip_row "$name" "thr0 $thr outside the allowed cells (0x20 .. P 0x422)"; continue; fi ;;
		esac ;;
	M:*)
		IFS=: read -r kind grp kk off mp <<MREF
$P
MREF
		r=$(m_cell "$grp" "$kk" "$off" "$mp")
		case "$r" in
		SKIP*) P_RES="-"; skip_row "$name" "${r#SKIP }"; continue ;;
		REPICK*) thr=${r#REPICK }; pnote="repicked (calibration $grp off the model): "; echo "  $name: calibration $grp off the model, cell re-picked from its own S$kk" ;;
		*) thr=$r ;;
		esac
		P_RES=$(printf '0x%x' $((thr + 34)))
		if [ "$thr" -lt "$MIN_THR0" ] || [ $((thr + 34)) -gt "$MAX_P" ]; then skip_row "$name" "thr0 $thr outside the allowed cells (0x20 .. P 0x422)"; continue; fi ;;
	0x*) ;;
	*) echo "## STOP: P $P of $name is neither a number nor S: or M:"; exit 7 ;;
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
	new_w || { echo "## STOP: no work directory under $TMPROOT before $name"; exit 13; }
	mark "knobs $name render_pb_pages=$P_RES"
	rb=$(set_knob render_pb_pages "$P_RES"); echo "  render_pb_pages written $P_RES, read back $rb"; mark "readback $name render_pb_pages=$rb"
	[ $((rb)) -eq $((P_RES)) ] || { echo "## STOP: render_pb_pages read back $rb, wrote $P_RES"; exit 9; }
	eval "set -- $args"
	echo "  cmd: $T $*"
	# every directory the tool writes into exists (the landed sessioncheck.py outdirs; r6-misc's dump directory was never made)
	od=$("$PY3" "$HERE_LIB/sessioncheck.py" outdirs --dir-opt=--dump-render --dir-opt=--words -- "$@") \
		|| { echo "## STOP: an output directory of $name is missing: $od"; exit 13; }
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
	for k in param tadata tparam ttadata; do
		f=$("$PY3" "$HERE_LIB/r7read.py" dumpfile "$k")
		[ -f "$W/dump/$f" ] && keep "$name" "$W/dump/$f" "$(kept_name "$name" "$k")"
	done
	for f in "$W"/words/*; do
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
	# 2. the own task's page and the EDM's ticks (s-k)
	if [ "$fwk" = 1 ]; then
		fw page > "$W/$name.page.json"; keep "$name" "$W/$name.page.json" "$(kept_name "$name" page)"
		fw status > "$W/$name.status.json"; keep "$name" "$W/$name.status.json" "$(kept_name "$name" status)"
		if ! fw_alive "$(cat "$W/$name.status.json")"; then
			STALLS=$((STALLS + 1))
			if [ "$STALLS" -ge 2 ]; then echo "## STOP: a second EDM stall (after $name): s-k ends"; exit 11; fi
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
		: # the capture is checked before anything is read from it (r5 freeze 2)
		dk=""; [ "$vprem" = 1 ] && dk=dump    # s-v's calibrations: G5's block reading needs both dump files whole
		[ "$tdump" = 1 ] && dk="$dk tdump"     # s-b's 2048x2048 calibration: H-WALK64 reads its tri dump
		why=$(capture_ok "$name" "$dk") || {
			printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P_RES" "$knobs" "$rt" "$args" "$rc" "capture" "$why" >> "$KEEP/cases.tsv"
			echo "## STOP: the capture of $name is not whole ($why): nothing is read from it"; exit 13; }
	fi
	rd=$(dpm_read "$W/$name.out" "$W/after.buf09.bin")
	oc=$(field "$rd" cls)
	if [ "$fwk" = 1 ]; then rg=$("$PY3" "$HERE_LIB/r7read.py" ring "$W/$name.page.json" "$W/$name.out"); rd="$rd $rg"; fi
	note="${pnote}class $oc $rd"
	echo "  reading: $rd"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P_RES" "$knobs" "$rt" "$args" "$rc" "$class" "$note" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	hang|fault|fail) echo "## STOP: $class in $name (rc $rc)"; reset_gpu; health </dev/null; exit 4 ;;
	esac
	# 4. premises, calibrations, controls.  First: a control without a reading of a key it declared STOPS (it never reaches a gate)
	thr=$((P_RES - 34))
	if [ -n "$rkeys" ]; then
		pm=$(premise "$name" "$rkeys" "$rd") || stopctl "$(printf '%s' "$pm" | grep STOP | head -n 1)"
	fi
	if [ "$prem" = 1 ]; then
		kn=$(field "$rd" knob)
		[ -n "$kn" ] && [ "$kn" != - ] && [ $((kn)) -eq "$thr" ] || stopctl "$name: its own 0x0624 read ${kn:-?}, P - 0x22 is $(printf '0x%x' "$thr")"
	fi
	if [ -n "$cal" ]; then
		"$PY3" "$HERE_LIB/r7read.py" steps "$W/$name.out" > "$STATE/$cal.steps"
		if [ -n "$mdl" ]; then
			if mw=$("$PY3" "$HERE_LIB/r7read.py" model "$W/$name.out" "$mdl"); then : > "$STATE/$cal.modelok"; echo "  calibration $cal: steps in the model's brackets"
			else
				[ "$prem" = 1 ] && stopctl "calibration $name off the frozen model ($mw)"
				: > "$STATE/$cal.modeloff"; echo "  calibration $cal: OFF the model ($mw): its M cells are re-picked from its own steps"
			fi
		fi
		if [ "$vprem" = 1 ] && [ "$(field "$rd" gmax)" != - ] && [ "$(($(field "$rd" gmax)))" -lt 2 ]; then
			: > "$STATE/$cal.bad"; echo "  calibration $cal: no second global page, not the 1500-vertex scene: its cells will be skipped"
		fi
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
	if [ -n "$cleft" ]; then   # the reader prints numbers as 0x..: compared numerically (lib_check.sh num_eq)
		gl=$(field "$rd" gps_left); num_eq "$gl" "$cleft" || stopctl "control $name left ${gl:-?} global pages, frozen $cleft"
	fi
	if [ -n "$ccnt" ]; then
		np=$(field "$rd" nparts); num_eq "$np" "$ccnt" || stopctl "control $name read ${np:-?} partial renders, frozen $ccnt"
	fi
	if [ -n "$cneed" ]; then
		nd=$(field "$rd" need); num_eq "$nd" "$cneed" || stopctl "control $name read a page need of ${nd:-?}, frozen $cneed"
	fi
	if [ -n "$cpeaks" ]; then
		pk=$(field "$rd" runpeaks); [ "$pk" = "$cpeaks" ] || stopctl "control $name read run peaks ${pk:-?}, frozen $cpeaks"
	fi
	if [ "$fwprem" = 1 ]; then
		rc_=$(field "$rd" ring_counts); num_eq "$rc_" 1 || stopctl "premise $name: the rungs' page counts are not inside the host samples (ring_counts ${rc_:-?})"
	fi
	drop_w
done
set +f
if [ -n "$ONLY" ] && [ "$njob" -eq 0 ]; then echo "## abort: ONLY=$ONLY ran no job"; exit 1; fi
health </dev/null
echo "## end: $njob jobs of $STAGE"
