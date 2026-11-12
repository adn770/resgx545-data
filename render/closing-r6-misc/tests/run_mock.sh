#!/bin/bash
# tests/run_mock.sh: the r6-misc runner and driver end to end against the ARGV-DRIVEN fake tools (tests/worlds.py: t4 refuses odd
# heights as the rgn4 build does) and a fake debugfs whose directory is mode 000 (only the sudo shim reaches it).  Built from round
# 5's r5-render4x run_mock.sh.  No timing window anywhere: the runner has no held flow and the fake answers synchronously; every
# sleep is set to 0 and the tee fallback to 30 s (it only fires if tee hangs).
#   1. the whole driver (staging with the t6 hash as input, m.sh, scorer, verdict) in the model world and in the rival worlds;
#   2. the runner's rules: only `reset 1` written, laptop files under ~/scratch/r6m and work dirs removed, the hypothesis groups and
#      the fault limit, gateodd, every stop code;
#   3. the freeze with the t6 slot;  4. the guard (injections into copies of the tree);  5. the dry runs.
# Needs a current freeze (run/freeze_m.sh freeze).  Every run writes into a new mktemp directory under debug/.
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
"$P/run/freeze_m.sh" verify 0000000000000000000000000000000000000000000000000000000000000000 > "$W/v0" 2>&1
grep -q 'FROZEN FILES CHANGED\|not frozen' "$W/v0" && { echo "FAIL: not frozen (run/freeze_m.sh freeze)"; exit 1; }
S4=$(sha "$P/tests/fake_tool4.sh"); S6=$(sha "$P/tests/fake_tool6.sh")
export PATH="$P/tests/shims:$PATH" M_TOOL_SHA=$S4 M_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 TEE_GRACE=30
N=0
world() { # world [WORLD]: a fresh fake laptop running WORLD (default model)
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home/scratch/r6m/bin"
	for f in reset regs kpoke; do : > "$M/dbgreal/$f"; done
	echo "${FAKE_PB_INIT:-0x422}" > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"; echo 0 > "$M/dbgreal/render_rgn_arrays"
	echo N > "$M/dbgreal/hold_recovery"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo "${FAKE_SRCV:-MOCKSRCV}" > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	cp "$P/tests/fake_tool4.sh" "$M/home/sgxfive-test-rgn4"
	chmod 000 "$M/dbg"
	FAKE_WORLD=${1:-model}
}
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log HOME=$M/home FAKE_HOME=$M/home FAKE_P=$P/tests"; }
KD() { echo "$M/home/scratch/r6m/out/$ATT/$1"; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
# a copy of the session with TOOL6.sha256 holding the fake t6's hash (the lead's step), the runner as on the laptop
ttree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/lead" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" \
		"$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$P/TOOL6SRC.sha256" "$P/TOOL6.sha256" "$C/"
	mkdir -p "$C/debug"
	# the copy starts from the slot (the session's own TOOL6.sha256 holds the lead's real t6 hash), then the fake t6's hash is written
	printf 'SLOT-the-lead-writes-the-t6-sha256-here-with-run/freeze_m.sh-tool6  /home/jtorra/scratch/r6m/bin/sgxfive-test\n' > "$C/TOOL6.sha256"
	(cd "$C" && run/freeze_m.sh tool6 "$S6" > /dev/null) || bad "tool6 in the copy"; }
