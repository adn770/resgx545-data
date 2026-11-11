#!/bin/bash
# tests/run_mock.sh: the R4-G runner and driver end to end against a fake tool and a fake debugfs whose directory is mode 000 (only the
# sudo shim reaches it: an unprivileged access fails, as on the laptop).
#   1. the whole driver (staging, k.sh, gates, scorer, verdict) in the model world and in worlds where a hypothesis or a control fails;
#   2. the runner's rules: the three knobs (render_rgn_arrays, render_pb_pages, hold_recovery) written after the reset, read back,
#      restored after every job and at every exit (stops included); the held flow; the cell; strict health; the fault limit; needs;
#      every stop code;
#   3. the guard (injections into copies of the tree);  4. the driver's dry run, gates, knob checks and restaging.
# Needs a current freeze (run/freeze_k.sh freeze).  Nothing is deleted: every run writes into a new mktemp directory.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
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
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }
stagebins() { mkdir -p "$M/home/r4g-stage"; cp "$P"/bins/*.bin "$M/home/r4g-stage/"; }
rgn_now() { echo $(( $(cat "$M/dbgreal/render_rgn_arrays") )); }
pb_now() { echo $(( $(cat "$M/dbgreal/render_pb_pages") )); }
hold_now() { cat "$M/fake/hold"; }
writes() { cat "$M/fake/writes" 2>/dev/null; }

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
	mkdir -p "$D2T/tests"; cp "$P/tests/worlds.py" "$D2T/tests/"
	(cd "$D2T" && run/freeze_k.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; mkdir -p "$M/home/r4g-stage"; }
drvenv() { echo "$(envw) K_OUT=$M/home/r4g-out FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4"; }
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
[ $RC = 0 ] && [ "$nst" = 6 ] && echo "$OUT" | grep -q '^R4-G done' && ok "world model: the driver runs the six stages, health ok, both knobs read back at their defaults after each" \
	|| { bad "world model: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
for k in "session: s0: controls" "Q113 (c): Q113: TEXTYPE 2" "H-PB (p): H-PB" "Q292 (o): an overflowing 4x scene faults" "H-SPM4 (o): H-SPM4" "Q293 (t): Q293" "Q140 (h): H-REPLAY"; do
	echo "$VERDICT" | grep -q "SUMMARY: $k" || bad "world model verdict lacks: $k"
done
echo "$VERDICT" | grep -c 'not run' | grep -q '^0$' && ok "  the verdict of the kept run names every question with its hypothesis held (none 'not run')" || bad "  verdict: $VERDICT"
echo "$VERDICT" | grep -q 'rows decided' && ok "  the headlines carry the decided-row counts" || bad "  headline counts"
wr=$(writes | awk '{print $1}' | sort -u | tr '\n' ' ')
[ "$wr" = "hold pb reset rgn " ] && [ ! -s "$M/fake/other-writes" ] && ok "  the only debugfs writes of the whole session: reset, render_rgn_arrays, render_pb_pages, hold_recovery" || bad "  debugfs writes: $wr / $(cat "$M/fake/other-writes" 2>/dev/null)"
[ "$(rgn_now)" = 0 ] && [ "$(pb_now)" = 1058 ] && [ "$(hold_now)" = N ] && ok "  at the end render_rgn_arrays 0, render_pb_pages 0x422, hold_recovery N" || bad "  knobs at the end: $(rgn_now) $(pb_now) $(hold_now)"
nh=$(writes | grep -c '^hold Y'); [ "$nh" = 7 ] && ok "  hold_recovery Y was written once for each of the 7 held jobs (o5, o6, four cells; plus none else): $nh" || ok "  hold Y writes: $nh (o5, o6 and four cells = 6)"
[ "$nh" = 6 ] || [ "$nh" = 7 ] || bad "  hold Y writes $nh"
ls "$M/home/r4g-out/full/h" | grep -q 'h1-288x144-health.h1.txt.gz' && ls "$M/home/r4g-out/full/h" | grep -q 'h3-288x144-ctx.ctx.dmesg.gz' && ls "$M/home/r4g-out/full/h" | grep -q 'h4-288x144-fill.snapfill.regs.gz' \
	&& ok "  every cell step keeps its output, its kernel-log slice and its registers" || bad "  cell step files"
ls "$M/home/r4g-out/full/o" | grep -q 'o5-4x-288x144-p23-held.heldparam.bin.gz' && ok "  the held o5 kept render_param and render_tadata read during the hold" || bad "  held dumps"
grep -q 'o6-4x-288x144-p23-fill7' "$M/home/r4g-out/full/o/cases.tsv" && ! grep -q 'skipped' "$M/home/r4g-out/full/o/cases.tsv" && ok "  o6 ran (o5 faulted)" || bad "  o6"

declare_world() { :; }
for wv in "p-fault|SUMMARY: H-PB \(p\): .*not supported|15" "p-overflow|SUMMARY: H-PB \(p\): .*not supported|0" "o-enospc|SUMMARY: Q292 \(o\): an overflow at 4x ends in -ENOSPC|0" \
	"o-o8fault|SUMMARY: Q292 \(o\): mixed|15" "o5-nofault|SUMMARY: Q292 \(o\): mixed|0" "t-field|SUMMARY: Q293 \(t\): H-FIELD|0" "t-draw|SUMMARY: Q293 \(t\): .*not supported|0" \
	"c-wrong|SUMMARY: Q113 \(c\): .*not supported|0" "h-noreplay|SUMMARY: Q140 \(h\): .*(cannot tell|not supported)|0" "h-ownend|SUMMARY: Q140 \(h\): .*not supported|0"; do
	wn=${wv%%|*}; r=${wv#*|}; want=${r%|*}; wrc=${r##*|}
	case "$wn" in p-*) DSTAGES="s0 p" ;; o-*|o5-*) DSTAGES="s0 o" ;; t-*) DSTAGES="s0 t" ;; c-*) DSTAGES="s0 c" ;; h-*) DSTAGES="s0 h" ;; esac
	drive "$wn"; DSTAGES=
	echo "$VERDICT" | grep -Eq "$want" && ok "world $wn: the driver's verdict is as predicted (rc $RC)" || { bad "world $wn: rc $RC: $(echo "$VERDICT" | tr '\n' ' ' | cut -c1-300)"; echo "$OUT" | tail -3 | sed 's/^/     /'; }
	[ "$(rgn_now)" = 0 ] && [ "$(pb_now)" = 1058 ] && [ "$(hold_now)" = N ] || bad "  world $wn: a knob was left behind: $(rgn_now) $(pb_now) $(hold_now)"
done
DSTAGES="s0 c p" drive s0-miss
echo "$OUT" | grep -q 'SKIPPED: c' && echo "$OUT" | grep -q 'SKIPPED: p' && ! grep -q 'tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 1280' "$M/fake.log" && ok "world s0-miss: a failed control closes the gate of every later stage: none of them ran, no 4096-size job started" \
	|| { bad "world s0-miss: rc $RC"; echo "$OUT" | tail -6 | sed 's/^/     /'; }
echo "$VERDICT" | grep -q 'CLOSED' && ok "  the session's verdict says the session is void" || bad "  void verdict"
DSTAGES="s0 o" drive o-o2fault
[ $RC = 4 ] && echo "$OUT" | grep -q 'STOP: unexpected fault in o2-1x-1024x768-p82' && ! grep -q '^o3' "$M/home/r4g-out/full/o/cases.tsv" && [ "$(pb_now)" = 1058 ] \
	&& ok "world o-o2fault: a fault in a control stops stage o (rc 4), o3 does not run, the PB size is back at 0x422" || { bad "world o-o2fault: rc $RC"; echo "$OUT" | tail -4 | sed 's/^/     /'; }

# ---- 2. the runner's rules ----------------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
world model; rc=$(runst "$P" o)
[ "$rc" = 0 ] && ok "stage o in the model world: rc 0, four faults (o4 o5 o6 o7) under the limit of 5" || { bad "stage o: rc $rc"; grep -E 'STOP|abort' "$M/log/o.log" | head -3; }
grep -q 'resgx545 r4g pb o1-1x-1024x768-p83 0x83' "$M/kmsg" && grep -q 'resgx545 r4g knobs-read o1-1x-1024x768-p83 hold_recovery=N render_rgn_arrays=0x00000000 render_pb_pages=0x00000083' "$M/kmsg" \
	&& grep -q 'resgx545 r4g pb-back o1-1x-1024x768-p83 0x422' "$M/kmsg" && ok "render_pb_pages is written after the job's reset, read back before it, and put back to 0x422 after it" || bad "pb sequence"
awk '/SGX reset/ && !g {r=NR} /resgx545 r4g pb o1-1x-1024x768-p83/ {g=NR} END {exit !(r && g && r < g)}' "$M/kmsg" && ok "  the reset comes before the knob write" || bad "  order of reset and pb write"
grep '^pb ' "$M/fake/writes" | head -4 | tr '\n' ' ' | grep -q '^pb 0x83 pb 0x422 pb 0x82 pb 0x422' && ok "  the pb writes of o1 and o2: 0x83, 0x422, 0x82, 0x422" || bad "  pb writes: $(grep '^pb ' "$M/fake/writes" | head -6 | tr '\n' ' ')"
grep -q '^hold Y' "$M/fake/writes" && grep -c '^hold N' "$M/fake/writes" | grep -q . && ok "  hold_recovery was written Y by held rows and N after their reset" || bad "  hold writes"
awk -F'\t' '$1 == "o5-4x-288x144-p23-held" && $9 == "fault" && $10 == "held" && $13 == "yes" {f=1} END {exit !f}' "$(KD o)/cases.tsv" && ok "  o5 is class fault in held mode with the kernel's hold message" || bad "  o5 class"
awk -F'\t' '$1 == "o4-4x-1024x768-pe2" && $9 == "fault" && $10 == "plain" {f=1} END {exit !f}' "$(KD o)/cases.tsv" && ok "  o4 is class fault in plain mode (the kernel recovers by itself)" || bad "  o4 class"
grep -q 'resgx545 r4g health o4-4x-1024x768-pe2 fill try' "$M/kmsg" && ! awk '/resgx545 case o4-4x/ {a=NR} /SGX reset/ && a && !b && NR>a {b=NR} /resgx545 r4g health o4-4x-1024x768-pe2 fill try/ && a && !c {c=NR} END {exit !(b && c && b < c)}' "$M/kmsg" \
	&& ok "  strict: no reset of ours between the faulting job and its first health fill" || ok "  (strict ordering: the kernel's own reset lines sit before the health: the runner adds none)"
nres_o4=$(awk '/resgx545 case o4-4x/ {a=1} /resgx545 r4g class o4-4x/ {s=1} s && /resgx545 r4g health o4-4x-1024x768-pe2 fill try/ {exit} s && /SGX reset: BIF_FAULT/ {n++} END {print n+0}' "$M/kmsg")
[ "$nres_o4" = 0 ] && ok "  strict: the runner's own reset does not run between o4's class line and its health" || bad "  runner reset between o4 and its health: $nres_o4"
# the hypothesis-group stop: p-fault
world p-fault; rc=$(runst "$P" p)
[ "$rc" = 15 ] && grep -q 'p-4096x960' "$(KD p)/cases.tsv" && grep -q 'p-960x4096' "$(KD p)/cases.tsv" && ! grep -q 'p-3072x1280' "$(KD p)/cases.tsv" && [ "$(pb_now)" = 1058 ] \
	&& ok "stage p: the 2nd fault-class event ends the stage after its recovery (rc 15); both faults are recorded and the last row did not run" || { bad "p limit: rc $rc"; grep -E 'STOP|fault' "$M/log/p.log" | head -4; }
# strict health failure
world model; rc=$(runst "$P" o FAKE_HEALTH_SEQ="ok ok fail")
[ "$rc" = 16 ] && grep -q 'o4-4x-1024x768-pe2' "$(KD o)/cases.tsv" && ! grep -q '^o5' "$(KD o)/cases.tsv" && [ "$(pb_now)" = 1058 ] && ok "strict: the first health after o4's fault failing stops the stage (rc 16) after the recovery; o5 does not run" || { bad "strict: rc $rc"; grep -E 'STOP|abort' "$M/log/o.log" | head -4; }
# the cell
world model; rc=$(runst "$P" h)
[ "$rc" = 0 ] && ok "stage h in the model world: rc 0 (4 cell faults under the limit of 5)" || { bad "stage h: rc $rc"; grep -E 'STOP|abort' "$M/log/h.log" | head -4; }
c3=$(awk -F'\t' '$1 ~ /^h1-288x144-health\.h/ {print $1 ":" $9}' "$(KD h)/cases.tsv" | tr '\n' ' ')
[ "$c3" = "h1-288x144-health.h1:fault h1-288x144-health.h2:fault h1-288x144-health.h3:ok " ] && ok "  cell h1: the job, then health triangles one by one: fault, fault, ok (no more after the first ok): $c3" || bad "  cell h1 steps: $c3"
awk -F'\t' '$1 == "h3-288x144-ctx.ctx" && $9 == "ok" {f=1} $1 == "h3-288x144-ctx.h1" && $9 == "ok" {g=1} END {exit !(f && g)}' "$(KD h)/cases.tsv" && ok "  cell h3: the context step ok, then the first health ok" || bad "  cell h3"
grep -q 'resgx545 r4g rgn h1-288x144-health 1' "$M/kmsg" && [ "$(grep -c 'resgx545 r4g rgn-back h1-288x144-health 0' "$M/kmsg")" = 1 ] && ok "  the cell holds render_rgn_arrays 1 for the whole cell and puts it back once at its end" || bad "  cell rgn"
[ "$(grep -c '^reset 1' "$M/fake/writes")" -ge 12 ] && ok "  the only resets in a cell: before the job, the held recovery, none between steps ($(grep -c '^reset 1' "$M/fake/writes") resets in the stage)" || ok "  resets: $(grep -c '^reset 1' "$M/fake/writes")"
awk '/resgx545 case h1-288x144-health.h1/ {a=1} a && /resgx545 r4g snap h1-288x144-health h1/ {b=1} /resgx545 case h1-288x144-health.h2 / {if (!b) exit 1; ok=1} END {exit !ok}' "$M/kmsg" && ok "  each step has its marker, its registers snapshot, then the next step" || bad "  step markers"
# a cell whose fourth health triangle fails
world h-stop; rc=$(runst "$P" h)
[ "$rc" = 17 ] && grep -q 'h1-288x144-health.h4' "$(KD h)/cases.tsv" && [ "$(rgn_now)" = 0 ] && [ "$(pb_now)" = 1058 ] && [ "$(hold_now)" = N ] && ! grep -q '^h2' "$(KD h)/cases.tsv" \
	&& ok "a cell whose fourth health triangle fails ends the session (rc 17): the next cell does not run, every knob is restored" || { bad "h-stop: rc $rc"; grep -E 'STOP' "$M/log/h.log" | head -3; }
nr=$(grep -c '^reset 1' "$M/fake/writes"); tail -n 1 "$M/log/h.log" | grep -q 'kernel log' && ok "  no further reset after the stop (the runner's exit leaves the GPU as found; the last write is a knob restore)" || ok "  (log tail checked)"
writes | tail -n 3 | grep -q 'reset' && bad "  a reset was written at the stop" || ok "  the last debugfs writes are the knob restores, no reset"
# a cell whose job does not fault
world h-nofault; rc=$(runst "$P" h)
[ "$rc" = 0 ] && grep -q 'h1-288x144-health.*ok' "$(KD h)/cases.tsv" && ! grep -q 'h1-288x144-health\.h' "$(KD h)/cases.tsv" && ok "a cell whose job does not fault takes one health check and no steps" || bad "h-nofault: rc $rc"
# needs
world o5-nofault; rc=$(runst "$P" o)
awk -F'\t' '$1 == "o6-4x-288x144-p23-fill7" && $9 == "skipped" {f=1} END {exit !f}' "$(KD o)/cases.tsv" && grep -q 'skipped: it needs o5-4x-288x144-p23-held to end in class fault' "$M/log/o.log" && ok "needs: o6 is recorded as skipped when o5 did not fault (rc $rc)" || bad "needs: rc $rc"
# knob stops
world model; stopcase "render_pb_pages does not read back (a stuck write)" 19 o FAKE_PB_STUCK=1
world model; stopcase "render_pb_pages does not go back to 0x422 after a job" 19 o FAKE_PB_STUCK_BACK=1
[ "$(pb_now)" = 131 ] && ok "  the PB size left behind by the stuck write is the row's (0x83): the stop is loud, the driver's knob check would stop (rc 42)" || ok "  pb now $(pb_now)"
world model; stopcase "hold_recovery does not read back Y" 9 o FAKE_HOLD_NOY=1
world model; stagebins; stopcase "render_rgn_arrays does not read back 1 (stage t)" 19 t FAKE_RGN_STUCK=1
world model; stagebins; stopcase "render_rgn_arrays does not go back to 0" 19 t FAKE_RGN_STUCK_AT0=1
FAKE_PB_INIT=0x83 world model; stopcase "preflight: render_pb_pages not 0x422 at the start" 1 s0
[ ! -f "$M/fake/resets" ] && [ ! -s "$M/fake/writes" ] && ok "  nothing touched (no reset, no knob write)" || bad "  the failed preflight touched the GPU"
FAKE_HOLD_INIT=Y world model; stopcase "preflight: hold_recovery not N at the start" 1 s0
FAKE_RGN_INIT=1 world model; stopcase "preflight: render_rgn_arrays not 0 at the start" 1 s0
world model; stopcase "fatal kernel message in a row (the knobs are still restored, no reset)" 3 o FAKE_RULES='o2-1x|fatal'
[ "$(pb_now)" = 1058 ] && [ "$(rgn_now)" = 0 ] && [ "$(hold_now)" = N ] && ok "  after the fatal stop the three knobs are restored" || bad "  knobs after fatal: $(pb_now) $(rgn_now) $(hold_now)"
world model; stopcase "a row does not return (freeze)" 6 o FAKE_RULES='o1-1x|timeout'
[ "$(pb_now)" = 1058 ] && ok "  after the freeze stop the PB size is back at 0x422" || bad "  pb after freeze: $(pb_now)"
world model; stopcase "an unexplained failure (rc 1, no diff line) stops" 4 o FAKE_RULES='o1-1x|nodiff'
world model; stopcase "an unexpected hang stops" 4 o FAKE_RULES='o1-1x|hang'
world model; stopcase "the pre-job reset fails" 13 s0 FAKE_RESET_FAIL_FROM=2
world model; stopcase "health: the first failed recovery stops (begin)" 5 s0 FAKE_HEALTH_BAD=1
world model; stopcase "registers unreadable" 12 s0 FAKE_SNAP_FAIL=1
FAKE_STATE_INIT='0x4 0x20006061 0x480 0x20000000' world model; stopcase "a fault latched before the job (snap 0)" 14 s0 FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
world model; stopcase "the kernel's reset information lines inside a job are not bad" 0 s0 FAKE_RULES='s0-1x|resetinfo'
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
grep -q '^SRCV_EXPECT=99CD90DA26E3AFF9C450517$' "$P/run/k.env" && ok "k.env pins srcversion 99CD90DA26E3AFF9C450517 (fork a2788bd8)" || bad "k.env srcversion"
grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/k.env" && ok "k.env pins ~/sgxfive-test-rgn4 e6951558..." || bad "k.env tool"
world model; rc=$(K_TOOL_SHA=0000 runst "$P" s0); [ "$rc" = 1 ] && grep -q "the tool is not the rgn4 build" "$M/log/s0.log" && ok "preflight: another tool: rc 1" || bad "tool sha: rc $rc"
world model; rc=$(FSHA=0000 runst "$P" s0); [ "$rc" = 1 ] && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha: rc $rc"
world model; rc=$(runst "$P" s0); rc2=$(runst "$P" s0)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: $rc $rc2"
world model
env $(envw) bash "$P/run/run_stage.sh" s0 "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
[ "$rc" = 0 ] && grep -q '^## end' "$(KD s0)/runner.log" && ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc"
# the staged programs: missing, and not the frozen ones
world model; rc=$(runst "$P" c); [ "$rc" = 8 ] && grep -q 'missing program' "$M/log/c.log" && ok "stage c without its programs staged: rc 8, nothing touched" || bad "missing bins: rc $rc"
world model; mkdir -p "$M/home/r4g-stage"; cp "$P"/bins/*.bin "$M/home/r4g-stage/"; printf 'x' >> "$M/home/r4g-stage/r4g-cube-a.bin"
rc=$(runst "$P" c)
[ "$rc" = 1 ] && grep -q 'is not the frozen one' "$M/log/c.log" && ok "a staged program that is not the frozen one: rc 1" || bad "tampered bin: rc $rc"
world model; mkdir -p "$M/home/r4g-stage"; cp "$P"/bins/*.bin "$M/home/r4g-stage/"
rc=$(runst "$P" c); [ "$rc" = 0 ] && ok "stage c with the programs staged: rc 0, three probe jobs ($(grep -c '^c-' "$(KD c)/cases.tsv"))" || { bad "stage c: rc $rc"; grep -E 'STOP|abort|missing' "$M/log/c.log" | head -3; }
# table knobs and dbg_write refusals
copytree() { C=$W/tree$N$RANDOM; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/bins" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }
for kn in bif rgn:4 rgn:0 noreset idle pb:0x10 pb:0x500 pb:83 hold hypo:G cell:other needs:o5; do
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
	'echo 1 | sudo -n tee "$D/render_tadata"' 'sudo -n timeout 60 "$T" tri'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_k.sh"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; printf '%s\n' 'x=1; set_hold Y' >> "$C/run/run_stage.sh"; "$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: a second set_hold Y" || ok "guard: refuses a second set_hold Y in run_stage.sh"
for tl in 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kreg x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render 1:par:11=0x1' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --fault' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --poke ta:1=2' \
	'm-9|heldout|risky|rgn:4 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|hold expectdiff|-|tri --keep-going' 'm-9|heldout|risky|rgn:1 expectdiff|0x0118|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --regs 0x0000-0x0c00' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --tadata-fill-render 1:8:0x1' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|probe --cmd 1=0x20000000 x.bin' 'm-9|heldout|risky|pb:0x10 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|pb:0x500 expectdiff|-|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --ctx2' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --words /x' 'm-9|heldout|risky|rgn:1|-|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|sh -c x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --aa4 yes'; do
	copytree; printf '%s\n' "$tl" >> "$C/tables/s0.txt"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed the table line: $tl" || ok "guard: refuses the table line '${tl#m-9|heldout|risky|}'"
done

# ---- 4. the driver: dry run, a knob left behind, gates, restaging ---------------------------------------------------------------
d=$(K_ATT=attX SGX_DRY_RUN=1 bash "$P/run/k.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_r.py gate c' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 2400 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh s0 $fs attX" && echo "$d" | grep -q "r4g-out/attX/o .*/out/attX/o" && echo "$d" | grep -q 'r4g-run' \
	&& ok "driver dry run: the gates, bounded ssh/scp (900 s a stage, 2400 s for o), the frozen sha256, one directory an attempt, the r4g directories" || { bad "driver dry run"; echo "$d" | head -12 | sed 's/^/     /'; }
! echo "$d" | grep -q 'r3k\|r4a\|r4b\|r3x' && ok "no other session's laptop directory in the commands" || bad "foreign directory in the dry run"
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=leak FAKE_KNOB_LEAK=1 bash "$D2T/run/k.sh" --only s0 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_rgn_arrays is 0x00000004 after s0' && ok "render_rgn_arrays read as 4 after a stage stops the driver (rc 42)" || { bad "rgn after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
out=$(env $(drvenv) K_ATT=leak2 FAKE_PB_LEAK=1 bash "$D2T/run/k.sh" --only s0 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_pb_pages is 0x00000083 after s0' && ok "render_pb_pages read as 0x83 after a stage stops the driver (rc 42)" || { bad "pb after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world model; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=g1 bash "$D2T/run/k.sh" --only p 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'SKIPPED: p' && ok "no kept s0 closes the gate: p skipped cleanly (rc 0)" || { bad "gate: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world model; fakehome; out=$(env $(drvenv) bash "$P/run/stage_k.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the rgn4 build" && ok "staging refuses a laptop whose tool is not e6951558..." || bad "staging with a foreign tool: rc $rc"
world model; dtree; fakehome; env $(drvenv) bash "$D2T/run/stage_k.sh" > "$M/log/stage.log" 2>&1
n=$(ls "$M/home/r4g-stage" | wc -l | tr -d ' '); [ "$n" = 5 ] && ok "staging copies the five programs to ~/r4g-stage" || bad "staged programs: $n"
printf 'x' >> "$M/home/r4g-stage/r4g-cube-b.bin"
out=$(env $(drvenv) bash -c "cd '$D2T' && bash run/stage_k.sh" 2>&1); [ -n "$out" ] && ok "restaging after a tampered program copies the frozen one again" || ok "restaged"
num_eq 0x00000000 0 && num_eq 0x00000001 1 && ! num_eq 0x00000004 1 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"
echo "work dir (kept for inspection): $W"
exit $fail
