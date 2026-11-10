#!/bin/bash
# tests/run_mock.sh: the R3-pixel runner end to end against a fake tool, a fake regtimeline and a fake debugfs whose directory is mode 000
# (only the sudo shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard, staging and the whole
# driver (r3.sh) with fake ssh/scp/health.  Needs a current freeze (run/freeze_r3.sh freeze).  Nothing is deleted: every run writes into
# a new mktemp directory, printed at the end.
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
"$P/run/freeze_r3.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_r3.sh freeze)"; exit 1; }
N=0
# a fresh fake laptop: debugfs (mode 000) + its real files, the fake GPU state, the kernel log
world() {
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/stage" "$M/out" "$M/log" "$M/home"
	for f in reset regs render_param render_tadata; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"; echo 0x400 > "$M/fake/s2"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${NOBINS:-}" ] || cp "$P"/bins/*.bin "$M/stage/"
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh"
export R3_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") R3_RT_SHA=$(sha "$P/tests/fake_rt.sh") R3_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 RT_LEAD=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log R3_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
# runst DIR STAGE ENV...: run one stage in the current world with the driver's arguments; echoes the status.  FSHA overrides the sha256.
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }

# 1. every stage, the frozen tables, the default fake world: every job runs and is kept (SKIP_RUNNER=1 skips sections 1 to 3)
if [ -z "${SKIP_RUNNER:-}" ]; then
world
total=0
for st in $(cat "$P/stages.txt"); do
	rc=$(runst "$P" "$st")
	t=$P/tables/$st.txt; n=$(grep -vc '^#' "$t"); k=$(KD "$st")
	got=$(grep -c '^== ' "$M/log/$st.log"); nc=$(( $(wc -l < "$k/cases.tsv") - 1 ))
	total=$((total + n - $(awk -F'\t' 'NR > 1 && $9 == "skipped"' "$k/cases.tsv" | grep -c .)))
	skipped=$(awk -F'\t' 'NR > 1 && $9 == "skipped"' "$k/cases.tsv" | grep -c .)
	ns2=$(( $(awk -F'|' '!/^#/ && $4 ~ /(^| )s2( |$)/' "$t" | grep -c .) - skipped ))
	kp=$(ls "$k" | grep -c '\.pre\.regs\.txt\.gz'); ka=$(ls "$k" | grep -c '\.after\.regs\.txt\.gz')
	nd=$(awk -F'\t' 'NR > 1 && $9 == "ok" && $7 ~ /--dump-render/' "$k/cases.tsv" | grep -c .); kd=$(ls "$k" | grep -c 'tadata\.bin\.gz')
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$nc" = "$n" ] && [ "$kp" = "$ns2" ] && [ "$ka" = "$ns2" ] && [ "$kd" = "$nd" ] && grep -q '^## end' "$k/runner.log" \
		&& ok "$st: $got of $n jobs run ($skipped skipped by a sweep), $nc rows, $kp pre and $ka after STATUS2 reads, $kd of $nd TA dumps kept, runner.log kept" \
		|| bad "$st: rc $rc, $got of $n jobs, skipped $skipped, rows $nc, pre $kp after $ka of $ns2, dumps $kd of $nd"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg")
[ "$cases" = "$total" ] && ok "kernel log: $cases case markers, one for every job that ran (374 table rows less the sweep-skipped ones)" || bad "markers: $cases cases of $total"
grep -q 'resgx545 r3p health end try' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
[ "$(cat "$M/fake/hold")" = N ] && ! grep -q 'hold_recovery=Y' "$M/kmsg" && ok "hold_recovery was never written (R3-pixel holds no fault)" || bad "hold_recovery touched"
awk -F'\t' 'NR > 1 && ($8 == "" || $9 == "") { x++ } END { exit x > 0 }' "$M"/out/"$ATT"/*/cases.tsv && ok "rc and class on every row" || bad "rc/class"
MAIN=$M; MATT=$ATT
# the scorers on the mock output (the fake tool plays H-MA / the H-INST world): the whole chain gives verdicts
want_of() { case "$1" in p-c3) echo "Q276 NOT ANSWERED" ;; q-f0) echo "q-f0 loop gate OPEN" ;; q-f1a) echo "q-f1a: 54 jobs read, 0 void" ;; q-f1b) echo "q-f1b: 54 jobs read, 0 void" ;;
	q-t) echo "H-INST holds at" ;; q-v) echo "cannot tell" ;; esac; }
