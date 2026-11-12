#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT TOOL6_SHA256: one r6-misc job table on the laptop, one job a line of tables/STAGE.txt in
# file order.  FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (m.sh passes it): the laptop's copy must be that file.
# TOOL6_SHA256 is the sha256 of the t6 build the lead froze (TOOL6.sha256): the laptop's TOOL6.sha256 must hold it, and a stage with
# a t6 row runs only if ~/scratch/r6m/bin/sgxfive-test has it.  ATTEMPT names ~/scratch/r6m/out/ATTEMPT/STAGE (new or empty).  SIGPIPE
# and SIGHUP are ignored (a dropped ssh does not stop a stage half way); everything printed also goes to $KEEP/runner.log.
# Built from round 5's r5-render4x runner without its knobs and held flow (this session writes no debugfs knob).
# Table header lines:  #stage NAME   #limit N (the fault-class events the stage may take)
# Line: name|set|risk|knobs|tool|args        (tool t4 = ~/sgxfive-test-rgn4, t6 = ~/scratch/r6m/bin/sgxfive-test; $W the job's dir)
#   knobs  words (space separated), only these:
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every tri row
#            strict       after a fault-class event the FIRST health fill and triangle must draw: else recovery and stop (rc 16)
#            hypo:G:MAX   a FAULT is a stated hypothesis of group G: measured (class recorded, strict health); after MAX faults the
#                         group's other rows are skipped; a fault in a row without it stops the stage (rc 4, after strict health)
#            needhash     the output must have `target: WxH hash 0x...`; the second such row without it stops the stage (rc 17)
#            gateodd      (q287's first row) a `rejected` job (rc 1, no fault, no diff line): the module refuses the odd height;
#                         the stage ends cleanly (rc 21) and the driver goes on
#          any other word is refused: rc 7, nothing runs
# STOP RULES: an unexpected fault, hang or failure ends the stage (strict health, rc 4); a hypothesis fault whose BIF_INT_STAT bits
# 15:0 are not 0x0100 or whose BIF_FAULT is not 0x100000xx (E511's 3D-side class), or a "recovery failed: -110" line, ends it
# (rc 18); the LIMIT-th fault-class event of the stage ends it when rows that would run remain (rc 15); a fatal kernel message is
# rc 3 and a job that did not return rc 6; less than MIN_FREE_KB free on ~ before a job rc 22.
# Every job: free space, a reset, the case marker right before the job; stdout and stderr kept apart (NAME.txt.gz, NAME.err.gz: a
# message cannot split a pixel row, E511's correction); the kernel log after the marker (NAME.dmesg.gz); the registers after the job
# (snap 9); the job's work directory removed once kept.  After the last job a reset and the end health.
# Exit status: 0 stage done; 1 preflight (a table, runner or tool that is not the frozen one); 3 FATAL kernel message; 4 an
# unexpected hang, fault or failure; 5 a failed health recovery; 6 a job did not return; 7 a forbidden knob or tool; 12 registers
# unreadable; 13 the reset before a job failed; 14 a fault latched before a job; 15 the fault limit with rows left; 16 strict health
# failed; 17 two rows without a hash; 18 a fault that is not the 3D-side class, or a -110; 21 gateodd: odd heights refused (clean);
# 22 not enough free space.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours, no wait loop.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
TOOL6_SHA=${4:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$DIR/../FROZEN.sha256" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$DIR/../FROZEN.sha256" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_m.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (m.sh passes it)"; exit 1; }
case "$TOOL6_SHA" in [0-9a-f]*) [ ${#TOOL6_SHA} -eq 64 ] || { echo "the t6 sha256 is not 64 hex digits"; exit 1; } ;; *) echo "no t6 sha256 (m.sh passes TOOL6.sha256's)"; exit 1 ;; esac
[ "$(cut -d' ' -f1 "$DIR/../TOOL6.sha256")" = "$TOOL6_SHA" ] || { echo "the laptop's TOOL6.sha256 does not hold $TOOL6_SHA: run run/stage_m.sh again"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|strict|needhash|gateodd|hypo:[a-z0-9]+:[0-9]+)$/) { print $1 ": " k[i]; bad=1 } if ($5 != "t4" && $5 != "t6") { print $1 ": tool " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or tool that r6-misc does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-1}
NEED_T6=0; awk -F'|' '!/^#/ && NF>=6 && $5 == "t6" { f=1 } END { exit !f }' "$FILE" && NEED_T6=1
. "$DIR/lib_m.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$DIR/../FROZEN.sha256"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_m.sh run_stage.sh m.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done

# ---- the rows ---------------------------------------------------------------------------------------------------------------
begin
njob=0; SKIP_GRPS=""; FAULT_EVENTS=0; NOHASH=0
grep -v '^#' "$FILE" | grep -v '^$' > "$WROOT/rows"
TOTAL=$(grep -c . "$WROOT/rows")
# rows_left I: the rows after the I-th that would still run (their group not skipped)
rows_left() {
	awk -F'|' -v i="$1" -v sk=" $SKIP_GRPS " 'NR > i { g = ""; n = split($4, k, " "); for (j = 1; j <= n; j++) if (k[j] ~ /^hypo:/) { split(k[j], p, ":"); g = p[2] } if (g == "" || index(sk, " " g " ") == 0) c++ } END { print c + 0 }' "$WROOT/rows"
}
for i in $(seq 1 "$TOTAL"); do
	line=$(sed -n "${i}p" "$WROOT/rows")
	IFS='|' read -r name sset risk knobs tool args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0; needhash=0; gateodd=0
	for k in $knobs; do
		case "$k" in
		hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;;
		needhash) needhash=1 ;;
		gateodd) gateodd=1 ;;
		expectdiff|strict|-) ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	case "$tool" in t4) TT=$T4 ;; t6) TT=$T6 ;; *) echo "## STOP: unknown tool $tool in $name"; exit 7 ;; esac
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp reached its $gmax faults"; continue; } ;; esac
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; mkdir -p "$JW"; W=$JW
	echo "== $name set=$sset risk=$risk tool=$tool knobs=[$knobs]"
	fk=$(free_kb); free_ok || { echo "## STOP: $fk KiB free on ~ before $name (at least $MIN_FREE_KB)"; exit 22; }
	reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; }
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	eval "set -- $args"
	echo "  cmd: $TT $*"
	mark_case "$name"
	sudo -n timeout -k 10 "$JOB_TIMEOUT" "$TT" "$@" > "$JW/$name.out" 2> "$JW/$name.err" </dev/null
	rc=$?
	snap "$name" 9 || { echo "## STOP: registers unreadable after $name"; exit 12; }
	echo "  rc $rc $(grep -E '^(job|target|diff|outside)' "$JW/$name.out" | head -4 | tr '\n' ' ' | cut -c1-220)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.err" ".err"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	for f in "$JW"/*.regs "$JW"/depth.*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	# 1. the kernel itself in trouble: stop at once, touch nothing more
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$name.dmesg" "$JW/$name.out" "$JW/$name.err" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job
	class=$(classify_plain "$JW/$name.out" "$JW/$name.err" "$JW/$name.dmesg" "$rc")
	if [ "$class" = fail ]; then
		case " $knobs " in *" expectdiff "*)
			if [ "$rc" -eq 1 ] && grep -q '^diff:' "$JW/$name.out" && ! grep -Eq "FAILED after|rejected|cancelled|Segmentation|failed:|^sgxfive-test: " "$JW/$name.out" "$JW/$name.err"; then class=ok; fi ;;
		esac
	fi
	fint=-; fword=-
	if [ "$class" = fault ]; then fint=$(fault_int "$JW/$name.dmesg"); fword=$(fault_word "$JW/$name.dmesg"); fi
	echo "  class $class"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$tool" "$args" \
		"$rc" "$class" "${fint:-unread}" "${fword:-unread}" "$fk" >> "$KEEP/cases.tsv"
	case "$class" in
	ok)
		if [ "$needhash" = 1 ] && ! grep -Eq '^target: [0-9]+x[0-9]+ hash 0x[0-9a-f]+' "$JW/$name.out"; then
			NOHASH=$((NOHASH + 1)); echo "  no hash line ($NOHASH)"
			[ "$NOHASH" -ge 2 ] && { echo "## STOP: the second row without a hash ($name)"; drop_work "$JW"; exit 17; }
		fi ;;
	fault)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		echo "  fault: BIF_INT_STAT bits 15:0 ${fint:-unread}, BIF_FAULT ${fword:-unread}"
		mark "fault $name ${fint:-unread} ${fword:-unread}"
		if [ -z "$grp" ]; then
			echo "## STOP: unexpected fault in $name"
			strict_health "$name" </dev/null; drop_work "$JW"; exit 4
		fi
		gv=$(printf '%s' "$grp" | tr -c 'A-Za-z0-9' '_'); eval "HYPO_$gv=\$(( \${HYPO_$gv:-0} + 1 ))"; eval "n=\$HYPO_$gv"
		echo "  fault $n of at most $gmax in group $grp (a hypothesis: measured); fault-class events of the stage: $FAULT_EVENTS of $FAULT_LIMIT"
		[ "$n" -ge "$gmax" ] && SKIP_GRPS="$SKIP_GRPS $grp"
		strict_health "$name" </dev/null
		if [ "${fint:-x}" != 256 ] || ! word_3d "${fword:-x}" || grep -q 'recovery failed: -110' "$JW/$name.dmesg"; then
			echo "## STOP: the fault of $name is not the 3D-side class (bits 15:0 ${fint:-unread}, BIF_FAULT ${fword:-unread}) or a -110: stop (rc 18)"
			drop_work "$JW"; exit 18
		fi
		if [ "$FAULT_EVENTS" -ge "$FAULT_LIMIT" ] && [ "$(rows_left "$i")" -gt 0 ]; then
			echo "## STOP: the $FAULT_EVENTS-th fault-class event of the stage ($FAULT_LIMIT is the limit) with rows left: stop after $name"
			drop_work "$JW"; exit 15
		fi ;;
	hang)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		echo "## STOP: unexpected hang in $name"
		reset_gpu
		strict_health "$name" </dev/null; drop_work "$JW"; exit 4 ;;
	fail)
		if [ "$gateodd" = 1 ] && [ "$rc" -eq 1 ] && grep -Eq 'rejected|render: Invalid argument' "$JW/$name.out" "$JW/$name.err" && ! grep -q '^diff:' "$JW/$name.out"; then
			echo "## gateodd: $name was refused (the module or tool takes no odd height): the stage ends cleanly"
			health "$name" </dev/null; drop_work "$JW"; exit 21
		fi
		echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; drop_work "$JW"; exit 4 ;;
	esac
	drop_work "$JW"
done
JW=$WROOT/end; mkdir -p "$JW"
reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
health end </dev/null
drop_work "$JW"
echo "## end: $njob jobs of $STAGE"