runst() { # runst TREE STAGE [ENV...]: the laptop runner of TREE on the fake laptop; prints its exit status
	local d=$1 st=$2; shift 2
	cp "$P/tests/fake_tool6.sh" "$M/home/scratch/r6m/bin/sgxfive-test"
	env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "${FSHA:-$(sha "$d/FROZEN.sha256")}" "$ATT" "${RS6:-$S6}" > "$M/log/$st.log" 2>&1; echo $?; }
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
drive() { # drive WORLD [ENV...]: stage (with the t6 hash) and run the whole driver on a fresh laptop; sets OUT, RC, C, M, VERDICT
	local wn=$1; shift
	world "$wn"; ttree
	env $(envw) T6_LOCAL="$P/tests/fake_tool6.sh" bash "$C/run/stage_m.sh" "$S6" > "$M/log/stage.log" 2>&1 || bad "staging for world $wn: $(grep FAIL "$M/log/stage.log" | head -2)"
	OUT=$(env $(envw) "$@" M_ATT=full bash "$C/run/m.sh" "$S6" ${DSTAGES:+--only $DSTAGES} 2>&1); RC=$?
	VERDICT=$("$PY" "$C/score/score_m.py" verdict "$C/out/full" "$S6" 2>&1)
	ATT=full
}
laptop_files_ok() { # every file the session left on the fake laptop is under ~/scratch/r6m (or is the rgn4 tool); ~/scratch/tmp empty
	local extra left
	extra=$(cd "$M/home" && find . -type f | grep -vE '^\./scratch/r6m/|^\./sgxfive-test-rgn4$')
	left=$(ls -A "$M/home/scratch/tmp" 2>/dev/null)
	[ -z "$extra" ] && [ -z "$left" ] && return 0
	echo "     files outside ~/scratch/r6m: ${extra:-none}; left in ~/scratch/tmp: ${left:-none}"; return 1
}

