#!/bin/bash
# tests/run_mock.sh: the R4-pixel runner end to end against a fake tool, a fake regtimeline and a fake debugfs whose directory is mode 000
# (only the sudo shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard, staging and the whole
# driver (r4.sh) with fake ssh/scp/health (the fake tool plays: bit 6 at 55 iterations of a b8 or load loop, never for ld8; bit 7 when the TA run L reaches 129.5 us; real E784 object dumps with the loop's depth words).  Needs a current freeze (run/freeze_r4.sh freeze).  Nothing is deleted: every run writes into
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
"$P/run/freeze_r4.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_r4.sh freeze)"; exit 1; }
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
export R4_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") R4_RT_SHA=$(sha "$P/tests/fake_rt.sh") R4_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 RT_LEAD=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log R4_OUT=$M/out HOME=$M/home"; }
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
grep -q 'resgx545 r4p health end try' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
[ "$(cat "$M/fake/hold")" = N ] && ! grep -q 'hold_recovery=Y' "$M/kmsg" && ok "hold_recovery was never written (R4-pixel holds no fault)" || bad "hold_recovery touched"
awk -F'\t' 'NR > 1 && ($8 == "" || $9 == "") { x++ } END { exit x > 0 }' "$M"/out/"$ATT"/*/cases.tsv && ok "rc and class on every row" || bad "rc/class"
MAIN=$M; MATT=$ATT
# the scorers on the mock output: every stage prints one SUMMARY (the Q276 and w stages cannot tell on a fake image)
want_of() { case "$1" in p4-o4) echo "cannot tell" ;; q4-v) echo "bit 7 follows the TA clock run L" ;; q4-f) echo "H-YIELD alone is consistent" ;; q4-t) echo "consistent ['H-N']" ;; g4-rw) echo "cannot tell" ;; esac; }
for st in $(cat "$P/stages.txt"); do
	s=$("$PY" "$P/score/score_r4.py" "$st" "$MAIN/out/$MATT/$st" | grep '^SUMMARY:'); w=$(want_of "$st")
	case "$s" in *"$w"*) ok "scorer $st: ${s:0:130}" ;; *) bad "scorer $st: ${s:-no SUMMARY} (wanted $w)" ;; esac
done
for st in q4-v q4-f q4-t; do
	"$PY" "$P/score/score_r4.py" gate "$st" "$MAIN/out/$MATT/$st" > "$W/gate-$st.txt" && ok "gate $st: the bridge controls pass in the mock world" || { bad "gate $st"; head -3 "$W/gate-$st.txt"; }
done
"$PY" "$P/score/score_r4.py" gate p4-o4 "$MAIN/out/$MATT/p4-o4" > "$W/gate-p4.txt"; [ $? != 0 ] && ok "gate p4-o4: the o4 controls cannot pass on a fake image (exit non-zero: the driver would stop)" || bad "gate p4-o4 passed on a fake image"
v=$("$PY" "$P/score/score_r4.py" verdict "$MAIN/out/$MATT")
case "$v" in *"p4-o4:"*"q4-v:"*"q4-f:"*"q4-t:"*"g4-rw:"*) ok "verdict: one line a stage" ;; *) bad "verdict: $v" ;; esac

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 q4-f; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && ok "  another session's hold left as it was: no knob write, no reset" || bad "  the failed preflight touched the GPU"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" q4-f)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/q4-f.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion of the loaded module differs from the installed one: rc 1, nothing touched" || bad "srcversion check: rc $rc"
world; rc=$(R4_SRCV_EXPECT=99CD90DA26E3AFF9C450517 runst "$P" q4-f)
[ "$rc" = 1 ] && grep -q 'is not the expected build (99CD90DA26E3AFF9C450517)' "$M/log/q4-f.log" && [ ! -f "$M/fake/resets" ] && ok "loaded = installed but not the expected build 99CD90DA...: rc 1, nothing touched" || bad "expected srcversion: rc $rc"
grep -q '^SRCV_EXPECT=99CD90DA26E3AFF9C450517$' "$P/run/r4.env" && ok "r4.env pins the expected srcversion 99CD90DA26E3AFF9C450517" || bad "r4.env srcversion"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" q4-f)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/q4-f.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; rc=$(R4_TOOL_SHA=0000 runst "$P" q4-f)
[ "$rc" = 1 ] && grep -q "the tool is not the pinned rgn4 tool" "$M/log/q4-f.log" && ok "preflight: a tool that is not the pinned rgn4 build (rc 1: stop and ask, no rebuild)" || bad "tool sha: rc $rc"
world; rc=$(R4_RT_SHA=0000 runst "$P" q4-f)
[ "$rc" = 1 ] && grep -q "regtimeline is not the staged one" "$M/log/q4-f.log" && ok "preflight: a regtimeline that is not the staged one (rc 1)" || bad "regtimeline sha: rc $rc"
world; rc=$(R4_RT_SHA=0000 runst "$P" p4-o4)
[ "$rc" = 0 ] && ok "p4-o4 needs no regtimeline: its preflight does not check it" || bad "p4-o4 with a foreign regtimeline: rc $rc"
check "fatal kernel message" 3 q4-f FAKE_RULES='loop-rel-b8-i56|fatal'
check "plain job does not return (freeze)" 6 q4-v FAKE_RULES='vloop-b8v-i880|timeout'
check "unexpected fault in a fill job" 4 q4-f FAKE_RULES='loop-rel-ld0-k70|fault:0x90004:0x20006062'
check "unexpected hang in a fill job" 4 q4-f FAKE_RULES='loop-rel-ld0-k70|hang'
check "a hang message at the head of 12000 characters is found in the WHOLE output" 4 q4-f FAKE_RULES='loop-rel-ld0-k53|headmsg'
check "unexplained failure (rc 1, no diff line)" 4 q4-t FAKE_RULES='--width 8 --height 8|nodiff'
check "STATUS2 not 0x400 after the reset: the stage stops before the job (rc 16)" 16 q4-f FAKE_PRE_S2=0x480
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started with STATUS2 0x480" || ok "  no job started"
[ "$(awk -F'\t' 'NR > 1 && $9 == "fail"' "$(KD q4-f)/cases.tsv" | grep -c .)" = 1 ] && ok "  the stopped job is recorded (class fail, pre STATUS2 not 0x400)" || bad "  no case row for the stopped job"
check "the relative loop does not prove itself at the first bridge row: stop with rc 17, health first" 17 q4-f FAKE_RULES='loop-rel-b8-i16|noloop'
awk -F'\t' '$9 == "proof"' "$(KD q4-f)/cases.tsv" | grep -q . && ok "  the row is recorded as class proof, the stage stopped at the FIRST row" || bad "  no proof row"
[ $(( $(wc -l < "$(KD q4-f)/cases.tsv") )) = 2 ] && ok "  nothing after the first row ran" || bad "  the stage went on"
grep -q 'resgx545 r4p health f-rel-b8-16 try' "$M/kmsg" && ok "  a health triangle ran after the proof failure" || bad "  no health after the proof failure"
check "a bridge control reads otherwise (136 iterations not setting bit 6): stop with rc 18, health first" 18 q4-f FAKE_RULES='loop-rel-b8-i136|st2:0x400'
[ $(( $(wc -l < "$(KD q4-f)/cases.tsv") )) = 5 ] && ok "  the stage ran the three bridge rows before it (16, 53, 56) and the failing one, nothing after" || bad "  rows after a failed bridge control"
grep -q 'resgx545 r4p health f-rel-b8-136 try' "$M/kmsg" && ok "  a health triangle ran after the bridge stop" || bad "  no health after the bridge stop"
check "a bridge control STATUS2 unreadable after the job cannot pass want2" 18 q4-v FAKE_RULES='vloop-b8v-i1760|st2:0x400'
check "a q4-t row that draws but whose loop did not run is class ok (the scorer voids it; only the proofstop rows stop)" 0 q4-t FAKE_RULES='loop-rel-b8-i1.bin|noloop'
check "health: the first failed recovery stops" 5 q4-f FAKE_HEALTH_BAD=1
check "the pre-job reset fails" 13 q4-f FAKE_RESET_FAIL_FROM=2
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job (snap 0)" 14 q4-f FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
check "registers unreadable" 12 q4-f FAKE_SNAP_FAIL=1
NOBINS=1 world
rc=$(runst "$P" q4-f); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" q4-f)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/q4-f.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world; rc=$(FSHA=none runst "$P" q4-f); [ "$rc" = 1 ] && ok "no frozen sha256 argument: rc 1" || bad "no sha argument: rc $rc"
# SIGPIPE / SIGHUP ignored, the output also in runner.log: a dropped ssh does not stop the stage
world
env $(envw) bash "$P/run/run_stage.sh" q4-f "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD q4-f)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 16 ] && grep -q '^## end' "$(KD q4-f)/runner.log" && ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc, rows $nc"
# one directory an attempt, never merged
world; rc=$(runst "$P" q4-f); rc2=$(runst "$P" q4-f)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/q4-f.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"
ATT=att-second; rc3=$(runst "$P" q4-f)
[ "$rc3" = 0 ] && [ -f "$M/out/att-second/q4-f/cases.tsv" ] && ok "a new attempt gets its own directory" || bad "new attempt: rc $rc3"

# 3. a copy of the tree: a changed table, an unknown knob, a probe --tri row without a frozen program, a bare debugfs access
copytree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$C/"; }
world; copytree
echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/q4-f.txt"
rc=$(runst "$C" q4-f)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/q4-f.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
world; copytree; echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/q4-f.txt"; mkdir -p "$W/emptydir"
"$PY" "$C/score/score_r4.py" q4-f "$W/emptydir" > "$W/refuse.txt" 2>&1; rcs=$?
[ "$rcs" = 3 ] && grep -q 'REFUSING: the frozen files do not verify' "$W/refuse.txt" && ok "the scorer refuses to run when the frozen files do not verify (rc 3)" || bad "scorer freeze refusal: rc $rcs"
world; copytree
printf '#stage q-mock\nm-1|heldout|safe|stophang bogus:1|-|probe\n' > "$C/tables/q-mock.txt"
(cd "$C" && run/freeze_r4.sh freeze > /dev/null 2>&1)
rc=$(runst "$C" q-mock); [ "$rc" = 7 ] && grep -q 'unknown knob bogus:1' "$M/log/q-mock.log" && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
world; copytree
printf '#stage q-mock\nm-1|heldout|safe|stophang|-|tri --keep-going --width 64 --height 64\n' > "$C/tables/q-mock.txt"
rc=$(runst "$C" q-mock)
[ "$rc" = 1 ] && grep -q 'a tri row without expectdiff' "$M/log/q-mock.log" && ok "a tri row without expectdiff is refused before anything runs (rc 1)" || bad "missing expectdiff: rc $rc"
[ ! -f "$M/fake/resets" ] && ok "  nothing touched" || bad "  the refusal touched the GPU"
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_r4.sh"
cp "$P/FROZEN.sha256" "$C/FROZEN.sha256"; sed -i '' "s#^.*  run/lib_r4.sh\$#$(sha "$C/run/lib_r4.sh")  run/lib_r4.sh#" "$C/FROZEN.sha256"
rc=$(runst "$C" q4-f)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_r4.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kregnow"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' 'dbg_write hold_recovery Y' 'set_hold N' 'dbg_write render_pb_pages 0x100'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_r4.sh"
	"$C/run/guard_r4.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; grep -v "^trap '' PIPE HUP" "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_r4.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without trap '' PIPE HUP" || ok "guard: refuses a runner that does not ignore PIPE and HUP"
copytree; grep -v 'modinfo -F srcversion' "$P/run/lib_r4.sh" > "$C/run/lib_r4.sh"
"$C/run/guard_r4.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without the srcversion check" || ok "guard: refuses a runner without the srcversion check"
copytree; printf 'm-9|heldout|safe|stophang|-|tri --kreg x --keep-going\n' >> "$C/tables/q4-f.txt"
"$C/run/guard_r4.sh" "$C" > /dev/null 2>&1 && bad "guard missed a forbidden table option" || ok "guard: refuses a forbidden table option"
copytree; printf 'm-9|heldout|safe|stophang s2|-|probe --tri pixel --width 8 --height 8 "$S/loop-abs-b8-i53.bin"\n' >> "$C/tables/q4-t.txt"
"$C/run/guard_r4.sh" "$C" > /dev/null 2>&1 && bad "guard missed an abs (ba) loop in a --tri row" || ok "guard: refuses an abs (ba) loop program in a --tri row (R3-P1)"
"$P/run/guard_r4.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"

fi
# 4. the driver: dry run (bounded commands, the frozen sha256, the attempt) and numeric knob compare
d=$(R4_ATT=attX SGX_DRY_RUN=1 bash "$P/run/r4.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' && echo "$d" | grep -q "run_stage.sh p4-o4 $fs attX" && echo "$d" | grep -q "run_stage.sh g4-rw $fs attX" \
	&& echo "$d" | grep -q "r4p-out/attX/q4-v .*/out/attX/q4-v" && [ "$(echo "$d" | grep -c 'run_stage.sh')" = 5 ] \
	&& ok "driver dry run: five stages in order, bounded ssh/scp, the frozen sha256, one directory an attempt" || bad "driver dry run"
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
# a copy of the tree whose r4.env names the fake tool and regtimeline (the real hashes are the rgn4 tool and regtimeline)
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$R4_TOOL_SHA/" -e "s/^RT_SHA=.*/RT_SHA=$R4_RT_SHA/" -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=MOCKSRCV/" "$P/run/r4.env" > "$D2T/run/r4.env"
	for f in lib_check.sh; do :; done
	# the real pins stay in TOOL.sha256; the copy's freeze is rebuilt without the pin check
	sed -i '' -e '/^\tpin=/d' -e '/does not name the pinned tool/d' -e '/cmp -s score\/scorekit.py/d' "$D2T/run/freeze_r4.sh"
	(cd "$D2T" && run/freeze_r4.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; cp "$P/tests/fake_rt.sh" "$M/home/regtimeline"; }
