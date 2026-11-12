#!/bin/bash
# tests/run_mock.sh: the r7-rp runner and driver end to end against the ARGV-DRIVEN fake tools (tests/worlds.py and the areas'
# world_*.py: t4 refuses odd widths as the rgn4 build does) and a fake debugfs whose directory is mode 000 (only the sudo shim reaches
# it).  r6-misc's run_mock.sh for round 7: THE STAGED TREE runs, under env -i: run/stage_r7.sh copies the session to the fake laptop
# (~/scratch/r7r/run, stage, bin) and the driver's ssh (tests/shims/ssh) runs the laptop side under `env -i` with only the fake laptop's
# variables; the single-stage cases below run the staged copy under env -i too.  No timing window anywhere: the runner has no held
# flow and the fake answers synchronously; every sleep is 0 and the tee fallback 30 s (it only fires if tee hangs).
#   1. the whole driver in the model world: nine stages, the gates, health and knobs after each, only `reset 1` and
#      `render_rgn_arrays 1|0` written (q293's rows only), every laptop file under ~/scratch/r7r, every scorer input kept
#      (score_r7.py missing; sessioncheck.py kept with the scorer's own reader), the tools per row;
#   2. the gates: s0 failing stops the session (40); q291g failing skips q291, p7-rdc failing skips p7-rd, the session goes on;
#      odd widths refused: q287 ends 21 after its even-width rows, the session goes on; q086's FX bridge completing stops (19);
#   3. the runner's stop codes on single stages;  4. the freeze with the t7 slot;  5. the guard;  6. the dry runs;
#   7. sessioncheck.py staged on the exact list stage_r7.sh copies, and envi of the staged runner.
# Needs a current freeze (run/freeze_r7.sh freeze).  Every run writes into a new mktemp directory under debug/.
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
"$P/run/freeze_r7.sh" verify 0000000000000000000000000000000000000000000000000000000000000000 > "$W/v0" 2>&1
grep -q 'FROZEN FILES CHANGED\|not frozen' "$W/v0" && { echo "FAIL: not frozen (run/freeze_r7.sh freeze)"; cat "$W/v0"; exit 1; }
SF=$(sha "$P/tests/fake_tool.sh")      # the fake t4, t6 and t7 are one script (its path says which build it is)
Z64=0000000000000000000000000000000000000000000000000000000000000000
export PATH="$P/tests/shims:$PATH" PY R7_TOOL_SHA=$SF R7_TOOL6_SHA=$SF R7_SRCV_EXPECT=MOCKSRCV
export RESET_WAIT=0 HEALTH_WAIT=0 TEE_GRACE=30
N=0
world() { # world [WORLD]: a fresh fake laptop running WORLD (default model)
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home/scratch"
	for f in reset regs kpoke; do : > "$M/dbgreal/$f"; done
	echo "${FAKE_PB_INIT:-0x422}" > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"; echo 0 > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_ROOM_INIT:-0}" > "$M/dbgreal/render_tail_room"
	echo N > "$M/dbgreal/hold_recovery"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo "${FAKE_SRCV:-MOCKSRCV}" > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"
	chmod 000 "$M/dbg"
	FAKE_WORLD=${1:-model}
}
# the fake laptop's own variables (the ssh shim passes exactly these, under env -i)
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log FAKE_HOME=$M/home FAKE_P=$P/tests FAKE_SRCV=${FAKE_SRCV:-MOCKSRCV}"; }
KD() { echo "$M/home/scratch/r7r/out/$ATT/$1"; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
# a copy of the session with TOOL7.sha256 holding the fake t7's hash (the lead's step)
ttree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/lead" "$P/bins" "$P/templates" "$P/stages.txt" "$P/TABLES.md" \
		"$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOL6.sha256" "$P/TOOLSRC.sha256" "$P/TOOL6SRC.sha256" "$P/TOOL7SRC.sha256" "$C/"
	rm -rf "$C/score/__pycache__" "$C/gen/__pycache__"
	mkdir -p "$C/debug" "$C/tests"; cp "$P/tests/fake_tool.sh" "$C/tests/"
	printf 'SLOT-the-lead-writes-the-t7-sha256-here-with-run/freeze_r7.sh-tool7  /home/jtorra/scratch/r7r/bin/sgxfive-test-t7\n' > "$C/TOOL7.sha256"
	(cd "$C" && run/freeze_r7.sh tool7 "$SF" > /dev/null) || bad "tool7 in the copy"; }