# ---- 1. the whole driver -----------------------------------------------------------------------------------------------------
drive model
nst=$(echo "$OUT" | grep -c '^stage q[0-9]* done, health ok, knobs at their defaults')
[ $RC = 0 ] && [ "$nst" = 3 ] && echo "$OUT" | grep -q '^r6-misc done' && ok "world model: staging with the t6 hash, the driver runs the three stages, health and knobs ok after each" \
	|| { bad "world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
for k in "Q289: M-OR held (20 of 20 held-out rows, 8 of 8 separating); M-ADD refuted" "Q287 (odd heights, W 34): rule A held on the held-out cells (7 of 7), FLOOR refuted" \
	"Q086: H-COV held (9 of 9 held-out rows), H-ANY refuted (6 of 9); 11 rows not run; control R passes"; do
	echo "$VERDICT" | grep -qF "SUMMARY: $k" || bad "world model verdict lacks: $k"
done
echo "$VERDICT" | grep -q 'cannot tell\|not run$' && bad "  the model world's verdict has cannot tell: $VERDICT" || ok "  the verdict decides every question (Q289 OR, Q287 A, Q086 H-COV)"
wr=$(writes | sort -u | tr '\n' ' ')
[ "$wr" = "reset 1 " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs write of the whole session: reset 1" || bad "  debugfs writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
laptop_files_ok && ok "  every laptop file under ~/scratch/r6m; every work directory (mktemp under ~/scratch/tmp) removed" || bad "  laptop files"
n6=$(grep -c '^sgxfive-test tri ' "$M/fake.log"); n4d=$(grep -c '^sgxfive-test-rgn4 tri .*--depth' "$M/fake.log"); nodd=$(grep '^sgxfive-test-rgn4 tri .*--depth' "$M/fake.log" | grep -cE -- '--height [0-9]*[13579] ')
[ "$n6" = 19 ] && [ "$n4d" = 1 ] && [ "$nodd" = 0 ] && ok "  q287: 19 depth jobs ran with t6, the 34 x 18 control once with t4, no odd height with t4" || bad "  tools: t6 $n6, t4 depth $n4d, t4 odd $nodd"
nf=$(awk -F'\t' 'NR > 1 && $9 == "fault"' "$(KD q086)/cases.tsv" | wc -l | tr -d ' '); nr=$(awk 'NR > 1' "$(KD q086)/cases.tsv" | wc -l | tr -d ' ')
[ "$nf" = 3 ] && [ "$nr" = 10 ] && grep -q 'q086-448x224-HS skipped: group hs reached its 2 faults' "$C/out/full/q086.log" \
	&& ok "  q086: 10 jobs, 3 faults (u 0, fx 1, hs 2), the other 11 skipped by their groups, no stop (no row left to run)" || bad "  q086: $nr jobs, $nf faults"
for st in q289 q287 q086; do
	n=$(awk 'NR > 1' "$(KD $st)/cases.tsv" | wc -l | tr -d ' '); k=$(ls "$(KD $st)" | grep -c '\.txt\.gz$')
	[ "$n" -gt 0 ] && ls "$(KD $st)" | grep -q 'runner.log' || bad "  $st kept files"
done
missing() { # missing STAGE DIR: the files the stage's scorer reads that the kept directory lacks (score_m.missing_files)
	"$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import score_m as S; m = S.missing_files(sys.argv[2], sys.argv[3]); print(len(m), " ".join(m[:3]))' "$P/score" "$1" "$2"; }
for st in q289 q287 q086; do
	m=$(missing "$st" "$C/out/full/$st")
	[ "${m%% *}" = 0 ] && ok "  $st: every file its scorer reads (score_m.REQUIRED) is in the kept output on the Mac" || bad "  $st kept output lacks: $m"
done
ls "$(KD q287)" | grep -q 'z-34x19-x-r1.depth.1.bin.gz' && ls "$(KD q086)" | grep -q 'q086-320x160-U2.err.gz' && ok "  q287 depth dumps and every job's stderr kept apart" || bad "  kept dumps / stderr"

for wv in "add|Q289: M-OR refuted (12 of 20 held-out rows, 0 of 8 separating); M-ADD held" "floor|rule A refuted on the held-out cells (0 of 7), FLOOR held (7 of 7)" \
	"hany|Q086: H-COV refuted (6 of 20 held-out rows), H-ANY held (20 of 20); 0 rows not run" \
	"xor|Q289: cannot tell: controls: f-ctl-64x32-x10: FAILED"; do
	wn=${wv%%|*}; want=${wv#*|}
	drive "$wn"
	[ $RC = 0 ] && echo "$VERDICT" | grep -qF "$want" && ok "world $wn: the verdict follows the world: $want" || { bad "world $wn: rc $RC: $(echo "$VERDICT" | tr '\n' ' ' | cut -c1-300)"; echo "$OUT" | tail -3 | sed 's/^/     /'; }
done
drive refuse-odd
[ $RC = 0 ] && echo "$OUT" | grep -q 'q287: gateodd' && echo "$VERDICT" | grep -q 'SUMMARY: Q287: odd heights refused' && echo "$VERDICT" | grep -q 'SUMMARY: Q086: H-COV held' \
	&& [ "$(awk 'NR > 1' "$(KD q287)/cases.tsv" | wc -l | tr -d ' ')" = 1 ] && ok "world refuse-odd: the module refuses 34 x 17: q287 ends after its gate row (rc 21), scored as refused, and q086 still runs" \
	|| { bad "world refuse-odd: rc $RC"; echo "$OUT" | tail -4 | sed 's/^/     /'; }

# ---- 2. the runner's rules ----------------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$C" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
world model; ttree
stopcase "stage q289 in the model world" 0 q289
grep -q "^f-128x64-x10	q289	heldout	safe	expectdiff needhash	t4	.*	1	ok	" "$(KD q289)/cases.tsv" && ok "  a fill with wrong pixels exits 1 with its diff line: class ok (expectdiff)" || bad "  expectdiff on fills"
laptop_files_ok && ok "  the stage left no work directory" || bad "  stage files"
world fill-fault; ttree; stopcase "an unexpected fault in q289 stops the stage after strict health" 4 q289
world nohash; ttree; stopcase "the second fill without a hash line stops q289" 17 q289
grep -q 'STOP: the second row without a hash (f-128x64-x08)' "$M/log/q289.log" && ok "  it names the row (the control was the first)" || bad "  nohash text"
world q086-ta; ttree; stopcase "a q086 fault that is not the 3D-side class (TA 0x90004 at 0x20006061) stops the stage" 18 q086
world allfault; ttree; stopcase "the third fault with rows of a live group left (u, fx and the first hs) stops q086" 15 q086
grep -q 'STOP: the 3-th fault-class event' "$M/log/q086.log" && [ "$(awk -F'\t' '$9 == "fault"' "$(KD q086)/cases.tsv" | wc -l | tr -d ' ')" = 3 ] && ok "  three faults recorded, then the stop" || bad "  limit text"
world model; ttree; stopcase "less than 200 MB free on ~ before the second job stops the stage" 22 q289 FAKE_DF_FROM=3
world model; ttree; stopcase "less than 200 MB free at the preflight stops before any job" 22 q289 FAKE_DF_KB=1000
[ ! -s "$M/fake.log" ] && ok "  no tool ran at all" || bad "  the tool ran: $(head -2 "$M/fake.log" | tr '\n' ' ')"
world model; echo "0x90100 0x10000016 0x480 0x20000000" > "$M/fake/state"; ttree
stopcase "a fault latched before the first job that a reset does not clear stops (rc 14)" 14 q289 FAKE_STUCK=1
world model; ttree; stopcase "registers unreadable stop the stage" 12 q289 FAKE_SNAP_FAIL=1
world model; ttree; stopcase "a failed reset before a job stops the stage" 13 q289 FAKE_RESET_FAIL_FROM=2
world model; ttree; stopcase "the begin health failing after a reset and a retry stops (rc 5)" 5 q289 FAKE_HEALTH_BAD=1
FAKE_PB_INIT=0x100 world model; ttree; stopcase "a knob not at its default at the start: preflight refuses, nothing written" 1 q289
[ ! -s "$M/fake/writes" ] && ok "  no debugfs write at all" || bad "  writes: $(writes | tr '\n' ' ')"
FAKE_SRCV=OTHERSRCV world model; ttree; stopcase "a module that is not the expected build: preflight refuses" 1 q289
world model; ttree; FSHA=0000 stopcase "a laptop FROZEN.sha256 that is not the Mac's is refused" 1 q289
world model; ttree; RS6=$S4 stopcase "a t6 hash that TOOL6.sha256 does not hold is refused" 1 q289
# a t6 binary that is not the frozen build: q287 (t6 rows) refuses at the preflight, q289 (t4 only) runs
world model; ttree; rc=$(env $(envw) SGXFIVE_TEST6="$M/home/sgxfive-test-rgn4" bash "$C/run/run_stage.sh" q287 "$(sha "$C/FROZEN.sha256")" "$ATT" "$S6" > "$M/log/q287.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q 't6 is not the frozen build' "$M/log/q287.log" && ok "a t6 binary that is not the frozen build: q287's preflight refuses (rc 1)" || bad "t6 check: rc $rc"
world model; ttree; rc=$(env $(envw) SGXFIVE_TEST6="$M/nonexistent" bash "$C/run/run_stage.sh" q289 "$(sha "$C/FROZEN.sha256")" "$ATT" "$S6" > "$M/log/q289.log" 2>&1; echo $?)
[ "$rc" = 0 ] && ok "  q289 (t4 rows only) does not need t6 (rc 0 with no t6 on the laptop)" || bad "  q289 without t6: rc $rc"
world model; ttree; printf 'q-x|heldout|safe|expectdiff pb:0x40|t4|fill --width 64 --height 32\n' >> "$C/tables/q289.txt"
stopcase "a knob the session does not allow (pb:0x40) is refused before anything runs" 7 q289
world model; ttree; printf 'q-y|heldout|safe|expectdiff|t5|fill --width 64 --height 32\n' >> "$C/tables/q289.txt"
stopcase "a tool column that is neither t4 nor t6 is refused" 7 q289
world model; ttree; sed -i '' 's/--height 7 /--height 9 /' "$C/tables/q287.txt"; stopcase "a table that is not the frozen one is refused" 1 q287
# a row whose tool is t4 at an odd height (the slip the tool column prevents): the fake rgn4 tool refuses it as the real one does
world model; ttree; sed -i '' 's/^\(z-fit-34x19-y-r1|fit|safe|expectdiff|\)t6|/\1t4|/' "$C/tables/q287.txt"; (cd "$C" && run/freeze_m.sh freeze > /dev/null && run/freeze_m.sh tool6 "$S6" > /dev/null)
stopcase "a t4 row at an odd height (frozen that way) fails as the rgn4 tool refuses it: an unexplained failure stops q287" 4 q287
world model; ttree; stopcase "q287 in the model world" 0 q287
zcat < "$(KD q287)/z-dry-34x17-y.txt.gz" | grep -q 'diff: 0 of 578 pixels' && ok "  the gate row (34 x 17) ran with t6 and drew" || bad "  gate row"

# freeze 1's runner (freeze1/run: no $JW/depth) against the same argv-driven world: it exits 0 but keeps no depth dump, and the
# kept-files check above FAILS on it (the slip of attempt 20261112-144153); the fixed runner stops on a dump that was not written
world model; ttree; cp "$P"/freeze1/run/run_stage.sh "$P"/freeze1/run/lib_m.sh "$P"/freeze1/run/m.env "$C/run/"; cp "$P/freeze1/FROZEN.sha256" "$C/FROZEN.sha256"
rc=$(runst "$C" q287); m=$(missing q287 "$(KD q287)")
[ "$rc" = 0 ] && [ "${m%% *}" = 20 ] && zcat < "$(KD q287)/z-ctl-34x18-y-t4.txt.gz" | grep -q -- '--depth-dump: No such file or directory' \
	&& ok "REGRESSION: freeze 1's runner keeps no depth dump (20 of 20 missing, the tool's --depth-dump error in the output): the kept-files check fails on it" \
	|| bad "regression on freeze 1's runner: rc $rc, missing $m"
world nodump; ttree; stopcase "a depth dump the tool did not write stops q287 at its first row (rc 23)" 23 q287
grep -q 'STOP: the depth dump of z-dry-34x17-y was not written or not kept' "$M/log/q287.log" && ok "  it names the row" || bad "  rc 23 text"

# ---- 3. the freeze and its t6 slot --------------------------------------------------------------------------------------------
world model; ttree
(cd "$C" && run/freeze_m.sh verify > /dev/null 2>&1) && bad "verify without the t6 hash passed" || ok "freeze: verify without the t6 hash is refused"
(cd "$C" && run/freeze_m.sh verify "$S4" > /dev/null 2>&1) && bad "verify with another hash passed" || ok "freeze: verify with a hash TOOL6.sha256 does not hold is refused"
(cd "$C" && run/freeze_m.sh verify "$S6" > /dev/null 2>&1) && ok "freeze: verify with the lead's hash passes" || bad "verify with S6"
(cd "$C" && run/freeze_m.sh tool6 "$S4" > /dev/null 2>&1) && bad "tool6 replaced a hash" || ok "freeze: tool6 does not replace a hash it already holds"
C2=$W/slot; mkdir -p "$C2"; cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/lead" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" \
	"$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$P/TOOL6SRC.sha256" "$C2/"
printf 'SLOT-the-lead-writes-the-t6-sha256-here-with-run/freeze_m.sh-tool6  /home/jtorra/scratch/r6m/bin/sgxfive-test\n' > "$C2/TOOL6.sha256"
(cd "$C2" && run/freeze_m.sh verify "$S6" > /dev/null 2>&1) && bad "the slot verified" || ok "freeze: the session as built (TOOL6.sha256 the slot) does not verify with any hash until the lead writes it"
(cd "$C2" && run/freeze_m.sh tool6 xyz > /dev/null 2>&1) && bad "tool6 took a non-hash" || ok "freeze: tool6 refuses a value that is not 64 hex digits"
(cd "$C" && echo "#" >> tables/q086.txt && run/freeze_m.sh verify "$S6" > /dev/null 2>&1) && bad "a changed table verified" || ok "freeze: a changed table fails verify"
(cd "$C" && git checkout 2>/dev/null; cp "$P/tables/q086.txt" tables/q086.txt; : > tables/new.txt; run/freeze_m.sh verify "$S6" > /dev/null 2>&1) && bad "a new table verified" || ok "freeze: a file added since fails verify"

# ---- 4. the guard -------------------------------------------------------------------------------------------------------------
"$P/run/guard_m.sh" > /dev/null && ok "guard: the session is clean" || bad "guard: the session is not clean"
inject() { local nm=$1 f=$2 line=$3; local G=$W/g$RANDOM$RANDOM; mkdir -p "$G"; cp -R "$P/run" "$P/tables" "$P/lead" "$G/"
	printf '%s\n' "$line" >> "$G/$f"
	"$P/run/guard_m.sh" "$G" > /dev/null 2>&1 && bad "guard missed: $nm" || ok "guard catches: $nm"; }
inject "a /tmp work file" run/run_stage.sh 'echo x > /tmp/r6m.out'
inject "a knob write" run/run_stage.sh 'dbg_write render_pb_pages 0x40'
inject "a delete outside drop_work" run/lib_m.sh 'rm -rf "$KEEP"'
inject "a wait loop" run/run_stage.sh 'while true; do sleep 1; done'
inject "a timeout without -k" run/lib_m.sh 'sudo -n timeout 20 "$T4" fill'
inject "an unprivileged debugfs read" run/lib_m.sh 'cat "$D/regs"'
inject "an unbounded ssh in the driver" run/m.sh 'ssh $SSHO "$T" true'
inject "a kreg in a table" tables/q086.txt 'x|heldout|risky|expectdiff|t4|tri --kreg 0x0c00=1'
inject "a --poke outside the three forms" tables/q289.txt "x|heldout|safe|expectdiff|t4|fill --poke 'xfer:3=0x1'"
inject "a kpoke-render outside ta:143/144/146" tables/q086.txt 'x|heldout|risky|expectdiff|t4|tri --aa4 --kpoke-render 1:rd:1=0x0'
inject "a fourth tool" tables/q289.txt 'x|heldout|safe|expectdiff|t7|fill'
inject "the build script reaching the laptop" lead/build_tool6.sh 'scp x "$SGX_TARGET_HOST:"'
inject "a reboot" run/lib_m.sh 'sudo -n reboot'

# ---- 5. dry runs ---------------------------------------------------------------------------------------------------------------
world model; ttree
out=$(env $(envw) SGX_DRY_RUN=1 bash "$C/run/stage_m.sh" "$S6" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q "scratch/r6m/bin/sgxfive-test" && echo "$out" | grep -q "mkdir -p scratch/r6m/run/run" && ok "stage_m.sh dry run: the commands, every path under ~/scratch/r6m" || bad "stage dry run: rc $rc"
out=$(env $(envw) SGX_DRY_RUN=1 bash "$C/run/m.sh" "$S6" 2>&1); rc=$?
[ $rc = 0 ] && [ "$(echo "$out" | grep -c "run_stage.sh q[0-9]* [0-9a-f]* full\|run_stage.sh q[0-9]* [0-9a-f]* [0-9-]* $S6")" -ge 3 ] && ok "m.sh dry run: three stages, each with the FROZEN and t6 hashes" || bad "m.sh dry run: rc $rc"
out=$(env $(envw) bash "$C/run/m.sh" 2>&1); rc=$?
[ $rc = 2 ] && ok "m.sh without the t6 hash: usage (rc 2)" || bad "m.sh without hash: rc $rc"
out=$(SGX_DRY_RUN=1 RESGX545_MAIN=/Users/jtorra/src/resgx545 bash "$P/lead/build_tool6.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'sgxt-r6m' && ! echo "$out" | grep -q 'u@fake' && ok "lead/build_tool6.sh dry run: archive checked against TOOL6SRC.sha256, build host only" || bad "build dry run: rc $rc: $(echo "$out" | head -2)"

[ $fail = 0 ] && echo "run_mock: ALL PASS" || echo "run_mock: FAILURES"
exit $fail
