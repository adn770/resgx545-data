#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# run_stage.sh STAGE FROZEN_SHA256 ATTEMPT: one job table of a kit session on the laptop
# (tools/closing/kit, HACKING.md "Session kit"), one job a line of tables/STAGE.txt in file order.
# The Mac driver (kit/session.py run) passes the sha256 of its FROZEN.sha256: the laptop's copy
# must be that file, and every file of run/staged.lst must be the frozen one. ATTEMPT names
# ~/scratch/$PREFIX/out/ATTEMPT/STAGE (new or empty). SIGPIPE and SIGHUP are ignored (a dropped
# ssh does not stop a stage half way); everything printed also goes to the kept runner.log.
#
# Table header lines: #stage NAME, #limit N (the faults and hangs of `expectfault` rows the stage
# may take; a control's expected fault is its reading and is not counted; the Nth one stops the
# stage with rc 24 when rows are left, and the log names them: "## not run (limit): A B"). Line: name|set|risk|knobs|tool|args (tool: a name of session.toml [tools]; in args
# $W is the job's work directory, every file the tool writes there is kept, and $S the staged tree;
# a tool declared `wraps = true`, as regtimeline, runs `-- "$HOME/PATH" ...` of a declared tool)
#   knobs  words, only these (any other: rc 7, nothing runs):
#     -              none
#     expectdiff     rc 1 WITH the tool's `job: ok` and a `diff:` line (its reference check) is a
#                    reading, not a failure; `job: rejected` (a kernel refusal, r8-geo's E934) or
#                    any other job line is a failure
#     expectfault    a fault or hang is a reading: kept, reset, strict health, counted against #limit
#     expect:NAME    an expected outcome (kitscore.OUTCOMES): the job's end with that rc and line in
#                    its output is a completed job (class ok), as rc 0 is; only these:
#                    expect:rc3-overflow  rc 3 with "scene overflowed the parameter buffer" (a
#                                         `probe` DPM cell's normal end)
#                    expect:rc0-overflow  rc 0 with "N overflowed" in the summary (`tri
#                                         --keep-overflow`); rc 0 without it is a failure
#     after          the health fill and triangle right after the job (strict)
#     soft           a failure (no fault, no hang) goes to void.tsv and the stage goes on; the second
#                    soft failure in a row stops it (rc 24)
#     grp:G, gate    a gate row's refusal (rc 1, no diff line) goes to void.tsv and skips group G
#     reads:K[,K]    a control's reading keys: hook_reading's `k=v` words must have them all
#                    (sessioncheck.py premise), else the stage STOPS (rc 25)
#     dbg:NAME=V     the debugfs knob NAME written V before the job, read back (rc 19), restored to
#                    its default after the job and by the exit trap (session.toml [knobs])
#     kreg:OFF=V     a register write of ours (round 29, Q024): debugfs kreg `OFF=V` after the
#                    reset and the knobs, right before the job, OFF one of the kit's KIT_KREGS
#                    (0x0a78 alone, V at most 0x3f) and V one session.toml [kregs] declares; only
#                    in a stage session.toml declares `class = "flagged"`, one a row, never with
#                    expectfault (else rc 7, nothing runs). The register must read its default
#                    before the write and V after it (rc 19, the job never runs); after the job
#                    the default is written and read back (else a reset and once more, then rc
#                    19), and the exit trap writes it again at every exit once one was written
#     pre:miscinfo   the debugfs miscinfo read (round 32, Q111): one GETMISCINFO command to the
#                    firmware with the pending cache control (no INVAL_DATA), after the reset, the
#                    knobs, the kregs and idle, right before snap0; any stage, one a row, never
#                    with noreset (else rc 7). Kept as NAME.miscinfo; not served (a read status
#                    other than 0, no "GETMISCINFO answered" or "all values match" line, or a
#                    MISMATCH) stops the stage before the job (rc 19); a FATAL kernel line after
#                    it rc 3, a fault or hang rc 4
#     noreset        no GPU reset before the job, so it starts from the state the row before left
#                    (Q163's hang sequences): only after a row that ended ok, or an expected hang
#                    the runner already reset; after any other end (a soft failure, a gate refusal,
#                    a skipped row) the row is skipped, never run; refused on the first row (rc 7)
#     idle:S         one fixed sleep of S seconds (1 to 120, one per row) right before the job,
#                    after the reset and the knobs (IDLE_WAIT, which the mock sets to 0)
#     EXTRA_KNOBS    the session's own words, for its hooks (run/hooks.sh)
# An owntask stage (round 36: one of our own firmware tasks; its `arm` line in run/owntask.tsv,
# which kit/session.py prepare writes): flagged only, every row `name|set|risk|-|owntask|{job}`
# (knobs - or reads:K only) with its `job` line in run/owntask.tsv. After the first reset and
# health the runner checks the staged blob against the map's sha256 and arms it once with the
# kit's fwtask_run.py (`arm`, kept as owntask.arm.json; not ok: rc 26); each row runs with no
# reset before it (a reset disarms the task): `run` with its one job (its JSON is NAME.txt), then
# `page`, the results page as NAME.own_res.json, whatever the end; after a row that ended ok,
# `gate` (NAME.gate.json; not ok: recovery, rc 16). At the stage's end `reset` disarms
# (owntask.reset.json; not ok: rc 13) in place of the kit's last reset. Round 41 (N3f K1, K2, K3):
# a row's job line may be a JSON list (one run of several jobs, one page and one gate after it);
# the gate runs in the arm line's order (its sixth column: fill,tri, the default, or tri,fill) and
# keeps the tools' whole outputs (NAME.gate-fill.txt, .gate-tri.txt) and the devcoredumps pending
# before and after it (NAME.devcd-pre.txt, .devcd.txt), between the marks owntask-gate-begin and
# owntask-gate.
# Hooks (run/hooks.sh, optional, staged): hook_reading NAME prints a control's `k=v` reading from
# the job's files ($JW/NAME.out, .err, .dmesg, $W); hook_check NAME prints a reason to stop the
# stage after a job that read ok (rc 24), or nothing; it runs in the runner's shell, so a count
# it keeps survives from row to row; hook_fault NAME is the same after an expected fault or hang
# row (after its reset and strict health), for a rule on the fault's own kernel lines.
# Exit status: 0 stage done; 1 preflight or a file that is not the frozen one; 3 FATAL kernel
# message; 4 an unexpected fault, hang or failure; 5 a failed health recovery; 6 a job did not
# return; 7 a forbidden knob or tool; 12 registers unreadable; 13 a reset failed; 14 a fault latched
# before a job; 16 strict health failed; 19 a knob did not read back; 22 not enough free space;
# 23 a file the scorer reads was not kept, or an output directory missing; 24 the stage stopped by
# its rule; 25 a control without its reading; 19 also a kreg that did not read back, or a
# pre:miscinfo read that was not served; 26 the own-task arm of an owntask stage failed.
# No reboot, no boot-loader change, no kernel build, no wait loop, and no register write of ours
# but a flagged stage's kreg:OFF=V to a register of KIT_KREGS; no firmware task of ours but a
# flagged owntask stage's blob.
trap '' PIPE HUP
STAGE=${1:?stage name}
FROZEN_WANT=${2:-}
ATT=${3:-}
KIT=$(cd "$(dirname "$0")" && pwd)
STAGED=$(dirname "$KIT")
FILE=$STAGED/tables/$STAGE.txt
FZ=$STAGED/FROZEN.sha256
[ -f "$FILE" ] || { echo "no $FILE"; exit 1; }
[ -f "$FZ" ] || { echo "no $FZ: stage again"; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then FROZEN_GOT=$(sha256sum "$FZ" | cut -d' ' -f1)
else FROZEN_GOT=$(shasum -a 256 "$FZ" | cut -d' ' -f1); fi
[ -n "$FROZEN_WANT" ] && [ "$FROZEN_WANT" = "$FROZEN_GOT" ] || { echo "the laptop's FROZEN.sha256 is not the Mac's (${FROZEN_GOT:-none}, Mac ${FROZEN_WANT:-not given}): stage again"; exit 1; }
[ -n "$ATT" ] || { echo "no attempt name (the driver passes it)"; exit 1; }
. "$STAGED/run/session.env"
# an owntask stage: its arm line and its rows' job lines in run/owntask.tsv (kit/session.py)
OWN_TSV=$STAGED/run/owntask.tsv
OWN_BLOB=""; OWN_SHA=""; OWN_ARM=""; OWN_JOBS=""
if [ -f "$OWN_TSV" ]; then
	OWN_BLOB=$(awk -F'\t' -v s="$STAGE" '$1 == "arm" && $2 == s { print $3; exit }' "$OWN_TSV")
	OWN_SHA=$(awk -F'\t' -v s="$STAGE" '$1 == "arm" && $2 == s { print $4; exit }' "$OWN_TSV")
	OWN_ARM=$(awk -F'\t' -v s="$STAGE" '$1 == "arm" && $2 == s { print $5; exit }' "$OWN_TSV")
	OWN_JOBS=$(awk -F'\t' -v s="$STAGE" '$1 == "job" && $2 == s { printf " %s", $3 }' "$OWN_TSV")
	OWN_GATE=$(awk -F'\t' -v s="$STAGE" '$1 == "arm" && $2 == s { print $6; exit }' "$OWN_TSV")
fi
OWN_GATE=${OWN_GATE:-fill,tri}
if [ -n "$OWN_BLOB$OWN_SHA$OWN_ARM" ]; then
	case " ${FLAGGED_STAGES:-} " in
	*" $STAGE "*) ;;
	*) echo "stage $STAGE: an owntask stage that is not flagged (a planned firmware break if wrong)"; exit 7 ;;
	esac
	printf '%s\n' "$OWN_BLOB" | grep -Eqx '[a-z0-9_]+' \
		&& printf '%s\n' "$OWN_SHA" | grep -Eqx '[0-9a-f]{64}' \
		&& printf '%s\n' "$OWN_ARM" | grep -Eqx 'slots=0x[0-9a-f]{1,2} entry=[0-9]{1,2}(,[0-9]{1,2})*( trc=[0-9]{1,2})?( pds=(crumb|halt|crumb3|land|mark|landv))?( pdsat=fw14)?( pds2=req)?( form=(sb001|sb002|sb003|sb040|sb041|sb042|sb043|sb800|sb801|sb802|sb803|sb840|sb841|sb842|fw14|sbc43|sb403|sb402|sb400))?' \
		|| { echo "stage $STAGE: owntask blob '$OWN_BLOB', sha256 '$OWN_SHA' or arm line '$OWN_ARM' is not one the kit arms"; exit 7; }
	case "$OWN_GATE" in
	fill,tri|tri,fill) ;;
	*) echo "stage $STAGE: owntask gate order '$OWN_GATE' is not fill,tri or tri,fill"; exit 7 ;;
	esac