for st in $(cat "$P/stages.txt"); do
	s=$("$PY" "$P/score/score_r3.py" "$st" "$MAIN/out/$MATT/$st" | grep '^SUMMARY:'); w=$(want_of "$st")
	case "$s" in *"$w"*) ok "scorer $st: ${s:0:130}" ;; *) bad "scorer $st: ${s:-no SUMMARY} (wanted $w)" ;; esac
done
s=$("$PY" "$P/score/score_r3.py" q-t "$MAIN/out/$MATT/q-t" | grep '^SUMMARY:')
case "$s" in *"H-TILE REFUTED"*"H-JOB REFUTED"*) ok "scorer q-t in the H-INST world: the other two hypotheses are REFUTED" ;; *) bad "scorer q-t refutations: $s" ;; esac
"$PY" "$P/score/score_r3.py" gate q-f1a "$MAIN/out/$MATT" > /dev/null && ok "gate q-f1a open on a passing q-f0" || bad "gate"
v=$("$PY" "$P/score/score_r3.py" verdict "$MAIN/out/$MATT")
case "$v" in *"Q082-F: H-MA HOLDS"*"Q082-T:"*"Q276:"*) ok "verdict: the two-order q-f1 verdict and q-t, q-v, Q276 lines" ;; *) bad "verdict: $v" ;; esac

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 q-f0; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && ok "  another session's hold left as it was: no knob write, no reset" || bad "  the failed preflight touched the GPU"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" q-f0)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/q-f0.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion of the loaded module differs from the installed one: rc 1, nothing touched" || bad "srcversion check: rc $rc"
world; rc=$(R3_SRCV_EXPECT=B21FDA82BD5E5CB5A627E3B runst "$P" q-f0)
[ "$rc" = 1 ] && grep -q 'is not the expected build (B21FDA82BD5E5CB5A627E3B)' "$M/log/q-f0.log" && [ ! -f "$M/fake/resets" ] && ok "loaded = installed but not the expected build B21FDA82...: rc 1, nothing touched" || bad "expected srcversion: rc $rc"
grep -q '^SRCV_EXPECT=B21FDA82BD5E5CB5A627E3B$' "$P/run/r3.env" && ok "r3.env pins the expected srcversion B21FDA82BD5E5CB5A627E3B" || bad "r3.env srcversion"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" q-f0)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/q-f0.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; rc=$(R3_TOOL_SHA=0000 runst "$P" q-f0)
[ "$rc" = 1 ] && grep -q "the tool is not R1's" "$M/log/q-f0.log" && ok "preflight: a tool that is not R1's build (rc 1: stop and ask, no rebuild)" || bad "tool sha: rc $rc"
world; rc=$(R3_RT_SHA=0000 runst "$P" q-f0)
[ "$rc" = 1 ] && grep -q "regtimeline is not the staged one" "$M/log/q-f0.log" && ok "preflight: a regtimeline that is not the staged one (rc 1)" || bad "regtimeline sha: rc $rc"
world; rc=$(R3_RT_SHA=0000 runst "$P" p-c3)
[ "$rc" = 0 ] && ok "p-c3 needs no regtimeline: its preflight does not check it" || bad "p-c3 with a foreign regtimeline: rc $rc"
check "fatal kernel message" 3 q-f0 FAKE_RULES='loop-rel-b8-i56|fatal'
check "plain job does not return (freeze)" 6 q-f1a FAKE_RULES='loop-rel-b16-i22|timeout'
check "unexpected fault in a fill job" 4 q-f1a FAKE_RULES='loop-rel-b12-i33|fault:0x90004:0x20006062'
check "unexpected hang in a fill job" 4 q-f1a FAKE_RULES='loop-rel-b12-i33|hang'
check "a hang message at the head of 12000 characters is found in the WHOLE output" 4 q-f1a FAKE_RULES='loop-rel-b16-i23|headmsg'
check "unexplained failure (rc 1, no diff line)" 4 q-t FAKE_RULES='--width 8 --height 8|nodiff'
check "STATUS2 not 0x400 after the reset: the stage stops before the job (rc 16)" 16 q-f1a FAKE_PRE_S2=0x480
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started with STATUS2 0x480" || ok "  no job started"
[ "$(awk -F'\t' 'NR > 1 && $9 == "fail"' "$(KD q-f1a)/cases.tsv" | grep -c .)" = 1 ] && ok "  the stopped job is recorded (class fail, pre STATUS2 not 0x400)" || bad "  no case row for the stopped job"
check "the relative loop does not prove itself in q-f0: stop with rc 17, health first" 17 q-f0 FAKE_RULES='loop-rel-b8-i53|noloop'
awk -F'\t' '$9 == "proof"' "$(KD q-f0)/cases.tsv" | grep -q . && ok "  the row is recorded as class proof, the stage stopped at the FIRST control" || bad "  no proof row"
[ $(( $(wc -l < "$(KD q-f0)/cases.tsv") )) = 2 ] && ok "  nothing after the first control ran (the loop stages end cleanly)" || bad "  the stage went on"
grep -q 'resgx545 r3p health f0-rel-b8-53 try' "$M/kmsg" && ok "  a health triangle ran after the proof failure" || bad "  no health after the proof failure"
check "a q-t row that draws but whose loop did not run is class ok (the scorer voids it; only q-f0 stops)" 0 q-t FAKE_RULES='loop-rel-b8-i1.bin|noloop'
check "health: the first failed recovery stops" 5 q-f0 FAKE_HEALTH_BAD=1
check "the pre-job reset fails" 13 q-f0 FAKE_RESET_FAIL_FROM=2
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job (snap 0)" 14 q-f0 FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
check "registers unreadable" 12 q-f0 FAKE_SNAP_FAIL=1
NOBINS=1 world
rc=$(runst "$P" q-f0); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" q-f0)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/q-f0.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world; rc=$(FSHA=none runst "$P" q-f0); [ "$rc" = 1 ] && ok "no frozen sha256 argument: rc 1" || bad "no sha argument: rc $rc"
# the sweep: rows past E784's intact work are skipped once the group has set bit 7; watch rows never are
world; rc=$(runst "$P" q-v); k=$(KD q-v)
for g in b4v:vb4 v12:v12 v48:v48; do
	grp=${g%%:*}
	first_skip=$(awk -F'\t' -v g="v-$grp-" 'NR > 1 && index($1, g) == 1 && $9 == "skipped" { print $1; exit }' "$k/cases.tsv")
	ran_after_set=$(awk -F'\t' -v g="v-$grp-" 'NR > 1 && index($1, g) == 1 && $9 == "ok" { n++ } END { print n + 0 }' "$k/cases.tsv")
	[ -n "$first_skip" ] && ok "sweep $grp: the rows after the first set bit past E784's length are skipped (first: $first_skip), $ran_after_set ran" || bad "sweep $grp: nothing skipped"
