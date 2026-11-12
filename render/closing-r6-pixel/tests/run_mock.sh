#!/bin/bash
# tests/run_mock.sh: the R6-pixel runner end to end against a fake tool and a fake debugfs whose directory is mode 000 (only the sudo
# shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard, staging and the whole driver
# (r6.sh) with fake ssh/scp/health.  R5-pixel's run_mock.sh for R6's stages.  Round 5/6 rules: the fake tool answers by the command's
# ARGV and the staged program's bytes (tests/fake_tool.sh -> fake_o4.py / fake_rw.py run the program in sgx-sim; a command of
# another shape draws nothing the scorers read), with no timing at all (no sleep, no clock, no ring window: it passes under load);
# the laptop's files live under the mock HOME's scratch/r6p and scratch/tmp only, and TMPDIR points at a directory that does not
# exist, so a mktemp without the runner's template fails the run; the fake df answers the free space (FAKE_FREE_KB, FAKE_FREE_LOW_FROM).
# Needs a current freeze (run/freeze_r6.sh freeze) and the sim harness (debug/target/debug/simcheck, built by tests/test_sim.py).
# Every run writes into a new mktemp directory under debug/tmp (printed at the end).
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run_mock.XXXXXX")
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_r6.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_r6.sh freeze)"; exit 1; }
[ -x "$P/debug/target/debug/simcheck" ] || { echo "FAIL: no sim harness (run tests/test_sim.py first)"; exit 1; }
N=0
world() {
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home/scratch/r6p/stage" "$M/home/scratch/tmp"
	for f in reset regs render_param render_tadata kpoke; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"; echo 0x400 > "$M/fake/s2"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${NOBINS:-}" ] || cp "$P"/bins/*.bin "$M/home/scratch/r6p/stage/"
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" FAKE_P="$P" TMPDIR=$W/no-such-tmpdir
export R6_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") R6_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_Y_O3_LANE=1
# the mock HOME is the laptop's; the Mac side still reads the landed tree (pbdump, usse-asm) and its bringup
export RESGX545_MAIN=${RESGX545_MAIN:-$HOME/src/resgx545} RESGX545_DATA=${RESGX545_DATA:-$HOME/src/resgx545-data}
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log HOME=$M/home"; }
KD() { echo "$M/home/scratch/r6p/out/$ATT/$1"; }
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; echo $?; }
leftover() { ls "$M/home/scratch/tmp" | grep -c '^r6p\.'; }

# 1. every stage, the frozen tables, the default fake world (H-STORE gated, OR(o0,o3), lane 1 for L3's y jobs, e smooth)
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
	[ "$(leftover)" = 0 ] && ok "  $st: every work directory under ~/scratch/tmp removed once its files were kept" || bad "  $st: $(leftover) work directories left"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg")
[ "$cases" = "$total" ] && [ "$total" = 202 ] && ok "kernel log: $cases case markers, one for every job (202)" || bad "markers: $cases cases of $total"
grep -q 'resgx545 r6p health end try' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
[ "$(cat "$M/fake/hold")" = N ] && ok "hold_recovery was never written" || bad "hold_recovery touched"
nk=$(grep -c -- '--kpoke rd:9=' "$M/fake.log")
[ ! -s "$M/dbgreal/kpoke" ] && [ ! -e "$M/fake/kpoke-writes" ] && [ "$nk" = 22 ] && ! grep -q 'kreg' "$M/fake.log" \
	&& ok "kpoke: 22 commands carried --kpoke rd:9=0|1 (p6-s only), each applied and dropped; the runner wrote no kpoke; no kreg" || bad "kpoke: $nk commands, writes $(cat "$M/fake/kpoke-writes" 2>/dev/null)"
grep -c 'kpoke after: \[\]' "$(KD p6-s)/runner.log" | grep -qx 22 && ok "  the runner read debugfs kpoke empty after each of the 22 kpoke rows" || bad "  kpoke after reads"
[ -z "$(ls "$M/home" | grep -v '^scratch$')" ] && [ -z "$(ls "$M/home/scratch" | grep -vE '^(r6p|tmp)$')" ] && ok "the laptop's files: ~/scratch/r6p and ~/scratch/tmp only (TMPDIR unusable: no mktemp without the template ran)" || bad "laptop files: $(ls -R "$M/home" | head -5)"
MAIN=$M; MATT=$ATT
want_of() { case "$1" in p6-rd) echo "rd vector S S S S S S S: H-STORE" ;; p6-l3) echo "H-Y1" ;; g6-rwa) echo "part a: PASS" ;; g6-rw) echo "H-FRAC PASS" ;; p6-s) echo "H-OR:" ;; esac; }
for st in $(cat "$P/stages.txt"); do
	s=$("$PY" "$P/score/score_r6.py" "$st" "$MAIN/home/scratch/r6p/out/$MATT/$st" | grep '^SUMMARY:'); w=$(want_of "$st")
	case "$s" in *"$w"*) ok "scorer $st on the mock's argv-driven output: ${s:0:120}" ;; *) bad "scorer $st: ${s:-no SUMMARY} (wanted $w)" ;; esac
	"$PY" "$P/score/score_r6.py" gate "$st" "$MAIN/home/scratch/r6p/out/$MATT/$st" > "$W/gate-$st.txt" && ok "  gate $st passes" || { bad "gate $st"; head -3 "$W/gate-$st.txt"; }
done
v=$("$PY" "$P/score/score_r6.py" verdict "$MAIN/home/scratch/r6p/out/$MATT")
case "$v" in *"p6-rd:"*"p6-l3:"*"g6-rwa:"*"g6-rw:"*"p6-s:"*) ok "verdict: one line a stage" ;; *) bad "verdict: $v" ;; esac
# another world: H-FOUR (o4..o7 read back a leftover)
world; rc=$(runst "$P" p6-rd FAKE_RD_MODEL=H-FOUR)
s=$("$PY" "$P/score/score_r6.py" p6-rd "$(KD p6-rd)" | grep '^SUMMARY:')
case "$s" in *": H-FOUR;"*"o4: cannot tell by design"*) ok "a world playing H-FOUR: named, o4's predicate cannot tell by design" ;; *) bad "H-FOUR world: $s" ;; esac
# R4's o2 slip by construction: a control row of another shape (the default triangle) cannot pass in the argv-driven mock
world; C=$W/o2tree; mkdir -p "$C"; cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/tests" "$P/debug-src" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$C/"
sed -i '' -e '/^c-u-x|/s/ --width 64 --height 64 --vtx-coords 2 --blk 4=0x00030001//' "$C/tables/p6-rd.txt"
(cd "$C" && run/freeze_r6.sh freeze > /dev/null 2>&1)
rc=$(runst "$C" p6-rd)
"$PY" "$C/score/score_r6.py" gate p6-rd "$(KD p6-rd)" > "$W/gate-o2.txt"; g=$?
[ "$rc" = 0 ] && [ "$g" != 0 ] && grep -q 'G-o1 c-u' "$W/gate-o2.txt" && ok "a control of another shape (c-u-x on the default triangle, R4's o2 slip) fails the bridge gate in the mock" || bad "o2 slip: rc $rc gate $g"

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 g6-rwa; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && ok "  another session's hold left as it was: no write, no reset" || bad "  the failed preflight touched the GPU"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" g6-rwa)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/g6-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion loaded != installed: rc 1, nothing touched" || bad "srcversion: rc $rc"
world; rc=$(R6_SRCV_EXPECT=99CD90DA26E3AFF9C450517 runst "$P" g6-rwa)
[ "$rc" = 1 ] && grep -q 'is not the expected build (99CD90DA26E3AFF9C450517)' "$M/log/g6-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "loaded = installed but not the rgn4 build 99CD90DA...: rc 1, nothing touched" || bad "expected srcversion: rc $rc"
grep -q '^SRCV_EXPECT=99CD90DA26E3AFF9C450517$' "$P/run/r6.env" && grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/r6.env" && ok "r6.env pins srcversion 99CD90DA26E3AFF9C450517 and tool e6951558..." || bad "r6.env pins"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" g6-rwa)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/g6-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; mv "$M/dbgreal/kpoke" "$M/dbgreal/kpoke.gone"; rc=$(runst "$P" p6-s)
[ "$rc" = 1 ] && grep -q "has no debugfs kpoke" "$M/log/p6-s.log" && [ ! -f "$M/fake/resets" ] && ok "preflight of p6-s: no debugfs kpoke: rc 1, nothing touched" || bad "preflight without kpoke: rc $rc"
world; mv "$M/dbgreal/kpoke" "$M/dbgreal/kpoke.gone"; rc=$(runst "$P" g6-rwa)
[ "$rc" = 0 ] && ok "  a stage without kpoke rows does not need debugfs kpoke" || bad "  g6-rwa without kpoke: rc $rc"
world; echo "rd:9=1" > "$M/dbgreal/kpoke"; rc=$(runst "$P" p6-s)
[ "$rc" = 1 ] && grep -q "debugfs kpoke is armed at the start" "$M/log/p6-s.log" && [ ! -f "$M/fake/resets" ] && [ "$(cat "$M/dbgreal/kpoke")" = "rd:9=1" ] \
	&& ok "preflight of p6-s: a kpoke armed by someone else: rc 1, nothing touched (not even cleared)" || bad "armed kpoke at start: rc $rc"
check "a kpoke the kernel did not drop: the stage stops (rc 19) after the first kpoke row" 19 p6-s FAKE_KPOKE_STICK=1
[ ! -s "$M/dbgreal/kpoke" ] && [ -s "$M/fake/kpoke-writes" ] && [ "$(grep -c 'resgx545 case' "$M/kmsg")" = 1 ] && ok "  and debugfs kpoke was cleared (the restore), one job ran" || bad "  kpoke not cleared: [$(cat "$M/dbgreal/kpoke")]"
world; rc=$(R6_TOOL_SHA=0000 runst "$P" g6-rwa)
[ "$rc" = 1 ] && grep -q "the tool is not the pinned rgn4 tool" "$M/log/g6-rwa.log" && ok "preflight: a tool that is not the pinned rgn4 build (rc 1: stop and ask)" || bad "tool sha: rc $rc"
world; rc=$(R6_RT_SHA=0000 runst "$P" p6-l3)
[ "$rc" = 0 ] && ok "no row runs under regtimeline: the preflight does not need it" || bad "regtimeline: rc $rc"
check "preflight: less than 200 MB free on ~/scratch (rc 1, nothing touched)" 1 g6-rwa FAKE_FREE_KB=150000
[ ! -f "$M/fake/resets" ] && ok "  nothing touched" || bad "  the low-space preflight touched the GPU"
check "free space drops under 200 MB during the stage: the next job does not start (rc 21)" 21 g6-rwa FAKE_FREE_LOW_FROM=4
check "fatal kernel message" 3 g6-rwa FAKE_RULES='rw-k2.bin|fatal'
check "a job does not return (freeze)" 6 p6-rd FAKE_RULES='r6o-rd-2-x.bin|timeout'
check "an unexpected fault" 4 p6-rd FAKE_RULES='r6o-c-ow-x.bin|fault:0x90004:0x20006062'
check "an unexpected hang" 4 g6-rwa FAKE_RULES='rw-k2.bin|hang'
check "a hang message at the head of the output is found in the WHOLE output" 4 g6-rwa FAKE_RULES='d-01.bin|headmsg'
check "an unexplained failure (rc 1)" 4 g6-rwa FAKE_RULES='d-02.bin|nodiff'
check "STATUS2 not 0x400 after the reset: the stage stops before the job (rc 16)" 16 p6-rd FAKE_PRE_S2=0x480
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started with STATUS2 0x480" || ok "  no job started"
check "health: the first failed recovery stops" 5 g6-rwa FAKE_HEALTH_BAD=1
check "the pre-job reset fails" 13 g6-rwa FAKE_RESET_FAIL_FROM=2
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job" 14 g6-rwa FAKE_STUCK=1
check "registers unreadable" 12 g6-rwa FAKE_SNAP_FAIL=1
NOBINS=1 world; rc=$(runst "$P" g6-rwa); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" g6-rwa)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/g6-rwa.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world
env $(envw) bash "$P/run/run_stage.sh" g6-rwa "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD g6-rwa)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 8 ] && grep -q '^## end' "$(KD g6-rwa)/runner.log" && ok "the reader of the runner's output goes away: the stage completes" || bad "closed pipe: rc $rc, rows $nc"
world; rc=$(runst "$P" g6-rwa); rc2=$(runst "$P" g6-rwa)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/g6-rwa.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"

# 3. a copy of the tree: a changed table, the scorer's refusal, an unknown knob, kpoke without the knob, a bare debugfs access, the guard
copytree() { C=$W/tree$N.$RANDOM; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/templates" "$P/tests" "$P/debug-src" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$C/"; }
world; copytree; echo "x-extra|heldout|safe|stophang|-|probe" >> "$C/tables/g6-rwa.txt"
rc=$(runst "$C" g6-rwa)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/g6-rwa.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
mkdir -p "$W/emptydir"; "$PY" "$C/score/score_r6.py" g6-rwa "$W/emptydir" > "$W/refuse.txt" 2>&1; rcs=$?
[ "$rcs" = 3 ] && grep -q 'REFUSING: the frozen files do not verify' "$W/refuse.txt" && ok "the scorer refuses to run when the frozen files do not verify (rc 3)" || bad "scorer freeze refusal: rc $rcs"
world; copytree; printf '#stage q-mock\nm-1|heldout|safe|stophang bogus:1|-|probe\n' > "$C/tables/q-mock.txt"
(cd "$C" && run/freeze_r6.sh freeze > /dev/null 2>&1)
rc=$(runst "$C" q-mock); [ "$rc" = 7 ] && grep -q 'unknown knob bogus:1' "$M/log/q-mock.log" && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
for row in 'k-1|heldout|safe|stophang s2|-|probe --kpoke rd:9=1 "$S/rw-k0.bin"' 'k-1|heldout|safe|stophang s2 kpoke|-|probe --kpoke ta:3=1 "$S/rw-k0.bin"' \
	'k-1|heldout|safe|stophang s2 kpoke|-|probe --kpoke rd:9=1 --kpoke rd:9=0 "$S/rw-k0.bin"'; do
	world; copytree; printf '#stage k-mock\n%s\n' "$row" > "$C/tables/k-mock.txt"
	(cd "$C" && run/freeze_r6.sh freeze > /dev/null 2>&1)
	rc=$(runst "$C" k-mock)
	[ "$rc" = 7 ] && ! grep -q 'resgx545 case' "$M/kmsg" && ok "runner refuses a kpoke row outside the rule before the job (rc 7): ${row:0:60}" || bad "kpoke row: rc $rc: $row"
	"$C/run/guard_r6.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $row" || ok "  guard refuses it too"
done
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_r6.sh"
sed -i '' "s#^.*  run/lib_r6.sh\$#$(sha "$C/run/lib_r6.sh")  run/lib_r6.sh#" "$C/FROZEN.sha256"
rc=$(runst "$C" g6-rwa)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_r6.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kregnow"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' 'dbg_write hold_recovery Y' 'reboot' 'rm -rf "$KEEP"' \
	'W=$(mktemp -d)' 'cd /tmp' 'printf "rd:9=1\n" | sudo -n tee "$D/kpoke"' 'dbg_write kpoke rd:9=1' 'unlink "$JW/x"'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_r6.sh"
	"$C/run/guard_r6.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; sed -i '' -e 's/space_ok/space_skip/g' "$C/run/run_stage.sh"
"$C/run/guard_r6.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without the free-space check" || ok "guard: refuses a runner without the free-space check"
"$P/run/guard_r6.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"
grep -nE '(^|[^a-zA-Z0-9_.])/tmp' "$P"/run/*.sh "$P"/run/r6.env | grep -v '/guard_r6.sh:' | grep -v '^[^:]*:[0-9]*:#' && bad "/tmp in the runner" || ok "no /tmp in any runner file (laptop files under ~/scratch)"
# rmwork refuses anything that is not a work directory
sed -n '/^rmwork()/,/^}$/p' "$P/run/lib_r6.sh" > "$W/rmwork.sh"
out=$(bash -c 'R6TMP=/x/scratch/tmp; WROOT=/x/scratch/tmp/r6p.root; . "$1"; rmwork /x/scratch/r6p/out; echo "rc $?"; rmwork "$WROOT"; echo "rc $?"; rmwork /x/scratch/tmp/r6p.; echo "rc $?"' _ "$W/rmwork.sh")
[ "$(echo "$out" | grep -c '^rc 1$')" = 3 ] && ok "rmwork refuses the out directory, the stage root and a bare prefix" || bad "rmwork: $out"

# 4. the driver: dry run
d=$(R6_ATT=attX SGX_DRY_RUN=1 bash "$P/run/r6.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'bounded 1500 ssh' && echo "$d" | grep -q 'bounded 300 scp' && echo "$d" | grep -q "run_stage.sh p6-rd $fs attX" && echo "$d" | grep -q "run_stage.sh p6-s $fs attX" \
	&& echo "$d" | grep -q "scratch/r6p/out/attX/g6-rwa .*/out/attX/g6-rwa" && [ "$(echo "$d" | grep -c 'run_stage.sh')" = 5 ] \
	&& [ "$(echo "$d" | grep 'run_stage.sh' | awk '{print $(NF-4)}' | tr '\n' ' ')" = "p6-rd p6-l3 g6-rwa g6-rw p6-s " ] \
	&& ok "driver dry run: five tables in order (p6-s last), bounded ssh/scp, the frozen sha256, ~/scratch/r6p/out, one directory an attempt" || { bad "driver dry run"; echo "$d" | grep run_stage | head -3; }

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
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$R6_TOOL_SHA/" -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=MOCKSRCV/" "$P/run/r6.env" > "$D2T/run/r6.env"
	sed -i '' -e '/^\tpin=/d' -e '/does not name the pinned tool/d' -e '/cmp -s score\/scorekit.py/d' "$D2T/run/freeze_r6.sh"
	(cd "$D2T" && run/freeze_r6.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; rm -rf "$M/home/scratch"; }
