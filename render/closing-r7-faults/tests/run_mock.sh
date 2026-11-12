#!/bin/bash
# tests/run_mock.sh: the runner and driver end to end against the ARGV-DRIVEN fake tool (tests/worlds.py) and a fake debugfs whose
# directory is mode 000 (only the sudo shim reaches it).  From r6-held's run_mock.sh.  Every world runs THE STAGED TREE: the driver
# stages a frozen copy of this directory (f.env's two pins set to the fake tool's sha256 and MOCKSRCV, refrozen; nothing else
# differs) through the fake scp into the fake home, and the fake ssh runs the staged runner with `env -i`, HOME the fake home and a
# PATH of the laptop's commands only (tests/shims and an allow-list of coreutils: no python, no perl, no Mac path); every log of every
# world is then searched for "command not found".
#   1. worlds of the whole driver: model (R-PAGE, H-SELF; the budget of 16 ends the session in m, rc 25), clr + reflag, time +
#      recount, size, and the stops dead (rc 26), ctl640 (d stops on its control, m runs), word (the word stop, rc 24 in d and m),
#      replay3 (rc 17), kregrefuse (s0's gate row fails: l, d, m skipped), nofault, a ledger left at 15 (rc 25 after the first -110);
#   2. the laptop files: everything under ~/scratch/r7f and one mktemp directory under ~/scratch/tmp, removed; free space (rc 21);
#   3. no timing window on the fake's start-up (a fake 3 s late, HOLD_READ 0.2 s);
#   4. the runner's preflight and knobs, the debugfs writes (reset, render_rgn_arrays, hold_recovery, kregnow 0x0c00^=0x10 only);
#   5. the scorer reads only files the runner kept (SCORE_READLOG) and score/sessioncheck.py kept passes on every stage of a world;
#      score/sessioncheck.py staged on the staged runner files, and envi on the staged runner;
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
export FAKE_LAPTOP_PATH=$LBIN FAKE_PY=$PY FAKE_P=$P/tests

# a frozen copy of the tree, the fake's pins in f.env
TREE=$W/tree; mkdir -p "$TREE"
( cd "$P" && cp -R gen score run tables predictions tests bins stages.txt TABLES.md TOOL.sha256 TOOLSRC.sha256 "$TREE/" )
rm -rf "$TREE/tests/__pycache__" "$TREE/score/__pycache__" "$TREE/gen/__pycache__"
sed -i '' -e "s/^TOOL_SHA=.*/TOOL_SHA=$FAKE_SHA/" -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=MOCKSRCV/" "$TREE/run/f.env"
printf '%s  /home/jtorra/sgxfive-test-rgn4\n' "$FAKE_SHA" > "$TREE/TOOL.sha256"
( cd "$TREE" && run/freeze_f.sh freeze > /dev/null ) || { echo "FAIL: the tree copy does not freeze"; exit 1; }
[ "$(diff -r "$P/run" "$TREE/run" | grep -c '^[<>]')" = 4 ] && ok "the mock's tree differs from this one only in f.env's two pins" || bad "the mock tree differs more: $(diff -r "$P/run" "$TREE/run" | head -5)"

mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export PATH="$P/tests/shims:$PATH" RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS= PY
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=0.2 HOLD_GAP=0.1 LONG_EXTRA=1.5 FAKE_LONG_S=1.2 TEE_GRACE=3