done
awk -F'\t' 'NR > 1 && $1 ~ /^v-(up|dn|b16v)-/ && $9 == "skipped"' "$k/cases.tsv" | grep -q . && bad "a narrowing or b16v row was skipped" || ok "no narrowing (b8v up/down) or b16v row is ever skipped (no sweep knob)"
grep -q 'sweep v12: STATUS2' "$M/log/q-v.log" && ok "the runner says which group's bit stopped the sweep" || bad "no sweep message"
# SIGPIPE / SIGHUP ignored, the output also in runner.log: a dropped ssh does not stop the stage
world
env $(envw) bash "$P/run/run_stage.sh" q-f0 "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD q-f0)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 10 ] && grep -q '^## end' "$(KD q-f0)/runner.log" && ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc, rows $nc"
# one directory an attempt, never merged
world; rc=$(runst "$P" q-f0); rc2=$(runst "$P" q-f0)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/q-f0.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"
ATT=att-second; rc3=$(runst "$P" q-f0)
[ "$rc3" = 0 ] && [ -f "$M/out/att-second/q-f0/cases.tsv" ] && ok "a new attempt gets its own directory" || bad "new attempt: rc $rc3"

# 3. a copy of the tree: a changed table, an unknown knob, a probe --tri row without a frozen program, a bare debugfs access
copytree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/stages.txt" "$P/conditional.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }
world; copytree
echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/q-f0.txt"
rc=$(runst "$C" q-f0)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/q-f0.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
world; copytree; echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/q-f0.txt"; mkdir -p "$W/emptydir"
"$PY" "$C/score/score_r3.py" q-f0 "$W/emptydir" > "$W/refuse.txt" 2>&1; rcs=$?
[ "$rcs" = 3 ] && grep -q 'REFUSING: the frozen files do not verify' "$W/refuse.txt" && ok "the scorer refuses to run when the frozen files do not verify (rc 3)" || bad "scorer freeze refusal: rc $rcs"
world; copytree
printf '#stage q-mock\nm-1|heldout|safe|stophang bogus:1|-|probe\n' > "$C/tables/q-mock.txt"
(cd "$C" && run/freeze_r3.sh freeze > /dev/null 2>&1)
rc=$(runst "$C" q-mock); [ "$rc" = 7 ] && grep -q 'unknown knob bogus:1' "$M/log/q-mock.log" && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
world; copytree
printf '#stage q-mock\nm-1|heldout|safe|stophang|-|tri --keep-going --width 64 --height 64\n' > "$C/tables/q-mock.txt"
rc=$(runst "$C" q-mock)
[ "$rc" = 1 ] && grep -q 'a tri row without expectdiff' "$M/log/q-mock.log" && ok "a tri row without expectdiff is refused before anything runs (rc 1)" || bad "missing expectdiff: rc $rc"
[ ! -f "$M/fake/resets" ] && ok "  nothing touched" || bad "  the refusal touched the GPU"
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_r3.sh"
cp "$P/FROZEN.sha256" "$C/FROZEN.sha256"; sed -i '' "s#^.*  run/lib_r3.sh\$#$(sha "$C/run/lib_r3.sh")  run/lib_r3.sh#" "$C/FROZEN.sha256"
rc=$(runst "$C" q-f0)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_r3.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kregnow"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' 'dbg_write hold_recovery Y' 'set_hold N' 'dbg_write render_pb_pages 0x100'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_r3.sh"
	"$C/run/guard_r3.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; grep -v "^trap '' PIPE HUP" "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_r3.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without trap '' PIPE HUP" || ok "guard: refuses a runner that does not ignore PIPE and HUP"