drvenv() { echo "$(envw) FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_r6.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies to ~/scratch/r6p/run and ~/scratch/r6p/stage, compares every file, checks the tool hash" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
[ -d "$M/home/scratch/r6p/run/run" ] && [ -d "$M/home/scratch/r6p/stage" ] && [ -d "$M/home/scratch/tmp" ] && [ -z "$(ls "$M/home" | grep -vE '^(scratch|sgxfive-test-rgn4)$')" ] \
	&& ok "  the laptop directories are ~/scratch/r6p/{run,stage,out} and ~/scratch/tmp only" || bad "  laptop directories: $(ls "$M/home")"
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_r6.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the pinned rgn4 tool" && ok "staging refuses a laptop whose tool is not the pinned rgn4 build" || bad "staging with a foreign tool: rc $rc"
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r6.sh" > /dev/null 2>&1
out=$(env $(drvenv) R6_ATT=full bash "$D2T/run/r6.sh" 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage .* done, health ok')
[ $rc = 0 ] && [ "$nst" = 5 ] && echo "$out" | grep -q '^R6-pixel done' && [ "$(echo "$out" | grep -c '^gate .*: PASS')" = 5 ] \
	&& ok "the whole session in the mock: 5 tables done with health, each gate PASS" || { bad "driver run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
grep -q 'H-STORE' "$D2T/out/full/score-p6-rd.txt" && grep -q 'H-FRAC PASS' "$D2T/out/full/score-g6-rw.txt" && grep -q 'H-OR' "$D2T/out/full/score-p6-s.txt" \
	&& ok "  the scorers ran after each stage (SUMMARY kept)" || bad "  score files"
[ "$(ls "$M/home/scratch/tmp" | grep -c '^r6p\.')" = 0 ] && ok "  no work directory left on the laptop after the session" || bad "  work dirs left: $(ls "$M/home/scratch/tmp" | head -3)"
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r6.sh" > /dev/null 2>&1
out=$(env $(drvenv) R6_ATT=b1 FAKE_RD_MODEL=DEAD bash "$D2T/run/r6.sh" 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'the bridge controls of p6-rd did not pass' && [ ! -d "$D2T/out/b1/p6-l3" ] && ok "p6-rd's bridge (a dead readback, c-rd-0) stops the session with exit 42 before p6-l3" || { bad "bridge stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r6.sh" > /dev/null 2>&1
out=$(env $(drvenv) R6_ATT=b2 FAKE_RW_RULE=rz bash "$D2T/run/r6.sh" --only g6-rwa g6-rw 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'the bridge controls of g6-rwa did not pass' && [ ! -d "$D2T/out/b2/g6-rw" ] && ok "g6-rwa's control words off (RZ always): the gate stops the session before g6-rw (exit 42)" || { bad "g6-rwa stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_r6.sh" > /dev/null 2>&1
out=$(env $(drvenv) R6_ATT=s1 FAKE_RULES='rw-k2.bin|hang' bash "$D2T/run/r6.sh" --only g6-rwa 2>&1); rc=$?
[ $rc = 4 ] && echo "$out" | grep -q 'run/r6.sh --from g6-rwa' && ok "an unexpected hang stops the driver (rc 4) and prints how to continue" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
echo "work dir (kept for inspection): $W"
exit $fail
