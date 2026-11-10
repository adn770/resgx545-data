#!/bin/bash
# tests/run_mock.sh: the R2 runner end to end against a fake tool, a fake regtimeline and a fake debugfs whose directory is
# mode 000 (only the sudo shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard,
# staging and the whole driver (r2.sh) with fake ssh/scp/health.  Needs a current freeze (run/freeze_r2.sh freeze).
# The fake kernel plays the watchdog: hold_recovery written N while a render fault is latched makes it recover on its own.
# Nothing is deleted: every run writes into a new mktemp directory, printed at the end.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
W=$(mktemp -d)
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_r2.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_r2.sh freeze)"; exit 1; }
N=0
# a fresh fake laptop: debugfs (mode 000) + its real files, the fake GPU state, the kernel log
world() {
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/stage" "$M/out" "$M/log" "$M/home"
	for f in reset regs render_param render_tadata; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${NOBINS:-}" ] || cp "$P"/bins/*.bin "$M/stage/"
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh"
export R2_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") R2_RT_SHA=$(sha "$P/tests/fake_rt.sh") PY
# HOLD_READ must outlast the fake job's start, as on the laptop the 2.8 s outlast the fault
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=0.5 HOLD_GAP=0.1 RT_LEAD=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log R2_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
# runst DIR STAGE ENV...: run one stage in the current world with the driver's arguments (the sha256 of DIR's
# FROZEN.sha256, the attempt); echoes the status.  FSHA overrides the sha256 ("none": no argument).
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }

# 1. every stage, the frozen tables, default (frozen-hypothesis) outcomes: every job runs and is kept
world
for st in $(cat "$P/stages.txt" "$P/conditional.txt"); do
	rc=$(runst "$P" "$st")
	t=$P/tables/$st.txt; n=$(grep -vc '^#' "$t"); k=$(KD "$st")
	got=$(grep -c '^== ' "$M/log/$st.log"); nc=$(( $(wc -l < "$k/cases.tsv") - 1 ))
	nheld=$(grep -v '^#' "$t" | grep -cE '\|held[ |]')
	nsnap=$(ls "$k" | grep -c 'snap[0-3]\.regs\.gz')
	# a dump is kept for every completed job that asks for one (a faulted job's context is gone): the set -f regression
	nd=$(awk -F'\t' 'NR > 1 && $9 == "ok" && $7 ~ /--dump-render/' "$k/cases.tsv" | grep -c .); kd=$(ls "$k" | grep -c 'tadata\.bin\.gz')
	h=$(cat "$M/fake/hold")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$nc" = "$n" ] && [ "$h" = N ] && [ "$kd" = "$nd" ] \
		&& [ "$nsnap" -ge $((nheld * 4 + n - nheld)) ] && grep -q '^## end' "$k/runner.log" \
		&& ok "$st: $got of $n jobs, $nc rows, $nsnap snapshots, $kd of $nd TA dumps kept, runner.log kept, hold N at the end" \
		|| bad "$st: rc $rc, $got of $n jobs, rows $nc, snapshots $nsnap, dumps $kd of $nd, hold $h"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg"); holds=$(grep -c 'readback .* hold_recovery=Y' "$M/kmsg")