fi
# the registers kreg:OFF=V may write, frozen with kit/session.py's KREG_ALLOWED: OFF=DEFAULT/MAX
# (CR_PDS_REG_0A78: E045 drew 0x00-0x3f exactly; 0x2c the firmware's value, E141)
KIT_KREGS="0x0a78=0x2c/0x3f"
# the table's knobs and tools, before anything is touched
ALLOWED="$EXTRA_KNOBS"
for k in $KNOBS; do v="KNOB_${k}_VALUES"; for x in ${!v}; do ALLOWED="$ALLOWED dbg:$k=$x"; done; done
# kreg words: only in a flagged stage, a register of KIT_KREGS, a declared value up to its MAX
case " ${FLAGGED_STAGES:-} " in
*" $STAGE "*)
	for r in ${KREGS:-}; do
		for e in $KIT_KREGS; do
			[ "${e%%=*}" = "$r" ] || continue
			v="KREG_${r}_VALUES"
			for x in ${!v}; do
				case "$x" in 0x*) ;; *) continue ;; esac
				[ $(( x )) -le $(( ${e##*/} )) ] && ALLOWED="$ALLOWED kreg:$r=$x"
			done
		done
	done ;;
esac
awk -F'|' -v allowed=" $ALLOWED " -v tools=" $TOOLS " -v own="$OWN_BLOB" -v jobs="$OWN_JOBS " '
	!/^#/ && NF >= 6 && $5 == "owntask" {
		row++
		if (own == "") { print $1 ": tool owntask, and this is not an owntask stage"; bad = 1; next }
		n = split($4, k, " ")
		for (i = 1; i <= n; i++) if (k[i] != "-" && k[i] !~ /^reads:[a-z0-9_]+(,[a-z0-9_]+)*$/) { print $1 ": knob " k[i] " (an owntask row takes only - and reads:K)"; bad = 1 }
		if (!index(jobs, " " $1 " ")) { print $1 ": no job line in run/owntask.tsv"; bad = 1 }
		if ($2 == "control" && $4 !~ /(^| )reads:/) { print $1 ": a control row without reads:"; bad = 1 }
		next
	}
	!/^#/ && NF >= 6 && own != "" { print $1 ": tool " $5 " (an owntask stage runs owntask rows only)"; bad = 1; next }
	!/^#/ && NF >= 6 {
		n = split($4, k, " "); row++; idles = 0; kregs = 0; xf = 0; mis = 0; nr = 0
		for (i = 1; i <= n; i++) { if (k[i] == "expectfault") xf = 1; if (k[i] == "noreset") nr = 1 }
		for (i = 1; i <= n; i++) {
			w = k[i]
			if (w == "pre:miscinfo") {
				if (++mis > 1) { print $1 ": more than one pre:miscinfo word"; bad = 1 }
				if (nr) { print $1 ": pre:miscinfo with noreset (the read follows the row'"'"'s reset)"; bad = 1 }
				continue
			}
			if (w ~ /^kreg:/) {
				if (++kregs > 1) { print $1 ": more than one kreg word"; bad = 1 }
				if (xf) { print $1 ": kreg with expectfault (a fault with our register written is a stop)"; bad = 1 }
				if (!index(allowed, " " w " ")) { print $1 ": knob " w " (kreg: a flagged stage, a register of the kit and a declared value only)"; bad = 1 }
				continue
			}
			if (w ~ /^(-|expectdiff|expectfault|after|soft|gate|noreset|grp:[a-z0-9]+|expect:(rc3-overflow|rc0-overflow)|reads:[a-z0-9_]+(,[a-z0-9_]+)*)$/) {
				if (w == "noreset" && row == 1) { print $1 ": knob noreset on the stage'"'"'s first row (nothing before it to keep)"; bad = 1 }
				continue
			}
			if (w ~ /^idle:[1-9][0-9]*$/ && substr(w, 6) + 0 <= 120) {
				if (++idles > 1) { print $1 ": more than one idle: word"; bad = 1 }
				continue
			}
			if (w ~ /^idle:/) { print $1 ": knob " w " (idle:S takes 1 to 120 seconds)"; bad = 1; continue }
			if (index(allowed, " " w " ")) continue
			print $1 ": knob " w; bad = 1
		}
		if (!index(tools, " " $5 " ")) { print $1 ": tool " $5; bad = 1 }
		if ($2 == "control" && $4 !~ /(^| )reads:/) { print $1 ": a control row without reads:"; bad = 1 }
		if ($4 ~ /(^| )gate( |$)/ && $4 !~ /grp:/) { print $1 ": a gate row without its group"; bad = 1 }
	}
	!/^#/ && NF > 0 && NF < 6 { print "a row that is not name|set|risk|knobs|tool|args: " $0; bad = 1 }
	END { exit bad }' "$FILE" || { echo "table $STAGE: a knob, tool or row that the session does not allow"; exit 7; }
FAULT_LIMIT=$(awk '$1 == "#limit" { print $2; exit }' "$FILE"); FAULT_LIMIT=${FAULT_LIMIT:-0}
. "$KIT/lib_kit.sh"
expect_sha() { awk -v p="$1" '$2 == p { print $1; exit }' "$FZ"; }
for f in tables/$STAGE.txt $(cat "$STAGED/run/staged.lst"); do
	want=$(expect_sha "$f"); got=$(sha "$STAGED/$f" | cut -d' ' -f1)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "$f is not the frozen one ($got, frozen ${want:-none})"; exit 1; }
done
hook_reading() { return 0; }
hook_check() { return 0; }
hook_fault() { return 0; }
[ -f "$STAGED/run/hooks.sh" ] && . "$STAGED/run/hooks.sh"
S=$STAGED

# ---- the rows ---------------------------------------------------------------------------------
begin
if [ -n "$OWN_BLOB" ]; then
	# the own task, armed once for the stage: the staged blob must be the map's
	JW=$WROOT/arm; mkdir -p "$JW"
	got=$(sha "$STAGED/owntask/$OWN_BLOB.blob" | cut -d' ' -f1)
	[ "$got" = "$OWN_SHA" ] || { echo "## STOP: owntask/$OWN_BLOB.blob is not the map's ($got, map $OWN_SHA)"; exit 1; }
	echo "== owntask arm $OWN_BLOB [$OWN_ARM]"
	mark "owntask-arm $STAGE $OWN_BLOB $OWN_ARM"
	owntask_call arm "{\"blob\": \"$STAGED/owntask/$OWN_BLOB.blob\", \"arm\": \"$OWN_ARM\"}" "$JW/arm.json" "$JW/arm.err" 120
	r=$?
	keep owntask "$JW/arm.json" ".arm.json"
	keep owntask "$JW/arm.err" ".arm.err"
	if [ "$r" -ne 0 ] || ! json_ok "$JW/arm.json"; then
		echo "## STOP: the own-task arm of $OWN_BLOB failed (status $r, $(head -c 300 "$JW/arm.json" "$JW/arm.err" | tr '\n' ' '))"
		reset_gpu; health owntask-arm </dev/null; exit 26
	fi
	rm_work "$JW"
fi
njob=0; SKIP_GRPS=""; FAULT_EVENTS=0; SOFT_RUN=0
# how the row before ended (its class, or skipped), and its name: what a noreset row builds on
PREV_END=""; PREV_NAME=begin
grep -v '^#' "$FILE" | grep -v '^$' > "$WROOT/rows"
TOTAL=$(grep -c . "$WROOT/rows")
for i in $(seq 1 "$TOTAL"); do
	line=$(sed -n "${i}p" "$WROOT/rows")
	IFS='|' read -r name sset risk knobs tool args <<EOF
$line
EOF
	[ -z "$name" ] && continue
	grp=""; gate=0; soft=0; after=0; expectdiff=0; expectfault=0; reads=""; dbgs=""; kregs=""; expect=""; noreset=0; idle=0; premisc=0
	for k in $knobs; do
		case "$k" in
		grp:*) grp=${k#grp:} ;;
		gate) gate=1 ;;
		soft) soft=1 ;;
		after) after=1 ;;
		expectdiff) expectdiff=1 ;;
		expectfault) expectfault=1 ;;
		expect:*) expect="$expect ${k#expect:}" ;;
		reads:*) reads=$(printf '%s' "${k#reads:}" | tr ',' ' ') ;;
		dbg:*) dbgs="$dbgs ${k#dbg:}" ;;
		kreg:*) kregs="$kregs ${k#kreg:}" ;;
		noreset) noreset=1 ;;
		idle:*) idle=${k#idle:} ;;
		pre:miscinfo) premisc=1 ;;
		*) ;;
		esac
	done
	case " $SKIP_GRPS " in *" $grp "*) [ -n "$grp" ] && { echo "== $name skipped: group $grp was refused at its gate"; PREV_END=skipped; PREV_NAME=$name; continue; } ;; esac
	# noreset builds on the row before: only an ok end, or an expected hang already reset
	if [ "$noreset" = 1 ]; then
		case "$PREV_END" in
		ok|hang) ;;
		*) echo "== $name skipped: noreset after $PREV_NAME, which ended ${PREV_END:-nothing}"
			PREV_END=skipped; PREV_NAME=$name; continue ;;
		esac
	fi
	njob=$((njob + 1))
	JW=$WROOT/$njob-$name; W=$JW/w; mkdir -p "$W"
	TT=""   # an owntask row runs the kit's fwtask_run.py, no tool of [tools]
	[ -n "$OWN_BLOB" ] || TT=$(tool_path "$tool")
	echo "== $name set=$sset risk=$risk tool=$tool knobs=[$knobs]"
	fk=$(free_kb); space_ok || { echo "## STOP: $fk KiB free on ~ before $name (at least $MIN_FREE_MB MiB)"; exit 22; }
	if [ -n "$OWN_BLOB" ]; then
		echo "  owntask: no reset before $name (a reset disarms the task armed for the stage)"
		mark "owntask-noreset $name"
	elif [ "$noreset" = 1 ]; then
		echo "  noreset: no reset before $name (the row before, $PREV_NAME, ended $PREV_END)"
		mark "noreset $name $PREV_END"
	else
		reset_gpu || { echo "## STOP: the reset before $name failed"; exit 13; }
	fi
	for kv in $dbgs; do
		knob_set "${kv%%=*}" "${kv#*=}" || { echo "## STOP: knob ${kv%%=*} does not read back ${kv#*=} before $name"; exit 19; }
		mark "knob $name $kv"
	done
	for kv in $kregs; do
		kreg_set "${kv%%=*}" "${kv#*=}" || { echo "## STOP: kreg ${kv%%=*} does not read back ${kv#*=} before $name"; exit 19; }
		mark "kreg $name $kv"
	done
	if [ "$idle" -gt 0 ]; then
		echo "  idle $idle s before $name"
		mark "idle $name $idle"
		sleep "${IDLE_WAIT:-$idle}"
	fi
	if [ "$premisc" = 1 ]; then
		miscinfo_read "$name"; mr=$?
		case "$mr" in
		0) ;;
		3) echo "## STOP: kernel watchdog/lockup/BUG after the miscinfo read before $name"; FATAL_STOP=1; exit 3 ;;
		4) echo "## STOP: a fault or hang after the miscinfo read before $name"; reset_gpu; strict_health "$name" </dev/null; exit 4 ;;
		*) echo "## STOP: the miscinfo read before $name was not served (status $MISCINFO_STATUS, $MISCINFO_WHY)"; exit 19 ;;
		esac
	fi
	snap "$name" 0 || { echo "## STOP: registers unreadable before $name"; exit 12; }
	f0=$(fault_req "$JW/snap0.regs")
	[ "$f0" = 0 ] || { echo "## STOP: a fault is latched before $name (bits 15:0 = $f0)"; exit 14; }
	if [ -n "$OWN_BLOB" ]; then
		job=$(awk -F'\t' -v s="$STAGE" -v n="$name" '$1 == "job" && $2 == s && $3 == n { print $4; exit }' "$OWN_TSV")
		echo "  owntask run: $job"
		# a job-list row (round 41) is a JSON list already, a one-job row an object
		case "$job" in
		\[*) jobs=$job ;;
		*) jobs="[$job]" ;;
		esac
		mark_case "$name"
		owntask_call run "{\"name\": \"$name\", \"outdir\": \"$W\", \"jobs\": $jobs}" "$JW/$name.out" "$JW/$name.err" "$JOB_TIMEOUT"
		rc=$?
	else
		eval "set -- $args"
		miss=$(outdirs "$@")
		[ -z "$miss" ] || { echo "## STOP: $miss (an output directory the tool writes into, before $name)"; exit 23; }
		echo "  cmd: $TT $*"
		mark_case "$name"
		sudo -n timeout -k 10 "$JOB_TIMEOUT" "$TT" "$@" > "$JW/$name.out" 2> "$JW/$name.err" </dev/null
		rc=$?
	fi
	snap "$name" 9 || { echo "## STOP: registers unreadable after $name"; exit 12; }
	# an owntask row's results page, whatever its end (but a job that did not return)
	if [ -n "$OWN_BLOB" ] && [ "$rc" -ne 124 ]; then
		owntask_call page '{}' "$W/own_res.json" "$JW/page.err" 60 || echo "  owntask: the page dump after $name failed ($(head -c 200 "$JW/page.err"))"
	fi
	echo "  rc $rc $(grep -E '^(job|target|diff|outside)' "$JW/$name.out" | head -n 3 | tr '\n' ' ' | cut -c1-200)"
	# a file or command the tool could not find is said in the log, where the driver stops on it
	grep -Eh 'No such file or directory|command not found|: not found' "$JW/$name.out" "$JW/$name.err" | head -n 3 | sed 's/^/  tool: /'
	slice_since "resgx545 case $name $RUN" > "$JW/$name.dmesg"
	keep "$name" "$JW/$name.out"
	keep "$name" "$JW/$name.err" ".err"
	keep "$name" "$JW/$name.dmesg" ".dmesg"
	keep "$name" "$JW/snap0.regs" ".snap0.regs"
	keep "$name" "$JW/snap9.regs" ".snap9.regs"
	for f in $(find "$W" -type f | sort); do keep "$name" "$f" ".${f##*/}"; done
	# 1. the kernel itself in trouble: stop at once, touch nothing more
	if [ "$rc" -eq 124 ]; then echo "## STOP: $name did not return (freeze)"; FATAL_STOP=1; exit 6; fi
	if bad_lines "$JW/$name.dmesg" "$JW/$name.out" "$JW/$name.err" | grep -Eq "$FATAL_RE"; then
		echo "## STOP: kernel watchdog/lockup/BUG after $name"; FATAL_STOP=1; exit 3
	fi
	# 2. classify the job
	class=$(classify "$rc" "$JW/$name.out" "$JW/$name.err" "$JW/$name.dmesg")
	if [ "$class" = fail ] && [ "$expectdiff" = 1 ] && [ "$rc" -eq 1 ] && grep -q '^diff:' "$JW/$name.out"; then
		if grep -q '^job: ok' "$JW/$name.out"; then class=ok
		else echo "  expectdiff: a diff line without \`job: ok\` ($(grep -m 1 '^job:' "$JW/$name.out" || echo 'no job line')): not a reading"; fi
	fi
	if [ "$class" = ok ] && unmet_end "$rc" "$JW/$name.out" $expect; then
		class=fail; echo "  expect:$expect declared but the job ended rc 0 without it: a failure"
	fi
	if [ "$class" = fail ] && expected_end "$rc" "$JW/$name.out" $expect; then class=ok; echo "  expected end:$expect (rc $rc)"; fi
	fint=-; fword=-
	if [ "$class" = fault ]; then fint=$(fault_req "$JW/snap9.regs"); fword=$(regval "$JW/snap9.regs" 0x0c08); fi
	echo "  class $class"
	PREV_END=$class; PREV_NAME=$name
	mark "class $name $class"
	tsv=cases.tsv
	if [ "$class" = fail ] && { [ "$soft" = 1 ] || { [ "$gate" = 1 ] && [ "$rc" -eq 1 ] && ! grep -q '^diff:' "$JW/$name.out"; }; }; then tsv=void.tsv; fi
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$STAGE" "$sset" "$risk" "$knobs" "$tool" "$args" \
		"$rc" "$class" "${fint:-unread}" "${fword:-unread}" "$fk" >> "$KEEP/$tsv"
	if [ -n "$KNOBS_SET$dbgs" ]; then knobs_restore || { echo "## STOP: a knob did not go back to its default after $name"; exit 19; }; fi
	if [ -n "$kregs" ]; then
		if ! kregs_restore; then
			echo "  kreg: not back at its default after $name: a reset, then once more"
			reset_gpu; kregs_restore || { echo "## STOP: a kreg did not go back to its default after $name"; exit 19; }
		fi
		mark "kreg-restored $name"
	fi
	# an owntask row that ended ok: the health gate (fill and triangle) with the task armed
	if [ -n "$OWN_BLOB" ] && [ "$class" = ok ]; then
		# in the stage's order, the tools' whole outputs and the devcoredumps before and after it
		# in $JW/gate (round 41), kept whatever the gate's end
		mkdir -p "$JW/gate"
		mark "owntask-gate-begin $name $OWN_GATE"
		owntask_call gate "{\"order\": \"$OWN_GATE\", \"outdir\": \"$JW/gate\"}" "$JW/gate.json" "$JW/gate.err" 120
		r=$?
		keep "$name" "$JW/gate.json" ".gate.json"
		for f in $(find "$JW/gate" -type f | sort); do keep "$name" "$f" ".${f##*/}"; done
		mark "owntask-gate $name"
		if [ "$r" -ne 0 ] || ! json_ok "$JW/gate.json"; then
			echo "## STOP: the gate after $name failed (status $r, $(head -c 300 "$JW/gate.json" | tr '\n' ' ')): recovery, then stop"
			reset_gpu; health "$name" </dev/null; exit 16
		fi
	fi
	case "$class" in
	ok)
		SOFT_RUN=0
		miss=$(required_missing "$name" | tr '\n' ' ')
		[ -z "$miss" ] || { echo "## STOP: the scorer reads $miss, which $name did not write or the runner did not keep"; exit 23; }
		# in this shell, not a subshell: a hook's count survives from row to row
		hook_check "$name" > "$JW/check.txt"
		why=$(cat "$JW/check.txt")
		[ -z "$why" ] || { echo "## STOP (stage $STAGE): $why, after $name"; health "$name" </dev/null; exit 24; } ;;
	fault|hang)
		mark "$class $name ${fint:-unread} ${fword:-unread}"
		if [ "$expectfault" != 1 ]; then
			echo "## STOP: unexpected $class in $name"; reset_gpu; strict_health "$name" </dev/null; exit 4
		fi
		# a control's expected fault is its reading, not one of the stage's (r8-k2's isolation)
		if [ "$sset" = control ]; then echo "  $class (the control's reading, not counted against #limit)"
		else FAULT_EVENTS=$((FAULT_EVENTS + 1)); fi
		echo "  $class (a reading): events $FAULT_EVENTS of $FAULT_LIMIT; reset, then strict health"
		reset_gpu; strict_health "$name" </dev/null
		# the files of its class the scorer reads (REQUIRED's "fault:", "hang:" and "any:" ones)
		miss=$(required_missing "$name" "$class" | tr '\n' ' ')
		[ -z "$miss" ] || { echo "## STOP: the scorer reads $miss, which $name ($class) did not write or the runner did not keep"; exit 23; }
		hook_fault "$name" > "$JW/check.txt"
		why=$(cat "$JW/check.txt")
		[ -z "$why" ] || { echo "## STOP (stage $STAGE): $why, after $name"; exit 24; }
		if [ "$FAULT_EVENTS" -ge "$FAULT_LIMIT" ] && [ "$i" -lt "$TOTAL" ]; then
			left=$(sed -n "$((i + 1)),\$p" "$WROOT/rows" | cut -d'|' -f1 | tr '\n' ' ')
			mark "notrun-limit $left"
			echo "## STOP (stage $STAGE): $FAULT_EVENTS faults or hangs (the limit is $FAULT_LIMIT) with rows left, after $name"
			echo "## not run (limit): $left"; exit 24
		fi ;;
	fail)
		if [ "$gate" = 1 ] && [ "$rc" -eq 1 ] && ! grep -q '^diff:' "$JW/$name.out"; then
			SKIP_GRPS="$SKIP_GRPS $grp"
			echo "## gate: $name was refused (rc 1, no diff line): group $grp is skipped (cannot tell)"
			health "$name" </dev/null; rm_work "$JW"; continue
		fi
		if [ "$soft" = 1 ]; then
			SOFT_RUN=$((SOFT_RUN + 1))
			echo "  soft failure ($SOFT_RUN in a row): recorded, the stage goes on"
			reset_gpu; health "$name" </dev/null
			[ "$SOFT_RUN" -ge 2 ] && { echo "## STOP (stage $STAGE): the second soft failure in a row ($name)"; exit 24; }
			rm_work "$JW"; continue
		fi
		echo "## STOP: unexplained failure in $name (rc $rc)"; reset_gpu; health "$name" </dev/null; exit 4 ;;
	esac
	# 3. a control's premise: every reading it declares was read (sessioncheck.py premise)
	if [ "$sset" = control ]; then
		reading=$(hook_reading "$name" | tr '\n' ' ')
		printf '%s\t%s\t%s\n' "$name" "$reads" "$reading" >> "$KEEP/readings.tsv"
		printf '%s\n' "$reading" > "$JW/premise.txt"
		echo "  premise $name [$reads]: $reading"
		python3 "$KIT/sessioncheck.py" premise "$name" "$reads" "$JW/premise.txt" \
			|| { echo "## STOP: premise: control $name lacks a reading it declares ($reads)"; exit 25; }
	fi
	if [ "$after" = 1 ]; then strict_health "$name" </dev/null; fi
	rm_work "$JW"
done
if [ -n "$OWN_BLOB" ]; then
	# the disarm: fwtask_run.py's reset (own_arm off, ticks, health), the stage's last reset
	JW=$WROOT/disarm; mkdir -p "$JW"
	mark "owntask-disarm $STAGE $OWN_BLOB"
	owntask_call reset '{}' "$JW/reset.json" "$JW/reset.err" 120
	r=$?
	keep owntask "$JW/reset.json" ".reset.json"
	if [ "$r" -ne 0 ] || ! json_ok "$JW/reset.json"; then
		echo "## STOP: the own-task reset at the end of $STAGE did not disarm (status $r)"; exit 13
	fi
	rm_work "$JW"
fi
miss=$(required_missing | tr '\n' ' ')
[ -z "$miss" ] || { echo "## STOP: the scorer reads $miss, which the stage did not keep"; exit 23; }
JW=$WROOT/end; mkdir -p "$JW"
if [ -z "$OWN_BLOB" ]; then
	reset_gpu || { echo "## STOP: the reset after the last job failed"; exit 13; }
fi
health end </dev/null
rm_work "$JW"
echo "## end: $njob jobs of $STAGE"
