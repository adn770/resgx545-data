#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE: one R3 job table on the laptop, one job a line of tables/STAGE.txt in file order.
# Line: name|set|risk|P|knobs|rt|args      (the tool is $T = ~/sgxfive-test-r1, staged programs $S, work directory $W)
#   P      render_pb_pages for the job ("-": leave it); put back after the job and at exit.  Or a cell the runner DERIVES from the
#          observations kept so far (state files in ~/r3g-out/state, one line a job: thr0 and class R raise / N none / V void):
#            B:G        the bisect cell of group G: thr0 = lo + (hi - lo) / 2, lo the highest raise, hi the lowest silent cell above
#                       it (run/bis.awk); none if the bracket is closed, absent, non-monotone or holds a void cell
#            L:G[:off]  the last raise of group G (+ off), F:G[:off] the first silent cell above it (+ off); P = thr0 + 0x22
#          A derived cell below thr0 0x60 or above P 0x422 is skipped.
#   knobs  words (space separated):
#            noreset      no GPU reset before this job (default: a reset before every job)
#            stophang     a hang in this job ends the stage (every unexpected hang or fault does anyway)
#            expectdiff   rc 1 WITH a `diff:` line is not a failure (no R3 row needs it)
#            ctl:R|N      a control: after the job its class (raise R / none N, read from the kept output: the second run must reach
#                         thr0 and the control block's dword 38 must be 0x20 for R) must be the one written; a different reading
#                         STOPS the session (rc 10: nothing after a failed control is a reading) and writes state/CTLFAIL, which
#                         refuses every later DPM stage until g-c4 is run again (CTL_OVERRIDE=1 overrides)
#            obs:G        the job's class and thr0 are appended to group G's state (the stage start empties the groups its rows own)
#            cal:G        a calibration: the page need (the peak 0x0724) and the partial renders are kept in state G.cal
#            gate:N       with cal: more than N partial renders at the calibration end the stage: every later row is skipped (g-c7)
#            fit:G        the row is skipped if 2 thr0 is not below the page need of G's calibration (the second run cannot reach thr0)
#   rt     "-", or a regtimeline register list LO-HI[,LO-HI]: the tool runs under it (read-only)
# There are no hypothesis rows: EVERY hang, fault or failure stops the stage (rc 3 with "scene overflowed" is the normal class of the DPM
# jobs and is ok).  Env: ONLY=NAME runs just that row of the table.
# Every job: kernel-log marker before the knob write ("knobs"), after the read-back ("readback") and the case marker ("resgx545 case NAME
# RUN") right before the tool starts; the kernel log slice after the case marker is kept as NAME.dmesg.gz.  cases.tsv gets rc, class
# and a note after every job, with the P actually written.
# Exit status: 0 stage done; 1 preflight (also a table or program whose sha256 differs from FROZEN.sha256, ONLY naming no row, the tool
# or the module not the pinned / expected ones, a refused DPM stage after a failed control); 3 FATAL kernel message (watchdog, lockup,
# BUG ...); 4 an unexpected hang, fault or failure; 5 the first failed health recovery; 6 a job did not return (freeze); 7 a forbidden knob;
# 8 a staged program is missing; 9 a knob read-back differs from the value written; 10 a control did not read its frozen value.
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
awk -F'|' -v pat="--kp""oke" '!/^#/ && NF>=7 && index($7, pat) { print $1; bad = 1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a poke (R3 has none)"; exit 1; }
. "$DIR/lib_r3.sh"
# the table and every staged program must be the frozen ones (the sha256 the freeze recorded)
expect_sha() { grep -h "  $1\$" "$DIR/../FROZEN.sha256" 2>/dev/null | head -n 1 | cut -d' ' -f1; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run stage_r3.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done
if [ -n "$ONLY" ] && ! grep -q "^$ONLY|" "$FILE"; then echo "ONLY=$ONLY names no row of $STAGE"; exit 1; fi
# the controls of g-c4 are the session's: a DPM stage after a failed control is refused (g-c4 itself clears the flag at its start)
HAS_CTL=$(awk -F'|' '!/^#/ && NF>=7 && $5 ~ /(^| )ctl:[RN]( |$)/ {f=1} END{print f+0}' "$FILE")
if [ "$NEED_RT" = 1 ] && [ "$HAS_CTL" = 0 ] && [ -e "$STATE/CTLFAIL" ] && [ "${CTL_OVERRIDE:-0}" != 1 ]; then
	echo "a control of an earlier DPM stage failed ($(cat "$STATE/CTLFAIL")): $STAGE is refused (CTL_OVERRIDE=1 to override)"; exit 1
fi
begin
# the groups this stage owns (rows with obs:G or cal:G) start empty; a group of an earlier stage (g-c4's) is only read
if [ -z "$ONLY" ]; then
	for g in $(awk -F'|' '!/^#/ && NF>=7 { n = split($5, k, " "); for (i = 1; i <= n; i++) if (k[i] ~ /^(obs|cal):/) { sub(/^[a-z]+:/, "", k[i]); print k[i] } }' "$FILE" | sort -u); do
		: > "$STATE/$g.obs"; : > "$STATE/$g.cal"
	done
	[ "$HAS_CTL" = 1 ] && rm -f -- "$STATE/CTLFAIL"
fi
echo "stage $STAGE: no gate (R1's 0x072c trial passed); dynamic rows read ~/r3g-out/state" > "$KEEP/notes.txt"
njob=0
GATED=""
skip_row() { # NAME REASON: a row that is not run, recorded as class skipped
	echo "== $1 set=$sset: skipped ($2)"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$STAGE" "$sset" "$risk" "${P_RES:--}" "$knobs" "$rt" "$args" "-" "skipped" "$2" >> "$KEEP/cases.tsv"
}
set -f
for line in $(grep -v '^#' "$FILE" | grep -v '^$' | tr ' ' '\001'); do
	set +f
	line=$(printf '%s' "$line" | tr '\001' ' ')
	IFS='|' read -r name sset risk P knobs rt args <<ROW
$line
ROW
	[ -z "$name" ] && continue
	[ -n "$ONLY" ] && [ "$name" != "$ONLY" ] && continue
	ctl=""; obs=""; cal=""; gate=""; fit=""
	for k in $knobs; do
		case "$k" in
		noreset|stophang|expectdiff) ;;
		ctl:*) ctl=${k#ctl:} ;;
		obs:*) obs=${k#obs:} ;;
		cal:*) cal=${k#cal:} ;;
		gate:*) gate=${k#gate:} ;;
		fit:*) fit=${k#fit:} ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	# 0. the P of a derived row, from the kept observations of its group
	P_RES=$P
	case "$P" in
	[BLF]:*)
		kind=${P%%:*}; rest=${P#*:}; grp=${rest%%:*}; off=0
		case "$rest" in *:*) off=${rest#*:}; off=${off#+} ;; esac
		r=$(bis "$grp" "$kind" "$off")
		case "$r" in
		SKIP*) P_RES="-"; skip_row "$name" "${r#SKIP }"; continue ;;
		*) thr=$r; P_RES=$(printf '0x%x' $((thr + 34)))
		   if [ "$thr" -lt "$MIN_THR0" ] || [ $((thr + 34)) -gt 1058 ]; then skip_row "$name" "thr0 $thr outside the allowed cells (0x60 .. 0x400)"; continue; fi ;;
		esac ;;
	esac
	if [ -n "$GATED" ]; then skip_row "$name" "gate closed by $GATED"; continue; fi
	if [ -n "$fit" ] && [ "$P_RES" != "-" ]; then
		need=$(cal_need "$fit")
		thr=$(( P_RES - 34 ))
		if [ -n "$need" ] && [ $((2 * thr)) -ge "$need" ]; then skip_row "$name" "2 thr0 $((2 * thr)) is not below the page need $need of $fit"; continue; fi
	fi
	njob=$((njob + 1))
	echo "== $name set=$sset risk=$risk P=$P_RES knobs=[$knobs] rt=$rt"
	case " $knobs " in *" noreset "*) echo "  no reset before (noreset)" ;; *) reset_gpu ;; esac
	mkdir -p "$W/dump" "$W/words" "$W/depth"; clean_w
	mark "knobs $name render_pb_pages=$P_RES"
	if [ "$P_RES" != "-" ]; then
		rb=$(set_knob render_pb_pages "$P_RES"); echo "  render_pb_pages written $P_RES, read back $rb"; mark "readback $name render_pb_pages=$rb"
		[ $((rb)) -eq $((P_RES)) ] || { echo "## STOP: render_pb_pages read back $rb, wrote $P_RES"; exit 9; }
	fi
	eval "set -- $args"
	echo "  cmd: $T $*"
	mark_case "$name"
	tmo=${JOB_TIMEOUT:-120}
	if [ "$rt" = "-" ]; then
		sudo -n timeout "$tmo" "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	else
		sudo -n timeout "$tmo" "$RT" 0 0.3 "$rt" -- "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	fi
	rc=$?
	echo "  rc $rc $(grep -E '^(job|tri:|probe .*: failed)' "$W/$name.out" | head -2 | tr '\n' ' ' | cut -c1-150)"
	slice_since "resgx545 case $name $RUN" > "$W/$name.dmesg"
	keep "$name" "$W/$name.out"
	keep "$name" "$W/$name.dmesg" ".dmesg"
	sudo -n cat "$D/buf09" > "$W/after.buf09.bin" 2>/dev/null && keep "$name" "$W/after.buf09.bin" ".after.buf09.bin"
	sudo -n cat "$D/regs" > "$W/after.regs.txt" 2>/dev/null && keep "$name" "$W/after.regs.txt" ".after.regs.txt"
	for f in "$W"/dump/* "$W"/words/* "$W"/depth/*; do
		[ -f "$f" ] && keep "$name" "$f" ".$(basename "$f")"
	done
	# restore the knob of the job before anything else touches the GPU
	[ "$P_RES" != "-" ] && [ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE" >/dev/null
	# 1. the kernel itself in trouble: stop at once, touch nothing
	if [ "$rc" -eq 124 ]; then
		echo "## STOP: $name did not return in $tmo s (freeze)"; FATAL_STOP=1; exit 6
	fi
	if grep -Eq "$FATAL_RE" "$W/$name.dmesg" "$W/$name.out"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name:"; grep -E "$FATAL_RE" "$W/$name.dmesg" | head -3; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job: hang and fault first, searched in the WHOLE output (rc 3 with "scene overflowed" is the normal overflow class)
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
	note="-"; oc=""; rd=""; thr=""
	if [ "$class" = ok ] && { [ -n "$obs" ] || [ -n "$cal" ] || [ -n "$ctl" ]; }; then
		rd=$(dpm_read "$W/$name.out")
		oc=$(obs_class "$name")
		thr=$(( P_RES - 34 ))
		note="class $oc $rd"
		echo "  reading: $rd -> $oc"
	fi
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$P_RES" "$knobs" "$rt" "$args" "$rc" "$class" "$note" >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	hang|fault|fail) echo "## STOP: $class in $name (rc $rc)"; reset_gpu; health </dev/null; exit 4 ;;
	esac
	# 3. the observations this job adds to its groups, the calibration and its gate
	[ -n "$obs" ] && obs_add "$obs" "$thr" "$oc" "$name"
	if [ -n "$cal" ]; then
		echo "$(field "$rd" need) $(field "$rd" nparts) $name" > "$STATE/$cal.cal"
		echo "  calibration $cal: page need $(field "$rd" need), partial renders $(field "$rd" nparts)"
		if [ -n "$gate" ] && [ "$(field "$rd" nparts)" -gt "$gate" ]; then
			GATED="$name ($(field "$rd" nparts) partial renders, more than $gate)"
			echo "  GATE CLOSED: $GATED: the rest of $STAGE is skipped"
		fi
	fi
	# 4. a control reads its frozen class or the session stops
	if [ -n "$ctl" ] && [ "$oc" != "$ctl" ]; then
		echo "## STOP: control $name read class ${oc:-?} ($rd), frozen $ctl: nothing after a failed control is a reading"
		echo "$name read ${oc:-?}, frozen $ctl" > "$STATE/CTLFAIL"
		exit 10
	fi
	clean_w
done
set +f
if [ -n "$ONLY" ] && [ "$njob" -eq 0 ]; then echo "## abort: ONLY=$ONLY ran no job"; exit 1; fi
health </dev/null
echo "## end: $njob jobs of $STAGE"
