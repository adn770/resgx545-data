#!/bin/bash
# tests/run_mock.sh: the R5-pixel runner end to end against a fake tool and a fake debugfs whose directory is mode 000 (only the sudo
# shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard, staging and the whole driver
# (r5.sh) with fake ssh/scp/health.  R4-pixel's run_mock.sh for R5's stages.  Round 5 rule: the fake tool answers by the command's
# ARGV (tests/fake_tool.sh -> fake_o4.py / fake_rw.py run the staged program the command names in sgx-sim; a command of another shape
# draws nothing the scorers read), so the scorers' SUMMARY lines below come from the frozen tables' own commands and programs.
# Needs a current freeze (run/freeze_r5.sh freeze) and the sim harness (debug/target/debug/simcheck, built by tests/test_sim.py).
# Nothing of the session is deleted: every run writes into a new mktemp directory, printed at the end.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
W=$(mktemp -d "$P/debug/tmp/run_mock.XXXXXX")
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_r5.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_r5.sh freeze)"; exit 1; }
[ -x "$P/debug/target/debug/simcheck" ] || { echo "FAIL: no sim harness (run tests/test_sim.py first)"; exit 1; }
N=0
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
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" FAKE_P="$P"
export R5_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") R5_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log R5_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }

# 1. every stage, the frozen tables, the default fake world (FAKE_O4_MODEL OR(o0,o3), FAKE_RW_RULE hmant)
world
total=0
for st in $(cat "$P/stages.txt"); do
	rc=$(runst "$P" "$st")
	t=$P/tables/$st.txt; n=$(grep -vc '^#' "$t"); k=$(KD "$st")
	got=$(grep -c '^== ' "$M/log/$st.log"); nc=$(( $(wc -l < "$k/cases.tsv") - 1 ))
	total=$((total + n))
	kp=$(ls "$k" | grep -c '\.pre\.regs\.txt\.gz'); ka=$(ls "$k" | grep -c '\.after\.regs\.txt\.gz')
	kd=$(ls "$k" | grep -c 'tadata\.bin\.gz')
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$nc" = "$n" ] && [ "$kp" = "$n" ] && [ "$ka" = "$n" ] && [ "$kd" = "$n" ] && grep -q '^## end' "$k/runner.log" \
		&& ok "$st: $got of $n jobs run, $nc rows, $kp pre and $ka after STATUS2 reads, $kd TA dumps kept, runner.log kept" \
		|| bad "$st: rc $rc, $got of $n jobs, rows $nc, pre $kp after $ka, dumps $kd"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg")
[ "$cases" = "$total" ] && [ "$total" = 106 ] && ok "kernel log: $cases case markers, one for every job (106)" || bad "markers: $cases cases of $total"
grep -q 'resgx545 r5p health end try' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
[ "$(cat "$M/fake/hold")" = N ] && ok "hold_recovery was never written" || bad "hold_recovery touched"
[ ! -e "$M/fake/written" ] && ! grep -qE 'kpoke|kreg' "$M/fake.log" && ok "no knob write, no kpoke or kreg in any command" || bad "a knob or register write"
MAIN=$M; MATT=$ATT
want_of() { case "$1" in p5-o4) echo "the tag-5 word is OR(o0,o3)" ;; g5-rwa) echo "part a: PASS" ;; g5-rw) echo "H-MANT held: 42 of 42" ;; esac; }
for st in $(cat "$P/stages.txt"); do
	s=$("$PY" "$P/score/score_r5.py" "$st" "$MAIN/out/$MATT/$st" | grep '^SUMMARY:'); w=$(want_of "$st")
	case "$s" in *"$w"*) ok "scorer $st on the mock's argv-driven output: ${s:0:120}" ;; *) bad "scorer $st: ${s:-no SUMMARY} (wanted $w)" ;; esac
	"$PY" "$P/score/score_r5.py" gate "$st" "$MAIN/out/$MATT/$st" > "$W/gate-$st.txt" && ok "  gate $st passes" || { bad "gate $st"; head -3 "$W/gate-$st.txt"; }
