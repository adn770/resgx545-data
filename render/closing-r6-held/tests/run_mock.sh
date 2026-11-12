#!/bin/bash
# tests/run_mock.sh: part H's runner and driver end to end against the ARGV-DRIVEN fake tool (tests/worlds.py) and a fake debugfs
# whose directory is mode 000 (only the sudo shim reaches it).  From r6-render4x's run_mock.sh.  Every world runs THE STAGED TREE: the
# driver stages a frozen copy of this directory (h.env's two pins set to the fake tool's sha256 and MOCKSRCV, refrozen; nothing else
# differs) through the fake scp into the fake home, and the fake ssh runs the staged runner with `env -i`, HOME the fake home and a
# PATH of the laptop's commands only (tests/shims and an allow-list of coreutils: no python, no perl, no Mac path); every log of every
# world is then searched for "command not found" (a function or a command the runner calls that the laptop does not have).
#   1. worlds of the whole driver: model (H-LIST, H-PEND), flushclears (H-FLUSH), word (H-WORD), replay2, noreplay (a0's control
#      fails: the K2 rows cannot tell), nofault, fillfault, and the stops m110 (rc 22), replay3 (rc 17), othershape (rc 18), gatebad
#      (rc 23 in s0), flushrefused (rc 23 after b0);
#   2. the laptop files: everything under ~/scratch/r6h and one mktemp directory under ~/scratch/tmp, removed; free space (rc 21);
#   3. no timing window on the fake's start-up (a fake 3 s late, HOLD_READ 0.2 s);
#   4. the runner's preflight and knobs (missing peek / bif_flush / render_tail_room, render_tail_room not 0, a peek of another
#      offset, srcversion, tool), the debugfs writes (reset, render_rgn_arrays, hold_recovery, bif_flush only);
#   5. the scorer reads only files the runner kept (SCORE_READLOG over the model world's verdict);
#   6. the guard (injections into copies of the tree);  7. the driver's dry run.
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
FAKE_SHA=$(sha "$P/tests/fake_tool.sh")

# the laptop's commands: the shims and an allow-list (no python, no perl: the fake tool's python is the mock's plumbing, FAKE_PY)
LBIN=$W/lbin; mkdir -p "$LBIN"
for c in bash sh cat awk grep sed gzip mkfifo mktemp tee mkdir date uname seq sleep wc tr cut head tail kill ls env rm dirname basename shasum test; do
	ln -s "$(type -P "$c")" "$LBIN/$c" || { echo "no $c on this Mac"; exit 1; }
done
for c in sudo timeout df modinfo sha256sum; do ln -s "$P/tests/shims/$c" "$LBIN/$c"; done
# shasum is a perl script: it finds /usr/bin/perl by its own first line, the runner never calls perl (guard_h.sh)
export FAKE_LAPTOP_PATH=$LBIN FAKE_PY=$PY FAKE_P=$P/tests

# a frozen copy of the tree, the fake's pins in h.env
TREE=$W/tree; mkdir -p "$TREE"
( cd "$P" && cp -R gen score run tables predictions tests private stages.txt TABLES.md TOOL.sha256 TOOLSRC.sha256 "$TREE/" )
rm -rf "$TREE/private/o3/__pycache__" "$TREE/tests/__pycache__" "$TREE/score/__pycache__" "$TREE/gen/__pycache__"
sed -i '' -e "s/^TOOL_SHA=.*/TOOL_SHA=$FAKE_SHA/" -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=MOCKSRCV/" "$TREE/run/h.env"
printf '%s  /home/jtorra/sgxfive-test-rgn4\n' "$FAKE_SHA" > "$TREE/TOOL.sha256"
( cd "$TREE" && run/freeze_h.sh freeze > /dev/null ) || { echo "FAIL: the tree copy does not freeze"; exit 1; }
[ "$(diff -r "$P/run" "$TREE/run" | grep -c '^[<>]')" = 4 ] && ok "the mock's tree differs from this one only in h.env's two pins" || bad "the mock tree differs more: $(diff -r "$P/run" "$TREE/run" | head -5)"

mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export PATH="$P/tests/shims:$PATH" RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS= PY
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=0.2 HOLD_GAP=0.1 TEE_GRACE=3

