#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT: one r7-geo job table on the laptop, one job a line of tables/STAGE.txt in file order.
# FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (g.sh passes it): the laptop's copy must be that file.  ATTEMPT names
# ~/scratch/r7g/out/ATTEMPT/STAGE (new or empty).  SIGPIPE and SIGHUP are ignored (a dropped ssh does not stop a stage half way);
# everything printed also goes to $KEEP/runner.log.  Built from round 6's r6-misc runner (closing6/r6-misc/run/run_stage.sh, freeze
# 2, which ran) with round 7's knobs: no hypothesis faults (r7-geo expects none), gate groups, soft rows, a health check after a
# row, the controls' premise check.
# Table header lines:  #stage NAME   #limit N (the fault-class events the stage may take: 1, the first stops)
# Line: name|set|risk|knobs|tool|args   (tool t4 = ~/sgxfive-test-rgn4, t6 = ~/scratch/r7g/bin/sgxfive-test; $W the job's work
#                                        directory, $S the staged programs ~/scratch/r7g/stage)
#   knobs  words (space separated), only these:
#            -            none
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every tri row
#            needhash     the output must have `target: WxH hash 0x...`; the second such row without it stops the stage (rc 17)
#            after        the health fill and triangle right after the job (strict: a failure recovers and stops, rc 16)
#            soft         a failure that is no fault and no hang (rc != 0 without a diff line, or a depth dump not written) is
#                         recorded in void.tsv (class fail) and the stage goes on; the second soft failure IN A ROW stops it (rc 24)
#            grp:G        the row belongs to size group G
#            gate         (with grp:G) a refusal (rc 1, no fault, no hang, no diff line) is recorded in void.tsv and skips the
#                         rest of group G (cannot tell); the stage goes on
#          any other word is refused: rc 7, nothing runs
# CONTROLS (set control): the run-time premise check: the reading keys gen/data/controls.tsv lists for the row (hash: the target
# line; tri: the triangle count line; dump: the depth dump's sha256; rows: the pixel rows) must all have been read, or the stage
# STOPS (rc 25, sessioncheck.py premise: a control with no reading never reaches a gate).
# STOP RULES: any fault or hang ends the stage (strict health, rc 4; the LIMIT is 1); a fatal kernel message rc 3; a job that did
# not return rc 6; an unexplained failure of a row that is not soft or a gate rc 4; less than the free space before a job rc 22; a
# file the scorer reads not kept rc 23; two soft failures in a row rc 24; a control without its reading rc 25.
# Every job: free space, a reset, the case marker right before the job; stdout and stderr kept apart (NAME.txt.gz, NAME.err.gz);
# the kernel log after the marker (NAME.dmesg.gz); the registers before and after the job; the depth dump (NAME.depth.1.bin.gz);
# the job's work directory removed once kept.  After the last job a reset and the end health.
# Exit status: 0 stage done; 1 preflight (a table, runner, program or tool that is not the frozen one); 3 FATAL kernel message;
# 4 an unexpected hang, fault or failure; 5 a failed health recovery; 6 a job did not return; 7 a forbidden knob or tool;
# 12 registers unreadable; 13 the reset before a job failed; 14 a fault latched before a job; 16 strict health failed; 17 two rows
# without a hash; 22 not enough free space; 23 a file the scorer reads was not written or not kept; 24 two soft failures in a
# row; 25 a control without its reading.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours, no wait loop.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$DIR/../FROZEN.sha256" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$DIR/../FROZEN.sha256" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_g.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (g.sh passes it)"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|needhash|after|soft|gate|grp:[a-z0-9]+)$/) { print $1 ": " k[i]; bad=1 } if ($5 != "t4" && $5 != "t6") { print $1 ": tool " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or tool that r7-geo does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 && $4 ~ /(^| )gate( |$)/ && $4 !~ /grp:/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a gate row without its group"; exit 7; }
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-1}
NEED_T6=0; awk -F'|' '!/^#/ && NF>=6 && $5 == "t6" { f=1 } END { exit !f }' "$FILE" && NEED_T6=1
NEED_STAGE=0; grep -v '^#' "$FILE" | grep -q '\$S/' && NEED_STAGE=1
NEED_PY=0; awk -F'|' '!/^#/ && NF>=6 && $2 == "control" { f=1 } END { exit !f }' "$FILE" && NEED_PY=1
. "$DIR/lib_g.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$DIR/../FROZEN.sha256"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in run/lib_g.sh run/run_stage.sh run/g.env score/sessioncheck.py score/scorekit.py gen/data/controls.tsv bins/SHA256SUMS; do
	b=${f##*/}; case "$f" in gen/*|bins/*) p=$DIR/../$b ;; *) p=$DIR/$b ;; esac
	want=$(expect_sha "$f"); got=$(sha "$p" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "$f (staged as $p) is not the frozen one"; exit 1; }
done

# ---- the rows ---------------------------------------------------------------------------------------------------------------
begin
njob=0; SKIP_GRPS=""; FAULT_EVENTS=0; NOHASH=0; SOFT_RUN=0
grep -v '^#' "$FILE" | grep -v '^$' > "$WROOT/rows"
TOTAL=$(grep -c . "$WROOT/rows")
for i in $(seq 1 "$TOTAL"); do
	line=$(sed -n "${i}p" "$WROOT/rows")
	IFS='|' read -r name sset risk knobs tool args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; needhash=0; gate=0; soft=0; after=0
	for k in $knobs; do
		case "$k" in
		grp:*) grp=${k#grp:} ;;
		needhash) needhash=1 ;;
		gate) gate=1 ;;
		soft) soft=1 ;;
		after) after=1 ;;
		expectdiff|-) ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	case "$tool" in t4) TT=$T4 ;; t6) TT=$T6 ;; *) echo "## STOP: unknown tool $tool in $name"; exit 7 ;; esac
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp was refused at its gate"; continue; } ;; esac
	njob=$((njob + 1))
	# the job's work directory and the directories its options name: --depth-dump DIR writes DIR/depth.N.bin into an existing DIR
	JW=$WROOT/$njob-$name; mkdir -p "$JW" "$JW/depth"; W=$JW; S=$STAGED
	echo "== $name set=$sset risk=$risk tool=$tool knobs=[$knobs]"
	need=$MIN_FREE_KB
	case " $args " in *" --depth-pages "*) pg=$(printf '%s\n' "$args" | sed -n 's/.*--depth-pages \([0-9]*\).*/\1/p'); need=$((MIN_FREE_KB + 8 * ${pg:-0})) ;; esac
	fk=$(free_kb); free_ok "$need" || { echo "## STOP: $fk KiB free on ~ before $name (at least $need)"; exit 22; }
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
	echo "  rc $rc $(grep -E '^(job|target|diff|outside|tri [0-9]+x[0-9]+ #1: [0-9])' "$JW/$name.out" | head -4 | tr '\n' ' ' | cut -c1-220)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.err" ".err"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	for f in "$JW"/*.regs "$JW"/depth/*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	# 0. every file a scorer reads must be kept (score_g.py REQUIRED): the output always; a completed --depth-dump row's dump (below)
	if [ ! -s "$KEEP/$name.txt.gz" ]; then echo "## STOP: the output of $name was not kept"; drop_work "$JW"; exit 23; fi
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
	# a --depth-dump row that completed but whose dump was not written or not kept: a soft row records it, any other stops (rc 23)
	dumpok=1
	if [ "$class" = ok ]; then
		case " $args " in *" --depth-dump "*)
			if ! has_kept "$KEEP/$name".depth.*.bin.gz || grep -q -- "--depth-dump: " "$JW/$name.out"; then dumpok=0; fi ;;
		esac
	fi
	if [ "$class" = ok ] && [ "$dumpok" = 0 ] && [ "$soft" = 1 ]; then class=fail; fi
	fint=-; fword=-
	if [ "$class" = fault ]; then fint=$(fault_int "$JW/$name.dmesg"); fword=$(fault_word "$JW/$name.dmesg"); fi
	echo "  class $class"
	mark "class $name $class"
	# a soft row's failure and a gate's refusal are void rows: void.tsv (the scorer reads them as cannot tell), never cases.tsv,
	# whose rows are the ones every REQUIRED file of the scorer must exist for
	tsv=cases.tsv
	if [ "$class" = fail ] && { [ "$soft" = 1 ] || { [ "$gate" = 1 ] && [ "$rc" -eq 1 ] && ! grep -q '^diff:' "$JW/$name.out"; }; }; then tsv=void.tsv; fi
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$tool" "$args" \
		"$rc" "$class" "${fint:-unread}" "${fword:-unread}" "$fk" >> "$KEEP/$tsv"
	case "$class" in
	ok)
		SOFT_RUN=0
		if [ "$dumpok" = 0 ]; then
			echo "## STOP: the depth dump of $name was not written or not kept (the scorer reads $name.depth.1.bin.gz)"; drop_work "$JW"; exit 23
		fi
		if [ "$needhash" = 1 ] && ! grep -Eq '^target: [0-9]+x[0-9]+ hash 0x[0-9a-f]+' "$JW/$name.out"; then
			NOHASH=$((NOHASH + 1)); echo "  no hash line ($NOHASH)"
			[ "$NOHASH" -ge 2 ] && { echo "## STOP: the second row without a hash ($name)"; drop_work "$JW"; exit 17; }
		fi ;;
	fault|hang)
		FAULT_EVENTS=$((FAULT_EVENTS + 1))
		echo "  $class: BIF_INT_STAT bits 15:0 ${fint:-unread}, BIF_FAULT ${fword:-unread}"
		mark "$class $name ${fint:-unread} ${fword:-unread}"
		echo "## STOP: unexpected $class in $name (r7-geo expects none; the stage's limit is $FAULT_LIMIT)"
		[ "$class" = hang ] && reset_gpu
		strict_health "$name" </dev/null; drop_work "$JW"; exit 4 ;;
	fail)
		if [ "$gate" = 1 ] && [ "$rc" -eq 1 ] && ! grep -q '^diff:' "$JW/$name.out"; then
			SKIP_GRPS="$SKIP_GRPS $grp"
			echo "## gate: $name was refused (rc 1, no diff line): group $grp is skipped (cannot tell), the stage goes on"
			mark "gate $name refused $grp"
			health "$name" </dev/null; drop_work "$JW"; continue
		fi
		if [ "$soft" = 1 ]; then
			SOFT_RUN=$((SOFT_RUN + 1))
			echo "  soft failure ($SOFT_RUN in a row): recorded, the stage goes on"
			reset_gpu; health "$name" </dev/null
			[ "$SOFT_RUN" -ge 2 ] && { echo "## STOP: the second soft failure in a row ($name)"; drop_work "$JW"; exit 24; }
			drop_work "$JW"; continue
		fi
		echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; drop_work "$JW"; exit 4 ;;
	esac
	# 3. a control's premise: every reading it declares (gen/data/controls.tsv) was read
	if [ "$sset" = control ]; then
		keys=$(awk -F'\t' -v n="$name" '$1 == n { print $3; exit }' "$DIR/../controls.tsv")
		reading=""
		h=$(sed -n 's/^target: [0-9]*x[0-9]* hash \(0x[0-9a-f]*\).*/\1/p' "$JW/$name.out" | head -n 1); [ -n "$h" ] && reading="$reading hash=$h"
		t=$(sed -n 's/^tri [0-9]*x[0-9]* #1: \([0-9]*\) triangle.*/\1/p' "$JW/$name.out" | head -n 1); [ -n "$t" ] && reading="$reading tri=$t"
		[ -s "$JW/depth/depth.1.bin" ] && reading="$reading dump=$(sha "$JW/depth/depth.1.bin" | cut -d' ' -f1)"
		nr=$(grep -cE '^row [0-9]+:|^probe [^ ]+: row [0-9]+:' "$JW/$name.out"); [ "$nr" -gt 0 ] && reading="$reading rows=$nr"
		echo "  premise $name [$keys]:$reading"
		printf '%s\n' "$reading" > "$JW/premise.txt"
		if ! python3 "$DIR/sessioncheck.py" premise "$name" "$keys" "$JW/premise.txt"; then
			echo "## STOP: premise: control $name lacks a reading it declares ($keys)"; drop_work "$JW"; exit 25
		fi
	fi
	if [ "$after" = 1 ]; then strict_health "$name" </dev/null; fi
	drop_work "$JW"
done
JW=$WROOT/end; mkdir -p "$JW"
reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
health end </dev/null
drop_work "$JW"
echo "## end: $njob jobs of $STAGE"
