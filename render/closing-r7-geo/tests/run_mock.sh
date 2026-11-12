#!/bin/bash
# tests/run_mock.sh: the r7-geo runner and driver end to end against the ARGV-DRIVEN fake tools (tests/worlds.py: t4 refuses odd
# heights as the rgn4 build does; a texture probe is answered from the T1 word its program loads; the records' own argv answer
# with the records' kept outputs) and a fake debugfs whose directory is mode 000 (only the sudo shim reaches it).  Built from round
# 6's r6-misc run_mock.sh.  No timing window anywhere: the runner has no held flow and the fake answers synchronously; every sleep
# is 0 and the tee fallback 30 s (it only fires if tee hangs).
#   1. the whole driver (staging, g.sh over the six stages, the kept-files check, the scorers, the verdict) in the model world:
#      every verdict decided, only `reset 1` written, laptop files under ~/scratch/r7g, t6 only on the odd heights; then
#      sessioncheck.py staged (the stage script's exact list) and kept (every stage, --call read_files) on the output;
#   2. the runner's rules on reduced tables (a copy, refrozen): gate refusals, soft failures (one goes on, two stop), a fault,
#      no hash twice, no dump, the premise stop, free space, a latched fault, unreadable registers, a failed reset, the begin
#      health, the module, the frozen table, a knob or tool the session does not allow;
#   3. the staged runner under env -i (sessioncheck.py envi);  4. the freeze;  5. the guard (injections);  6. the dry runs.
# Needs a current freeze (run/freeze_g.sh freeze).  Every run writes into a new mktemp directory under debug/.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
mkdir -p "$P/debug"
W=$(mktemp -d "$P/debug/runmock.XXXXXX")
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_g.sh" verify > /dev/null 2>&1 || { echo "FAIL: not frozen (run/freeze_g.sh freeze)"; exit 1; }
S4=$(sha "$P/tests/fake_tool4.sh"); S6=$(sha "$P/tests/fake_tool6.sh")
# python3 is the session venv's (scorekit.py needs 3.10 or later; the laptop's preflight checks its own)
export PATH="$P/tests/shims:$(dirname "$PY"):$PATH" G_TOOL_SHA=$S4 G_TOOL6_SHA=$S6 G_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 TEE_GRACE=30
N=0
world() { # world [WORLD]: a fresh fake laptop running WORLD (default model)
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home/scratch/r7g/bin"
	for f in reset regs kpoke peek bif_flush; do : > "$M/dbgreal/$f"; done
	echo "${FAKE_PB_INIT:-0x422}" > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"; echo 0 > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_TR_INIT:-0}" > "$M/dbgreal/render_tail_room"
	echo N > "$M/dbgreal/hold_recovery"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo "${FAKE_SRCV:-MOCKSRCV}" > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	cp "$P/tests/fake_tool4.sh" "$M/home/sgxfive-test-rgn4"
	chmod 000 "$M/dbg"
	FAKE_WORLD=${1:-model}
}
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log HOME=$M/home FAKE_HOME=$M/home FAKE_P=$P/tests"; }
KD() { echo "$M/home/scratch/r7g/out/$ATT/$1"; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
# a copy of the session (the frozen tree as the stage script and the driver see it)
ttree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/templates" "$P/bin" "$P/stages.txt" "$P/TABLES.md" \
		"$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$P/TOOL6.sha256" "$P/TOOL6SRC.sha256" "$C/"
	mkdir -p "$C/debug"; ln -s "$P/debug/asm" "$C/debug/asm"; }