# stage TREE onto the fake laptop with stage_r7.sh (the staged tree is what runs from here on)
stage() { env $(envw) T7_LOCAL="$P/tests/fake_tool.sh" T6_LOCAL="$P/tests/fake_tool.sh" bash "$C/run/stage_r7.sh" "$SF" > "$M/log/stage.log" 2>&1; }
# runst STAGE [K=V...]: the STAGED runner of one stage on the fake laptop under env -i; prints its exit status
runst() { local st=$1; shift
	(cd "$M/home" && env -i PATH="$PATH" HOME="$M/home" PY="$PY" R7_TOOL_SHA="$SF" R7_TOOL6_SHA="$SF" R7_SRCV_EXPECT=MOCKSRCV RESET_WAIT=0 HEALTH_WAIT=0 TEE_GRACE=30 \
		$(envw) "$@" bash "$M/home/scratch/r7r/run/run/run_stage.sh" "$st" "${FSHA:-$(sha "$C/FROZEN.sha256")}" "$ATT" "${RS7:-$SF}") > "$M/log/$st.log" 2>&1; echo $?; }
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
drive() { # drive WORLD [ENV...]: stage and run the whole driver on a fresh laptop; sets OUT, RC, C, M, VERDICT
	local wn=$1; shift
	world "$wn"; ttree
	stage || bad "staging for world $wn: $(grep FAIL "$M/log/stage.log" | head -2)"
	OUT=$(env $(envw) "$@" R7_ATT=full bash "$C/run/r7.sh" "$SF" ${DSTAGES:+--only $DSTAGES} 2>&1); RC=$?
	VERDICT=$("$PY" "$C/score/score_r7.py" verdict "$C/out/full" "$SF" 2>&1)
	ATT=full
}
laptop_files_ok() { # every file the session left on the fake laptop is under ~/scratch/r7r (or is the rgn4 tool); ~/scratch/tmp empty
	local extra left
	extra=$(cd "$M/home" && find . -type f | grep -vE '^\./scratch/r7r/|^\./sgxfive-test-rgn4$')
	left=$(ls -A "$M/home/scratch/tmp" 2>/dev/null)
	[ -z "$extra" ] && [ -z "$left" ] && return 0
	echo "     files outside ~/scratch/r7r: ${extra:-none}; left in ~/scratch/tmp: ${left:-none}"; return 1
}
ALLST=$(tr '\n' ' ' < "$P/stages.txt")
scorer_of() { case "$1" in s0|q287) echo score_q287 ;; q291g|q291) echo score_q291 ;; p7-rdc|p7-rd) echo score_rd7 ;; q293|q139) echo score_dump ;; q086) echo score_q086 ;; esac; }