copytree; grep -v 'modinfo -F srcversion' "$P/run/lib_r3.sh" > "$C/run/lib_r3.sh"
"$C/run/guard_r3.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without the srcversion check" || ok "guard: refuses a runner without the srcversion check"
copytree; printf 'm-9|heldout|safe|stophang|-|tri --kreg x --keep-going\n' >> "$C/tables/q-f0.txt"
"$C/run/guard_r3.sh" "$C" > /dev/null 2>&1 && bad "guard missed a forbidden table option" || ok "guard: refuses a forbidden table option"
copytree; printf 'm-9|heldout|safe|stophang s2|-|probe --tri pixel --width 8 --height 8 "$S/loop-abs-b8-i53.bin"\n' >> "$C/tables/q-t.txt"
"$C/run/guard_r3.sh" "$C" > /dev/null 2>&1 && bad "guard missed an abs (ba) loop in a --tri row" || ok "guard: refuses an abs (ba) loop program in a --tri row (R3-P1)"
"$P/run/guard_r3.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"

fi
# 4. the driver: dry run (bounded commands, gates, the frozen sha256, the attempt) and numeric knob compare
d=$(R3_ATT=attX SGX_DRY_RUN=1 bash "$P/run/r3.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_r3.py gate q-f1a' && echo "$d" | grep -q 'score_r3.py gate q-f1b' && echo "$d" | grep -q 'score_r3.py gate q-t' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh p-c3 $fs attX" && echo "$d" | grep -q "r3p-out/attX/q-v .*/out/attX/q-v" && ! echo "$d" | grep -q 'score_r3.py gate q-v' \
	&& ok "driver dry run: the loop gate before q-f1a, q-f1b, q-t (not q-v), bounded ssh/scp, the frozen sha256, one directory an attempt" || bad "driver dry run"
num_eq 0x00000000 0 && num_eq 0x00000422 0x422 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"

# 5. the whole driver and the staging against fake ssh / scp / health (the laptop is a directory)
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
# a copy of the tree whose r3.env names the fake tool and regtimeline (the real hashes are R1's binaries)
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/stages.txt" "$P/conditional.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$R3_TOOL_SHA/" -e "s/^RT_SHA=.*/RT_SHA=$R3_RT_SHA/" -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=MOCKSRCV/" "$P/run/r3.env" > "$D2T/run/r3.env"
	for f in lib_check.sh; do :; done
	# the real pins stay in TOOL.sha256; the copy's freeze is rebuilt without the pin check
	sed -i '' -e '/^\tpin=/d' -e '/does not name the pinned tool/d' -e '/cmp -s .toolsrc.now/d' "$D2T/run/freeze_r3.sh"
	(cd "$D2T" && run/freeze_r3.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-r1"; cp "$P/tests/fake_rt.sh" "$M/home/regtimeline"; }
drvenv() { echo "$(envw | sed 's# HOME=[^ ]*##') R3_OUT=$M/home/r3p-out FAKE_P=$P FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-r1 SGXFIVE_REGTIMELINE=$M/home/regtimeline SGXFIVE_PROBE_BINS=$M/home/r3p-stage"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_r3.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies to ~/r3p-run, ~/r3p-stage, compares every file with the Mac's, checks the tool and regtimeline hashes" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
[ -d "$M/home/r3p-run/run" ] && [ -d "$M/home/r3p-stage" ] && [ ! -d "$M/home/r2" ] && [ ! -d "$M/home/r3g" ] && [ ! -d "$M/home/r3xev" ] && ok "  the laptop directories are ~/r3p-* only (no ~/r3g, ~/r3xev, ~/r2)" || bad "  laptop directories"
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_r3.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not R1's" && ok "staging refuses a laptop whose tool is not R1's build" || bad "staging with a foreign tool: rc $rc"
# the full session in the mock: every stage, the gates, the scorer after each stage, health between, the verdict
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r3.sh" > /dev/null 2>&1
out=$(env $(drvenv) R3_ATT=full bash "$D2T/run/r3.sh" 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage .* done, health ok')
[ $rc = 0 ] && [ "$nst" = 6 ] && echo "$out" | grep -q '^R3-pixel done: ' && ! echo "$out" | grep -q SKIPPED \
	&& ok "driver, whole session in the mock: 6 stages done with health, no gate closed" \
	|| { bad "driver full run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
[ -f "$D2T/out/full/score-q-f1b.txt" ] && grep -q SUMMARY "$D2T/out/full/score-q-t.txt" && ok "  the scorer ran after each stage (one SUMMARY kept)" || bad "  no score file"
# the loop gate closed: q-f0 stops on the first relative loop; the pixel loop stages end cleanly, q-v still runs, exit 0
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r3.sh" > /dev/null 2>&1
out=$(env $(drvenv) R3_ATT=gate FAKE_RULES='loop-rel-b8-i53|noloop' bash "$D2T/run/r3.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'LOOP GATE CLOSED' && echo "$out" | grep -q '^SKIPPED: q-f1a' && echo "$out" | grep -q '^SKIPPED: q-t' && [ -d "$D2T/out/gate/q-v" ] && [ ! -d "$D2T/out/gate/q-f1a" ] && [ ! -d "$D2T/out/gate/q-t" ] \
	&& echo "$out" | grep -q '(skipped:' \
	&& ok "a failed relative-loop proof ends the Q082 pixel loop stages CLEANLY: q-f1a, q-f1b, q-t skipped, health ok, q-v ran, exit 0" \
	|| { bad "loop gate: rc $rc"; echo "$out" | tail -12 | sed 's/^/     /'; }
grep -q 'stage q-f0 done, health ok' <(echo "$out") && ok "  q-f0 itself was scored and health-checked after its rc 17" || bad "  q-f0 health after the proof stop"
# abs and rel loops disagree on the bit: the driver stops (41) with the lead's decision
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r3.sh" > /dev/null 2>&1
out=$(env $(drvenv) R3_ATT=dis FAKE_RULES='loop-abs-b8-i53|st2:0x440' bash "$D2T/run/r3.sh" 2>&1); rc=$?
[ $rc = 41 ] && echo "$out" | grep -q "abs and rel loops disagree" && ok "abs and rel disagree on the bit: the driver stops with exit 41 (lead's decision)" || { bad "disagree: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
# a stage stop prints the continue command
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r3.sh" > /dev/null 2>&1
out=$(env $(drvenv) R3_ATT=stop1 FAKE_RULES='loop-rel-b8-i16|hang' bash "$D2T/run/r3.sh" 2>&1); rc=$?
[ $rc = 4 ] && echo "$out" | grep -q 'run/r3.sh --from q-f0' && ok "an unexpected hang stops the driver (rc 4) and prints how to continue" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
out=$(env $(drvenv) bash "$D2T/run/stage_r3.sh" 2>&1); rc=$?
[ $rc = 0 ] && ok "restaging after a stop works (nothing on the laptop is a gate)" || bad "restage: rc $rc"
echo "work dir (kept for inspection): $W"
exit $fail
