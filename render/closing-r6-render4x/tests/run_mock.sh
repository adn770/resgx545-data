#!/bin/bash
# tests/run_mock.sh: the r6-render4x runner and driver end to end against the ARGV-DRIVEN fake tool (tests/worlds.py) and a fake debugfs
# whose directory is mode 000 (only the sudo shim reaches it: an unprivileged access fails, as on the laptop).  Copied from r5-render4x's.
#   1. the whole driver (staging, k.sh, gates and gate files, scorer, verdict) in the model world and in worlds that stop (a4 faults;
#      K-OR's eighth fault with rows left), over two attempts (s0 in the first, a in the second: s0 read through the gate file);
#   2. the laptop files: everything under ~/scratch/r6x and one mktemp directory under ~/scratch/tmp, every work directory removed
#      after the stage (and after a stop), nothing in $TMPDIR; the free-space check (preflight and before each job, rc 21);
#   3. no timing window on the fake's start-up: a fake that takes 3 s to answer, with HOLD_READ 0.2 s, still gives the held rows'
#      faults and sets (the regs read of the held flow waits for the fake's answer, not for a clock);
#   4. the runner's rules: knobs written after the reset, read back, restored after every job and at every exit; strict health after
#      every fault; the limit with rows left (rc 15); a fault that is not E845's word (rc 18); an unexpected fault (rc 4); every other
#      stop code; kpoke kept after each job;
#   5. the guard (injections into copies of the tree);  6. the driver's dry run, knob checks and restaging;
#   7. stage B's design: a fake set B added to a copy of the tree is frozen, staged and run as a second freeze while stage A's
#      FROZEN.sha256 stays byte for byte and still verifies.
# Needs a current freeze (run/freeze_k.sh freeze).  Its own files go to one mktemp directory under debug/.
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
"$P/run/freeze_k.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_k.sh freeze)"; exit 1; }
N=0
world() { # world [WORLD]: a fresh fake laptop running WORLD (default model)
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/log" "$M/home" "$M/tmpdir"
	for f in reset regs render_param render_tadata kpoke hold_recovery; do : > "$M/dbgreal/$f"; done
	echo "${FAKE_ROOM_INIT:-0}" > "$M/dbgreal/render_tail_room"
	echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_RGN_INIT:-0}" > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${FAKE_PB_INIT:-}" ] && echo "$FAKE_PB_INIT" > "$M/dbgreal/render_pb_pages"
	[ -n "${FAKE_DF_INIT:-}" ] && echo "$FAKE_DF_INIT" > "$M/fake/df_kb"
	chmod 000 "$M/dbg"
	FAKE_WORLD=${1:-model}
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh"
export K_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") K_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=0.2 HOLD_GAP=0.1 TEE_GRACE=3
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log HOME=$M/home TMPDIR=$M/tmpdir FAKE_P=$P/tests"; }
KD() { echo "$M/home/scratch/r6x/out/$ATT/$1"; }
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; echo $?; }
stagebins() { mkdir -p "$M/home/scratch/r6x/stage"; cp "$P"/bins/*.bin "$M/home/scratch/r6x/stage/"; }
rgn_now() { echo $(( $(cat "$M/dbgreal/render_rgn_arrays") )); }
pb_now() { echo $(( $(cat "$M/dbgreal/render_pb_pages") )); }
hold_now() { cat "$M/fake/hold"; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
leftover() { ls -A "$M/home/scratch/tmp" 2>/dev/null; ls -A "$M/tmpdir" 2>/dev/null; }
copytree() { C=$W/tree$N$RANDOM; mkdir -p "$C"
	cp -R "$P/run" "$P/sets" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }
refreeze() { (cd "$1" && rm -f FROZEN.sha256 PREDICTIONS.sha256 && run/freeze_k.sh freeze > /dev/null); }

# ---- the driver pieces every world below uses --------------------------------------------------------------------------------
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/sets" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	mkdir -p "$D2T/debug"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$K_TOOL_SHA/" "$P/run/k.env" > "$D2T/run/k.env"
	printf '%s  /home/jtorra/sgxfive-test-rgn4\n' "$K_TOOL_SHA" > "$D2T/TOOL.sha256"
	refreeze "$D2T"; }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; }
drvenv() { echo "$(envw) FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4"; }
drive() { # drive WORLD [ENV...]: stage and run the whole driver on a fresh laptop; sets OUT, RC, D2T, M
	local wn=$1; shift
	world "$wn"; dtree; fakehome
	env $(drvenv) bash "$D2T/run/stage_k.sh" > "$M/log/stage.log" 2>&1 || { bad "staging for world $wn: $(tail -n 2 "$M/log/stage.log")"; }
	OUT=$(env $(drvenv) "$@" K_ATT=full bash "$D2T/run/k.sh" ${DSTAGES:+--only $DSTAGES} 2>&1); RC=$?
	VERDICT=$("$PY" "$D2T/score/score_r.py" verdict "$D2T/out/full" 2>&1)
}

# ---- 1. the whole driver -----------------------------------------------------------------------------------------------------
drive model
nst=$(echo "$OUT" | grep -c '^stage [a-z0-9]* done, health ok, render_rgn_arrays 0x00000000, render_pb_pages 0x00000422')
[ $RC = 0 ] && [ "$nst" = 3 ] && echo "$OUT" | grep -q '^r6-render4x set A done' && ok "world model: the driver runs s0, a, t, health ok, both knobs read back at their defaults after each" \
	|| { bad "world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
for k in "session: s0: controls" "H-TPM (a): H-TPM: a four-array 4x job faults iff" "(11 of 11 rows decided)" "h1: fault, BIF_INT_STAT bits 15:0 0x0100" "set equal (43)" "set equal (511)" \
	"a variants: variants of the Z-order rule no decided row contradicts: TPM-y-rgn" "Q293 (t): Q293: CR_TE_AA 0xc0000000" "(3 of 3 rows decided)"; do
	echo "$VERDICT" | grep -qF "$k" || bad "world model verdict lacks: $k"
done
echo "$VERDICT" | grep -Eq 'NODATA|READER-MISS|cannot tell|not run|not supported' && bad "  the model world's verdict has NODATA, READER-MISS, cannot tell, not run or not supported: $VERDICT" || ok "  the verdict decides every question (no NODATA, READER-MISS, cannot tell, not run, not supported)"
cat "$D2T"/out/full/score-*.txt | grep -Eq 'NODATA|READER-MISS|cannot tell' && bad "  a stage score has NODATA, READER-MISS or cannot tell" || ok "  no stage score has NODATA, READER-MISS or cannot tell"
wr=$(writes | awk '{print $1}' | sort -u | tr '\n' ' ')
[ "$wr" = "hold pb reset rgn " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs writes of the session: reset, render_rgn_arrays, render_pb_pages (0x422), hold_recovery" || bad "  debugfs writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
grep '^pb ' "$M/fake/writes" | grep -vq '^pb 0x422$' && bad "  a render_pb_pages write other than 0x422 in stage A" || ok "  every render_pb_pages write is 0x422 (stage A has no PB knob)"
[ "$(rgn_now)" = 0 ] && [ "$(pb_now)" = 1058 ] && [ "$(hold_now)" = N ] && ok "  at the end render_rgn_arrays 0, render_pb_pages 0x422, hold_recovery N" || bad "  knobs at the end: $(rgn_now) $(pb_now) $(hold_now)"
nh=$(writes | grep -c '^hold Y'); [ "$nh" = 2 ] && ok "  hold_recovery Y was written twice (h1, h2)" || bad "  hold Y writes $nh"
OA=$M/home/scratch/r6x/out/full
ls "$OA/a" | grep -q 'h1-1024x800-held.heldtadata.bin.gz' && ls "$OA/a" | grep -q 'h2-1280x768-held.heldtadata.bin.gz' && ok "  the held rows kept render_tadata read during the hold, under ~/scratch/r6x/out" || bad "  held dumps"
ls "$OA/t" | grep -q 't5-line-tec0.p1131-green__0.param.bin.gz' && ls "$OA/t" | grep -q 't6-point-tec0.p1131-psizes__1.param.bin.gz' && ls "$OA/t" | grep -q 't7-tri-te40-poke11.kpoke.txt.gz' \
	&& ok "  probe dumps named from their argv (PROG); every job's debugfs kpoke kept" || bad "  probe dump names / kpoke"
zcat < "$OA/t/t7-tri-te40-poke11.dmesg.gz" | grep -q 'kpoke par:11=0x00000001 applied' && ok "  t7's kernel slice holds the fake kernel's 'kpoke par:11=0x00000001 applied'" || bad "  t7 kpoke line"
grep -q "^s0 at $D2T/out/full/s0\$" "$D2T/out/full/gate-a.txt" && grep -q "^s0 at $D2T/out/full/s0\$" "$D2T/out/full/gate-t.txt" && ok "  the gate files name where s0 was found" || bad "  gate files"
nf=$(awk -F'\t' '$9 == "fault"' "$D2T/out/full/a/cases.tsv" | wc -l | tr -d ' ')
[ "$nf" = 6 ] && ok "  six fault-class events in the model world (a2, a3, a5, a14, h1, h2), as frozen" || bad "  faults: $nf"
[ -z "$(leftover)" ] && ok "  laptop files: no work directory left in ~/scratch/tmp, nothing in \$TMPDIR" || bad "  left over: $(leftover | tr '\n' ' ')"
[ -d "$M/home/scratch/r6x/run/run" ] && [ -d "$M/home/scratch/r6x/stage" ] && [ -z "$(ls -A "$M/home" | grep -v '^scratch$' | grep -v '^sgxfive-test-rgn4$')" ] \
	&& ok "  the fake home holds only ~/scratch (r6x/{run,stage,out}, tmp) and the tool" || bad "  home: $(ls -A "$M/home" | tr '\n' ' ')"
grep -q "## work directory: $M/home/scratch/tmp/r6x\." "$OA/a/runner.log" && ok "  the runner's work directory was ~/scratch/tmp/r6x.XXXXXX" || bad "  work directory line"

DSTAGES="s0 a" drive rule:K-OR
nf=$(awk -F'\t' '$9 == "fault"' "$D2T/out/full/a/cases.tsv" | wc -l | tr -d ' ')
[ $RC = 15 ] && [ "$nf" = 8 ] && ! grep -q '^a1r-' "$D2T/out/full/a/cases.tsv" && ! grep -q '^h1-' "$D2T/out/full/a/cases.tsv" \
	&& ok "world K-OR: a1 faults (a1r skipped), the 8th fault-class event with rows left stops stage a (rc 15) before a14, h1, h2" || { bad "world K-OR: rc $RC, $nf faults"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
[ -z "$(leftover)" ] && [ "$(rgn_now)" = 0 ] && [ "$(hold_now)" = N ] && ok "  after the stop: no work directory left, knobs at their defaults" || bad "  after the stop: $(leftover) $(rgn_now) $(hold_now)"
DSTAGES="s0 a" drive a4-fault
[ $RC = 4 ] && echo "$OUT" | grep -q 'STOP: unexpected fault in a4-1024x768-max2048x1024' && [ "$(grep -c . "$D2T/out/full/a/cases.tsv")" = 2 ] \
	&& ok "world a4-fault: the premise faulting stops stage a at once (rc 4) after strict health; nothing else runs" || { bad "world a4-fault: rc $RC"; echo "$OUT" | tail -3 | sed 's/^/     /'; }
DSTAGES="s0 a" drive h-xset
echo "$VERDICT" | grep -q "the lost set is the x-even interleave's" && [ $RC = 0 ] && ok "world h-xset: the driver's verdict names the x-even set (rc 0)" || bad "world h-xset: rc $RC"
DSTAGES="s0 t" drive t-field
echo "$VERDICT" | grep -q 'H-FIELD: the inserted dword is non-zero at 0xc0000000' && ok "world t-field: the driver's verdict reads H-FIELD" || bad "world t-field"
DSTAGES="s0 a" drive s0-miss
echo "$OUT" | grep -q 'SKIPPED: a' && ! grep -q 'aa4 --poke cmd:1=0xe0000000.*--width 1024 --height 1280' "$M/fake.log" && ok "world s0-miss: a failed control closes stage a's gate: nothing of a ran" || { bad "world s0-miss: rc $RC"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
# two attempts: s0 in the first, a in the second; a's score reads s0 through the gate file
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
env $(drvenv) K_ATT=a1 bash "$D2T/run/k.sh" --only s0 > "$M/log/a1.log" 2>&1
env $(drvenv) K_ATT=a2 bash "$D2T/run/k.sh" --only a > "$M/log/a2.log" 2>&1; rc=$?
[ $rc = 0 ] && grep -q "^s0 at $D2T/out/a1/s0\$" "$D2T/out/a2/gate-a.txt" && ! grep -q NODATA "$D2T/out/a2/score-a.txt" && grep -q '(11 of 11 rows decided)' "$D2T/out/a2/score-a.txt" \
	&& ok "two attempts: the gate file of the second names the first's s0, and a's own score reads s0 there (no NODATA)" || { bad "two attempts: rc $rc"; tail -3 "$D2T/out/a2/score-a.txt" | sed 's/^/     /'; }

# ---- 2. free space ---------------------------------------------------------------------------------------------------------------
FAKE_DF_INIT=200000 world model; rc=$(runst "$P" s0)
[ "$rc" = 21 ] && grep -q 'less than 300 MiB free on ~' "$M/log/s0.log" && [ ! -f "$M/fake/resets" ] && [ -z "$(leftover)" ] \
	&& ok "preflight: 195 MiB free on ~ stops before anything is touched (rc 21); the work directory is gone" || bad "free space at the preflight: rc $rc, $(leftover)"
world model; rc=$(runst "$P" s0 FAKE_RULES='--width 288 --height 144|bigdump')
[ "$rc" = 21 ] && grep -q 'STOP: less than 300 MiB free on ~ before s0-4x-1024x768' "$M/log/s0.log" && grep -q '^s0-4x-288x144' "$(KD s0)/cases.tsv" \
	&& [ "$(pb_now)" = 1058 ] && [ "$(rgn_now)" = 0 ] && [ -z "$(leftover)" ] && ok "a job that eats the free space: the next job stops before it starts (rc 21), knobs restored, work directory gone" || bad "free space mid-stage: rc $rc"

# ---- 3. no timing window on the fake's start-up --------------------------------------------------------------------------------
world model; rc=$(runst "$P" a FAKE_SLOW_START=3)
[ "$rc" = 0 ] && awk -F'\t' '$1 ~ /^h[12]-/ && $9 == "fault" && $10 == "held" && $11 == "256"' "$(KD a)/cases.tsv" | grep -c . | grep -q '^2$' \
	&& ok "a fake that takes 3 s to answer with HOLD_READ 0.2 s: both held rows read their fault at snap 1 (no start-up timing)" || { bad "slow fake: rc $rc"; grep -E 'STOP|class' "$M/log/a.log" | head -5; }
"$PY" "$P/score/score_r.py" a "$(KD a)" 2>/dev/null | grep -q 'set equal (43)' && ok "  and h1's held dump scores set equal (43)" || bad "  slow fake: h1's set"

# ---- 4. the runner's rules ----------------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
world model; rc=$(runst "$P" a FAKE_HEALTH_SEQ="ok ok fail")
[ "$rc" = 16 ] && grep -q '^a2-1024x1296' "$(KD a)/cases.tsv" && ! grep -q '^a3-' "$(KD a)/cases.tsv" && ok "strict: the first health after a2's fault failing stops the stage (rc 16) after the recovery; a3 does not run" || { bad "strict: rc $rc"; grep -E 'STOP|abort' "$M/log/a.log" | head -4; }
nres=$(awk '/resgx545 r6x class a2-/ {s=1} s && /resgx545 r6x health a2-1024x1296 fill try/ {exit} s && /SGX reset: BIF_FAULT/ {n++} END {print n+0}' "$M/kmsg")
[ "$nres" = 0 ] && ok "  strict: no reset of the runner's between a2's class line and its first health" || bad "  runner reset before strict health: $nres"
[ -z "$(leftover)" ] && ok "  after the strict stop the work directory is gone" || bad "  left over after rc 16: $(leftover)"
world model; stopcase "a fault that is not E845's word (TA side 0x20006061) in a hypothesis row stops the stage" 18 a FAKE_RULES='--width 1024 --height 1296|fault'
grep -q "is not E845's 3D-side word (bits 15:0 4, BIF_FAULT 0x20006061)" "$M/log/a.log" && ! grep -q '^a3' "$(KD a)/cases.tsv" && ok "  the stop names the word; a3 did not run" || bad "  rc 18 text"
world model; copytree
sed -i '' -e 's/^#limit 8$/#limit 1/' "$C/tables/a.txt"; refreeze "$C"
rc=$(runst "$C" a); [ "$rc" = 15 ] && grep -q '^a2-1024x1296' "$(KD a)/cases.tsv" && ! grep -q '^a3-' "$(KD a)/cases.tsv" \
	&& ok "the limit with rows left: the 1st fault (a2) of a stage limited to 1 stops it before a3 (rc 15)" || { bad "limit: rc $rc"; grep STOP "$M/log/a.log"; }
world model; rc=$(runst "$P" a)
[ "$rc" = 0 ] && awk -F'\t' '$1 ~ /^h[12]-/ && $9 == "fault" && $10 == "held" && $13 == "yes"' "$(KD a)/cases.tsv" | grep -c . | grep -q '^2$' \
	&& ok "stage a: both held rows fault in held mode with the kernel's hold message; 6 events within the limit 8: rc 0" || { bad "stage a: rc $rc"; grep STOP "$M/log/a.log"; }
grep -q 'fault: BIF_INT_STAT bits 15:0 256, BIF_FAULT 0x10000011' "$M/log/a.log" && ok "  the held faults' word read from snap 1" || bad "  held word"
n=$(ls "$(KD a)"/*.kpoke.txt.gz | wc -l | tr -d ' '); [ "$n" = 13 ] && ok "  every job's kpoke read kept (13)" || bad "  kpoke kept: $n"
world model; stopcase "hold_recovery does not read back Y (h1)" 9 a FAKE_HOLD_NOY=1
world model; stagebins; stopcase "render_rgn_arrays does not read back 1 (stage t)" 19 t FAKE_RGN_STUCK=1
world model; stagebins; stopcase "render_rgn_arrays does not go back to 0" 19 t FAKE_RGN_STUCK_AT0=1
FAKE_PB_INIT=0x83 world model; stopcase "preflight: render_pb_pages not 0x422 at the start" 1 s0
[ ! -f "$M/fake/resets" ] && [ ! -s "$M/fake/writes" ] && [ -z "$(leftover)" ] && ok "  nothing touched (no reset, no knob write), no work directory left" || bad "  the failed preflight touched the GPU or left files"
FAKE_HOLD_INIT=Y world model; stopcase "preflight: hold_recovery not N at the start" 1 s0
FAKE_RGN_INIT=1 world model; stopcase "preflight: render_rgn_arrays not 0 at the start" 1 s0
world model; stopcase "fatal kernel message in a row (the knobs are still restored, no reset)" 3 s0 FAKE_RULES='--width 288 --height 144|fatal'
[ "$(pb_now)" = 1058 ] && [ "$(rgn_now)" = 0 ] && [ "$(hold_now)" = N ] && [ -z "$(leftover)" ] && ok "  after the fatal stop the three knobs are restored, no work directory left" || bad "  after fatal: $(pb_now) $(rgn_now) $(hold_now) $(leftover)"
world model; stopcase "a row does not return (freeze)" 6 a FAKE_RULES='--width 992 --height 1280|timeout'
world model; stopcase "an unexplained failure (rc 1, no diff line) stops" 4 s0 FAKE_RULES='--width 288 --height 144|nodiff'
world model; stopcase "an unexpected hang stops" 4 a FAKE_RULES='--width 512 --height 1536|hang'
world model; stopcase "the pre-job reset fails" 13 s0 FAKE_RESET_FAIL_FROM=2
world model; stopcase "health: the first failed recovery stops (begin)" 5 s0 FAKE_HEALTH_BAD=1
world model; stopcase "registers unreadable" 12 s0 FAKE_SNAP_FAIL=1
FAKE_STATE_INIT='0x4 0x20006061 0x480 0x20000000' world model; stopcase "a fault latched before the job (snap 0)" 14 s0 FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
world model; stopcase "the kernel's reset information lines inside a job are not bad" 0 s0 FAKE_RULES='--width 1024 --height 768 -n 1|resetinfo'
world model; printf 'gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20008062 (PD 0x0) stalls job 3, recovering\n' >> "$M/kmsg"
rc=$(runst "$P" s0); [ "$rc" = 0 ] && ! zcat < "$(KD s0)/s0-1x-1024x768.dmesg.gz" | grep -q 'stalls job 3' && ok "a fault line logged before the first case marker is not in any job's slice (rc 0)" || bad "slice by marker: rc $rc"
for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kpoke; do
	world model; mv "$M/dbgreal/$f" "$M/dbgreal/$f.gone"
	rc=$(runst "$P" s0)
	[ "$rc" = 1 ] && grep -q "has no debugfs $f" "$M/log/s0.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $f: rc 1, nothing touched" || bad "preflight without $f: rc $rc"
done
world model; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" s0)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/s0.log" && ok "srcversion loaded != installed: rc 1" || bad "srcversion: rc $rc"
world model; rc=$(K_SRCV_EXPECT=99CD90DA26E3AFF9C450517 runst "$P" s0)
[ "$rc" = 1 ] && grep -q 'is not the expected build (99CD90DA26E3AFF9C450517)' "$M/log/s0.log" && ok "installed = loaded but not 99CD90DA...: rc 1" || bad "expected build: rc $rc"
grep -q '^SRCV_EXPECT=99CD90DA26E3AFF9C450517$' "$P/run/k.env" && ok "k.env pins srcversion 99CD90DA26E3AFF9C450517 (fork a2788bd8, the rgn4 module of the handover)" || bad "k.env srcversion"
grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/k.env" && ok "k.env pins ~/sgxfive-test-rgn4 e6951558..." || bad "k.env tool"
world model; rc=$(K_TOOL_SHA=0000 runst "$P" s0); [ "$rc" = 1 ] && grep -q "the tool is not the rgn4 build" "$M/log/s0.log" && ok "preflight: another tool: rc 1" || bad "tool sha: rc $rc"
world model; rc=$(FSHA=0000 runst "$P" s0); [ "$rc" = 1 ] && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha: rc $rc"
world model; rc=$(env $(envw) bash "$P/run/run_stage.sh" s0 "$(sha "$P/FROZEN.sha256")" "$ATT" ../FROZEN.sha256 > "$M/log/fz.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q 'is not FROZEN.sha256 or FROZEN-X.sha256' "$M/log/fz.log" && ok "a freeze file name other than FROZEN.sha256 / FROZEN-X.sha256 is refused" || bad "freeze name: rc $rc"
world model; rc=$(runst "$P" s0); rc2=$(runst "$P" s0)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: $rc $rc2"
world model
env $(envw) bash "$P/run/run_stage.sh" s0 "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
[ "$rc" = 0 ] && grep -q '^## end' "$(KD s0)/runner.log" && [ -z "$(leftover)" ] && ok "the reader of the runner's output goes away: the stage completes, runner.log has it all, no work directory left" || bad "closed pipe: rc $rc"
world model; rc=$(runst "$P" t); [ "$rc" = 8 ] && grep -q 'missing program' "$M/log/t.log" && ok "stage t without its programs staged: rc 8, nothing touched" || bad "missing bins: rc $rc"
world model; stagebins; printf 'x' >> "$M/home/scratch/r6x/stage/p1131-green__0.bin"
rc=$(runst "$P" t); [ "$rc" = 1 ] && grep -q 'is not the frozen one' "$M/log/t.log" && ok "a staged program that is not the frozen one: rc 1" || bad "tampered bin: rc $rc"
world model; stagebins; rc=$(runst "$P" t); [ "$rc" = 0 ] && ok "stage t with the programs staged: rc 0, four jobs ($(grep -c '^t' "$(KD t)/cases.tsv"))" || { bad "stage t: rc $rc"; grep -E 'STOP|abort|missing' "$M/log/t.log" | head -3; }
# rm_work refuses anything outside the runner's own mktemp directory
world model; copytree
printf '\nrm_work "$HOME/scratch/r6x"\n' >> "$C/run/lib_k.sh"; refreeze "$C"
rc=$(runst "$C" s0); [ "$rc" = 1 ] && grep -q 'rm_work: .*/scratch/r6x is not under' "$M/log/s0.log" && [ -d "$M/home/scratch/r6x" ] && ok "rm_work refuses a path outside its mktemp directory (rc 1), ~/scratch/r6x intact" || bad "rm_work outside: rc $rc"
# table knobs and dbg_write refusals
for kn in bif rgn:4 rgn:0 noreset idle stophang pb:0x10 pb:0x500 pb:83 hold hypo:G cell:ctx needs:o5=fault room:0x4000; do
	world model; copytree
	printf '#stage x-mock\n#limit 1\nm-1|heldout|risky|%s expectdiff|-|tri --keep-going --width 64 --height 64\n' "$kn" > "$C/tables/x-mock.txt"
	sed -i '' -e 's#^SET_TABLES="\(.*\)"$#SET_TABLES="\1 tables/x-mock.txt"#' "$C/sets/A.env"; refreeze "$C"
	rc=$(runst "$C" x-mock)
	[ "$rc" = 7 ] && [ ! -f "$M/fake/resets" ] && ok "the knob '$kn' is refused before anything runs (rc 7)" || bad "knob $kn: rc $rc"
done
for nm in "hold_recovery X" "render_rgn_arrays 4" "render_pb_pages 0x10" "render_pb_pages 0x423" "alias_skip 1" "kpoke x" "kregnow 0x0c04=0x1" "render_tail_room 0x4000"; do
	world model; copytree
	printf '\ndbg_write %s\n' "$nm" >> "$C/run/lib_k.sh"
	refreeze "$C"; rc=$(runst "$C" s0)
	[ "$rc" = 7 ] && grep -q "dbg_write: ${nm} is not" "$M/log/s0.log" && ok "dbg_write $nm is refused at run time: rc 7" || bad "dbg_write $nm: rc $rc"
done

# ---- 5. the guard ------------------------------------------------------------------------------------------------------------
"$P/run/guard_k.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"
for inj in 'echo 1 | sudo -n tee "$D/kreg"' 'echo 1 | sudo -n tee "$D/kregnow"' 'echo par:11=0 | sudo -n tee "$D/kpoke"' 'echo 1 | sudo -n tee "$D/kicker"' \
	'until false; do :; done' 'x=$(cat f | tail -1)' 'sudo -n tee "$D/reset" || true' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' \
	'dbg_write alias_skip 1' 'dbg_write hold_recovery Y' 'dbg_write render_rgn_arrays 4' 'dbg_write render_pb_pages 0x10' 'echo 4 | sudo -n tee "$D/render_rgn_arrays"' \
	'echo 0x10 | sudo -n tee "$D/render_pb_pages"' 'echo x | sudo -n tee "$KMSG"' 'echo x | sudo -n tee /dev/kmsg' 'git status' 'rm -f x' 'reboot' \
	'echo 1 > /sys/x/clkgate' 'echo x >> own_arm' 'sed -n 5,9p "$JW/dmesg.all"' 'set_hold Y' 'rgn_set 4' 'pb_set 0x10' 'sudo -n cat "$D/render_param" > "$D/x"' \
	'echo 1 | sudo -n tee "$D/render_tadata"' 'sudo -n timeout 60 "$T" tri' 'trc_hazard=1' 'make -C x' \
	'X=$(mktemp -d)' 'X=$(mktemp -d /tmp/r6x.XXXXXX)' 'cd /tmp' 'cp x /tmp/x' 'rm -rf "$KEEP"' 'rm -rf -- "$HOME/scratch"' 'echo x > ~/r5x-out/y' 'TMPDIR=/var/tmp' \
	'dbg_write render_tail_room 0x4000' 'echo 0x4000 | sudo -n tee "$D/render_tail_room"'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_k.sh"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; printf '%s\n' 'x=1; set_hold Y' >> "$C/run/run_stage.sh"; "$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: a second set_hold Y" || ok "guard: refuses a second set_hold Y in run_stage.sh"
copytree; sed -i '' -e '/^	space_ok || { echo "## STOP: less than/d' "$C/run/run_stage.sh"; "$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: no free-space check" || ok "guard: refuses a runner without the free-space check before each job"
copytree; sed -i '' -e 's/^MIN_FREE_MB=.*/MIN_FREE_MB=${MIN_FREE_MB:-100}/' "$C/run/k.env"; "$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: MIN_FREE_MB 100" || ok "guard: refuses MIN_FREE_MB below 200"
copytree; sed -i '' -e '/^	rm_work "\$JW"$/d' "$C/run/run_stage.sh"; "$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: no rm_work" || ok "guard: refuses a runner that keeps its work directories"
for tl in 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kreg x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going -n 2 --geometry 1 --kpoke-render 2:par:12=0x00000001' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render 2:par:11=0x00000001' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going -n 2 --geometry 1 --kpoke-render2 2:par:11=0x00000001' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-job 1:par:11=0x1' 'm-9|heldout|risky|rgn:1 expectdiff|-|probe --kpoke par:11=0x1 x.bin' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --fault' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --poke ta:1=2' \
	'm-9|heldout|risky|rgn:4 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|hold expectdiff|-|tri --keep-going' 'm-9|heldout|risky|rgn:1 expectdiff|0x0118|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --regs 0x0000-0x0c00' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --tadata-fill-render 1:7:0x00012340' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|probe --cmd 1=0x20000000 x.bin' 'm-9|heldout|risky|pb:0x10 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|room:0x4000 expectdiff|-|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --ctx2' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --words /x' 'm-9|heldout|risky|rgn:1|-|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|sh -c x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --aa4 yes' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --dump-render /tmp/x'; do
	copytree; printf '%s\n' "$tl" >> "$C/tables/a.txt"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed the table line: $tl" || ok "guard: refuses the table line '${tl#m-9|heldout|risky|}'"
done

# ---- 6. the driver: dry run, a knob left behind, gates, restaging ---------------------------------------------------------------
d=$(K_ATT=attX SGX_DRY_RUN=1 bash "$P/run/k.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_r.py gate a' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 2400 ssh' && echo "$d" | grep -q 'bounded 600 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "~/scratch/r6x/run/run/run_stage.sh s0 $fs attX FROZEN.sha256" && echo "$d" | grep -q "scratch/r6x/out/attX/a .*/out/attX/a" \
	&& ok "driver dry run: the gates, bounded ssh/scp (900 s s0, 2400 s a, 600 s t), the frozen sha256 and its name, one directory an attempt, ~/scratch/r6x" || { bad "driver dry run"; echo "$d" | head -12 | sed 's/^/     /'; }
! echo "$d" | grep -Eq 'r5x|r4g|r3k|r4a|r5e-|r5p-|r5d-|/tmp' && ok "no other session's laptop directory and no /tmp in the driver's commands" || bad "foreign directory in the dry run"
s=$(SGX_DRY_RUN=1 bash "$P/run/stage_k.sh" 2>&1)
echo "$s" | grep -q 'mkdir -p scratch/r6x/run/run scratch/r6x/run/tables scratch/r6x/stage scratch/r6x/out scratch/tmp' && ! echo "$s" | grep -Eq 'r5x|(^|[ :])/tmp' \
	&& ok "staging dry run: ~/scratch/r6x/{run,stage,out} and ~/scratch/tmp, nothing else" || { bad "staging dry run"; echo "$s" | head -5 | sed 's/^/     /'; }
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=leak FAKE_KNOB_LEAK=1 bash "$D2T/run/k.sh" --only s0 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_rgn_arrays is 0x00000004 after s0' && ok "render_rgn_arrays read as 4 after a stage stops the driver (rc 42)" || { bad "rgn after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=g1 bash "$D2T/run/k.sh" --only a 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'SKIPPED: a' && ok "no kept s0 closes the gate: a skipped cleanly (rc 0)" || { bad "gate: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world model; fakehome; out=$(env $(drvenv) bash "$P/run/stage_k.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the rgn4 build" && ok "staging refuses a laptop whose tool is not e6951558..." || bad "staging with a foreign tool: rc $rc"
world model; dtree; fakehome; env $(drvenv) bash "$D2T/run/stage_k.sh" > "$M/log/stage.log" 2>&1
n=$(ls "$M/home/scratch/r6x/stage" | wc -l | tr -d ' '); [ "$n" = 2 ] && [ -d "$M/home/scratch/tmp" ] && ok "staging copies the two programs to ~/scratch/r6x/stage and makes ~/scratch/tmp" || bad "staged programs: $n"
num_eq 0x00000000 0 && num_eq 0x00000001 1 && ! num_eq 0x00000004 1 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"

# ---- 7. stage B's design: a second freeze beside stage A's ----------------------------------------------------------------------
world model; dtree; fakehome
A0=$(sha "$D2T/FROZEN.sha256"); AP0=$(sha "$D2T/PREDICTIONS.sha256")
mkdir -p "$D2T/sets"
cat > "$D2T/sets/B.env" <<'EOF2'
SET_NAME=B
SET_STAGES=stages-B.txt
SET_FREEZE=FROZEN-B.sha256
SET_PREDS=PREDICTIONS-B.sha256
SET_RUNDIR=run
SET_SCORER=score/score_bx.py
SET_GUARD=run/guard_k.sh
SET_TABLES="tables/s0.txt tables/bx.txt"
SET_PREDFILES="predictions/bx.tsv"
SET_BINS=""
set_files() {
	echo score/score_bx.py score/scorekit.py run/freeze_k.sh run/guard_k.sh run/k.sh run/lib_check.sh run/lib_k.sh run/run_stage.sh run/stage_k.sh run/k.env
	echo sets/B.env stages-B.txt TOOL.sha256 gen/data/sources.lst
	echo $SET_TABLES $SET_PREDFILES
}
alarm_of() { echo 900; }
EOF2
printf 's0\nbx\n' > "$D2T/stages-B.txt"
{ echo '#stage bx'; echo '#limit 1'; grep '^s0-4x-288x144|' "$D2T/tables/s0.txt" | sed 's/^s0-4x-288x144|/bx1-4x-288x144|/'; } > "$D2T/tables/bx.txt"
printf 'case\tquantity\tvalue\tmodel\tset\tsource\nbx1-4x-288x144\trc\t0\tmock\tctl\tmock\n' > "$D2T/predictions/bx.tsv"
cat > "$D2T/score/score_bx.py" <<'EOF2'
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [here, os.path.join(os.path.dirname(here), "gen")]
import score_r as S
if sys.argv[1] == "gate":
    print("gate %s: open\ns0 at %s" % (sys.argv[2], S.stage_dir(sys.argv[3:], "s0")))
    sys.exit(0)
S.preds()
if sys.argv[1] == "verdict":
    print("SUMMARY: set B verdict"); sys.exit(0)
if sys.argv[1] == "s0":
    ls, r = S.s0_stage(sys.argv[2]); print("SUMMARY: " + r["summary"]); sys.exit(0)
c = S.L.read_cases(sys.argv[2]); print("SUMMARY: bx: %s" % {n: r["class"] for n, r in c.items()})
EOF2
(cd "$D2T" && run/freeze_k.sh freeze B > /dev/null); fb=$?
[ $fb = 0 ] && [ -f "$D2T/FROZEN-B.sha256" ] && [ "$(sha "$D2T/FROZEN.sha256")" = "$A0" ] && [ "$(sha "$D2T/PREDICTIONS.sha256")" = "$AP0" ] \
	&& (cd "$D2T" && run/freeze_k.sh verify A > /dev/null) && (cd "$D2T" && run/freeze_k.sh verify B > /dev/null) \
	&& ok "stage B as a second freeze: FROZEN-B.sha256 written, stage A's FROZEN.sha256 and PREDICTIONS.sha256 byte for byte, both sets verify" || bad "set B freeze: $fb"
(cd "$D2T" && run/freeze_k.sh freeze A > /dev/null 2>&1) && bad "  a second freeze of A was not refused" || ok "  a set's freeze is never rewritten (freeze A refused once frozen)"
env $(drvenv) bash "$D2T/run/stage_k.sh" > "$M/log/stageA.log" 2>&1; env $(drvenv) bash "$D2T/run/stage_k.sh" --set B > "$M/log/stageB.log" 2>&1; rc=$?
[ $rc = 0 ] && [ -f "$M/home/scratch/r6x/run/FROZEN.sha256" ] && [ -f "$M/home/scratch/r6x/run/FROZEN-B.sha256" ] && [ -f "$M/home/scratch/r6x/run/tables/bx.txt" ] \
	&& ok "  set B staged beside set A under ~/scratch/r6x/run (both freeze files there)" || { bad "  staging set B: rc $rc"; tail -3 "$M/log/stageB.log" | sed 's/^/     /'; }
out=$(env $(drvenv) K_ATT=bA bash "$D2T/run/k.sh" --only s0 2>&1); out=$(env $(drvenv) K_ATT=bB bash "$D2T/run/k.sh" --set B --only bx 2>&1); rc=$?
[ $rc = 0 ] && grep -q "^s0 at $D2T/out/bA/s0\$" "$D2T/out/bB/gate-bx.txt" && grep -q "SUMMARY: bx: {'bx1-4x-288x144': 'ok'}" "$D2T/out/bB/score-bx.txt" \
	&& ok "  k.sh --set B runs set B's stage with set B's freeze and scorer, its gate reading stage A's s0" || { bad "  running set B: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
rc=$(env $(envw) bash "$D2T/run/run_stage.sh" bx "$A0" "x$N" FROZEN.sha256 > "$M/log/bxA.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q 'table bx.txt is not the frozen one' "$M/log/bxA.log" && ok "  set B's table run under stage A's freeze is refused (rc 1)" || bad "  bx under A's freeze: rc $rc"
"$D2T/run/guard_k.sh" "$D2T" A > /dev/null 2>&1 && ok "  stage A's guard is unchanged by set B's files" || bad "  A's guard with set B present"
# ---- 8. set B itself (stage B, the r6-kernel module's fake: FAKE_KERNEL=b) end to end -----------------------------------------------
SRCVB=0123456789ABCDEF0123456
dtreeb() { D2T=$W/drvb$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/run-b" "$P/sets" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/stages.txt" "$P/stages-B.txt" "$P/TABLES.md" "$P/TABLES-B.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	mkdir -p "$D2T/debug"
	for k in run/k.env run-b/k.env; do sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$K_TOOL_SHA/" "$P/$k" > "$D2T/$k"; done
	sed -i '' -e "s/^SRCV_EXPECT=.*/SRCV_EXPECT=$SRCVB/" "$D2T/run-b/k.env"
	printf '%s  /home/jtorra/sgxfive-test-rgn4\n' "$K_TOOL_SHA" > "$D2T/TOOL.sha256"
	refreeze "$D2T"; (cd "$D2T" && run/freeze_k.sh freeze B > /dev/null); }
driveb() { # driveb WORLD [ENV...]: set B staged and run on a fresh fake r6-kernel laptop (srcversion SRCVB, from run-b/k.env)
	local wn=$1; shift
	world "$wn"; echo "$SRCVB" > "$M/srcv"; dtreeb; fakehome
	env -u K_SRCV_EXPECT $(drvenv) FAKE_KERNEL=b FAKE_MODINFO=$SRCVB bash "$D2T/run/stage_k.sh" --set B > "$M/log/stageB.log" 2>&1 || bad "staging set B for world $wn: $(tail -n 2 "$M/log/stageB.log")"
	OUT=$(env -u K_SRCV_EXPECT $(drvenv) FAKE_KERNEL=b FAKE_MODINFO=$SRCVB "$@" K_ATT=fullb bash "$D2T/run/k.sh" --set B ${DSTAGES:+--only $DSTAGES} 2>&1); RC=$?
	VERDICT=$("$PY" "$D2T/score/score_b.py" verdict "$D2T/out/fullb" 2>&1)
}
driveb model
nst=$(echo "$OUT" | grep -c '^stage [a-z0-9]* done, health ok')
[ $RC = 0 ] && [ "$nst" = 4 ] && echo "$OUT" | grep -q '^r6-render4x set B done' && ok "set B, world model: the driver runs s0b, b, k, r on the r6-kernel fake, health ok after each" \
	|| { bad "set B world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
for k in "H-ROOM (b): H-ROOM" "(8 of 8 rows decided)" "k3: set equal (171)" "H-TPM knob (k):" "(3 of 3 rows decided)" "largest (r):"; do
	echo "$VERDICT" | grep -qF "$k" || bad "set B verdict lacks: $k"
done
echo "$VERDICT" | grep -Eq 'NODATA|cannot tell|not run|not supported|FAILED' && bad "  set B's verdict: $VERDICT" || ok "  set B's verdict decides every question"
rw=$(grep '^room ' "$M/fake/writes" | awk '{print $2}' | sort -u | tr '\n' ' ')
[ "$rw" = "0 0x3000 0x4000 0xa000 0xb000 " ] && [ "$(cat "$M/dbgreal/render_tail_room")" = 0 ] && ok "  render_tail_room written 0 and the four knob values only, 0 at the end" || bad "  room writes: $rw / end $(cat "$M/dbgreal/render_tail_room")"
grep -q 'resgx545 r6x room-back k2-1280x1024-roomb000 0' "$M/kmsg" && grep -q 'knobs-read k2-1280x1024-roomb000 .* render_tail_room=0x0000b000' "$M/kmsg" && ok "  k2: the knob read back 0xb000 before the job, put back to 0 after it" || bad "  k2 knob sequence"
nf=$(cat "$D2T"/out/fullb/*/cases.tsv | awk -F'\t' '$9 == "fault"' | wc -l | tr -d ' '); [ "$nf" = 3 ] && ok "  three fault-class events (k1, k4, k3), as frozen" || bad "  set B faults: $nf"
[ -z "$(leftover)" ] && [ -f "$M/home/scratch/r6x/run/FROZEN-B.sha256" ] && [ -f "$M/home/scratch/r6x/run/run-b/run_stage.sh" ] && ok "  laptop: set B's runner in ~/scratch/r6x/run/run-b beside set A's freeze file; no work directory left" || bad "  set B laptop files: $(leftover)"
grep -q "^s0b at $D2T/out/fullb/s0b\$" "$D2T/out/fullb/gate-k.txt" && ok "  the gate files name where s0b was found" || bad "  set B gate files"
pubA="$(dirname "$(dirname "$P")")/closing/$(basename "$P")/FROZEN.sha256"; [ -f "$pubA" ] || pubA=$P/FROZEN.sha256
[ "$(sha "$pubA")" = 5fbd64f7d2ea61052f4ca60aa996026c35768a49d5b179e6a8b1e5b3a1b031e8 ] && "$P/run/freeze_k.sh" verify A > /dev/null && "$P/run/freeze_k.sh" verify B > /dev/null \
	&& ok "set A's FROZEN.sha256 is the one stage A ran with (5fbd64f7...), both sets verify" || bad "set A's freeze changed"
world model; echo "$SRCVB" > "$M/srcv"; dtreeb; fakehome; env -u K_SRCV_EXPECT $(drvenv) FAKE_KERNEL=b bash "$D2T/run/stage_k.sh" --set B > /dev/null 2>&1
rgb() { env -u K_SRCV_EXPECT $(envw) FAKE_KERNEL=b FAKE_MODINFO=$SRCVB "$@" bash "$M/home/scratch/r6x/run/run-b/run_stage.sh" "$ST" "$(sha "$D2T/FROZEN-B.sha256")" "$ATT" FROZEN-B.sha256 > "$M/log/b-$ST.log" 2>&1; echo $?; }
ST=k; rc=$(rgb FAKE_ROOM_STUCK=1); [ "$rc" = 19 ] && grep -q 'render_tail_room does not read back 0x4000 before k1' "$M/log/b-k.log" && ok "set B: a render_tail_room write that does not take stops before k1 (rc 19)" || bad "room stuck: rc $rc"
ST=s0b; ATT=b2; echo 0x4000 > "$M/dbgreal/render_tail_room"; rc=$(rgb); [ "$rc" = 1 ] && grep -q 'render_tail_room is not 0 (automatic) at the start' "$M/log/b-s0b.log" && ok "set B preflight: render_tail_room not 0 at the start: rc 1" || bad "room at start: rc $rc"
echo 0 > "$M/dbgreal/render_tail_room"; ATT=b3; mv "$M/dbgreal/render_tail_room" "$M/dbgreal/rtr.gone"; rc=$(rgb); [ "$rc" = 1 ] && grep -q 'has no debugfs render_tail_room' "$M/log/b-s0b.log" && ok "set B preflight: a module without debugfs render_tail_room (rgn4): rc 1" || bad "no room file: rc $rc"
mv "$M/dbgreal/rtr.gone" "$M/dbgreal/render_tail_room"; ATT=b4; echo 99CD90DA26E3AFF9C450517 > "$M/srcv"; rc=$(rgb FAKE_MODINFO=99CD90DA26E3AFF9C450517); [ "$rc" = 1 ] && grep -q "is not the expected build ($SRCVB)" "$M/log/b-s0b.log" && ok "set B preflight: the rgn4 module (99CD90DA...) is refused: rc 1" || bad "set B on rgn4: rc $rc"
grep -q '^SRCV_EXPECT=41E2F5C756F96D20F7109A4$' "$P/run-b/k.env" && ok "run-b/k.env pins the r6-kernel module's srcversion 41E2F5C756F96D20F7109A4 (in FROZEN-B.sha256)" || bad "run-b srcversion"
echo "$SRCVB" > "$M/srcv"; ST=b; ATT=b6; rc=$(rgb FAKE_WORLD=b-b1fault)
[ "$rc" = 0 ] && awk -F'\t' '$1 == "b1-1280x1024" && $9 == "fault"' "$M/home/scratch/r6x/out/b6/b/cases.tsv" | grep -q . && grep -q '^b8-' "$M/home/scratch/r6x/out/b6/b/cases.tsv" \
	&& ok "set B, world b-b1fault: b1's fault is measured (the refutation), b2-b8 still run (rc 0)" || bad "b1 fault: rc $rc"
ST=r; ATT=b7; rc=$(rgb FAKE_WORLD=b-r3fault); [ "$rc" = 4 ] && grep -q 'STOP: unexpected fault in r3-4096x1152' "$M/log/b-r.log" && [ "$(cat "$M/dbgreal/render_tail_room")" = 0 ] && ok "set B: any fault in r stops it (rc 4), render_tail_room 0" || bad "r3 fault: rc $rc"
for kn in room:0x123 room:0x200000 room:0x0; do
	copytree; cp -R "$P/run-b" "$P/stages-B.txt" "$P/TABLES-B.md" "$C/"
	printf '#stage x-mock\n#limit 1\nm-1|heldout|risky|%s expectdiff|-|tri --keep-going --width 64 --height 64\n' "$kn" > "$C/tables/x-mock.txt"
	sed -i '' -e 's#^SET_TABLES="\(.*\)"$#SET_TABLES="\1 tables/x-mock.txt"#' "$C/sets/B.env"; (cd "$C" && rm -f FROZEN-B.sha256 PREDICTIONS-B.sha256 && run/freeze_k.sh freeze B > /dev/null)
	rc=$(env -u K_SRCV_EXPECT $(envw) FAKE_KERNEL=b FAKE_MODINFO=$SRCVB bash "$C/run-b/run_stage.sh" x-mock "$(sha "$C/FROZEN-B.sha256")" "x$N$kn" FROZEN-B.sha256 > "$M/log/xb.log" 2>&1; echo $?)
	[ "$rc" = 7 ] && ok "set B: the knob '$kn' is refused before anything runs (rc 7)" || bad "set B knob $kn: rc $rc"
done
"$P/run-b/guard_b.sh" "$P" B && ok "set B's guard: clean" || bad "set B's guard"
for inj in 'dbg_write render_tail_room 0x123' 'room_set 0x5000' 'echo 0x4000 | sudo -n tee "$D/render_tail_room"' 'dbg_write render_pb_pages 0x10'; do
	C=$W/gb$RANDOM; mkdir -p "$C"; cp -R "$P/run" "$P/run-b" "$P/sets" "$P/tables" "$C/"; printf '%s\n' "$inj" >> "$C/run-b/lib_k.sh"
	"$C/run-b/guard_b.sh" "$C" B > /dev/null 2>&1 && bad "set B's guard missed: $inj" || ok "set B's guard: refuses $inj"
done

# the fake debugfs directories go back to readable (mode 000 during the run), so debug/ can be listed and removed
chmod 700 "$W"/w*/dbg 2>/dev/null
echo "work dir (kept for inspection): $W"
exit $fail