# ---- 1. the whole driver -----------------------------------------------------------------------------------------------------
drive model
nst=$(echo "$OUT" | grep -c '^stage [a-z0-9-]* done, health ok, knobs at their defaults')
[ $RC = 0 ] && [ "$nst" = 9 ] && echo "$OUT" | grep -q '^r7-rp done' && ok "world model: staging, the driver runs the nine stages, health and knobs ok after each" \
	|| { bad "world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
echo "$VERDICT" | sed 's/^/     /'
echo "$VERDICT" | grep -iE 'cannot tell|refused' | grep -vE '[0-9]+ cannot tell of [0-9]+' | grep -q . && bad "  the model world's verdict has cannot tell or refused" || ok "  the verdict decides every question"
for g in s0 q291g p7-rdc; do grep -q "gate $g: passed" "$C/out/full/gate-$g.txt" && ok "  gate $g passed" || bad "  gate $g: $(cat "$C/out/full/gate-$g.txt" 2>/dev/null | tail -1)"; done
wr=$(writes | sort | uniq -c | awk '{ print $2 " " $3 " x" $1 }' | tr '\n' ',')
nrgn=$(grep -v '^#' "$P/tables/q293.txt" | grep -c 'rgn:1')
[ ! -s "$M/fake/other-writes" ] && [ "$(writes | grep -c '^render_rgn_arrays 1$')" = "$nrgn" ] && [ -z "$(writes | grep -v '^reset 1$' | grep -v '^render_rgn_arrays [01]$')" ] \
	&& ok "  debugfs writes: reset 1 and render_rgn_arrays 1 for the $nrgn rgn:1 rows, each put back to 0 ($wr)" || bad "  debugfs writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
[ "$(cat "$M/dbgreal/render_rgn_arrays")" = 0 ] && ok "  render_rgn_arrays is 0 at the end" || bad "  render_rgn_arrays left at $(cat "$M/dbgreal/render_rgn_arrays")"
laptop_files_ok && ok "  every laptop file under ~/scratch/r7r; every work directory (mktemp under ~/scratch/tmp) removed" || bad "  laptop files"
# the tools per row: the fake's log has the binary's name; each row's tool column is the binary that ran it
want=$(for st in $ALLST; do grep -v '^#' "$P/tables/$st.txt" | awk -F'|' 'NF >= 6 { print $5 }'; done | sort | uniq -c | awk '{ print $2 "=" $1 }' | tr '\n' ' ')
got=$(grep -v '^sgxfive-test-rgn4 \(tri\|fill\)$' "$M/fake.log" | awk '{ b = $1; sub(/sgxfive-test-rgn4/, "t4", b); sub(/sgxfive-test-/, "", b); print b }' | sort | uniq -c | awk '{ print $2 "=" $1 }' | tr '\n' ' ')
nbare=$(for st in $ALLST; do grep -v '^#' "$P/tables/$st.txt" | awk -F'|' 'NF >= 6 && $6 == "tri" && $5 == "t4"'; done | wc -l | tr -d ' ')
echo "     rows by tool $want; jobs by binary (health pairs left out, $nbare bare t4 tri rows among them) $got"
nodd4=$(grep '^sgxfive-test-rgn4 tri .*--depth' "$M/fake.log" | grep -cE -- '--width [0-9]*[13579] ')
[ "$nodd4" = 0 ] && ok "  no odd width ran with t4" || bad "  $nodd4 odd-width rows ran with t4"
for st in $ALLST; do
	m=$("$PY" "$C/score/score_r7.py" missing "$st" "$C/out/full/$st")
	[ "${m%% *}" = 0 ] && ok "  $st: every file its scorer declares (REQUIRED) is in the kept output on the Mac" || bad "  $st kept output lacks: $m"
	sc=$(scorer_of "$st")
	k=$(cd "$C/score" && R7_NO_VERIFY=tests-only "$PY" sessioncheck.py kept "$sc.py" "$st" "$C/out/full/$st" --call score 2>&1); kr=$?
	[ $kr = 0 ] && ok "  $st: sessioncheck kept ($sc.score reads only declared files)" || bad "  $st: sessioncheck kept: $(echo "$k" | head -3 | tr '\n' ' ')"
done

# ---- 2. the gates and the clean ends ------------------------------------------------------------------------------------------
drive t7bad
[ $RC = 40 ] && echo "$OUT" | grep -q 'STOP: the s0 gate did not pass' && [ ! -d "$C/out/full/q287" ] && ok "world t7bad: the s0 gate fails, the session stops (40) before q287" || { bad "world t7bad: rc $RC"; echo "$OUT" | tail -3 | sed 's/^/     /'; }
for wv in "${Q291_GATE_WORLD:-gate-miss}|q291g|q291" "${RD_GATE_WORLD:-gatefail}|p7-rdc|p7-rd"; do
	wn=${wv%%|*}; r=${wv#*|}; g=${r%%|*}; sk=${r#*|}
	drive "$wn"
	[ $RC = 0 ] && echo "$OUT" | grep -q "GATE: $g did not pass" && echo "$OUT" | grep -q "#### $sk skipped by its gate" && [ ! -d "$C/out/full/$sk" ] && [ -d "$C/out/full/q086" ] \
		&& ok "world $wn: the $g gate fails, $sk is skipped, the session goes on to q086 (rc 0)" || { bad "world $wn: rc $RC"; echo "$OUT" | grep -E 'GATE|STOP|skipped' | head -3 | sed 's/^/     /'; }
done
drive refuse-odd
nq=$(awk 'NR > 1' "$(KD q287)/cases.tsv" | wc -l | tr -d ' '); nodd=$(grep -v '^#' "$P/tables/q287.txt" | grep -c 'oddw'); nall=$(grep -vc '^#' "$P/tables/q287.txt")
[ $RC = 0 ] && echo "$OUT" | grep -q 'q287: gateodd' && [ "$nq" = $((nall - nodd + 1)) ] && [ -d "$C/out/full/q086" ] \
	&& ok "world refuse-odd: the gate row refused, the $((nall - nodd)) even-width rows still ran ($nq kept with the gate), q287 rc 21, the session goes on" \
	|| { bad "world refuse-odd: rc $RC, $nq q287 rows (want $((nall - nodd + 1)))"; echo "$OUT" | grep -E 'gateodd|STOP' | head -3 | sed 's/^/     /'; }
DSTAGES=q086 drive fxok
[ $RC = 19 ] && grep -q 'completed where every rule predicts a fault' "$C/out/full/q086.log" && ok "world fxok: the FX bridge completes, q086 stops (19) before its new-size rows" || bad "world fxok: rc $RC"

# ---- 3. the runner's rules (single stages, the staged tree under env -i) ---------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
fresh() { world "${1:-model}"; ttree; stage || bad "staging: $(grep FAIL "$M/log/stage.log" | head -2)"; }
fresh; stopcase "stage s0 alone in the model world" 0 s0
fresh; stopcase "stage q293 alone (rgn:1 rows)" 0 q293
[ "$(writes | grep -c '^render_rgn_arrays 0$')" -ge "$nrgn" ] && ok "  each rgn:1 row put the knob back to 0" || bad "  rgn writes: $(writes | tr '\n' ' ')"
fresh; stopcase "the knob not reading back 1 stops q293 before its first job (19)" 19 q293 FAKE_RGN_STUCK=1
fresh; stopcase "an unexpected 3D fault in q287 stops the stage after strict health" 4 q287 "FAKE_RULES=--width 19 |fault3d"
fresh; stopcase "an unexpected hang in q139 stops the stage" 4 q139 "FAKE_RULES=--dump-render|hang"
fresh; stopcase "a q086 fault of the TA side stops the stage (18)" 18 q086 "FAKE_RULES=0x00802002|faultta"
fresh; stopcase "a -110 after a q086 fault stops the stage (18)" 18 q086 "FAKE_RULES=0x00802002|neg110"
fresh; stopcase "a fatal kernel message stops at once (3)" 3 s0 "FAKE_RULES=--depth-pages|fatal"
fresh; stopcase "a job that does not return stops at once (6)" 6 s0 "FAKE_RULES=--depth-pages|timeout"
fresh; stopcase "a render dump not written stops q293 (23)" 23 q293 "FAKE_RULES=--dump-render|nodump"
fresh; stopcase "a depth dump not written stops q287 (23)" 23 q287 "FAKE_RULES=--depth-dump|nodump"
fresh; stopcase "less than 200 MB free before the second job stops the stage (22)" 22 s0 FAKE_DF_FROM=3
fresh; stopcase "less than 200 MB free at the preflight stops before any job" 22 s0 FAKE_DF_KB=1000
[ ! -s "$M/fake.log" ] && ok "  no tool ran at all" || bad "  the tool ran: $(head -2 "$M/fake.log" | tr '\n' ' ')"
world model; echo "0x90100 0x10000016 0x480 0x20000000" > "$M/fake/state"; ttree; stage
stopcase "a fault latched before the first job that a reset does not clear stops (14)" 14 s0 FAKE_STUCK=1
fresh; stopcase "registers unreadable stop the stage (12)" 12 s0 FAKE_SNAP_FAIL=1
fresh; stopcase "a failed reset before a job stops the stage (13)" 13 s0 FAKE_RESET_FAIL_FROM=2
fresh; stopcase "the begin health failing after a reset and a retry stops (5)" 5 s0 FAKE_HEALTH_BAD=1
FAKE_PB_INIT=0x100 fresh; stopcase "a knob not at its default at the start: preflight refuses" 1 s0
[ -z "$(writes | grep -v '^render_rgn_arrays 0$')" ] && ok "  nothing written but the exit trap's render_rgn_arrays 0" || bad "  writes: $(writes | tr '\n' ' ')"
FAKE_ROOM_INIT=0x20 fresh; stopcase "render_tail_room not at its default: preflight refuses" 1 s0
FAKE_SRCV=OTHERSRCV fresh; stopcase "a module that is not the expected build: preflight refuses" 1 s0
fresh; FSHA=$Z64 stopcase "a laptop FROZEN.sha256 that is not the Mac's is refused" 1 s0
fresh; RS7=$Z64 stopcase "a t7 hash that TOOL7.sha256 does not hold is refused" 1 s0
fresh; cp "$M/home/sgxfive-test-rgn4" "$M/home/scratch/r7r/bin/sgxfive-test-t7"; echo "# changed" >> "$M/home/scratch/r7r/bin/sgxfive-test-t7"
stopcase "a t7 binary that is not the frozen build: s0's preflight refuses" 1 s0
grep -q 't7 is not the frozen build' "$M/log/s0.log" && ok "  it names t7" || bad "  t7 text"
stopcase "  q139 (t4 rows only) does not need t7" 0 q139
fresh; rm -f "$M/home/scratch/r7r/stage/"*; stopcase "a staged program missing stops q291g before any job (8)" 8 q291g
fresh; printf 'x-a|heldout|safe|expectdiff pb:0x40|t4|tri\n' >> "$M/home/scratch/r7r/run/tables/s0.txt"
stopcase "a knob the session does not allow (pb:0x40) is refused before anything runs" 7 s0
fresh; printf 'x-b|heldout|safe|expectdiff|t5|tri\n' >> "$M/home/scratch/r7r/run/tables/s0.txt"
stopcase "a tool column that is not t4, t6 or t7 is refused" 7 s0
fresh; sed -i '' 's/--width 19 /--width 21 /' "$M/home/scratch/r7r/run/tables/q287.txt"; stopcase "a table that is not the frozen one is refused" 1 q287
# a t4 row at an odd width (the slip the tool column prevents), frozen that way: the fake rgn4 tool refuses it as the real one does
world model; ttree; r=$(grep -v '^#' "$C/tables/q287.txt" | grep '|t7|' | grep -E -- '--width (7|11|19|23|35) ' | grep -v gateodd | head -1 | cut -d'|' -f1)
sed -i '' "s/^\($r|[^|]*|[^|]*|[^|]*|\)t7|/\1t4|/" "$C/tables/q287.txt"; (cd "$C" && run/freeze_r7.sh freeze > /dev/null && printf 'SLOT  x\n' > TOOL7.sha256 && rm TOOL7.sha256 && run/freeze_r7.sh freeze > /dev/null && run/freeze_r7.sh tool7 "$SF" > /dev/null); stage
stopcase "a t4 row at an odd width ($r, frozen that way) fails as the rgn4 tool refuses it: an unexplained failure stops q287" 4 q287

# ---- 4. the freeze and its t7 slot -----------------------------------------------------------------------------------------------
world model; ttree
(cd "$C" && run/freeze_r7.sh verify > /dev/null 2>&1) && bad "verify without the t7 hash passed" || ok "freeze: verify without the t7 hash is refused"
(cd "$C" && run/freeze_r7.sh verify "$Z64" > /dev/null 2>&1) && bad "verify with another hash passed" || ok "freeze: verify with a hash TOOL7.sha256 does not hold is refused"
(cd "$C" && run/freeze_r7.sh verify "$SF" > /dev/null 2>&1) && ok "freeze: verify with the lead's hash passes" || bad "verify with S7"
(cd "$C" && run/freeze_r7.sh tool7 "$Z64" > /dev/null 2>&1) && bad "tool7 replaced a hash" || ok "freeze: tool7 does not replace a hash it already holds"
C2=$W/slot; mkdir -p "$C2"; cp -R "$C"/. "$C2/"
printf 'SLOT-the-lead-writes-the-t7-sha256-here-with-run/freeze_r7.sh-tool7  /home/jtorra/scratch/r7r/bin/sgxfive-test-t7\n' > "$C2/TOOL7.sha256"
(cd "$C2" && run/freeze_r7.sh verify "$SF" > /dev/null 2>&1) && bad "the slot verified" || ok "freeze: the session as built (TOOL7.sha256 the slot) does not verify until the lead writes it"
(cd "$C2" && run/freeze_r7.sh tool7 xyz > /dev/null 2>&1) && bad "tool7 took a non-hash" || ok "freeze: tool7 refuses a value that is not 64 hex digits"
(cd "$C" && echo "#" >> tables/q086.txt && run/freeze_r7.sh verify "$SF" > /dev/null 2>&1) && bad "a changed table verified" || ok "freeze: a changed table fails verify"
(cd "$C" && cp "$P/tables/q086.txt" tables/q086.txt && : > tables/new.txt && run/freeze_r7.sh verify "$SF" > /dev/null 2>&1) && bad "a new table verified" || ok "freeze: a file added since fails verify"
(cd "$C" && rm tables/new.txt && printf 'x' >> "bins/$(ls bins | head -1)" && run/freeze_r7.sh verify "$SF" > /dev/null 2>&1) && bad "a changed program verified" || ok "freeze: a changed staged program fails verify"
(cd "$P" && grep -q "PREDICTIONS.sha256\|predictions/q287.tsv" FROZEN.sha256) && ok "freeze: the predictions are in FROZEN.sha256" || bad "predictions not frozen"

# ---- 5. the guard -----------------------------------------------------------------------------------------------------------------
"$P/run/guard_r7.sh" > /dev/null && ok "guard: the session is clean" || bad "guard: the session is not clean: $("$P/run/guard_r7.sh" | head -3)"
inject() { local nm=$1 f=$2 line=$3; local G=$W/g$RANDOM$RANDOM; mkdir -p "$G"; cp -R "$P/run" "$P/tables" "$P/lead" "$G/"
	printf '%s\n' "$line" >> "$G/$f"
	"$P/run/guard_r7.sh" "$G" > /dev/null 2>&1 && bad "guard missed: $nm" || ok "guard catches: $nm"; }
inject "a /tmp work file" run/run_stage.sh 'echo x > /tmp/r7r.out'
inject "a knob write other than the rgn knob" run/run_stage.sh 'dbg_write render_pb_pages 0x40'
inject "a delete outside drop_work" run/lib_r7.sh 'rm -rf "$KEEP"'
inject "a wait loop" run/run_stage.sh 'while true; do sleep 1; done'
inject "a timeout without -k" run/lib_r7.sh 'sudo -n timeout 20 "$T4" fill'
inject "an unprivileged debugfs read" run/lib_r7.sh 'cat "$D/regs"'
inject "an unbounded ssh in the driver" run/r7.sh 'ssh $SSHO "$T" true'
inject "a kreg in a table" tables/q086.txt 'x|heldout|risky|expectdiff|t4|tri --kreg 0x0c00=1'
inject "a kpoke-render of a register page" tables/q086.txt 'x|heldout|risky|expectdiff|t4|tri --aa4 --kpoke-render 1:rd:1=0x0'
inject "a fourth tool" tables/s0.txt 'x|heldout|safe|expectdiff|t8|tri'
inject "a program outside the staged directory" tables/q139.txt 'x|heldout|safe|-|t4|probe --tri pixel /home/x/other.bin'
inject "a fill row" tables/s0.txt 'x|heldout|safe|expectdiff|t4|fill --width 64'
inject "the build script reaching the laptop" lead/build_tool7.sh 'scp x "$SGX_TARGET_HOST:"'
inject "a reboot" run/lib_r7.sh 'sudo -n reboot'
inject "a clock-gate register" run/run_stage.sh 'echo CLKGATE'
inject "trc_hazard" tables/q293.txt 'x|heldout|safe|expectdiff|t4|tri --trc_hazard'

# ---- 6. dry runs ---------------------------------------------------------------------------------------------------------------
world model; ttree
out=$(env $(envw) SGX_DRY_RUN=1 bash "$C/run/stage_r7.sh" "$SF" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q "scratch/r7r/bin/sgxfive-test-t7" && echo "$out" | grep -q "mkdir -p scratch/r7r/run/run" && ! echo "$out" | grep -qE '(^|[ :])/tmp' \
	&& ok "stage_r7.sh dry run: the commands, every path under ~/scratch/r7r" || bad "stage dry run: rc $rc"
out=$(env $(envw) SGX_DRY_RUN=1 bash "$C/run/r7.sh" "$SF" 2>&1); rc=$?
[ $rc = 0 ] && [ "$(echo "$out" | grep -c "run_stage.sh [a-z0-9-]* [0-9a-f]* [0-9-]* $SF")" = 9 ] && ok "r7.sh dry run: nine stages, each with the FROZEN and t7 hashes" || bad "r7.sh dry run: rc $rc"
out=$(env $(envw) bash "$C/run/r7.sh" 2>&1); rc=$?
[ $rc = 2 ] && ok "r7.sh without the t7 hash: usage (rc 2)" || bad "r7.sh without hash: rc $rc"
out=$(SGX_DRY_RUN=1 RESGX545_MAIN=/Users/jtorra/src/resgx545 bash "$C/lead/build_tool7.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'sgxt-r7r' && ! echo "$out" | grep -q 'u@fake' && ok "lead/build_tool7.sh dry run: archive of 1c64f3a checked against TOOL7SRC.sha256, build host only" || bad "build dry run: rc $rc: $(echo "$out" | head -2)"

# ---- 7. the staged tree --------------------------------------------------------------------------------------------------------
world model; ttree; stage
L=$M/home/scratch/r7r/run
s=$("$PY" "$P/score/sessioncheck.py" staged "$P/run" run_stage.sh lib_r7.sh r7.env 2>&1); r=$?   # src: every runner file; staged: the three stage_r7.sh copies
[ $r = 0 ] && ok "sessioncheck staged: $(echo "$s" | tail -1)" || bad "sessioncheck staged: $s"
[ "$(cd "$L/run" && ls | sort | tr '\n' ' ')" = "lib_r7.sh r7.env run_stage.sh " ] && ok "  the laptop's run/ holds exactly the three files stage_r7.sh copies" || bad "  laptop run/: $(ls "$L/run")"
e=$(cd "$M/home" && "$PY" "$P/score/sessioncheck.py" envi $(for v in $(envw) PY=$PY R7_TOOL_SHA=$SF R7_TOOL6_SHA=$SF R7_SRCV_EXPECT=MOCKSRCV RESET_WAIT=0 HEALTH_WAIT=0 TEE_GRACE=30 HOME=$M/home; do echo "--set $v"; done) \
	-- bash "$L/run/run_stage.sh" s0 "$(sha "$C/FROZEN.sha256")" "$ATT" "$SF" 2>&1); r=$?
[ $r = 0 ] && ok "sessioncheck envi: the staged runner's s0 under env -i, no command not found" || bad "sessioncheck envi: $(echo "$e" | tail -3)"

[ $fail = 0 ] && echo "run_mock: ALL PASS" || echo "run_mock: FAILURES"
exit $fail