[ "$cases" = 16 ] && [ "$holds" = 4 ] && ok "kernel log: $cases case markers, $holds hold read-backs" || bad "markers: $cases cases, $holds holds"
grep -q 'resgx545 r2 health d-L2e2-17 try [0-9]' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
awk -F'\t' 'NR > 1 && ($8 == "" || $9 == "") { x++ } END { exit x > 0 }' "$M"/out/"$ATT"/*/cases.tsv && ok "rc and class on every row" || bad "rc/class"
awk -F'\t' '$1 == "d-L2e2-18" && $8 == 3 && $9 == "ok"' "$(KD r2-d-safe)/cases.tsv" | grep -q . && ok "d-L2e2-18: rc 3 'no pixel written' is class ok (expectnopix), the stage went on" || bad "expectnopix"
awk -F'\t' '$1 == "d-L2e2-17" && $9 == "fault"' "$(KD r2-d-fault)/cases.tsv" | grep -q . && ok "d-L2e2-17 faulted as HL says, d-L2e2-16 ran after it" || bad "d-17 class"
grep -q 'BIF fault 0x90002 at 0x3e017001' "$M/kmsg" && ok "the fake fault word and address are the frozen ones" || bad "fault line"
r1=$(grep -n 'resgx545 r2 reset a5-320x400-max544 ' "$M/kmsg" | cut -d: -f1); n1=$(grep -n 'readback a5-320x400-max544 hold_recovery=N' "$M/kmsg" | cut -d: -f1)
[ -z "$r1" ] && r1=$(grep -n 'resgx545 r2 reset a6-320x400-max320 ' "$M/kmsg" | cut -d: -f1) && n1=$(grep -n 'readback a6-320x400-max320 hold_recovery=N' "$M/kmsg" | cut -d: -f1)
[ -n "$r1" ] && [ -n "$n1" ] && [ "$r1" -lt "$n1" ] && ok "held job: reset written with the hold Y, then N read back" || bad "reset/N order: reset line $r1, N line $n1"
grep -q 'stalls job' "$M/kmsg" && grep -n 'stalls job' "$M/kmsg" | grep -vq 'BIF fault 0x90002' && bad "the fake watchdog recovered a held fault (N written before the reset)" || ok "no watchdog recovery of a held fault"
MAIN=$M; MATT=$ATT
# the scorers on the mock output (the fakes play the frozen HL / H4 outcomes): the whole chain gives verdicts
for st in $(cat "$P/stages.txt" "$P/conditional.txt"); do
	s=$("$PY" "$P/score/score_r2.py" "$st" "$MAIN/out/$MATT/$st" | grep '^SUMMARY:')
	case "$st:$s" in
	r2-d-safe:*"d-L2e2-18x': 'HL'"*|r2-d-fault:*"d-L2e2-17': 'HL'"*|r2-a-safe:*"H4 for what the TA writes"*|r2-a-fault:*"a5 COMPLETES"*|r2-a-slack:*"sa5 COMPLETES"*) ok "scorer $st: ${s:0:120}" ;;
	*) bad "scorer $st: ${s:-no SUMMARY}" ;;
	esac
done
"$PY" "$P/score/score_r2.py" gate r2-a-fault "$MAIN/out/$MATT" > /dev/null && ok "gate r2-a-fault open on a passing a4 control" || bad "gate"
"$PY" "$P/score/score_r2.py" gate r2-a-slack "$MAIN/out/$MATT" > /dev/null; [ $? = 3 ] && ok "gate r2-a-slack: not needed when a5 completed (exit 3)" || bad "slack gate on H4"
v=$("$PY" "$P/score/score_r2.py" verdict "$MAIN/out/$MATT")
case "$v" in *"Q281: HL: all 2 held-out rows agree"*"Q286: closed H4"*) ok "verdict: Q281 HL, Q286 H4" ;; *) bad "verdict: $v" ;; esac

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 r2-a-safe; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && ok "  another session's hold left as it was: no knob write, no reset" || bad "  the failed preflight touched the GPU"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" r2-a-safe)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/r2-a-safe.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion of the loaded module differs from the installed one: rc 1, nothing touched" || bad "srcversion check: rc $rc"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" r2-a-safe)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/r2-a-safe.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; rc=$(R2_TOOL_SHA=0000 runst "$P" r2-a-safe)
[ "$rc" = 1 ] && grep -q "the tool is not R1's" "$M/log/r2-a-safe.log" && ok "preflight: a tool that is not R1's build (rc 1)" || bad "tool sha: rc $rc"
check "fatal kernel message" 3 r2-d-safe FAKE_RULES='--scratch-pages 19|fatal'
check "plain job does not return (freeze)" 6 r2-a-safe FAKE_RULES='--width 256|timeout'
check "held job does not return (freeze)" 6 r2-a-fault FAKE_RULES='--max-width 544|timeout'
check "unexpected fault in a completing job" 4 r2-a-safe FAKE_RULES='--width 320 --height 128|fault:0x90004:0x20006062:0x480'
check "unexplained failure (rc 1, no diff line)" 4 r2-a-safe FAKE_RULES='--width 320 --height 128|nodiff'
check "d-ok-64 failing (not a result) stops the stage" 4 r2-d-safe FAKE_RULES='--scratch-pages 64|nodiff'
check "a wrong image in a4 (expectdiff) is recorded, scored FAIL" 0 r2-a-safe FAKE_RULES='--max-width 544 --max-height 400|diff'
s=$("$PY" "$P/score/score_r2.py" r2-a-safe "$(KD r2-a-safe)" | grep '^SUMMARY:')
case "$s" in *"a4 control failed"*) ok "  scored: the a4 control failed (a wrong diff is not E727's 28)" ;; *) bad "  a4 score: $s" ;; esac
"$PY" "$P/score/score_r2.py" gate r2-a-fault "$M/out/$ATT" > "$W/gate.txt"; [ $? = 1 ] && grep -q 'rerun: run/r2.sh --only r2-a-safe' "$W/gate.txt" && ok "  the closed gate names the stage to rerun" || bad "gate message: $(cat "$W/gate.txt")"
check "a wrong image in a5 (expectdiff) is recorded" 0 r2-a-fault FAKE_RULES='--max-width 544|diff'
grep -q 'a5-320x400-max544.*	ok	held' "$(KD r2-a-fault)/cases.tsv" && ok "  a5 recorded as ok (diff kept for the scorer)" || bad "  a5 diff row"
check "a6 completing with a wrong image is recorded, then scored" 0 r2-a-fault FAKE_RULES='--max-width 320 --max-height 400|diff'
s=$("$PY" "$P/score/score_r2.py" r2-a-fault "$(KD r2-a-fault)" | grep '^SUMMARY:')
case "$s" in *"a6 control failed"*) ok "  scored: the a6 control failed (completed)" ;; *) bad "  a6 score: $s" ;; esac
check "a hang is an unexpected stop even in a hypothesis row" 4 r2-d-fault FAKE_RULES='--scratch-pages 17|hang'
check "a held hang is an unexpected stop" 4 r2-a-fault FAKE_RULES='--max-width 544|hang'
check "the 5th fault-class event stops the session (R2_FAULTS_PRIOR=4): d-L2e2-17 is the 5th" 15 r2-d-fault R2_FAULTS_PRIOR=4
grep -q 'd-L2e2-16' "$(KD r2-d-fault)/cases.tsv" && bad "  d-L2e2-16 ran after the limit" || ok "  nothing ran after the 5th event (d-L2e2-16 not run); the health ran first"
grep -q 'health d-L2e2-17 try' "$M/kmsg" && ok "  the 5th fault was followed by its health triangle" || bad "  no health after the 5th fault"
check "below the limit (R2_FAULTS_PRIOR=2) both D2 faults run" 0 r2-d-fault R2_FAULTS_PRIOR=2
check "d-L2e2-17 completing (HS) is recorded, not a stop" 0 r2-d-fault FAKE_RULES='--scratch-pages 17|okforce'
check "a held fault that does not clear: two resets, then stop" 10 r2-a-fault FAKE_STUCK=1
r=$(grep -c . "$M/fake/resets"); [ "$r" = 6 ] && ok "  resets: the start's, a pre-job and a held one for a5 (held jobs always reset), a pre-job one for a6, its held one and its one more; none at exit" || bad "  resets: $r"
check "hold_recovery does not read back N" 11 r2-a-fault FAKE_HOLD_STUCK=1
check "hold_recovery does not read back Y (job not started)" 9 r2-a-fault FAKE_HOLD_NOY=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started without its hold" || ok "  no job started"
check "registers unreadable" 12 r2-a-fault FAKE_SNAP_FAIL=1
check "health: the first failed recovery stops" 5 r2-a-safe FAKE_HEALTH_BAD=1
check "the pre-job reset fails" 13 r2-a-safe FAKE_RESET_FAIL_FROM=2
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job (snap 0)" 14 r2-a-fault FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
NOBINS=1 world
rc=$(runst "$P" r2-d-safe); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" r2-a-safe)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/r2-a-safe.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world; rc=$(FSHA=none runst "$P" r2-a-safe); [ "$rc" = 1 ] && ok "no frozen sha256 argument: rc 1" || bad "no sha argument: rc $rc"
# SIGPIPE / SIGHUP ignored, the output also in runner.log: a dropped ssh does not stop the stage
world
env $(envw) bash "$P/run/run_stage.sh" r2-d-safe "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD r2-d-safe)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 5 ] && grep -q '^## end' "$(KD r2-d-safe)/runner.log" && [ "$(cat "$M/fake/hold")" = N ] \
	&& ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc, rows $nc"
# one directory an attempt, never merged
world; rc=$(runst "$P" r2-d-safe); rc2=$(runst "$P" r2-d-safe)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/r2-d-safe.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"
ATT=att-second; rc3=$(runst "$P" r2-d-safe)
[ "$rc3" = 0 ] && [ -f "$M/out/att-second/r2-d-safe/cases.tsv" ] && ok "a new attempt gets its own directory" || bad "new attempt: rc $rc3"

# 3. a copy of the tree: a changed table, an unknown knob, a group bound, a tri row without expectdiff, a bare debugfs access
copytree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/stages.txt" "$P/conditional.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$C/"; }
world; copytree
echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/r2-a-safe.txt"
rc=$(runst "$C" r2-a-safe)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/r2-a-safe.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
world; copytree
printf '#stage r2-mock\nm-1|heldout|risky|hypo:g:1|-|probe --temps 32 --coords --pixels --scratch-pages 17 "$S/s1d-tw64x64-l2e2__0.bin"\nm-2|heldout|risky|hypo:g:1|-|probe --temps 32 --coords --pixels --scratch-pages 16 "$S/s1d-tw64x64-l2e2__0.bin"\nm-3|heldout|risky|kregx|-|tri\n' > "$C/tables/r2-mock.txt"
(cd "$C" && run/freeze_r2.sh freeze > /dev/null)
rc=$(runst "$C" r2-mock)
grep -q 'm-2 skipped: group g reached its 1 events' "$M/log/r2-mock.log" && ok "hypo group: one fault measured, the next job of the group skipped" || bad "group bound"
[ "$rc" = 7 ] && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
world; copytree
printf '#stage r2-mock\nm-1|heldout|risky|stophang|-|tri --keep-going --width 64 --height 64\n' > "$C/tables/r2-mock.txt"
(cd "$C" && run/freeze_r2.sh freeze > /dev/null)
rc=$(runst "$C" r2-mock)
[ "$rc" = 1 ] && grep -q 'a tri row without expectdiff' "$M/log/r2-mock.log" && ok "a tri row without expectdiff is refused before anything runs (rc 1)" || bad "missing expectdiff: rc $rc"
[ ! -f "$M/fake/resets" ] && ok "  nothing touched" || bad "  the refusal touched the GPU"
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_r2.sh"
(cd "$C" && run/freeze_r2.sh freeze > /dev/null)
rc=$(runst "$C" r2-a-safe)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_r2.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kregnow"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_r2.sh"
	"$C/run/guard_r2.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; grep -v "^trap '' PIPE HUP" "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_r2.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without trap '' PIPE HUP" || ok "guard: refuses a runner that does not ignore PIPE and HUP"
copytree; grep -v 'modinfo -F srcversion' "$P/run/lib_r2.sh" > "$C/run/lib_r2.sh"
"$C/run/guard_r2.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without the srcversion check" || ok "guard: refuses a runner without the srcversion check"
copytree; printf 'm-9|heldout|risky|stophang|-|tri --kreg x --keep-going\n' >> "$C/tables/r2-a-safe.txt"
"$C/run/guard_r2.sh" "$C" > /dev/null 2>&1 && bad "guard missed a forbidden table option" || ok "guard: refuses a forbidden table option"
"$P/run/guard_r2.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"

# 4. the driver: dry run (bounded commands, gates, the frozen sha256, the attempt, the fault count) and numeric knob compare
d=$(R2_ATT=attX SGX_DRY_RUN=1 bash "$P/run/r2.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_r2.py gate r2-a-fault' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh r2-d-safe $fs attX" && echo "$d" | grep -q "r2-out/attX/r2-d-safe .*/out/attX/r2-d-safe" \
	&& echo "$d" | grep -q 'score_r2.py gate r2-d-fault' && echo "$d" | grep -q 'score_r2.py gate r2-a-slack' \
	&& ok "driver dry run: gates, bounded ssh/scp, the frozen sha256, one directory an attempt, the conditional slack stage" || bad "driver dry run"