# stage a tree onto the fake laptop the way stage_g.sh does (its own copy commands)
stage() { env $(envw) T6_LOCAL="$P/tests/fake_tool6.sh" bash "$C/run/stage_g.sh" > "$M/log/stage.log" 2>&1; }
runst() { # runst TREE STAGE [ENV...]: the laptop runner of TREE on the fake laptop; prints its exit status
	local d=$1 st=$2; shift 2
	env $(envw) "$@" bash "$M/home/scratch/r7g/run/run/run_stage.sh" "$st" "${FSHA:-$(sha "$d/FROZEN.sha256")}" "$ATT" > "$M/log/$st.log" 2>&1; echo $?; }
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
laptop_files_ok() { # every file the session left on the fake laptop is under ~/scratch/r7g (or is the rgn4 tool); ~/scratch/tmp empty
	local extra left
	extra=$(cd "$M/home" && find . -type f | grep -vE '^\./scratch/r7g/|^\./sgxfive-test-rgn4$')
	left=$(ls -A "$M/home/scratch/tmp" 2>/dev/null)
	[ -z "$extra" ] && [ -z "$left" ] && return 0
	echo "     files outside ~/scratch/r7g: ${extra:-none}; left in ~/scratch/tmp: ${left:-none}"; return 1
}
# refreeze a copy after its tables changed (the runner checks the frozen table)
refreeze() { (cd "$C" && R7G_FREEZE_COPY=1 run/freeze_g.sh freeze > /dev/null) || bad "refreeze in the copy"; }

