#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT: one R4-A job table on the laptop, one job a line of tables/STAGE.txt in file order.
# FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (k.sh passes it): the laptop's copy must be that file.  ATTEMPT names the
# output directory ~/r4a-out/ATTEMPT/STAGE, which must not exist or be empty (one directory an attempt; nothing is merged).  SIGPIPE
# and SIGHUP are ignored (a dropped ssh does not stop a stage half way); everything printed also goes to $KEEP/runner.log.
# Built from R3K-regress's runner (closing3/overnight/r3k-regress) with the knob rgn:1 added.
# Line: name|set|risk|knobs|rt|args        (the tool is $T, the job's directory $W)
#   knobs  words (space separated), only these:
#            rgn:1        after the job's reset, debugfs render_rgn_arrays is written 1 and read back (rc 19 if it does not read
#                         1); after the job it is written 0 and read back (rc 19); at every exit the trap writes 0
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every
#                         `tri` row (a row without it is refused before anything runs)
#            stophang     accepted, no effect (any hang stops the stage anyway)
#          any other word (held, bif, idle, rgn:4, rgn:0, hypo:..., noreset ...) is refused: rc 7, nothing runs
#   rt     "-" only (no regtimeline in this session)
# STOP RULE (fault limit 1): the first fault-class event (a BIF fault, a hang, a timeout) or unexplained failure ends the stage:
# reset, health check, rc 4 (3 for a fatal kernel message, 6 for a job that did not return: nothing but the knob restore and the
# exit log touches the machine).
# Every job: a reset, the knob, kernel-log markers and the case marker ("resgx545 case NAME RUN") right before the job starts; the
# kernel log after the case marker is kept as NAME.dmesg.gz (the slice is by the marker, not by a line count); debugfs kpoke is read
# after the job and kept as NAME.kpoke.txt.gz (what is still armed); cases.tsv gets rc and class.  The reset information lines are
# not bad lines.  After the last job a reset (it disarms anything left) comes before the end health.
# Exit status: 0 stage done; 1 preflight (also a table that is not the frozen one, a tri row without expectdiff or --keep-going, a
# laptop FROZEN.sha256 that is not the Mac's); 3 FATAL kernel message; 4 an unexpected hang, fault or failure; 5 the first failed
# health recovery; 6 a job did not return (freeze); 7 a forbidden knob; 12 the registers could not be read; 13 the reset before a
# job failed; 14 a fault is latched before a job; 19 a knob did not read back.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours, no loop
# that waits.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$DIR/../FROZEN.sha256" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$DIR/../FROZEN.sha256" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_k.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (k.sh passes it)"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] != "expectdiff" && k[i] != "stophang" && k[i] != "rgn:1") { print $1 ": " k[i]; bad=1 } if ($5 != "-") { print $1 ": rt " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or rt that R4-A does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $6 !~ /--keep-going/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without --keep-going"; exit 1; }
. "$DIR/lib_k.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$DIR/../FROZEN.sha256"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_k.sh run_stage.sh k.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done
begin
njob=0
TOTAL=$(grep -v '^#' "$FILE" | grep -vc '^$')
for i in $(seq 1 "$TOTAL"); do
	line=$(grep -v '^#' "$FILE" | grep -v '^$' | sed -n "${i}p")
	IFS='|' read -r name sset risk knobs rt args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; mkdir -p "$JW/dump"; W=$JW
	echo "== $name set=$sset risk=$risk knobs=[$knobs]"
	reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; }
	want_rgn=0
	case " $knobs " in *" rgn:1 "*) want_rgn=1 ;; esac
	if [ "$want_rgn" = 1 ]; then
		rgn_set 1 || { echo "## STOP: render_rgn_arrays does not read back 1 before $name ($(rgn_now))"; exit 19; }
		mark "rgn $name 1"
	fi
	knobs_ok "$want_rgn" || { echo "## STOP: a knob is not as the row asks before $name (hold_recovery $(hold_now), render_rgn_arrays $(rgn_now))"; exit 19; }
	mark "knobs-read $name hold_recovery=$(hold_now) render_rgn_arrays=$(rgn_now)"
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	eval "set -- $args"
	echo "  cmd: $T $*"
	mark_case "$name"
	sudo -n timeout -k 10 "$JOB_TIMEOUT" "$T" "$@" > "$JW/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^(job|tri:|BIF_INT_STAT)' "$JW/$name.out" | head -3 | tr '\n' ' ' | cut -c1-200)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	dbg_cat kpoke > "$JW/$name.kpoke" 2>&1
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	keep "$name" "$JW/$name.kpoke" ".kpoke.txt"
	for f in "$JW"/*.regs "$JW"/dump/*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	# the knob back to the default before anything else (health, the next reset, a stop)
	if [ "$want_rgn" = 1 ]; then
		rgn_set 0 || { echo "## STOP: render_rgn_arrays does not read back 0 after $name ($(rgn_now))"; exit 19; }
		mark "rgn-back $name 0"
	fi
	# 1. the kernel itself in trouble: stop at once, touch nothing more
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$name.dmesg" "$JW/$name.out" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job (the reset information lines left out)
	if bad_lines "$JW/$name.out" "$JW/$name.dmesg" | grep -Eq "BIF fault|faulted"; then class=fault
	elif bad_lines "$JW/$name.out" "$JW/$name.dmesg" | grep -Eq "job [0-9]+ hung|hung|timed out waiting"; then class=hang
	elif [ "$rc" -eq 0 ]; then class=ok
	else class=fail; fi
	if [ "$class" = fail ]; then
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$JW/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:|^sgxfive-test: " "$JW/$name.out"; then class=ok; fi ;;
		esac
	fi
	echo "  class $class"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$rt" "$args" \
		"$rc" "$class" plain - - no >> "$KEEP/cases.tsv"
	case "$class" in
	ok) ;;
	fault) echo "## STOP: fault-class event in $name (fault limit 1: any fault ends the stage)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	hang) echo "## STOP: hang in $name (fault limit 1: any hang ends the stage)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	fail) echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	esac
done
JW=$WROOT/end; mkdir -p "$JW"
reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
health end </dev/null
echo "## end: $njob jobs of $STAGE"