num_eq 0x00000000 0 && num_eq 0x00000422 0x422 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"
mkdir -p "$W/fe/a" "$W/fe/b"; printf 'h\nx\t1\t1\t1\t1\t1\t1\t1\tfault\nx\t1\t1\t1\t1\t1\t1\t1\thang\nx\t1\t1\t1\t1\t1\t1\t1\tok\n' > "$W/fe/a/cases.tsv"
printf 'h\nx\t1\t1\t1\t1\t1\t1\t1\tfault\n' > "$W/fe/b/cases.tsv"
[ "$(fault_events "$W/fe/a" "$W/fe/b" "$W/fe/none")" = 3 ] && ok "fault_events counts fault and hang rows across stage directories" || bad "fault_events"

# 5. the whole driver and the staging against fake ssh / scp / health (the laptop is a directory)
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
# a copy of the tree whose r2.env names the fake tool and regtimeline (the real hashes are R1's binaries)
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/stages.txt" "$P/conditional.txt" "$P/TABLES.md" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$R2_TOOL_SHA/" -e "s/^RT_SHA=.*/RT_SHA=$R2_RT_SHA/" "$P/run/r2.env" > "$D2T/run/r2.env"
	(cd "$D2T" && run/freeze_r2.sh freeze > /dev/null); }