# ---- 1. the whole driver ---------------------------------------------------------------------------------------------------
world model; ttree
stage && ok "stage_g.sh: staged, the laptop copies checked" || bad "staging: $(grep -E 'FAIL|STOP' "$M/log/stage.log" | head -3)"
OUT=$(env $(envw) G_ATT=full bash "$C/run/g.sh" 2>&1); RC=$?
ATT=full
VERDICT=$(R7G_NO_FREEZE_CHECK=1 "$PY" "$C/score/score_g.py" verdict "$C/out/full" 2>&1)
nst=$(echo "$OUT" | grep -c '^stage [a-z]* done, health ok, knobs at their defaults')
[ $RC = 0 ] && [ "$nst" = 6 ] && echo "$OUT" | grep -q '^r7-geo done' && ok "world model: staging, the driver runs the six stages, kept-files check, health and knobs ok after each" \
	|| { bad "world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
for k in "Q206 both fields: H-INDEP held (8 of 8 rows decided)" "Q283 type 4 S32 held (5 of 5" "Q283 types 1 and 3 RASTERW held (6 of 6" \
	"Q178 type 5 H-STEP held (3 of 3" "memory: the image does not follow the texture) held (2 of 2" \
	"Q262 depth H-DEPTH held on every size (100 of 100" "Q262 depth H-E606 held on every size (100 of 100" "Q262 iteration H-ITER held (24 of 24" \
	"Q240 family H-E606 held on every size (240 of 240" "Q240 family H-ZLS held on every size (240 of 240" "Q260 H-HU exact on the held-out rows (143 of 143" \
	"HU at +0.5 y and +64.5 (the mirror) (51 of 51"; do
	echo "$VERDICT" | grep -qF "$k" && ok "  verdict: $k" || bad "world model verdict lacks: $k"
done
echo "$VERDICT" | grep -E ': (cannot tell|controls FAILED)' && bad "  the model world's verdict has cannot tell or a failed control" || ok "  no control failed and no headline cannot tell"
wr=$(writes | sort -u | tr '\n' ' ')
[ "$wr" = "reset 1 " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs write of the whole session: reset 1" || bad "  debugfs writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
laptop_files_ok && ok "  every laptop file under ~/scratch/r7g; every work directory (mktemp under ~/scratch/tmp) removed" || bad "  laptop files"
n6=$(grep -c '^sgxfive-test tri ' "$M/fake.log"); n6odd=$(grep '^sgxfive-test tri ' "$M/fake.log" | grep -cE -- '--height (33|47) ')
n4odd=$(grep '^sgxfive-test-rgn4 tri ' "$M/fake.log" | grep -cE -- '--height [0-9]*[13579] ')
[ "$n6" = 48 ] && [ "$n6odd" = 48 ] && [ "$n4odd" = 0 ] && ok "  t6 ran exactly the 48 odd-height rows; no odd height with t4" || bad "  tools: t6 $n6 ($n6odd odd), t4 odd $n4odd"
nv=0; for st in xf tx zd zi zf zs; do nv=$((nv + $(awk 'NR > 1' "$(KD $st)/void.tsv" | wc -l))); done
[ "$nv" = 0 ] && ok "  no void row in the model world" || bad "  $nv void rows"
for st in xf tx zd zi zf zs; do
	"$PY" "$P/score/sessioncheck.py" kept "$C/score/score_g.py" "$st" "$C/out/full/$st" --call read_files > "$W/kept-$st.out" 2>&1 \
		&& ok "  sessioncheck kept $st: $(tail -1 "$W/kept-$st.out")" || { bad "  sessioncheck kept $st"; head -3 "$W/kept-$st.out"; }
done
SF=$(sed -n 's/^RUNNER_FILES="\(.*\)"$/\1/p' "$P/run/stage_g.sh")
SD=$W/staged; mkdir -p "$SD"; for f in $SF; do cp "$P/$f" "$SD/"; done
"$PY" "$P/score/sessioncheck.py" staged "$SD" $(for f in $SF; do printf '%s ' "${f##*/}"; done) --entry run_stage.sh > "$W/staged.out" 2>&1 \
	&& ok "sessioncheck staged: the stage script's list (RUNNER_FILES) is complete: $(tail -1 "$W/staged.out")" || { bad "sessioncheck staged"; cat "$W/staged.out" | head -5; }
# a slip it must catch: lib_g.sh left out of the staged list
"$PY" "$P/score/sessioncheck.py" staged "$SD" run_stage.sh g.env sessioncheck.py scorekit.py --entry run_stage.sh > /dev/null 2>&1 \
	&& bad "sessioncheck staged passed without lib_g.sh" || ok "sessioncheck staged: a list without lib_g.sh fails"

# ---- 2. the runner's rules on reduced tables ----------------------------------------------------------------------------------
mini() { # mini STAGE N...: the copy's table STAGE keeps its header and the rows numbered N (1-based over the job rows)
	local st=$1; shift; local f=$C/tables/$st.txt
	{ grep '^#' "$f"; grep -v '^#' "$f" | awk -v keep=" $* " 'index(keep, " " NR " ")'; } > "$f.new" && mv "$f.new" "$f"; }
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$C" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
prep() { world "$1"; ttree; shift; [ $# -gt 0 ] && { "$@"; refreeze; }; stage || bad "staging (world $FAKE_WORLD)"; }
# zf rows: 1-2 controls, 3..26 64x128, ..., 123..146 32x16 (gate at 123), 147..170 16x8 (gate at 147), 171.. 4096x16, 195.. 64x33
prep tiny-refuse mini zf 1 2 123 124 125 147 148 171
stopcase "gate: 32 x 16 and 16 x 8 refused at their gate rows, their groups skipped, the stage goes on" 0 zf
[ "$(awk 'NR > 1' "$(KD zf)/void.tsv" | wc -l | tr -d ' ')" = 2 ] && grep -q 'zf-32x16-s-01 skipped: group s32x16' "$M/log/zf.log" \
	&& grep -q '^zf-4096x16-s-00	' "$(KD zf)/cases.tsv" && ok "  the two gate rows in void.tsv, the rest of each group skipped, 4096 x 16 ran" || bad "  gate bookkeeping"
# 4096 x 4096 rows 99..102: the world refuses 99, 100 and 102 (first x below 600000/256) and draws 101
prep big-fail mini zd 1 99 101
stopcase "soft: one 4096 x 4096 depth row refused (not in a row) is recorded and the stage goes on" 0 zd
[ "$(awk 'NR > 1' "$(KD zd)/void.tsv" | wc -l | tr -d ' ')" = 1 ] && ok "  the refused row is in void.tsv, not cases.tsv" || bad "  soft bookkeeping"
prep big-fail mini zd 1 99 100
stopcase "soft: two 4096 x 4096 depth rows refused in a row stop the stage" 24 zd
prep fault-zd mini zd 1 27
stopcase "a fault (none expected) stops the stage after strict health" 4 zd
prep nohash mini zs 1 3 4
stopcase "the second row without a hash stops zs" 17 zs
prep nodump mini zd 3
stopcase "a depth dump the tool did not write stops zd at its first row (rc 23)" 23 zd
prep model mini zf 1 2
stopcase "zf's two controls in the model world" 0 zf
# the premise: a control whose reading is missing (the fake prints no triangle count) stops before any gate
prep model mini zi 2 3
cat > "$M/home/sgxfive-test-rgn4" <<EOF2
#!/bin/bash
"$P/tests/fake_tool4.sh" "\$@" | grep -v '^tri [0-9]*x[0-9]* #1: '
exit \${PIPESTATUS[0]}
EOF2
chmod +x "$M/home/sgxfive-test-rgn4"
stopcase "premise: E680's control without its triangle-count reading stops the stage (rc 25)" 25 zi G_TOOL_SHA="$(sha "$M/home/sgxfive-test-rgn4")"
grep -q 'STOP: premise: control zi-ctl-e680-1024x768 has no reading of tri' "$M/log/zi.log" && ok "  sessioncheck premise names the control and the key" || bad "  premise text"
prep model mini xf 1 2 3
stopcase "less than the free space before the second job stops the stage" 22 xf FAKE_DF_FROM=3
prep model mini xf 1
stopcase "less than 200 MB free at the preflight stops before any job" 22 xf FAKE_DF_KB=1000
prep model mini zd 1 99
stopcase "a 4096 x 4096 depth row needs 204800 + 8 x 16400 KiB: 300000 KiB free stops before it" 22 zd FAKE_DF_KB=300000
prep model mini xf 1; echo "0x90100 0x10000016 0x480 0x20000000" > "$M/fake/state"
stopcase "a fault latched before the first job that a reset does not clear stops (rc 14)" 14 xf FAKE_STUCK=1
prep model mini xf 1; stopcase "registers unreadable stop the stage" 12 xf FAKE_SNAP_FAIL=1
prep model mini xf 1 2; stopcase "a failed reset before a job stops the stage" 13 xf FAKE_RESET_FAIL_FROM=2
prep model mini xf 1; stopcase "the begin health failing after a reset and a retry stops (rc 5)" 5 xf FAKE_HEALTH_BAD=1
FAKE_TR_INIT=0x100 prep model mini xf 1; stopcase "render_tail_room not at its default at the start: preflight refuses, nothing written" 1 xf
[ ! -s "$M/fake/writes" ] && ok "  no debugfs write at all" || bad "  writes: $(writes | tr '\n' ' ')"
FAKE_SRCV=OTHERSRCV prep model mini xf 1; stopcase "a module that is not the expected build: preflight refuses" 1 xf
prep model mini xf 1; FSHA=0000 stopcase "a laptop FROZEN.sha256 that is not the Mac's is refused" 1 xf
prep model mini tx 1; rm "$M/home/scratch/r7g/stage/r7g-ty3-32x16.bin"; stopcase "a staged program missing: preflight refuses" 1 tx
prep model mini zf 195; cp "$M/home/sgxfive-test-rgn4" "$M/home/scratch/r7g/bin/sgxfive-test"
stopcase "a t6 binary that is not round 6's build: zf (t6 rows) refuses at the preflight" 1 zf
prep model mini xf 1; printf 'q-x|heldout|safe|expectdiff|t4|fill --width 64 --height 32\n' >> "$M/home/scratch/r7g/run/tables/xf.txt"
stopcase "a table changed on the laptop is refused (not the frozen one)" 1 xf

# ---- 3. the staged runner under env -i -----------------------------------------------------------------------------------------
prep model mini xf 1
"$PY" "$P/score/sessioncheck.py" envi $(for kv in $(envw); do printf -- '--set %s ' "$kv"; done) --set PATH="$P/tests/shims:$(dirname "$PY"):/usr/bin:/bin" \
	--set G_TOOL_SHA=$S4 --set G_TOOL6_SHA=$S6 --set G_SRCV_EXPECT=MOCKSRCV --set PY=$PY --set RESET_WAIT=0 --set HEALTH_WAIT=0 --set TEE_GRACE=30 \
	-- bash "$M/home/scratch/r7g/run/run/run_stage.sh" xf "$(sha "$C/FROZEN.sha256")" envi > "$W/envi.out" 2>&1 \
	&& ok "sessioncheck envi: the staged runner runs xf under env -i (no command not found, no missing file)" || { bad "envi"; tail -5 "$W/envi.out"; }
prep model mini zi 2
"$PY" "$P/score/sessioncheck.py" envi $(for kv in $(envw); do printf -- '--set %s ' "$kv"; done) --set PATH="$P/tests/shims:$(dirname "$PY"):/usr/bin:/bin" \
	--set G_TOOL_SHA=$S4 --set G_TOOL6_SHA=$S6 --set G_SRCV_EXPECT=MOCKSRCV --set PY=$PY --set RESET_WAIT=0 --set HEALTH_WAIT=0 --set TEE_GRACE=30 \
	-- bash "$M/home/scratch/r7g/run/run/run_stage.sh" zi "$(sha "$C/FROZEN.sha256")" envi > "$W/envi2.out" 2>&1 \
	&& ok "sessioncheck envi: a control's premise check (python3 sessioncheck.py, staged) runs under env -i" || { bad "envi premise"; tail -5 "$W/envi2.out"; }

# ---- 4. the freeze ------------------------------------------------------------------------------------------------------------
world model; ttree
(cd "$C" && run/freeze_g.sh verify > /dev/null 2>&1) && ok "freeze: the copy verifies" || bad "the copy does not verify"
(cd "$C" && echo "#" >> tables/zs.txt && run/freeze_g.sh verify > /dev/null 2>&1) && bad "a changed table verified" || ok "freeze: a changed table fails verify"
(cd "$C" && cp "$P/tables/zs.txt" tables/zs.txt && : > bins/extra.bin && run/freeze_g.sh verify > /dev/null 2>&1) && bad "a new program verified" || ok "freeze: a program added since fails verify"
(cd "$C" && rm bins/extra.bin && printf 'x' >> bin/t6/sgxfive-test && run/freeze_g.sh verify > /dev/null 2>&1) && bad "a changed t6 verified" || ok "freeze: a changed t6 binary fails verify"

# ---- 5. the guard -------------------------------------------------------------------------------------------------------------
"$P/run/guard_g.sh" > /dev/null && ok "guard: the session is clean" || bad "guard: the session is not clean"
inject() { local nm=$1 f=$2 line=$3; local G=$W/g$RANDOM$RANDOM; mkdir -p "$G"; cp -R "$P/run" "$P/tables" "$G/"
	printf '%s\n' "$line" >> "$G/$f"
	"$P/run/guard_g.sh" "$G" > /dev/null 2>&1 && bad "guard missed: $nm" || ok "guard catches: $nm"; }
inject "a /tmp work file" run/run_stage.sh 'echo x > /tmp/r7g.out'
inject "a knob write" run/run_stage.sh 'dbg_write bif_flush 1'
inject "a delete outside drop_work" run/lib_g.sh 'rm -rf "$KEEP"'
inject "a wait loop" run/run_stage.sh 'while true; do sleep 1; done'
inject "a timeout without -k" run/lib_g.sh 'sudo -n timeout 20 "$T4" fill'
inject "an unprivileged debugfs read" run/lib_g.sh 'cat "$D/regs"'
inject "an unbounded ssh in the driver" run/g.sh 'ssh $SSHO "$T" true'
inject "a kreg in a table" tables/zd.txt 'x|heldout|safe|expectdiff|t4|tri --kreg 0x0c00=1'
inject "a --poke outside the two forms" tables/xf.txt "x|heldout|safe|expectdiff|t4|fill --poke 'xfer:3=0x1'"
inject "a kpoke-render" tables/zd.txt 'x|heldout|safe|expectdiff|t4|tri --kpoke-render 1:rd:1=0x0'
inject "a third tool" tables/xf.txt 'x|heldout|safe|expectdiff|t7|fill'
inject "a program not from \$S" tables/tx.txt 'x|heldout|safe|after|t4|probe --temps 32 /home/x/other.bin'
inject "a reboot" run/lib_g.sh 'sudo -n reboot'

# ---- 6. dry runs ---------------------------------------------------------------------------------------------------------------
world model; ttree
out=$(env $(envw) SGX_DRY_RUN=1 bash "$C/run/stage_g.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q "scratch/r7g/bin/sgxfive-test" && echo "$out" | grep -q "mkdir -p scratch/r7g/run/run" && ok "stage_g.sh dry run: the commands, every path under ~/scratch/r7g" || bad "stage dry run: rc $rc"
out=$(env $(envw) SGX_DRY_RUN=1 bash "$C/run/g.sh" 2>&1); rc=$?
[ $rc = 0 ] && [ "$(echo "$out" | grep -c "run_stage.sh [a-z]* [0-9a-f]* [0-9-]*'")" = 6 ] && ok "g.sh dry run: six stages, each with the FROZEN hash" || bad "g.sh dry run: rc $rc"

[ $fail = 0 ] && echo "run_mock: ALL PASS" || echo "run_mock: FAILURES"
exit $fail