done
v=$("$PY" "$P/score/score_r5.py" verdict "$MAIN/out/$MATT")
case "$v" in *"p5-o4:"*"g5-rwa:"*"g5-rw:"*) ok "verdict: one line a stage" ;; *) bad "verdict: $v" ;; esac
# another world: the model the fake plays is XOR(o3,o5,o6), and the predicate set P3 is scored (it reads o3): gated
world; rc=$(runst "$P" p5-o4 FAKE_O4_MODEL='XOR(o3,o5,o6)')
s=$("$PY" "$P/score/score_r5.py" p5-o4 "$(KD p5-o4)" | grep '^SUMMARY:')
case "$s" in *"the tag-5 word is XOR(o3,o5,o6)"*"P3 gated"*) ok "a world playing XOR(o3,o5,o6): named, P3 gated (the sim's predicate semantics)" ;; *) bad "XOR world: $s" ;; esac
# R4's o2 slip by construction: a control row of another shape (the default triangle) cannot pass in the argv-driven mock
world; C=$W/o2tree; mkdir -p "$C"; cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/tests" "$P/debug-src" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$C/"
sed -i '' -e '/^c-v-a4-x|/s/ --width 64 --height 64 --vtx-coords 2 --blk 4=0x00030001//' "$C/tables/p5-o4.txt"
(cd "$C" && run/freeze_r5.sh freeze > /dev/null 2>&1)
rc=$(runst "$C" p5-o4)
"$PY" "$C/score/score_r5.py" gate p5-o4 "$(KD p5-o4)" > "$W/gate-o2.txt"; g=$?
[ "$rc" = 0 ] && [ "$g" != 0 ] && grep -q 'c-v-a4' "$W/gate-o2.txt" && ok "a control of another shape (c-v-a4-x on the default triangle, R4's o2 slip) fails the bridge gate in the mock" || bad "o2 slip: rc $rc gate $g"

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 g5-rwa; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && ok "  another session's hold left as it was: no write, no reset" || bad "  the failed preflight touched the GPU"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" g5-rwa)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/g5-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion loaded != installed: rc 1, nothing touched" || bad "srcversion: rc $rc"
world; rc=$(R5_SRCV_EXPECT=99CD90DA26E3AFF9C450517 runst "$P" g5-rwa)
[ "$rc" = 1 ] && grep -q 'is not the expected build (99CD90DA26E3AFF9C450517)' "$M/log/g5-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "loaded = installed but not the rgn4 build 99CD90DA...: rc 1, nothing touched" || bad "expected srcversion: rc $rc"
grep -q '^SRCV_EXPECT=99CD90DA26E3AFF9C450517$' "$P/run/r5.env" && grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/r5.env" && ok "r5.env pins srcversion 99CD90DA26E3AFF9C450517 and tool e6951558..." || bad "r5.env pins"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" g5-rwa)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/g5-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; rc=$(R5_TOOL_SHA=0000 runst "$P" g5-rwa)
[ "$rc" = 1 ] && grep -q "the tool is not the pinned rgn4 tool" "$M/log/g5-rwa.log" && ok "preflight: a tool that is not the pinned rgn4 build (rc 1: stop and ask)" || bad "tool sha: rc $rc"
world; rc=$(R5_RT_SHA=0000 runst "$P" p5-o4)
[ "$rc" = 0 ] && ok "no row runs under regtimeline: the preflight does not need it" || bad "regtimeline: rc $rc"
check "fatal kernel message" 3 g5-rwa FAKE_RULES='q-16.bin|fatal'
check "a job does not return (freeze)" 6 p5-o4 FAKE_RULES='r5o-w-2-x.bin|timeout'
check "an unexpected fault" 4 p5-o4 FAKE_RULES='r5o-w-0-x.bin|fault:0x90004:0x20006062'
check "an unexpected hang" 4 g5-rwa FAKE_RULES='rw-k2.bin|hang'
check "a hang message at the head of the output is found in the WHOLE output" 4 g5-rwa FAKE_RULES='q-15.bin|headmsg'
check "an unexplained failure (rc 1)" 4 g5-rwa FAKE_RULES='q-17.bin|nodiff'
check "STATUS2 not 0x400 after the reset: the stage stops before the job (rc 16)" 16 p5-o4 FAKE_PRE_S2=0x480
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started with STATUS2 0x480" || ok "  no job started"
check "health: the first failed recovery stops" 5 g5-rwa FAKE_HEALTH_BAD=1
check "the pre-job reset fails" 13 g5-rwa FAKE_RESET_FAIL_FROM=2
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job" 14 g5-rwa FAKE_STUCK=1
check "registers unreadable" 12 g5-rwa FAKE_SNAP_FAIL=1
NOBINS=1 world; rc=$(runst "$P" g5-rwa); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" g5-rwa)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/g5-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world
env $(envw) bash "$P/run/run_stage.sh" g5-rwa "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD g5-rwa)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 12 ] && grep -q '^## end' "$(KD g5-rwa)/runner.log" && ok "the reader of the runner's output goes away: the stage completes" || bad "closed pipe: rc $rc, rows $nc"
world; rc=$(runst "$P" g5-rwa); rc2=$(runst "$P" g5-rwa)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/g5-rwa.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"