N=0
world() { # world WORLD: a fresh fake laptop
	N=$((N + 1)); M=$W/w$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home" "$M/tmpdir"
	for f in reset regs hold_recovery peek bif_flush; do : > "$M/dbgreal/$f"; done
	echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"; echo 0 > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_ROOM_INIT:-0}" > "$M/dbgreal/render_tail_room"
	echo N > "$M/fake/hold"; echo idle > "$M/fake/state"; echo 1 > "$M/fake/list"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${FAKE_DF_INIT:-}" ] && echo "$FAKE_DF_INIT" > "$M/fake/df_kb"
	chmod 000 "$M/dbg"
	cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"
	FAKE_WORLD=$1
}
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log FAKE_HOME=$M/home TMPDIR=$M/tmpdir"; }
leftover() { ls -A "$M/home/scratch/tmp" 2>/dev/null; ls -A "$M/tmpdir" 2>/dev/null; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
drive() { # drive WORLD [ENV...]: stage and run the whole driver on a fresh laptop in a fresh copy of the frozen tree
	local wn=$1; shift
	world "$wn"; D2T=$W/drv$N; cp -R "$TREE" "$D2T"
	env $(envw) "$@" bash "$D2T/run/stage_h.sh" > "$M/log/stage.log" 2>&1 || bad "staging for world $wn: $(tail -n 2 "$M/log/stage.log")"
	OUT=$(env $(envw) "$@" K_ATT=full bash "$D2T/run/h.sh" 2>&1); RC=$?
	echo "$OUT" > "$M/log/driver.log"
	VERDICT=$(SCORE_READLOG=$M/readlog "$PY" -B "$D2T/score/score_h.py" verdict "$D2T/out/full" 2>&1)
	OA=$M/home/scratch/r6h/out/full
}
runst() { # runst STAGE [ENV...]: the staged runner alone (stage_h.sh first), rc printed
	local st=$1; shift
	D2T=$W/drv$N; [ -d "$D2T" ] || cp -R "$TREE" "$D2T"
	env $(envw) bash "$D2T/run/stage_h.sh" > "$M/log/stage.log" 2>&1 || { echo stagefail; return; }
	env $(envw) "$@" ssh -o x u@fake "bash ~/scratch/r6h/run/run/run_h.sh $st $(sha "$D2T/FROZEN.sha256") att$N" > "$M/log/$st.log" 2>&1; echo $?
}
KD() { echo "$M/home/scratch/r6h/out/att$N/$1"; }
has() { echo "$VERDICT" | grep -qF "$1"; }

# ---- 1. worlds of the whole driver -----------------------------------------------------------------------------------------------
drive model
[ $RC = 0 ] && echo "$OUT" | grep -q '^r6-held part H done' && [ "$(echo "$OUT" | grep -c '^stage [a-z0-9]* done, health ok')" = 2 ] \
	&& ok "world model: the driver stages and runs s0 and q, health ok after each (rc 0)" || { bad "world model: rc $RC"; echo "$OUT" | tail -6 | sed 's/^/     /'; }
has "SUMMARY: s0: controls all PASS (4)" && ok "  s0's four controls pass (bif_flush refused, BIF_CTRL unchanged, peek format, health triangle)" || bad "  s0: $VERDICT"
has "H-LIST consistent (2 held, 0 FAILED" && has "H-WORD REFUTED (0 held, 2 FAILED" && ok "  H-LIST consistent 2 of 2 (a1, a2), H-WORD refuted" || bad "  list rows: $VERDICT"
has "H-PEND consistent" && has "H-FLUSH REFUTED (0 held, 3 FAILED" && ok "  H-PEND consistent, H-FLUSH refuted 3 of 3" || bad "  flush rows: $VERDICT"
has "Q003 list (q): H-LIST: the replay goes through the directory list current at the next TA run (" && has "q controls: 40 PASS, 0 FAIL, 0 NODATA" \
	&& ok "  the list headline decides; no control FAIL or NODATA" || bad "  headline: $(echo "$VERDICT" | grep -E 'list|controls')"
wr=$(writes | awk '{print $1}' | sort -u | tr '\n' ' ')
[ "$wr" = "bif_flush hold reset rgn " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs writes: reset, render_rgn_arrays, hold_recovery, bif_flush" || bad "  writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
[ "$(writes | grep -c '^bif_flush 1$')" = 4 ] && [ "$(writes | grep -c '^bif_flush')" = 4 ] && ok "  bif_flush written 4 times, always 1 (n0 and b0, b1, b2)" || bad "  bif_flush writes: $(writes | grep -c '^bif_flush')"
[ "$(writes | grep -c '^hold Y')" = 6 ] && ok "  hold_recovery Y six times (the six cells)" || bad "  hold Y: $(writes | grep -c '^hold Y')"
[ "$(cat "$M/dbgreal/render_rgn_arrays")" = 0 ] && [ "$(cat "$M/fake/hold")" = N ] && ok "  at the end render_rgn_arrays 0, hold_recovery N" || bad "  knobs at the end"
ls "$OA/q" | grep -q '^b0-640-flush-health.flush.txt.gz$' && ls "$OA/q" | grep -q '^a1-640-fill.t1.dmesg.gz$' && ls "$OA/q" | grep -q '^a1-640-fill.peek1.txt.gz$' \
	&& ok "  kept: the flush record, the steps' slices, the peek reads (under ~/scratch/r6h/out)" || bad "  kept files: $(ls "$OA/q" | head)"
[ -z "$(leftover)" ] && ok "  laptop files: nothing left in ~/scratch/tmp or \$TMPDIR" || bad "  left over: $(leftover | tr '\n' ' ')"
[ -z "$(ls -A "$M/home" | grep -v '^scratch$' | grep -v '^sgxfive-test-rgn4$')" ] && [ -d "$M/home/scratch/r6h/run/run" ] && [ -d "$M/home/scratch/r6h/out" ] \
	&& ok "  the fake home holds only ~/scratch (r6h/{run,out}, tmp) and the tool" || bad "  home: $(ls -A "$M/home" | tr '\n' ' ')"
grep -q "## work directory: $M/home/scratch/tmp/r6h\." "$OA/q/runner.log" && ok "  the work directory was ~/scratch/tmp/r6h.XXXXXX" || bad "  work directory line"
miss=$(grep -c '^MISSING' "$M/readlog"); nread=$(grep -c . "$M/readlog")
[ "$miss" = 0 ] && [ "$nread" -gt 50 ] && ok "  the scorer read $nread files, every one kept by the runner (no MISSING)" || bad "  scorer reads: $miss missing of $nread: $(grep MISSING "$M/readlog" | head -3)"

drive flushclears
has "H-FLUSH consistent (3 held, 0 FAILED" && has "H-PEND REFUTED" && has "Q003 flush (q): H-FLUSH: a BIF invalidate" && [ $RC = 0 ] \
	&& ok "world flushclears: H-FLUSH consistent 3 of 3, H-PEND refuted, the flush headline decides" || { bad "world flushclears: rc $RC"; echo "$VERDICT" | sed 's/^/     /'; }
drive word
has "H-WORD consistent" && has "H-LIST REFUTED" && ok "world word: H-WORD consistent, H-LIST refuted" || bad "world word: $VERDICT"
drive replay2
[ $RC = 15 ] && echo "$OUT" | grep -q '15 fault-class events of the stage (15 is the limit) with rows left: stop after a2-288-fill' && has "H-LIST consistent (2 held" \
	&& ok "world replay2: two replays in every cell exceed the budget (6 held + 6 + 3): the stage stops after a2 with b2 left (rc 15); a1, a2 still decide H-LIST" || { bad "world replay2: rc $RC"; echo "$OUT" | grep STOP; }
drive noreplay
[ $RC = 0 ] && has "a0:replay" || true
echo "$VERDICT" | grep -q 'Q003 flush (q): controls FAILED: a0:replay: FAILED' && echo "$VERDICT" | grep -q "Q003 list (q): cannot tell" \
	&& ok "world noreplay: a0's replay control FAILS and shuts the flush rows; nothing decides the list" || bad "world noreplay: $VERDICT"
drive nofault
[ $RC = 0 ] && echo "$VERDICT" | grep -q 'controls FAILED\|cannot tell' && ok "world nofault: no held job faults, the stage ends, nothing is decided" || bad "world nofault: rc $RC $VERDICT"
drive fillfault
[ $RC = 0 ] && grep -q 'a1-640-fill.fill	q.*	fault	step' "$OA/q/cases.tsv" && echo "$VERDICT" | grep -q 'a1-640-fill:fill_class:H-FILL' \
	&& ok "world fillfault: a fill faulting with the job's page is measured; the H-FILL control FAILS" || { bad "world fillfault: rc $RC"; echo "$OUT" | grep STOP; }
drive m110
[ $RC = 22 ] && echo "$OUT" | grep -q 'a -110 in two cells in a row' && [ "$(grep -c '^[ab][0-9]-[^.]*	' "$D2T/out/full/q/cases.tsv")" = 2 ] \
	&& ok "world m110: two cells in a row with a -110 stop the stage after the second (rc 22)" || { bad "world m110: rc $RC"; echo "$OUT" | grep STOP; }
drive replay3
[ $RC = 17 ] && echo "$OUT" | grep -q 'the third triangle failed after a0-640-health' && [ "$(cat "$M/dbgreal/render_rgn_arrays")" = 0 ] && [ "$(cat "$M/fake/hold")" = N ] \
	&& ok "world replay3: a cell's third failing triangle stops (rc 17), knobs restored" || { bad "world replay3: rc $RC"; echo "$OUT" | grep STOP; }
drive othershape
[ $RC = 18 ] && echo "$OUT" | grep -q 'faulted with another shape' && ok "world othershape: a replay at another page stops (rc 18)" || { bad "world othershape: rc $RC"; echo "$OUT" | grep STOP; }
drive gatebad
[ $RC = 23 ] && ! [ -d "$D2T/out/full/q" ] && ok "world gatebad: bif_flush taken with nothing held stops s0 (rc 23); q never runs" || { bad "world gatebad: rc $RC"; echo "$OUT" | tail -3; }
drive flushrefused
[ $RC = 23 ] && echo "$OUT" | grep -q 'bif_flush was refused with b0-640-flush-health held' && ! grep -q '^a1-' "$D2T/out/full/q/cases.tsv" \
	&& ok "world flushrefused: a refused held flush ends the stage after b0's cell and health (rc 23)" || { bad "world flushrefused: rc $RC"; echo "$OUT" | grep STOP; }
nf=$(grep -lE 'command not found|: not found' "$W"/w*/log/* "$W"/w*/home/scratch/r6h/out/*/*/runner.log 2>/dev/null | head -3)
[ -z "$nf" ] && ok "no world's log has 'command not found' (every function and command the staged runner calls exists on the laptop PATH)" || bad "command not found in: $nf"

# ---- 2/3/4. the runner alone ----------------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##|not' "$M/log/$st.log" | head -4 | sed 's/^/     /'; }; }
FAKE_DF_INIT=200000 world model; stopcase "preflight: 195 MiB free on ~ stops before anything is touched" 21 s0
[ ! -f "$M/fake/resets" ] && [ -z "$(leftover)" ] && ok "  nothing touched, no work directory left" || bad "  touched or left: $(leftover)"
world model; rc=$(runst q FAKE_SLOW_START=3)
[ "$rc" = 0 ] && [ "$(awk -F'\t' '$10 == "held" && $9 == "fault" && $11 == 4' "$(KD q)/cases.tsv" | grep -c .)" = 6 ] \
	&& ok "a fake that answers 3 s late with HOLD_READ 0.2 s: all six held cells read their fault at snap 1 (no start-up timing)" || { bad "slow fake: rc $rc"; grep -E 'STOP|class' "$M/log/q.log" | head -5; }
for f in peek bif_flush render_tail_room; do
	world model; mv "$M/dbgreal/$f" "$M/dbgreal/$f.gone"
	stopcase "preflight: no debugfs $f (not the r6-kernel build)" 1 s0
done
FAKE_ROOM_INIT=0x4000 world model; stopcase "preflight: render_tail_room not 0" 1 s0
world model; stopcase "preflight: peek prints another offset" 1 s0 FAKE_PEEK='reg 0x0690 0x00000000'
world model; echo OTHERSRCV > "$M/srcv"; stopcase "preflight: the loaded module is not the installed one" 1 s0
world model; rc=$(runst s0 FAKE_HEALTH_ONLY=1 >/dev/null; echo x)
cp "$P/tests/shims/df" "$M/home/sgxfive-test-rgn4"
env $(envw) ssh -o x u@fake "bash ~/scratch/r6h/run/run/run_h.sh s0 $(sha "$D2T/FROZEN.sha256") att${N}b" > "$M/log/tool.log" 2>&1; rc=$?
[ $rc = 1 ] && grep -q 'the tool is not the rgn4 build' "$M/log/tool.log" && ok "preflight: a tool changed after staging is refused (rc 1)" || bad "tool after staging: rc $rc"
world model; cp "$P/tests/shims/df" "$M/home/sgxfive-test-rgn4"; D2T=$W/drv$N; cp -R "$TREE" "$D2T"
env $(envw) bash "$D2T/run/stage_h.sh" > "$M/log/stage.log" 2>&1; rc=$?
[ $rc = 1 ] && grep -q "STAGING FAILED: the laptop's tool is not the rgn4 build" "$M/log/stage.log" && ok "staging: another tool on the laptop is refused" || bad "staging with another tool: rc $rc"
world model; stopcase "a held job that does not read back hold Y" 9 q FAKE_HOLD_NOY=1
world model; stopcase "render_rgn_arrays does not read back 1" 19 q FAKE_RGN_STUCK=1
world model; stopcase "registers unreadable" 12 s0 FAKE_SNAP_FAIL=1
world model; stopcase "a reset that leaves the held fault latched twice" 10 q FAKE_STUCK=1
grep -q "^SRCV_EXPECT=41E2F5C756F96D20F7109A4$" "$P/run/h.env" && grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/h.env" \
	&& ok "h.env pins the new module 41E2F5C756F96D20F7109A4 and ~/sgxfive-test-rgn4 e6951558..." || bad "h.env pins"

# ---- 6. the guard ------------------------------------------------------------------------------------------------------------------
"$P/run/guard_h.sh" "$P" > /dev/null && ok "guard: this tree is clean" || bad "guard: this tree is not clean"
inject() { local nm=$1 f=$2 expr=$3; local C=$W/g$RANDOM; cp -R "$P/run" "$P/tables" "$W/" 2>/dev/null; mkdir -p "$C"; cp -R "$P/run" "$P/tables" "$C/"
	sed -i '' -e "$expr" "$C/$f"
	if "$C/run/guard_h.sh" "$C" > "$C/out" 2>&1; then bad "guard misses: $nm"; else ok "guard refuses: $nm"; fi; }
inject "a /tmp path" run/lib_h.sh 's#mkdir -p "$HOME/scratch/tmp"#mkdir -p /tmp/x#'
inject "a timeout without -k" run/lib_h.sh 's#sudo -n timeout -k 5 20 cat "$D/$1"#sudo -n timeout 20 cat "$D/$1"#'
inject "a write to peek" run/lib_h.sh 's#"bif_flush 1") ;;#"bif_flush 1"|"peek 0x0690") ;;#'
inject "a third flush_write" run/run_h.sh 's@^		peek "$name" 3$@&; flush_write "$JW/x"@'
inject "an unprivileged debugfs read" run/lib_h.sh 's#sudo -n timeout -k 5 20 cat "$D/peek"#cat "$D/peek"#'
inject "a wait loop" run/run_h.sh 's#^begin$#begin; while false; do :; done#'
inject "an --aa4 row" tables/q.txt 's#--keep-going --wait-ms#--keep-going --aa4 --wait-ms#'
inject "a kpoke in a table" tables/q.txt 's#--poke cmd:1=#--kpoke-render 2:par:11=0x1 --poke cmd:1=#'
inject "an unbounded ssh" run/h.sh 's#bounded 60 ssh $SSHO#ssh $SSHO#'

# ---- 7. dry run -----------------------------------------------------------------------------------------------------------------
world model; D2T=$W/drv$N; cp -R "$TREE" "$D2T"
out=$(env $(envw) SGX_DRY_RUN=1 bash "$D2T/run/h.sh" 2>&1)
echo "$out" | grep -q "bash ~/scratch/r6h/run/run/run_h.sh s0 " && echo "$out" | grep -q "score_h.py gate q" && [ ! -d "$D2T/out" ] \
	&& ok "the driver's dry run prints the stage commands and the gate, and writes nothing" || bad "dry run: $out"

echo "mock: $( [ $fail = 0 ] && echo PASS || echo "FAILED (kept: $W)" )"
# a passing mock leaves nothing behind (the fake laptops are under debug/, a mktemp directory of this run only)
[ $fail = 0 ] && case "$W" in "$P"/debug/runmock.??????) rm -rf -- "$W" ;; esac
exit $fail