N=0
world() { # world WORLD [LOCK]: a fresh fake laptop
	local f
	N=$((N + 1)); M=$W/w$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home" "$M/tmpdir"
	for f in reset regs hold_recovery peek bif_flush kregnow; do : > "$M/dbgreal/$f"; done
	echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"; echo 0 > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_ROOM_INIT:-0}" > "$M/dbgreal/render_tail_room"
	echo N > "$M/fake/hold"; echo idle > "$M/fake/state"; echo 1 > "$M/fake/list"; echo 0 > "$M/fake/bifctrl"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${FAKE_DF_INIT:-}" ] && echo "$FAKE_DF_INIT" > "$M/fake/df_kb"
	chmod 000 "$M/dbg"
	cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"
	FAKE_WORLD=$1; FAKE_LOCK=${2:-self}
}
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD FAKE_LOCK=$FAKE_LOCK KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log FAKE_HOME=$M/home TMPDIR=$M/tmpdir"; }
leftover() { ls -A "$M/home/scratch/tmp" 2>/dev/null; ls -A "$M/tmpdir" 2>/dev/null; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
drive() { # drive WORLD LOCK [ENV...]: stage and run the whole driver on a fresh laptop in a fresh copy of the frozen tree
	local wn=$1 lk=$2; shift 2
	world "$wn" "$lk"; D2T=$W/drv$N; cp -R "$TREE" "$D2T"
	[ -n "${LEDGER_INIT:-}" ] && { mkdir -p "$M/home/scratch/r7f/run"; printf 'old d x %s\n' "$LEDGER_INIT" > "$M/home/scratch/r7f/run/minus110.ledger"; }
	env $(envw) "$@" bash "$D2T/run/stage_f.sh" > "$M/log/stage.log" 2>&1 || bad "staging for world $wn: $(tail -n 2 "$M/log/stage.log")"
	OUT=$(env $(envw) "$@" K_ATT=full bash "$D2T/run/f.sh" 2>&1); RC=$?
	echo "$OUT" > "$M/log/driver.log"
	VERDICT=$(SCORE_READLOG=$M/readlog "$PY" -B "$D2T/score/score_f.py" verdict "$D2T/out/full" 2>&1)
	echo "$VERDICT" > "$M/log/verdict.log"
	OA=$M/home/scratch/r7f/out/full
	OM=$D2T/out/full
}
runst() { # runst STAGE [ENV...]: the staged runner alone (stage_f.sh first), rc printed
	local st=$1; shift
	D2T=$W/drv$N; [ -d "$D2T" ] || cp -R "$TREE" "$D2T"
	env $(envw) bash "$D2T/run/stage_f.sh" > "$M/log/stage.log" 2>&1 || { echo stagefail; return; }
	env $(envw) "$@" ssh -o x u@fake "bash ~/scratch/r7f/stage/run/run_f.sh $st $(sha "$D2T/FROZEN.sha256") att$N" > "$M/log/$st.log" 2>&1; echo $?
}
KD() { echo "$M/home/scratch/r7f/out/att$N/$1"; }
has() { echo "$VERDICT" | grep -qF "$1"; }
showv() { echo "$VERDICT" | grep -E 'SUMMARY' | sed 's/^/     /'; echo "$OUT" | grep -E 'STOP|SKIPPED|done' | head -5 | sed 's/^/     /'; }

# ---- 1. worlds of the whole driver -----------------------------------------------------------------------------------------------
drive model self
[ $RC = 25 ] && echo "$OUT" | grep -q "budget of timed-out boots is reached in m" && [ "$(echo "$OUT" | grep -c '^stage [a-z0-9]* done, health ok')" = 4 ] \
	&& ok "world model: s0, l, d run; R-PAGE's boots (two a timing-out cell) reach the budget of 16 in m, after its cell's health (rc 25)" || { bad "world model: rc $RC"; showv; }
has "SUMMARY: s0: controls all PASS (5)" && ok "  s0's five controls pass (kregnow set and back at idle, the health triangle)" || { bad "  s0"; showv; }
has "H-SELF consistent (4 held, 0 FAILED" && has "H-REFLAG REFUTED" && has "H-RECOUNT REFUTED" && has "L-REP consistent (2 held" \
	&& ok "  l: H-SELF consistent 4 of 4, H-REFLAG and H-RECOUNT refuted, l4 replicates E088's hang after one quad" || { bad "  l"; showv; }
has "H-PAGE consistent (10 held, 0 FAILED" && has "H-SIZE REFUTED" && has "Q003 page (d): H-PAGE: the boot after" \
	&& ok "  d: H-PAGE consistent 10 of 10 (boot_held and boot_replay1 of five cells), H-SIZE refuted; the page headline decides" || { bad "  d"; showv; }
has "H-NULL consistent (2 held" && has "H-CLR REFUTED (0 held, 1 FAILED" && has "H-TIME REFUTED (0 held, 1 FAILED" \
	&& ok "  m: the three cells before the budget (m0a, m1a, m2a) decide H-NULL over H-CLR and H-TIME, gated by m0a alone" || { bad "  m"; showv; }
[ "$(awk '{ n += $4 } END { print n }' "$M/home/scratch/r7f/run/minus110.ledger")" = 16 ] && ok "  the ledger holds 16 timed-out boots (d 10, m 6)" || bad "  ledger: $(cat "$M/home/scratch/r7f/run/minus110.ledger")"
wr=$(writes | awk '{print $1}' | sort -u | tr '\n' ' ')
[ "$wr" = "hold kregnow reset rgn " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs writes: reset, render_rgn_arrays, hold_recovery, kregnow" || bad "  writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
[ "$(writes | grep -c '^kregnow 0x0c00^=0x10$')" = 4 ] && [ "$(writes | grep -c '^kregnow')" = 4 ] && ok "  kregnow written 4 times, always 0x0c00^=0x10 (n0's pair, m1a's pair)" || bad "  kregnow writes: $(writes | grep '^kregnow' | sort | uniq -c)"
[ "$(writes | grep -c '^hold Y')" = 10 ] && ok "  hold_recovery Y ten times (seven d cells, three m cells)" || bad "  hold Y: $(writes | grep -c '^hold Y')"
[ "$(cat "$M/dbgreal/render_rgn_arrays")" = 0 ] && [ "$(cat "$M/fake/hold")" = N ] && [ "$(cat "$M/fake/bifctrl")" = 0 ] && ok "  at the end render_rgn_arrays 0, hold_recovery N, BIF_CTRL 0" || bad "  knobs at the end"
ls "$OA/d" | grep -q '^d1-288x144.t1.regs.gz$' && ls "$OA/d" | grep -q '^d1-288x144.row.dmesg.gz$' && ls "$OA/m" | grep -q '^m1a-clr.kw.txt.gz$' && ls "$OA/l" | grep -q '^l2-lock-lock-rel-rel.txt.gz$' \
	&& ok "  kept: the steps' regs, the row slices, the kregnow statuses, the probe outputs (under ~/scratch/r7f/out)" || bad "  kept files: $(ls "$OA/d" | head)"
[ -z "$(leftover)" ] && ok "  laptop files: nothing left in ~/scratch/tmp or \$TMPDIR" || bad "  left over: $(leftover | tr '\n' ' ')"
[ -z "$(ls -A "$M/home" | grep -v '^scratch$' | grep -v '^sgxfive-test-rgn4$')" ] && [ "$(ls "$M/home/scratch/r7f" | tr '\n' ' ')" = "out run stage " ] \
	&& ok "  the fake home holds only ~/scratch (r7f/{out,run,stage}, tmp) and the tool" || bad "  home: $(ls -A "$M/home" | tr '\n' ' ') / $(ls "$M/home/scratch/r7f")"
grep -q "## work directory: $M/home/scratch/tmp/r7f\." "$OA/d/runner.log" && ok "  the work directory was ~/scratch/tmp/r7f.XXXXXX" || bad "  work directory line"
miss=$(grep -c '^MISSING' "$M/readlog"); nread=$(grep -c . "$M/readlog")
[ "$miss" = 0 ] && [ "$nread" -gt 100 ] && ok "  the scorer read $nread files, every one kept by the runner (no MISSING)" || bad "  scorer reads: $miss missing of $nread: $(grep MISSING "$M/readlog" | head -3)"
kc=0; for st in s0 l d m; do "$PY" -B "$D2T/score/sessioncheck.py" kept "$D2T/score/score_f.py" "$st" "$OM/$st" --call files_for > "$M/log/kept-$st.txt" 2>&1 && kc=$((kc + 1)); done
[ $kc = 4 ] && ok "  sessioncheck kept --call files_for: every file REQUIRED names is kept, no other file read (s0 l d m)" || bad "  kept: $(cat "$M"/log/kept-*.txt | grep FAIL | head -3)"
grep -q '^ok ' "$OM/kept-d.txt" && ok "  the driver ran the kept check before scoring (kept-d.txt)" || bad "  no kept-d.txt"
grep -q 'every control has its readings' "$OM/premise-l.txt" && ok "  the premise of l passed (every control has its readings)" || bad "  premise-l"

drive clr reflag BUDGET_110=40
[ $RC = 0 ] && has "H-CLR consistent (2 held, 0 FAILED" && has "H-TIME REFUTED" && has "H-REFLAG consistent (4 held" && has "H-SELF REFUTED" \
	&& ok "world clr + reflag (budget 40): H-CLR consistent 2 of 2, H-TIME refuted; l: H-REFLAG consistent, H-SELF refuted; rc 0" || { bad "world clr: rc $RC"; showv; }
grep -q 'kregnow 0x0c00: 0x00000000 -> 0x00000010, reads 0x00000010, BIF_INT_STAT 0x00000000 BIF_FAULT 0x00000000' "$M/kmsg" \
	&& ok "  m1's kregnow line while held: the registers hidden (E826 f2's form)" || bad "  kregnow line"
drive time recount BUDGET_110=40
[ $RC = 0 ] && has "H-TIME consistent (2 held, 0 FAILED" && has "H-CLR REFUTED" && has "H-RECOUNT consistent (4 held" \
	&& ok "world time + recount (budget 40): H-TIME consistent 2 of 2, H-CLR refuted; l: H-RECOUNT consistent; rc 0" || { bad "world time: rc $RC"; showv; }
drive size self BUDGET_110=40
has "H-SIZE consistent" && has "H-PAGE REFUTED" && ok "world size: H-SIZE consistent, H-PAGE refuted" || { bad "world size"; showv; }
drive dead self
[ $RC = 26 ] && echo "$OUT" | grep -q 'two failed boots in a row' && [ ! -d "$OM/m" ] && [ "$(cat "$M/fake/hold")" = N ] && [ "$(cat "$M/dbgreal/render_rgn_arrays")" = 0 ] \
	&& ok "world dead: the second boot fails: the session stops at once (rc 26), no further reset, knobs restored, m never runs" || { bad "world dead: rc $RC"; showv; }
[ "$(grep -c 'resgx545 r7f row d2' "$M/kmsg")" = 0 ] && ok "  nothing after d1 (the first cell that times out)" || bad "  ran past d1"
drive ctl640 self BUDGET_110=40
[ $RC = 0 ] && echo "$OUT" | grep -q 'stage d stopped by its rule (rc 24)' && [ -d "$OM/m" ] && [ "$(grep -c '^d[0-9]-[^.]*	' "$OM/d/cases.tsv")" = 1 ] \
	&& ok "world ctl640: d0's held reset times out: d stops after d0's health (rc 24), m runs" || { bad "world ctl640: rc $RC"; showv; }
has "D-CTL" || true
echo "$VERDICT" | grep -q 'Q003 page (d): controls FAILED' && ok "  the page headline names the FAILED D-CTL control" || { bad "  ctl640 headline"; showv; }
drive word self BUDGET_110=40
[ $RC = 0 ] && echo "$OUT" | grep -q 'stage d stopped by its rule' && echo "$OUT" | grep -q 'stage m stopped by its rule' && grep -q 'fault status 0x90008' "$OM/d/runner.log" \
	&& ok "world word: a replay with 0x90008 stops d and m by their rule after the cell's health (rc 24 each)" || { bad "world word: rc $RC"; showv; }
drive replay3 self BUDGET_110=40
[ $RC = 17 ] && echo "$OUT" | grep -q 'the third triangle failed after d0-640x480' && [ "$(cat "$M/fake/hold")" = N ] \
	&& ok "world replay3: a cell's third failing triangle stops the session (rc 17), knobs restored" || { bad "world replay3: rc $RC"; showv; }
drive kregrefuse self
[ $RC = 0 ] && echo "$OUT" | grep -q 'skipped: l d m' && echo "$VERDICT" | grep -q 's0: controls NOT passed' \
	&& ok "world kregrefuse: s0's gate row fails (rc 24), l, d and m are skipped by the gate" || { bad "world kregrefuse: rc $RC"; showv; }
drive nofault self
[ $RC = 44 ] && echo "$OUT" | grep -q 'STOP: premise: control d0-640x480:D-CTL has no reading of boot_held' && ! [ -d "$OM/m" ] \
	&& ok "world nofault: no held job faults: d's controls have no boot to read, the premise stops the session after d (rc 44)" || { bad "world nofault: rc $RC"; showv; }
LEDGER_INIT=15 drive model self
[ $RC = 25 ] && [ "$(grep -c '^d[0-9]-[^.]*	' "$OM/d/cases.tsv")" = 2 ] && ! [ -d "$OM/m" ] \
	&& ok "a ledger left at 15 by an earlier attempt: the session ends after d1's health, its first timed-out boot (rc 25)" || { bad "ledger 15: rc $RC"; showv; }
LEDGER_INIT=16 drive model self
[ $RC = 25 ] && grep -q 'budget of 16 timed-out boots is spent: nothing runs' "$OA/s0/runner.log" && ! grep -q 'reset 1' "$M/fake/writes" 2>/dev/null \
	&& ok "a spent ledger: the preflight refuses before anything is touched (rc 25)" || { bad "ledger 16: rc $RC"; showv; }
nf=$(grep -lE 'command not found|: not found|No such file' "$W"/w*/log/* "$W"/w*/home/scratch/r7f/out/*/*/runner.log 2>/dev/null | head -3)
[ -z "$nf" ] && ok "no world's log has 'command not found' or 'No such file'" || bad "command not found in: $nf"

# ---- 2/3/4. the runner alone ----------------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##|not' "$M/log/$st.log" | head -4 | sed 's/^/     /'; }; }
FAKE_DF_INIT=200000 world model; stopcase "preflight: 195 MiB free on ~ stops before anything is touched" 21 s0
[ ! -f "$M/fake/resets" ] && [ -z "$(leftover)" ] && ok "  nothing touched, no work directory left" || bad "  touched or left: $(leftover)"
world model; rc=$(runst m FAKE_SLOW_START=3 BUDGET_110=40)
[ "$rc" = 0 ] && [ "$(awk -F'\t' '$10 == "held" && $9 == "fault" && $11 == 4' "$(KD m)/cases.tsv" | grep -c .)" = 6 ] \
	&& ok "a fake that answers 3 s late with HOLD_READ 0.2 s: all six m cells read their fault at snap 1 (no start-up timing)" || { bad "slow fake: rc $rc"; grep -E 'STOP|class' "$M/log/m.log" | head -5; }
for f in peek bif_flush kregnow render_tail_room; do
	world model; mv "$M/dbgreal/$f" "$M/dbgreal/$f.gone"
	stopcase "preflight: no debugfs $f (not the r6-kernel build)" 1 s0
done
FAKE_ROOM_INIT=0x4000 world model; stopcase "preflight: render_tail_room not 0" 1 s0
world model; stopcase "preflight: peek prints another offset" 1 s0 FAKE_PEEK='reg 0x0690 0x00000000'
world model; echo OTHERSRCV > "$M/srcv"; stopcase "preflight: the loaded module is not the installed one" 1 s0
world model; runst s0 > /dev/null
cp "$P/tests/shims/df" "$M/home/sgxfive-test-rgn4"
env $(envw) ssh -o x u@fake "bash ~/scratch/r7f/stage/run/run_f.sh s0 $(sha "$D2T/FROZEN.sha256") att${N}b" > "$M/log/tool.log" 2>&1; rc=$?
[ $rc = 1 ] && grep -q 'the tool is not the rgn4 build' "$M/log/tool.log" && ok "preflight: a tool changed after staging is refused (rc 1)" || bad "tool after staging: rc $rc"
world model; cp "$P/tests/shims/df" "$M/home/sgxfive-test-rgn4"; D2T=$W/drv$N; cp -R "$TREE" "$D2T"
env $(envw) bash "$D2T/run/stage_f.sh" > "$M/log/stage.log" 2>&1; rc=$?
[ $rc = 1 ] && grep -q "STAGING FAILED: the laptop's tool is not the rgn4 build" "$M/log/stage.log" && ok "staging: another tool on the laptop is refused" || bad "staging with another tool: rc $rc"
world model; runst l > /dev/null; printf 'x' >> "$M/home/scratch/r7f/stage/bins/l2-lock-lock-rel-rel.bin"
env $(envw) ssh -o x u@fake "bash ~/scratch/r7f/stage/run/run_f.sh l $(sha "$D2T/FROZEN.sha256") att${N}c" > "$M/log/bin.log" 2>&1; rc=$?
[ $rc = 1 ] && grep -q 'bins/l2-lock-lock-rel-rel.bin is not the frozen one' "$M/log/bin.log" && ok "a staged program changed after staging is refused (rc 1)" || bad "changed bin: rc $rc"
world model; stopcase "a held job that does not read back hold Y" 9 d FAKE_HOLD_NOY=1
world model; stopcase "render_rgn_arrays does not read back 1" 19 d FAKE_RGN_STUCK=1
world model; stopcase "registers unreadable" 12 s0 FAKE_SNAP_FAIL=1
world model; stopcase "a reset that leaves the held fault latched twice" 10 d FAKE_STUCK=1
grep -q "^SRCV_EXPECT=41E2F5C756F96D20F7109A4$" "$P/run/f.env" && grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/f.env" \
	&& ok "f.env pins module 41E2F5C756F96D20F7109A4 and ~/sgxfive-test-rgn4 e6951558..." || bad "f.env pins"

# ---- 5. sessioncheck: the staged tree is complete; the staged runner under env -i -------------------------------------------------
"$PY" -B "$P/score/sessioncheck.py" staged "$P/run" lib_f.sh run_f.sh f.env > "$W/staged.txt" 2>&1 && ok "sessioncheck staged: $(cat "$W/staged.txt")" || bad "sessioncheck staged: $(cat "$W/staged.txt")"
"$PY" -B "$P/score/sessioncheck.py" staged "$P/run" run_f.sh f.env > "$W/staged2.txt" 2>&1 && bad "sessioncheck staged misses an unstaged lib_f.sh" || ok "sessioncheck staged refuses a tree without lib_f.sh: $(head -1 "$W/staged2.txt")"
[ "$(sed -n 's/^RFILES="\(.*\)"$/\1/p' "$P/run/stage_f.sh")" = "run/lib_f.sh run/run_f.sh run/f.env" ] && ok "stage_f.sh stages exactly those runner files" || bad "stage_f.sh RFILES"
world model; runst s0 > /dev/null
set -- $(envw)
"$PY" -B "$P/score/sessioncheck.py" envi --log "$W/envi.log" $(for kv in "$@" RESET_WAIT=0 HEALTH_WAIT=0 TEE_GRACE=3 "FAKE_PY=$PY" "FAKE_P=$P/tests"; do echo "--set $kv"; done) \
	--set "HOME=$M/home" --set "PATH=$LBIN" -- bash "$M/home/scratch/r7f/stage/run/run_f.sh" s0 "$(sha "$D2T/FROZEN.sha256")" att${N}e > "$W/envi.txt" 2>&1 \
	&& ok "sessioncheck envi: the staged runner's s0 under env -i (the laptop PATH only): $(cat "$W/envi.txt")" || bad "sessioncheck envi: $(cat "$W/envi.txt"; tail -5 "$W/envi.log")"

# ---- 6. the guard ------------------------------------------------------------------------------------------------------------------
"$P/run/guard_f.sh" "$P" > /dev/null && ok "guard: this tree is clean" || bad "guard: this tree is not clean"
inject() { local nm=$1 f=$2 expr=$3; local C=$W/g$RANDOM; mkdir -p "$C"; cp -R "$P/run" "$P/tables" "$P/bins" "$C/"
	sed -i '' -e "$expr" "$C/$f"
	if "$C/run/guard_f.sh" "$C" > "$C/out" 2>&1; then bad "guard misses: $nm"; else ok "guard refuses: $nm"; fi; }
inject "a /tmp path" run/lib_f.sh 's#mkdir -p "$HOME/scratch/tmp"#mkdir -p /tmp/x#'
inject "a timeout without -k" run/lib_f.sh 's#sudo -n timeout -k 5 20 cat "$D/$1"#sudo -n timeout 20 cat "$D/$1"#'
inject "another kregnow value" run/lib_f.sh "s#printf '%s\\\\n' \"0x0c00^=0x10\"#printf '%s\\\\n' \"0x0c04=0x1\"#"
inject "a fifth clr_write" run/run_f.sh 's@^			snap "$name" c2$@&; clr_write "$name" set@'
inject "a bif_flush write" run/lib_f.sh 's#"hold_recovery Y"|"hold_recovery N") ;;#"hold_recovery Y"|"hold_recovery N"|"bif_flush 1") ;;#'
inject "an unprivileged debugfs read" run/lib_f.sh 's#sudo -n timeout -k 5 20 cat "$D/$1"#cat "$D/$1"#'
inject "a wait loop" run/run_f.sh 's#^begin$#begin; while false; do :; done#'
inject "an append outside the kept files" run/lib_f.sh 's#>> "$LEDGER"#>> "$HOME/x"#'
inject "another budget" run/f.env 's#^BUDGET_110=${BUDGET_110:-16}#BUDGET_110=${BUDGET_110:-30}#'
inject "an --aa4 row" tables/d.txt 's#--keep-going --wait-ms#--keep-going --aa4 --wait-ms#'
inject "a kpoke in a table" tables/m.txt 's#--poke cmd:1=#--kpoke-render 2:par:11=0x1 --poke cmd:1=#'
inject "a probe with --pds" tables/l.txt 's#probe --temps 32 --pixels "$S/l0#probe --temps 32 --pixels --pds 4 "$S/l0#'
inject "a probe of a program not staged" tables/l.txt 's#"$S/l0-lock-release.bin"#"$S/l9-other.bin"#'
inject "an unbounded ssh" run/f.sh 's#bounded 60 ssh $SSHO#ssh $SSHO#'

# ---- 7. dry run -----------------------------------------------------------------------------------------------------------------
world model; D2T=$W/drv$N; cp -R "$TREE" "$D2T"
out=$(env $(envw) SGX_DRY_RUN=1 bash "$D2T/run/f.sh" 2>&1)
echo "$out" | grep -q "bash ~/scratch/r7f/stage/run/run_f.sh s0 " && echo "$out" | grep -q "score_f.py gate m" && [ ! -d "$D2T/out" ] \
	&& ok "the driver's dry run prints the stage commands and the gates, and writes nothing" || bad "dry run: $out"

echo "mock: $( [ $fail = 0 ] && echo PASS || echo "FAILED (kept: $W)" )"
# a passing mock leaves nothing behind but the last model world's kept stages (tests/run_all.sh runs sessioncheck kept on them)
if [ $fail = 0 ]; then
	rm -rf "$P/debug/mock-kept"; cp -R "$W/drv1/out/full" "$P/debug/mock-kept"
	case "$W" in "$P"/debug/runmock.??????) rm -rf -- "$W" ;; esac
fi
exit $fail