# 3. a copy of the tree: a changed table, the scorer's refusal, an unknown knob, a bare debugfs access, the guard
copytree() { C=$W/tree$N.$RANDOM; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/tests" "$P/debug-src" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$C/"; }
world; copytree; echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/g5-rwa.txt"
rc=$(runst "$C" g5-rwa)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/g5-rwa.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
mkdir -p "$W/emptydir"; "$PY" "$C/score/score_r5.py" g5-rwa "$W/emptydir" > "$W/refuse.txt" 2>&1; rcs=$?
[ "$rcs" = 3 ] && grep -q 'REFUSING: the frozen files do not verify' "$W/refuse.txt" && ok "the scorer refuses to run when the frozen files do not verify (rc 3)" || bad "scorer freeze refusal: rc $rcs"
world; copytree; printf '#stage q-mock\nm-1|heldout|safe|stophang bogus:1|-|probe\n' > "$C/tables/q-mock.txt"
(cd "$C" && run/freeze_r5.sh freeze > /dev/null 2>&1)
rc=$(runst "$C" q-mock); [ "$rc" = 7 ] && grep -q 'unknown knob bogus:1' "$M/log/q-mock.log" && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_r5.sh"
sed -i '' "s#^.*  run/lib_r5.sh\$#$(sha "$C/run/lib_r5.sh")  run/lib_r5.sh#" "$C/FROZEN.sha256"
rc=$(runst "$C" g5-rwa)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_r5.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kregnow"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' 'dbg_write hold_recovery Y' 'reboot' 'rm -rf "$KEEP"'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_r5.sh"
	"$C/run/guard_r5.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; printf 'm-9|heldout|safe|stophang|-|probe --kpoke 0x148=1 x\n' >> "$C/tables/g5-rw.txt"
"$C/run/guard_r5.sh" "$C" > /dev/null 2>&1 && bad "guard missed a forbidden table option" || ok "guard: refuses a forbidden table option (--kpoke: no E406 setup this round)"
"$P/run/guard_r5.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"

