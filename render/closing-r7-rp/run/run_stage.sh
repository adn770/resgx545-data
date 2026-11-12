#!/bin/bash
# SPDX-License-Identifier: MIT
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT TOOL7_SHA256: one r7-rp job table on the laptop, one job a line of tables/STAGE.txt in file
# order.  FROZEN_SHA256 is the sha256 of the Mac's FROZEN.sha256 (r7.sh passes it): the laptop's copy must be that file.  TOOL7_SHA256
# is the sha256 of the t7 build the lead froze (TOOL7.sha256): the laptop's TOOL7.sha256 must hold it, and a stage with a t7 row runs
# only if ~/scratch/r7r/bin/sgxfive-test-t7 has it.  ATTEMPT names ~/scratch/r7r/out/ATTEMPT/STAGE (new or empty).  SIGPIPE and SIGHUP
# are ignored (a dropped ssh does not stop a stage half way); everything printed also goes to $KEEP/runner.log.
# r6-misc's runner (closing6/r6-misc/run/run_stage.sh, freeze 2: the dump directory made and kept) with r6-render4x's rgn:1 knob and
# staged programs (#need), three tools and round 7's knobs oddw, expectfault and needdump.
# Table header lines:  #stage NAME   #limit N (the fault-class events the stage may take)   #need $S/FILE (a staged program)
# Line: name|set|risk|knobs|tool|args   (tool t4 = ~/sgxfive-test-rgn4, t6 = ~/scratch/r7r/bin/sgxfive-test-t6, t7 = ..-t7;
#                                        $W the job's work dir (with depth/ and dump/ made), $S = ~/scratch/r7r/stage)
#   knobs  words (space separated), only these:
#            expectdiff   rc 1 WITH a `diff:` line (the tool's reference check) is recorded, not a failure; REQUIRED on every tri row
#            strict       after a fault-class event the FIRST health fill and triangle must draw: else recovery and stop (rc 16)
#            hypo:G:MAX   a FAULT is a stated hypothesis of group G: measured (class recorded, strict health); after MAX faults the
#                         group's other rows are skipped; a fault in a row without it stops the stage (rc 4, after strict health)
#            needhash     the output must have `target: WxH hash 0x...`; the second such row without it stops the stage (rc 17)
#            gateodd      (q287's first row) a refused job (rc 1, `rejected` or `Invalid argument`, `FAILED after 0 renders`): every
#                         later `oddw` row is skipped, the others still run, and the stage exits 21 at its end (clean)
#            oddw         an odd-width row (skipped once gateodd fired)
#            rgn:1        after the job's reset, debugfs render_rgn_arrays is written 1 and read back (rc 19 if it does not read 1);
#                         written 0 and read back after the job (and at every exit)
#            expectfault  every rule predicts a fault: if the job COMPLETES, its files are kept and the stage stops (rc 19)
#            needdump     the row's --dump-render "$W/dump" must leave a file, kept (else rc 23)
#          any other word is refused: rc 7, nothing runs
# STOP RULES: an unexpected fault, hang or failure ends the stage (strict health, rc 4); a hypothesis fault whose BIF_INT_STAT bits
# 15:0 are not 0x0100 or whose BIF_FAULT is not 0x100000xx (E511's 3D-side class), or a "recovery failed: -110" line, ends it
# (rc 18); the LIMIT-th fault-class event of the stage ends it when rows that would run remain (rc 15); a fatal kernel message is
# rc 3 and a job that did not return rc 6; less than MIN_FREE_KB free on ~ before a job rc 22.
# Every job: free space, a reset, the knob, the case marker right before the job; stdout and stderr kept apart (NAME.txt.gz,
# NAME.err.gz); the kernel log after the marker (NAME.dmesg.gz); the registers before and after (snap 0, 9); every file the tool wrote
# in $W/depth and $W/dump (NAME.<file>.gz); the job's work directory removed once kept.  After the last job a reset and the end health.
# Exit status: 0 stage done; 1 preflight (a table, runner, program or tool that is not the frozen one); 3 FATAL kernel message; 4 an
# unexpected hang, fault or failure; 5 a failed health recovery; 6 a job did not return; 7 a forbidden knob or tool; 8 a staged
# program missing; 12 registers unreadable; 13 the reset before a job failed; 14 a fault latched before a job; 15 the fault limit with
# rows left; 16 strict health failed; 17 two rows without a hash; 18 a fault that is not the 3D-side class, or a -110; 19 the knob
# did not read back, or an expectfault row completed; 21 gateodd: odd widths refused (clean, the other rows ran); 22 not enough free
# space; 23 a file a scorer reads (the output, a depth dump, a render dump) was not written or not kept.
# No reboot, no boot-loader change, no kernel build, no clock-gate register, no trc_hazard, no register write of ours, no wait loop.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
TOOL7_SHA=${4:-}
DIR=$(cd "$(dirname "$0")" && pwd)
FILE=$DIR/../tables/$STAGE.txt
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$DIR/../FROZEN.sha256" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$DIR/../FROZEN.sha256" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): run run/stage_r7.sh again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (r7.sh passes it)"; exit 1; }
case "$TOOL7_SHA" in [0-9a-f]*) [ ${#TOOL7_SHA} -eq 64 ] || { echo "the t7 sha256 is not 64 hex digits"; exit 1; } ;; *) echo "no t7 sha256 (r7.sh passes TOOL7.sha256's)"; exit 1 ;; esac
[ "$(cut -d' ' -f1 "$DIR/../TOOL7.sha256")" = "$TOOL7_SHA" ] || { echo "the laptop's TOOL7.sha256 does not hold $TOOL7_SHA: run run/stage_r7.sh again"; exit 1; }
awk -F'|' '!/^#/ && NF>=6 { n = split($4, k, " "); for (i = 1; i <= n; i++) if (k[i] !~ /^(-|expectdiff|strict|needhash|gateodd|oddw|rgn:1|expectfault|needdump|hypo:[a-z0-9]+:[0-9]+)$/) { print $1 ": " k[i]; bad=1 } if ($5 != "t4" && $5 != "t6" && $5 != "t7") { print $1 ": tool " $5; bad=1 } } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a knob or tool that r7-rp does not allow"; exit 7; }
awk -F'|' '!/^#/ && NF>=6 && $6 ~ /^tri / && $4 !~ /(^| )expectdiff( |$)/ { print $1; bad=1 } END { exit bad }' "$FILE" \
	|| { echo "table $STAGE: a tri row without expectdiff"; exit 1; }
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-1}
NEED_T6=0; awk -F'|' '!/^#/ && NF>=6 && $5 == "t6" { f=1 } END { exit !f }' "$FILE" && NEED_T6=1
NEED_T7=0; awk -F'|' '!/^#/ && NF>=6 && $5 == "t7" { f=1 } END { exit !f }' "$FILE" && NEED_T7=1
. "$DIR/lib_r7.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$DIR/../FROZEN.sha256"; }
want=$(expect_sha "tables/$STAGE.txt"); got=$(sha "$FILE" | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "table $STAGE.txt is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
for f in lib_r7.sh run_stage.sh r7.env; do
	want=$(expect_sha "run/$f"); got=$(sha "$DIR/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "run/$f is not the frozen one"; exit 1; }
done
# every program a row names is staged and is the frozen one (bins/NAME in FROZEN.sha256)
for f in $(grep '^#need ' "$FILE" | cut -d' ' -f2-); do
	f=$(eval echo "$f"); [ -f "$f" ] || { echo "missing program $f: run run/stage_r7.sh first"; exit 8; }
	want=$(expect_sha "bins/${f##*/}"); got=$(sha "$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "program $f is not the frozen one"; exit 1; }
done

# ---- the rows ---------------------------------------------------------------------------------------------------------------
begin
njob=0; SKIP_GRPS=""; FAULT_EVENTS=0; NOHASH=0; ODD_REFUSED=0
grep -v '^#' "$FILE" | grep -v '^$' > "$WROOT/rows"
TOTAL=$(grep -c . "$WROOT/rows")
# rows_left I: the rows after the I-th that would still run (their group not skipped)
rows_left() {
	awk -F'|' -v i="$1" -v sk=" $SKIP_GRPS " -v oddref="$ODD_REFUSED" 'NR > i { g = ""; od = 0; n = split($4, k, " "); for (j = 1; j <= n; j++) { if (k[j] ~ /^hypo:/) { split(k[j], p, ":"); g = p[2] } if (k[j] == "oddw") od = 1 } if ((g == "" || index(sk, " " g " ") == 0) && !(od && oddref == 1)) c++ } END { print c + 0 }' "$WROOT/rows"
}
for i in $(seq 1 "$TOTAL"); do
	line=$(sed -n "${i}p" "$WROOT/rows")
	IFS='|' read -r name sset risk knobs tool args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gmax=0; needhash=0; gateodd=0; oddw=0; rgn=0; expectfault=0; needdump=0
	for k in $knobs; do
		case "$k" in
		hypo:*) g=${k#hypo:}; grp=${g%%:*}; gmax=${g##*:} ;;
		needhash) needhash=1 ;;
		gateodd) gateodd=1 ;;
		oddw) oddw=1 ;;
		rgn:1) rgn=1 ;;
		expectfault) expectfault=1 ;;
		needdump) needdump=1 ;;
		expectdiff|strict|-) ;;
		*) echo "## STOP: unknown knob $k in $name"; exit 7 ;;
		esac
	done
	case "$tool" in t4) TT=$T4 ;; t6) TT=$T6 ;; t7) TT=$T7 ;; *) echo "## STOP: unknown tool $tool in $name"; exit 7 ;; esac
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp reached its $gmax faults"; continue; } ;; esac
	[ "$ODD_REFUSED" = 1 ] && [ "$oddw" = 1 ] && { echo "== $name skipped: odd widths refused (gateodd)"; continue; }
	njob=$((njob + 1))
	# the job's work directory and the directories its options name: --depth-dump DIR writes DIR/depth.N.bin and --dump-render DIR its
	# dumps, into an existing DIR (r6-misc freeze 1 made no $JW/depth: the tool printed "--depth-dump: No such file or directory")
	JW=$WROOT/$njob-$name; mkdir -p "$JW" "$JW/depth" "$JW/dump"; W=$JW
	[ -d "$JW/depth" ] && [ -d "$JW/dump" ] || { echo "## STOP: the dump directories were not created for $name"; exit 23; }
	echo "== $name set=$sset risk=$risk tool=$tool knobs=[$knobs]"
	fk=$(free_kb); free_ok || { echo "## STOP: $fk KiB free on ~ before $name (at least $MIN_FREE_KB)"; exit 22; }
	reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; }
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	if [ "$rgn" = 1 ]; then
		rgn_set 1 || { echo "## STOP: render_rgn_arrays does not read back 1 before $name ($(rgn_now))"; exit 19; }
		mark "rgn $name 1"
	fi
	eval "set -- $args"
	echo "  cmd: $TT $*"
	mark_case "$name"
	sudo -n timeout -k 10 "$JOB_TIMEOUT" "$TT" "$@" > "$JW/$name.out" 2> "$JW/$name.err" </dev/null
	rc=$?
	snap "$name" 9 || { echo "## STOP: registers unreadable after $name"; exit 12; }
	if [ "$rgn" = 1 ]; then
		rgn_set 0 || { echo "## STOP: render_rgn_arrays does not read back 0 after $name ($(rgn_now))"; exit 19; }
		mark "rgn-back $name 0"
	fi
	echo "  rc $rc $(grep -E '^(job|target|diff|outside)' "$JW/$name.out" | head -4 | tr '\n' ' ' | cut -c1-220)"
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.err" ".err"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	for f in "$JW"/*.regs "$JW"/depth/* "$JW"/dump/*; do
		[ -f "$f" ] && keep "$name" "$f" ".${f##*/}"
	done
	# 0. every file a scorer reads must be kept (score/*.py REQUIRED): the output always; a completed row's depth or render dump (below)
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
	fint=-; fword=-
	if [ "$class" = fault ]; then fint=$(fault_int "$JW/$name.dmesg"); fword=$(fault_word "$JW/$name.dmesg"); fi
	echo "  class $class"
	mark "class $name $class"
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$tool" "$args" \
		"$rc" "$class" "${fint:-unread}" "${fword:-unread}" "$fk" >> "$KEEP/cases.tsv"
	case "$class" in
	ok)
		case " $args " in *" --depth-dump "*)
			if ! has_kept "$KEEP/$name".depth.*.bin.gz || grep -q -- "--depth-dump: " "$JW/$name.out"; then
				echo "## STOP: the depth dump of $name was not written or not kept (the scorer reads $name.depth.1.bin.gz)"; drop_work "$JW"; exit 23
			fi ;;
		esac
		if [ "$needdump" = 1 ] && ! has_kept "$KEEP/$name".*.bin.gz; then
			echo "## STOP: the render dump of $name was not written or not kept (--dump-render)"; drop_work "$JW"; exit 23
		fi
		if [ "$expectfault" = 1 ]; then
			echo "## STOP: $name completed where every rule predicts a fault (expectfault): the precedent depended on the old module (rc 19)"
			drop_work "$JW"; exit 19
		fi
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
		# the refusal prints `job: rejected (Invalid argument)` or `render: Invalid argument`, then a diff line of the unrendered
		# target and `tri: FAILED after 0 renders` (the t7 mock): rejected and no render, whatever the diff line says
		if [ "$gateodd" = 1 ] && [ "$rc" -eq 1 ] && grep -Eq 'job: rejected|render: Invalid argument' "$JW/$name.out" "$JW/$name.err" && grep -q 'FAILED after 0 renders' "$JW/$name.out" "$JW/$name.err"; then
			echo "## gateodd: $name was refused (the module or tool takes no odd width): the odd-width rows are skipped, the others run"
			ODD_REFUSED=1; health "$name" </dev/null; drop_work "$JW"; continue
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
[ "$ODD_REFUSED" = 1 ] && { echo "## gateodd: the stage ran its even-width rows; odd widths refused (rc 21)"; exit 21; }
exit 0