drvenv() { echo "$(envw | sed 's# HOME=[^ ]*##') R4_OUT=$M/home/r4p-out FAKE_P=$P FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4 SGXFIVE_REGTIMELINE=$M/home/regtimeline SGXFIVE_PROBE_BINS=$M/home/r4p-stage"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_r4.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies to ~/r4p-run, ~/r4p-stage, compares every file with the Mac's, checks the tool and regtimeline hashes" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
[ -d "$M/home/r4p-run/run" ] && [ -d "$M/home/r4p-stage" ] && [ ! -d "$M/home/r2" ] && [ ! -d "$M/home/r3g" ] && [ ! -d "$M/home/r3xev" ] && ok "  the laptop directories are ~/r4p-* only (no ~/r3g, ~/r3xev, ~/r2)" || bad "  laptop directories"
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_r4.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the pinned rgn4 tool" && ok "staging refuses a laptop whose tool is not the pinned rgn4 build" || bad "staging with a foreign tool: rc $rc"
# the session in the mock: the three Q082 stages with their bridge gates (the fake world passes them), scorer and health after each
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r4.sh" > /dev/null 2>&1
out=$(env $(drvenv) R4_ATT=full bash "$D2T/run/r4.sh" --only q4-v q4-f q4-t 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage .* done, health ok')
[ $rc = 0 ] && [ "$nst" = 3 ] && echo "$out" | grep -q '^R4-pixel done' && [ "$(echo "$out" | grep -c '^gate q4-.: PASS')" = 3 ] \
	&& ok "driver in the mock (q4-v q4-f q4-t): 3 stages done with health, each bridge gate PASS" \
	|| { bad "driver run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
[ -f "$D2T/out/full/score-q4-f.txt" ] && grep -q SUMMARY "$D2T/out/full/score-q4-t.txt" && ok "  the scorer ran after each stage (one SUMMARY kept)" || bad "  no score file"
# the first stage: the o4 controls cannot pass on a fake image, so the bridge gate stops the session with exit 42 before the next stage
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r4.sh" > /dev/null 2>&1
out=$(env $(drvenv) R4_ATT=g1 bash "$D2T/run/r4.sh" 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'the bridge controls of p4-o4 did not pass' && [ ! -d "$D2T/out/g1/q4-v" ] && ok "a bridge gate that does not pass stops the session with exit 42 before the next stage (p4-o4 on a fake image)" || { bad "bridge gate stop: rc $rc"; echo "$out" | tail -6 | sed 's/^/     /'; }
# a runner-side bridge control (rc 18): the stage is scored and health-checked, the session stops with 42
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r4.sh" > /dev/null 2>&1
out=$(env $(drvenv) R4_ATT=br FAKE_RULES='loop-rel-b8-i136|st2:0x400' bash "$D2T/run/r4.sh" --only q4-f q4-t 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'a bridge control of q4-f read otherwise' && grep -q 'stage q4-f done, health ok' <(echo "$out") && [ ! -d "$D2T/out/br/q4-t" ] \
	&& ok "a runner-side bridge control failing (rc 18): the stage is scored and health-checked, the session stops with exit 42" || { bad "rc 18 handling: rc $rc"; echo "$out" | tail -6 | sed 's/^/     /'; }
# a loop proof failing (rc 17) ends that stage only: scored, health ok, the session goes on
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r4.sh" > /dev/null 2>&1
out=$(env $(drvenv) R4_ATT=pf FAKE_RULES='loop-rel-b8-i16|noloop' bash "$D2T/run/r4.sh" --only q4-f q4-t 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'LOOP PROOF FAILED in q4-f' && grep -q 'stage q4-f done, health ok' <(echo "$out") && [ -d "$D2T/out/pf/q4-t" ] && echo "$out" | grep -q '(ended early: q4-f(proof))' \
	&& ok "a failed loop proof (rc 17) ends q4-f only: scored, health ok, the next stage ran, exit 0" || { bad "rc 17 handling: rc $rc"; echo "$out" | tail -8 | sed 's/^/     /'; }
# a stage stop prints the continue command
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r4.sh" > /dev/null 2>&1
out=$(env $(drvenv) R4_ATT=stop1 FAKE_RULES='loop-rel-ld0-k70|hang' bash "$D2T/run/r4.sh" --only q4-f 2>&1); rc=$?
[ $rc = 4 ] && echo "$out" | grep -q 'run/r4.sh --from q4-f' && ok "an unexpected hang stops the driver (rc 4) and prints how to continue" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
out=$(env $(drvenv) bash "$D2T/run/stage_r4.sh" 2>&1); rc=$?
[ $rc = 0 ] && ok "restaging after a stop works (nothing on the laptop is a gate)" || bad "restage: rc $rc"
echo "work dir (kept for inspection): $W"
exit $fail