# 4. the driver: dry run
d=$(R5_ATT=attX SGX_DRY_RUN=1 bash "$P/run/r5.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' && echo "$d" | grep -q "run_stage.sh p5-o4 $fs attX" && echo "$d" | grep -q "run_stage.sh g5-rw $fs attX" \
	&& echo "$d" | grep -q "r5p-out/attX/g5-rwa .*/out/attX/g5-rwa" && [ "$(echo "$d" | grep -c 'run_stage.sh')" = 3 ] \
	&& ok "driver dry run: three tables in order, bounded ssh/scp, the frozen sha256, ~/r5p-out, one directory an attempt" || bad "driver dry run"

# 5. the whole driver and the staging against fake ssh / scp / health (the laptop is a directory)
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/tests" "$P/debug-src" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$R5_TOOL_SHA/" -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=MOCKSRCV/" "$P/run/r5.env" > "$D2T/run/r5.env"
	sed -i '' -e '/^\tpin=/d' -e '/does not name the pinned tool/d' -e '/cmp -s score\/scorekit.py/d' "$D2T/run/freeze_r5.sh"
	(cd "$D2T" && run/freeze_r5.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; }
drvenv() { echo "$(envw | sed 's# HOME=[^ ]*##') R5_OUT=$M/home/r5p-out FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4 SGXFIVE_PROBE_BINS=$M/home/r5p-stage"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_r5.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies to ~/r5p-run and ~/r5p-stage, compares every file, checks the tool hash" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
[ -d "$M/home/r5p-run/run" ] && [ -d "$M/home/r5p-stage" ] && [ -z "$(ls "$M/home" | grep -v '^r5p-' | grep -v '^sgxfive-test-rgn4$')" ] && ok "  the laptop directories are ~/r5p-* only" || bad "  laptop directories: $(ls "$M/home")"
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_r5.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the pinned rgn4 tool" && ok "staging refuses a laptop whose tool is not the pinned rgn4 build" || bad "staging with a foreign tool: rc $rc"
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r5.sh" > /dev/null 2>&1
out=$(env $(drvenv) R5_ATT=full bash "$D2T/run/r5.sh" 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage .* done, health ok')
[ $rc = 0 ] && [ "$nst" = 3 ] && echo "$out" | grep -q '^R5-pixel done' && [ "$(echo "$out" | grep -c '^gate .*: PASS')" = 3 ] \
	&& ok "the whole session in the mock: 3 tables done with health, each gate PASS" || { bad "driver run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
grep -q 'the tag-5 word is OR(o0,o3)' "$D2T/out/full/score-p5-o4.txt" && grep -q 'H-MANT held' "$D2T/out/full/score-g5-rw.txt" && ok "  the scorers ran after each stage (SUMMARY kept)" || bad "  score files"
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r5.sh" > /dev/null 2>&1
out=$(env $(drvenv) R5_ATT=b1 FAKE_O4_MODEL=none bash "$D2T/run/r5.sh" 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'the bridge controls of p5-o4 did not pass' && [ ! -d "$D2T/out/b1/g5-rwa" ] && ok "p5-o4's bridge controls failing (no tag-5 word) stop the session with exit 42 before g5-rwa" || { bad "bridge stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r5.sh" > /dev/null 2>&1
out=$(env $(drvenv) R5_ATT=b2 FAKE_RW_RULE=noscale bash "$D2T/run/r5.sh" --only g5-rwa g5-rw 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'the bridge controls of g5-rwa did not pass' && [ ! -d "$D2T/out/b2/g5-rw" ] && ok "R4's unscaled design (q jobs clip): g5-rwa's gate stops the session before g5-rw (exit 42)" || { bad "shape stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r5.sh" > /dev/null 2>&1
out=$(env $(drvenv) R5_ATT=s1 FAKE_RULES='rw-k2.bin|hang' bash "$D2T/run/r5.sh" --only g5-rwa 2>&1); rc=$?
[ $rc = 4 ] && echo "$out" | grep -q 'run/r5.sh --from g5-rwa' && ok "an unexpected hang stops the driver (rc 4) and prints how to continue" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
echo "work dir (kept for inspection): $W"
exit $fail
