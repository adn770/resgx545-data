#!/bin/bash
# tests/run_mock.sh: the r5-render4x runner and driver end to end against the ARGV-DRIVEN fake tool (tests/worlds.py) and a fake debugfs
# whose directory is mode 000 (only the sudo shim reaches it: an unprivileged access fails, as on the laptop).  Built from R4-G's.
#   1. the whole driver (staging, k.sh, gates and gate files, scorer, verdict) in the model world, in rule worlds (x gated, the limits
#      reached on a stage's last row) and over two attempts (s0 in the first, t in the second: s0 read through the gate file);
#   2. the runner's rules: the three knobs written after the reset, read back, restored after every job and at every exit (stops
#      included); the held row; strict health after every fault; the limit with rows left (rc 15); a fault that is not E845's word
#      (rc 18); an unexpected fault (rc 4); every other stop code;
#   3. the guard (injections into copies of the tree);  4. the driver's dry run, knob checks and restaging.
# Needs a current freeze (run/freeze_k.sh freeze).  Nothing is deleted: every run writes into a new mktemp directory.
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
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/out" "$M/log" "$M/home"
	for f in reset regs render_param render_tadata kpoke hold_recovery; do : > "$M/dbgreal/$f"; done
	echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_RGN_INIT:-0}" > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${FAKE_PB_INIT:-}" ] && echo "$FAKE_PB_INIT" > "$M/dbgreal/render_pb_pages"
	chmod 000 "$M/dbg"
	FAKE_WORLD=${1:-model}
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh"
export K_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") K_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=1 HOLD_GAP=0.1 TEE_GRACE=3
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$FAKE_WORLD KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log K_OUT=$M/out HOME=$M/home FAKE_P=$P/tests"; }
KD() { echo "$M/out/$ATT/$1"; }
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; echo $?; }
stagebins() { mkdir -p "$M/home/r5x-stage"; cp "$P"/bins/*.bin "$M/home/r5x-stage/"; }
rgn_now() { echo $(( $(cat "$M/dbgreal/render_rgn_arrays") )); }
pb_now() { echo $(( $(cat "$M/dbgreal/render_pb_pages") )); }
hold_now() { cat "$M/fake/hold"; }
writes() { cat "$M/fake/writes" 2>/dev/null; }
copytree() { C=$W/tree$N$RANDOM; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }

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
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	mkdir -p "$D2T/debug"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$K_TOOL_SHA/" "$P/run/k.env" > "$D2T/run/k.env"
	printf '%s  /home/jtorra/sgxfive-test-rgn4\n' "$K_TOOL_SHA" > "$D2T/TOOL.sha256"
	(cd "$D2T" && run/freeze_k.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; mkdir -p "$M/home/r5x-stage"; }
drvenv() { echo "$(envw) K_OUT=$M/home/r5x-out FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4"; }
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
[ $RC = 0 ] && [ "$nst" = 7 ] && echo "$OUT" | grep -q '^r5-render4x done' && ok "world model: the driver runs the seven stages, health ok, both knobs read back at their defaults after each" \
	|| { bad "world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
for k in "session: s0: controls" "Q293 (t): Q293: the dword" "H-ENOSPC4 (o): H-ENOSPC4" "H-TPC (m): H-TPC" "Q292 (m, l, x): the rules no decided row contradicts (13 rows of m, l, x): TPC-d-rgn" "d: E845's fault replicated; scene pages 321"; do
	echo "$VERDICT" | grep -q "SUMMARY: $k" || bad "world model verdict lacks: $k"
done
echo "$VERDICT" | grep -Eq 'NODATA|READER-MISS|cannot tell|not run' && bad "  the model world's verdict has NODATA, READER-MISS, cannot tell or not run: $VERDICT" || ok "  the verdict of the kept run decides every question (no NODATA, READER-MISS, cannot tell, not run)"
cat "$D2T"/out/full/score-*.txt | grep -Eq 'NODATA|READER-MISS|cannot tell' && bad "  a stage score has NODATA, READER-MISS or cannot tell" || ok "  no stage score has NODATA, READER-MISS or cannot tell"
wr=$(writes | awk '{print $1}' | sort -u | tr '\n' ' ')
[ "$wr" = "hold pb reset rgn " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs writes of the whole session: reset, render_rgn_arrays, render_pb_pages, hold_recovery" || bad "  debugfs writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
[ "$(rgn_now)" = 0 ] && [ "$(pb_now)" = 1058 ] && [ "$(hold_now)" = N ] && ok "  at the end render_rgn_arrays 0, render_pb_pages 0x422, hold_recovery N" || bad "  knobs at the end: $(rgn_now) $(pb_now) $(hold_now)"
nh=$(writes | grep -c '^hold Y'); [ "$nh" = 1 ] && ok "  hold_recovery Y was written once (row d)" || bad "  hold Y writes $nh"
ls "$M/home/r5x-out/full/d" | grep -q 'd1-1280x1024-held.heldparam.bin.gz' && ok "  the held d row kept render_param and render_tadata read during the hold" || bad "  held dumps"
ls "$M/home/r5x-out/full/t" | grep -q 't3c-line-te80.p1131-green__0.param.bin.gz' && ls "$M/home/r5x-out/full/t" | grep -q 't4c-point-te80.p1131-psizes__1.param.bin.gz' \
	&& ! ls "$M/home/r5x-out/full/t" | grep -q 't3c-line-te80.tri.' && ok "  the fake tool named the probe dumps from their argv (PROG), as the real one does; the scorer found them" || bad "  probe dump names"
grep -q "^s0 at $D2T/out/full/s0\$" "$D2T/out/full/gate-t.txt" && grep -q "^m at $D2T/out/full/m\$" "$D2T/out/full/gate-x.txt" && ok "  the gate files name where s0 (and m, for x) were found" || bad "  gate files"
cat "$D2T"/out/full/m.log "$D2T"/out/full/l.log | grep -q 'fault: BIF_INT_STAT bits 15:0 256, BIF_FAULT 0x10000011' && ok "  every fault's word read by the runner (E845's: 256, 0x10000011)" || bad "  fault word line"
nf=$(cat "$D2T"/out/full/m/cases.tsv "$D2T"/out/full/l/cases.tsv "$D2T"/out/full/d/cases.tsv | awk -F'\t' '$9 == "fault"' | wc -l | tr -d ' ')
[ "$nf" = 4 ] && ok "  four fault-class events in the model world (m3, l4, l5, d), as frozen" || bad "  faults: $nf"

for wv in "rule:K-OR|Q292 \(m, l, x\): the rules no decided row contradicts \(10 rows of m, l, x\): K-OR$|0" "rule:K-W|Q292 \(m, l, x\): .*: K-W$|0" \
	"rule:TPC-rb-rgn|Q292 \(m, l, x\): .*: TPC-rb-rgn$|0" "o-fault4|H-ENOSPC4 \(o\): .*not supported|4" "t-field|Q293 \(t\): H-FIELD|0"; do
	wn=${wv%%|*}; r=${wv#*|}; want=${r%|*}; wrc=${r##*|}
	case "$wn" in rule:*) DSTAGES="s0 m l x" ;; o-*) DSTAGES="s0 o" ;; t-*) DSTAGES="s0 t" ;; esac
	drive "$wn"; DSTAGES=
	if [ "$wn" = o-fault4 ]; then
		[ $RC = 4 ] && echo "$OUT" | grep -q 'STOP: unexpected fault in o4-4x-1024x768-pe2' && ok "world $wn: a fault in o (none predicted) stops the stage at once (rc 4) after strict health" || bad "world $wn: rc $RC"
		continue
	fi
	echo "$VERDICT" | grep -Eq "SUMMARY: $want" && [ $RC = "$wrc" ] && ok "world $wn: the driver's verdict is as predicted (rc $RC)" || { bad "world $wn: rc $RC: $(echo "$VERDICT" | grep Q29 | tr '\n' ' ' | cut -c1-300)"; echo "$OUT" | tail -3 | sed 's/^/     /'; }
	case "$wn" in rule:K-*) echo "$OUT" | grep -q 'SKIPPED: x' && ok "  world $wn: x skipped cleanly (m did not hold H-TPC)" || bad "  world $wn: x not skipped" ;; esac
	[ "$(rgn_now)" = 0 ] && [ "$(pb_now)" = 1058 ] && [ "$(hold_now)" = N ] || bad "  world $wn: a knob was left behind: $(rgn_now) $(pb_now) $(hold_now)"
done
DSTAGES="s0 m l" drive rule:K-OR
nm=$(awk -F'\t' '$9 == "fault"' "$D2T/out/full/m/cases.tsv" | wc -l | tr -d ' '); nl=$(awk -F'\t' '$9 == "fault"' "$D2T/out/full/l/cases.tsv" | wc -l | tr -d ' ')
[ $RC = 0 ] && [ "$nm" = 4 ] && [ "$nl" = 5 ] && ok "world K-OR: m takes its 4 faults and l its 5, each limit reached on the stage's last row: no stop (rc 0)" || bad "K-OR limits: rc $RC m $nm l $nl"
DSTAGES="s0 t" drive s0-miss
echo "$OUT" | grep -q 'SKIPPED: t' && ! grep -q 'probe' "$M/fake.log" && ok "world s0-miss: a failed control closes the gate of every later stage: t did not run" || { bad "world s0-miss: rc $RC"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
# two attempts: s0 in the first, t in the second; t's score reads s0 through the gate file
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
env $(drvenv) K_ATT=a1 bash "$D2T/run/k.sh" --only s0 > "$M/log/a1.log" 2>&1
env $(drvenv) K_ATT=a2 bash "$D2T/run/k.sh" --only t > "$M/log/a2.log" 2>&1; rc=$?
[ $rc = 0 ] && grep -q "^s0 at $D2T/out/a1/s0\$" "$D2T/out/a2/gate-t.txt" && ! grep -q NODATA "$D2T/out/a2/score-t.txt" && grep -q '(6 of 6 rows decided)' "$D2T/out/a2/score-t.txt" \
	&& ok "two attempts: the gate file of the second names the first's s0, and t's own score reads s0 there (no NODATA; round 4's slip)" || { bad "two attempts: rc $rc"; tail -3 "$D2T/out/a2/score-t.txt" | sed 's/^/     /'; }

# ---- 2. the runner's rules ----------------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
world model; rc=$(runst "$P" o)
[ "$rc" = 0 ] && ok "stage o in the model world: rc 0, no fault" || { bad "stage o: rc $rc"; grep -E 'STOP|abort' "$M/log/o.log" | head -3; }
grep -q 'resgx545 r5x pb o1-1x-1024x768-p35 0x35' "$M/kmsg" && grep -q 'resgx545 r5x knobs-read o1-1x-1024x768-p35 hold_recovery=N render_rgn_arrays=0x00000000 render_pb_pages=0x00000035' "$M/kmsg" \
	&& grep -q 'resgx545 r5x pb-back o1-1x-1024x768-p35 0x422' "$M/kmsg" && ok "render_pb_pages is written after the job's reset, read back before it, and put back to 0x422 after it" || bad "pb sequence"
grep '^pb ' "$M/fake/writes" | head -4 | tr '\n' ' ' | grep -q '^pb 0x35 pb 0x422 pb 0x34 pb 0x422' && ok "  the pb writes of o1 and o2: 0x35, 0x422, 0x34, 0x422" || bad "  pb writes: $(grep '^pb ' "$M/fake/writes" | head -6 | tr '\n' ' ')"
awk -F'\t' '$1 == "o2-1x-1024x768-p34" && $9 == "ok"' "$(KD o)/cases.tsv" | grep -q . && zcat < "$(KD o)/o2-1x-1024x768-p34.txt.gz" | grep -q '1 overflowed' && zcat < "$(KD o)/o1-1x-1024x768-p35.txt.gz" | grep -q 'diff: 0 of 786432' \
	&& ok "  the fake decided from argv and the fake render_pb_pages: o1 (0x35) completes, o2 (0x34) overflows (the default triangle's 19 pages)" || bad "  o1/o2 outcome in the mock"
world model; rc=$(runst "$P" m FAKE_HEALTH_SEQ="ok ok fail")
[ "$rc" = 16 ] && grep -q 'm3-1280x1024-max2048x1024' "$(KD m)/cases.tsv" && ! grep -q '^m4' "$(KD m)/cases.tsv" && ok "strict: the first health after m3's fault failing stops the stage (rc 16) after the recovery; m4 does not run" || { bad "strict: rc $rc"; grep -E 'STOP|abort' "$M/log/m.log" | head -4; }
nres=$(awk '/resgx545 r5x class m3-/ {s=1} s && /resgx545 r5x health m3-1280x1024-max2048x1024 fill try/ {exit} s && /SGX reset: BIF_FAULT/ {n++} END {print n+0}' "$M/kmsg")
[ "$nres" = 0 ] && ok "  strict: no reset of the runner's between m3's class line and its first health" || bad "  runner reset before strict health: $nres"
world model; stopcase "an unexpected fault in m0 (no hypothesis knob) stops the stage after strict health" 4 m FAKE_RULES='--width 1024 --height 768 --max-width 2048|fault'
world model; stopcase "a fault that is not E845's word (TA side 0x20006061) in a hypothesis row stops the stage" 18 l FAKE_RULES='--width 2048 --height 240|fault'
grep -q "is not E845's 3D-side word (bits 15:0 4, BIF_FAULT 0x20006061)" "$M/log/l.log" && ! grep -q '^l2' "$(KD l)/cases.tsv" && ok "  the stop names the word; l2 did not run" || bad "  rc 18 text"
world model; copytree
sed -i '' -e 's/^#limit 5$/#limit 1/' "$C/tables/l.txt"; (cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" l); [ "$rc" = 15 ] && grep -q 'l4-1280x768' "$(KD l)/cases.tsv" && ! grep -q '^l5' "$(KD l)/cases.tsv" \
	&& ok "the limit with rows left: the 1st fault (l4) of a stage limited to 1 stops it before l5 (rc 15)" || { bad "limit: rc $rc"; grep STOP "$M/log/l.log"; }
world model; rc=$(runst "$P" d)
[ "$rc" = 0 ] && awk -F'\t' '$1 == "d1-1280x1024-held" && $9 == "fault" && $10 == "held" && $13 == "yes"' "$(KD d)/cases.tsv" | grep -q . \
	&& ok "stage d: the held row faults in held mode with the kernel's hold message; the limit 1 is reached on the last row: rc 0" || { bad "stage d: rc $rc"; grep STOP "$M/log/d.log"; }
grep -q 'fault: BIF_INT_STAT bits 15:0 256, BIF_FAULT 0x10000011' "$M/log/d.log" && ok "  the held fault's word read from snap 1" || bad "  held word"
world model; stopcase "render_pb_pages does not read back (a stuck write)" 19 o FAKE_PB_STUCK=1
world model; stopcase "render_pb_pages does not go back to 0x422 after a job" 19 o FAKE_PB_STUCK_BACK=1
world model; stopcase "hold_recovery does not read back Y (row d)" 9 d FAKE_HOLD_NOY=1
world model; stagebins; stopcase "render_rgn_arrays does not read back 1 (stage t)" 19 t FAKE_RGN_STUCK=1
world model; stagebins; stopcase "render_rgn_arrays does not go back to 0" 19 t FAKE_RGN_STUCK_AT0=1
FAKE_PB_INIT=0x83 world model; stopcase "preflight: render_pb_pages not 0x422 at the start" 1 s0
[ ! -f "$M/fake/resets" ] && [ ! -s "$M/fake/writes" ] && ok "  nothing touched (no reset, no knob write)" || bad "  the failed preflight touched the GPU"
FAKE_HOLD_INIT=Y world model; stopcase "preflight: hold_recovery not N at the start" 1 s0
FAKE_RGN_INIT=1 world model; stopcase "preflight: render_rgn_arrays not 0 at the start" 1 s0
world model; stopcase "fatal kernel message in a row (the knobs are still restored, no reset)" 3 o FAKE_RULES='--width 288 --height 144|fatal'
[ "$(pb_now)" = 1058 ] && [ "$(rgn_now)" = 0 ] && [ "$(hold_now)" = N ] && ok "  after the fatal stop the three knobs are restored" || bad "  knobs after fatal: $(pb_now) $(rgn_now) $(hold_now)"
world model; stopcase "a row does not return (freeze)" 6 o FAKE_RULES='--width 640 --height 480|timeout'
[ "$(pb_now)" = 1058 ] && ok "  after the freeze stop the PB size is back at 0x422" || bad "  pb after freeze: $(pb_now)"
world model; stopcase "an unexplained failure (rc 1, no diff line) stops" 4 o FAKE_RULES='--width 512 --height 384|nodiff'
world model; stopcase "an unexpected hang stops" 4 o FAKE_RULES='--width 512 --height 384|hang'
world model; stopcase "the pre-job reset fails" 13 s0 FAKE_RESET_FAIL_FROM=2
world model; stopcase "health: the first failed recovery stops (begin)" 5 s0 FAKE_HEALTH_BAD=1
world model; stopcase "registers unreadable" 12 s0 FAKE_SNAP_FAIL=1
FAKE_STATE_INIT='0x4 0x20006061 0x480 0x20000000' world model; stopcase "a fault latched before the job (snap 0)" 14 s0 FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
world model; stopcase "the kernel's reset information lines inside a job are not bad" 0 s0 FAKE_RULES='--width 1024 --height 768 -n 1|resetinfo'
awk -F'\t' '$1 == "s0-1x-1024x768" && $9 == "ok" {f=1} END {exit !f}' "$(KD s0)/cases.tsv" && ok "  s0-1x is class ok with both reset lines in its slice" || bad "  reset info class"
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
world model; rc=$(runst "$P" s0); rc2=$(runst "$P" s0)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: $rc $rc2"
world model
env $(envw) bash "$P/run/run_stage.sh" s0 "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
[ "$rc" = 0 ] && grep -q '^## end' "$(KD s0)/runner.log" && ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc"
world model; rc=$(runst "$P" t); [ "$rc" = 8 ] && grep -q 'missing program' "$M/log/t.log" && ok "stage t without its programs staged: rc 8, nothing touched" || bad "missing bins: rc $rc"
world model; stagebins; printf 'x' >> "$M/home/r5x-stage/p1131-green__0.bin"
rc=$(runst "$P" t); [ "$rc" = 1 ] && grep -q 'is not the frozen one' "$M/log/t.log" && ok "a staged program that is not the frozen one: rc 1" || bad "tampered bin: rc $rc"
world model; stagebins; rc=$(runst "$P" t); [ "$rc" = 0 ] && ok "stage t with the programs staged: rc 0, nine jobs ($(grep -c '^t' "$(KD t)/cases.tsv"))" || { bad "stage t: rc $rc"; grep -E 'STOP|abort|missing' "$M/log/t.log" | head -3; }
# table knobs and dbg_write refusals
for kn in bif rgn:4 rgn:0 noreset idle stophang pb:0x10 pb:0x500 pb:83 hold hypo:G cell:ctx needs:o5=fault; do
	world model; copytree
	printf '#stage x-mock\n#limit 1\nm-1|heldout|risky|%s expectdiff|-|tri --keep-going --width 64 --height 64\n' "$kn" > "$C/tables/x-mock.txt"
	(cd "$C" && run/freeze_k.sh freeze > /dev/null)
	rc=$(runst "$C" x-mock)
	[ "$rc" = 7 ] && [ ! -f "$M/fake/resets" ] && ok "the knob '$kn' is refused before anything runs (rc 7)" || bad "knob $kn: rc $rc"
done
for nm in "hold_recovery X" "render_rgn_arrays 4" "render_pb_pages 0x10" "render_pb_pages 0x423" "alias_skip 1" "kpoke x" "kregnow 0x0c04=0x1"; do
	world model; copytree
	printf '\ndbg_write %s\n' "$nm" >> "$C/run/lib_k.sh"
	(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" s0)
	[ "$rc" = 7 ] && grep -q "dbg_write: ${nm} is not" "$M/log/s0.log" && ok "dbg_write $nm is refused at run time: rc 7" || bad "dbg_write $nm: rc $rc"
done

# ---- 3. the guard ------------------------------------------------------------------------------------------------------------
"$P/run/guard_k.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"
for inj in 'echo 1 | sudo -n tee "$D/kreg"' 'echo 1 | sudo -n tee "$D/kregnow"' 'echo par:11=0 | sudo -n tee "$D/kpoke"' 'echo 1 | sudo -n tee "$D/kicker"' \
	'until false; do :; done' 'x=$(cat f | tail -1)' 'sudo -n tee "$D/reset" || true' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' \
	'dbg_write alias_skip 1' 'dbg_write hold_recovery Y' 'dbg_write render_rgn_arrays 4' 'dbg_write render_pb_pages 0x10' 'echo 4 | sudo -n tee "$D/render_rgn_arrays"' \
	'echo 0x10 | sudo -n tee "$D/render_pb_pages"' 'echo x | sudo -n tee "$KMSG"' 'echo x | sudo -n tee /dev/kmsg' 'git status' 'rm -f x' 'reboot' \
	'echo 1 > /sys/x/clkgate' 'echo x >> own_arm' 'sed -n 5,9p "$JW/dmesg.all"' 'set_hold Y' 'rgn_set 4' 'pb_set 0x10' 'sudo -n cat "$D/render_param" > "$D/x"' \
	'echo 1 | sudo -n tee "$D/render_tadata"' 'sudo -n timeout 60 "$T" tri' 'trc_hazard=1' 'make -C x'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_k.sh"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; printf '%s\n' 'x=1; set_hold Y' >> "$C/run/run_stage.sh"; "$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: a second set_hold Y" || ok "guard: refuses a second set_hold Y in run_stage.sh"
for tl in 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kreg x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render 1:par:11=0x1' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --fault' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --poke ta:1=2' \
	'm-9|heldout|risky|rgn:4 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|hold expectdiff|-|tri --keep-going' 'm-9|heldout|risky|rgn:1 expectdiff|0x0118|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --regs 0x0000-0x0c00' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --tadata-fill-render 1:7:0x00012340' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|probe --cmd 1=0x20000000 x.bin' 'm-9|heldout|risky|pb:0x10 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|pb:0x500 expectdiff|-|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --ctx2' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --words /x' 'm-9|heldout|risky|rgn:1|-|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|sh -c x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --aa4 yes' 'm-9|heldout|risky|cell:ctx expectdiff|-|tri --keep-going'; do
	copytree; printf '%s\n' "$tl" >> "$C/tables/s0.txt"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed the table line: $tl" || ok "guard: refuses the table line '${tl#m-9|heldout|risky|}'"
done

# ---- 4. the driver: dry run, a knob left behind, gates, restaging ---------------------------------------------------------------
d=$(K_ATT=attX SGX_DRY_RUN=1 bash "$P/run/k.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_r.py gate t' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 1500 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh s0 $fs attX" && echo "$d" | grep -q "r5x-out/attX/m .*/out/attX/m" && echo "$d" | grep -q 'r5x-run' \
	&& ok "driver dry run: the gates, bounded ssh/scp (900 s s0, 1500 s m and l), the frozen sha256, one directory an attempt, the r5x directories" || { bad "driver dry run"; echo "$d" | head -12 | sed 's/^/     /'; }
! echo "$d" | grep -Eq 'r4g|r3k|r4a|r4b|r3x|r5e-|r5p-|r5d-' && ok "no other session's laptop directory in the commands" || bad "foreign directory in the dry run"
grep -rEq 'r4g-' "$P/run" && bad "an r4g- path left in run/" || ok "no r4g- path in run/ (the laptop prefix is ~/r5x-)"
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=leak FAKE_KNOB_LEAK=1 bash "$D2T/run/k.sh" --only s0 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_rgn_arrays is 0x00000004 after s0' && ok "render_rgn_arrays read as 4 after a stage stops the driver (rc 42)" || { bad "rgn after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
out=$(env $(drvenv) K_ATT=leak2 FAKE_PB_LEAK=1 bash "$D2T/run/k.sh" --only s0 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_pb_pages is 0x00000083 after s0' && ok "render_pb_pages read as 0x83 after a stage stops the driver (rc 42)" || { bad "pb after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=g1 bash "$D2T/run/k.sh" --only m 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'SKIPPED: m' && ok "no kept s0 closes the gate: m skipped cleanly (rc 0)" || { bad "gate: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world model; fakehome; out=$(env $(drvenv) bash "$P/run/stage_k.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the rgn4 build" && ok "staging refuses a laptop whose tool is not e6951558..." || bad "staging with a foreign tool: rc $rc"
world model; dtree; fakehome; env $(drvenv) bash "$D2T/run/stage_k.sh" > "$M/log/stage.log" 2>&1
n=$(ls "$M/home/r5x-stage" | wc -l | tr -d ' '); [ "$n" = 2 ] && ok "staging copies the two programs to ~/r5x-stage" || bad "staged programs: $n"
num_eq 0x00000000 0 && num_eq 0x00000001 1 && ! num_eq 0x00000004 1 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"
echo "work dir (kept for inspection): $W"
exit $fail