fakehome() { # the laptop of this world: tool and regtimeline where the staging looks
	cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-r1"; cp "$P/tests/fake_rt.sh" "$M/home/regtimeline"; }
drvenv() { echo "$(envw) R2_OUT=$M/home/r2-out FAKE_P=$P FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-r1 SGXFIVE_REGTIMELINE=$M/home/regtimeline SGXFIVE_PROBE_BINS=$M/home/r2-stage"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_r2.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies, compares every file with the Mac's, checks the tool and regtimeline hashes" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_r2.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not R1's" && ok "staging refuses a laptop whose tool is not R1's build" || bad "staging with a foreign tool: rc $rc"
# the full session in the mock: every stage, the gates, the scorer after each stage, health between, the slack gate, the verdict
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r2.sh" > /dev/null 2>&1
out=$(env $(drvenv) R2_ATT=full bash "$D2T/run/r2.sh" 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage r2-.* done, health ok')
[ $rc = 0 ] && [ "$nst" = 4 ] && echo "$out" | grep -q 'gate r2-a-slack: not needed' && echo "$out" | grep -q '^R2 done' \
	&& ok "driver, whole session in the mock: 4 stages done with health, the slack pair not needed (a5 completed)" \
	|| { bad "driver full run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
[ -f "$D2T/out/full/score-r2-a-fault.txt" ] && grep -q SUMMARY "$D2T/out/full/score-r2-a-fault.txt" && ok "  the scorer ran after each stage (one SUMMARY kept)" || bad "  no score file"
# a5 faulting: the slack gate opens; the budget (4 events used) cannot hold both slack faults: stop 41 with the lead's command
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r2.sh" > /dev/null 2>&1
out=$(env $(drvenv) R2_ATT=slack1 FAKE_RULES='--max-width 544 --max-height 400 --poke cmd:1=0xe|fault:0x90004:0x2000a061:0x480' bash "$D2T/run/r2.sh" 2>&1); rc=$?
[ $rc = 41 ] && echo "$out" | grep -q 'gate r2-a-slack: open' && echo "$out" | grep -q 'R2_FAULT_LIMIT=6' && ok "a5 faults: the slack gate opens, the 5-event budget refuses the pair (rc 41) and prints the lead's command" \
	|| { bad "slack budget: rc $rc"; echo "$out" | tail -6 | sed 's/^/     /'; }
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r2.sh" > /dev/null 2>&1
out=$(env $(drvenv) R2_ATT=slack2 R2_FAULT_LIMIT=6 FAKE_RULES='--max-width 544 --max-height 400 --poke cmd:1=0xe|fault:0x90004:0x2000a061:0x480' bash "$D2T/run/r2.sh" 2>&1); rc=$?
v=$("$PY" "$D2T/score/score_r2.py" verdict "$D2T/out/slack2" 2>&1)
[ $rc = 0 ] && echo "$v" | grep -q 'Q286: H4 holds with slack' && ok "R2_FAULT_LIMIT=6: the slack pair runs; sa5 completes; verdict: H4 holds with slack" || { bad "slack run: rc $rc"; echo "$out" | tail -6 | sed 's/^/     /'; echo "$v" | sed 's/^/     /'; }
# a closed gate stops the driver with the stage to rerun
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r2.sh" > /dev/null 2>&1
out=$(env $(drvenv) R2_ATT=gate1 FAKE_RULES='--max-width 544 --max-height 400|diff' bash "$D2T/run/r2.sh" --only r2-a-safe r2-a-fault 2>&1); rc=$?
[ $rc = 40 ] && echo "$out" | grep -q 'rerun: run/r2.sh --only r2-a-safe' && ok "a failed a4 control closes the r2-a-fault gate (rc 40) and the driver names the stage to rerun" || { bad "gate stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
# a stage stop prints the fault count and the continue command
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r2.sh" > /dev/null 2>&1
out=$(env $(drvenv) R2_ATT=stop1 FAKE_RULES='--scratch-pages 17|hang' bash "$D2T/run/r2.sh" 2>&1); rc=$?
[ $rc = 4 ] && echo "$out" | grep -q 'R2_FAULTS_PRIOR=1 run/r2.sh --from r2-d-fault' && ok "an unexpected hang stops the driver (rc 4) and prints how to continue with the fault count" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
# restaging after a stop leaves the gates alone (no gate file): the next attempt's gate still reads the kept stage
out=$(env $(drvenv) bash "$D2T/run/stage_r2.sh" 2>&1); rc=$?
[ $rc = 0 ] && ok "restaging after a stop works (nothing on the laptop is a gate)" || bad "restage: rc $rc"
echo "work dir (kept for inspection): $W"
exit $fail
