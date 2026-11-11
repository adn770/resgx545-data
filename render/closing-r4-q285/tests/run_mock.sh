#!/bin/bash
# tests/run_mock.sh: the R4-A runner and driver end to end against a fake tool and a fake debugfs whose directory is mode 000 (only
# the sudo shim reaches it: an unprivileged access fails, as on the laptop).
#   1. every world of tests/worlds.py run through the WHOLE driver (staging, k.sh, gate, scorer, verdict): each hypothesis world
#      must print its verdict, each failing-control world must stop or close the gate as predicted;
#   2. the runner's rules: rgn:1 written after each reset and read back, render_rgn_arrays put back to 0 after every job and at
#      every exit (stops included); without rgn:1 the fake kernel refuses TE 0x40 (the knob is needed); the kmsg slice starts at
#      the case marker (a fault line before it is not the job's); the reset information lines are not bad; the stop rules;
#   3. the guard; 4. the driver's dry run, gate, knob check and restaging.
# Needs a current freeze (run/freeze_k.sh freeze).  Nothing is deleted: every run writes into a new mktemp directory.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/resgx545/.venv/bin/python}
W=$(mktemp -d)
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_k.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_k.sh freeze)"; exit 1; }
N=0
world() { # world [WORLD]: a fresh fake laptop running WORLD (default old)
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/out" "$M/log" "$M/home"
	for f in reset regs render_param render_tadata kpoke; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_RGN_INIT:-0}" > "$M/dbgreal/render_rgn_arrays"
	echo N > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	"$PY" "$P/tests/worlds.py" fake "$M/world" "${1:-old}" || { echo "FAIL: world ${1:-old}"; exit 1; }
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh"
export K_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") K_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake FAKE_WORLD=$M/world KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw FAKE_LOG=$M/fake.log K_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }
rgn_now() { echo $(( $(cat "$M/dbgreal/render_rgn_arrays") )); }
rgn_last() { tail -n 1 "$M/fake/rgn-writes" 2>/dev/null; }

# ---- 4 (first: the driver pieces every world below uses) -------------------------------------------------------------
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$K_TOOL_SHA/" "$P/run/k.env" > "$D2T/run/k.env"
	printf '%s  /home/jtorra/sgxfive-test-rgn4\n' "$K_TOOL_SHA" > "$D2T/TOOL.sha256"
	(cd "$D2T" && run/freeze_k.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-rgn4"; }
drvenv() { echo "$(envw) K_OUT=$M/home/r4a-out FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-rgn4"; }
drive() { # drive WORLD [ENV...]: stage and run the whole driver on a fresh laptop; sets OUT, RC, D2T, M
	local wn=$1; shift
	world "$wn"; dtree; fakehome
	env $(drvenv) bash "$D2T/run/stage_k.sh" > "$M/log/stage.log" 2>&1 || { bad "staging for world $wn: $(tail -n 2 "$M/log/stage.log")"; }
	OUT=$(env $(drvenv) "$@" K_ATT=full bash "$D2T/run/k.sh" 2>&1); RC=$?
	VERDICT=$("$PY" "$D2T/score/score_a.py" verdict "$D2T/out/full" 2>&1)
}

# ---- 1. every world through the whole driver -------------------------------------------------------------------------
drive old
nst=$(echo "$OUT" | grep -c '^stage a-pb.* done, health ok, render_rgn_arrays 0x00000000')
[ $RC = 0 ] && [ "$nst" = 2 ] && echo "$OUT" | grep -q '^R4-A done' && ok "world old: the driver runs both stages, health ok, render_rgn_arrays read back 0 after each" \
	|| { bad "world old: rc $RC, $nst stages"; echo "$OUT" | tail -8 | sed 's/^/     /'; }
echo "$VERDICT" | grep -q '^SUMMARY: Q285: H-OLD.*(4 of 4 rows decided)' && ok "world old: the verdict of the kept run is H-OLD" || bad "world old verdict: $VERDICT"
grep -q 'gate a-pb: open' "$D2T/out/full/gate-a-pb.txt" && ok "  the gate file says open (computed from the kept a-pb0)" || bad "  gate file"
[ "$(grep -c '^1$' "$M/fake/rgn-writes")" = 8 ] && [ "$(rgn_now)" = 0 ] && ok "  render_rgn_arrays written 1 for each of the 8 jobs and back to 0 at the end" \
	|| bad "  rgn writes: $(tr '\n' ' ' < "$M/fake/rgn-writes"), now $(rgn_now)"
[ ! -s "$M/fake/other-writes" ] && ok "  no debugfs write but reset and render_rgn_arrays" || bad "  other debugfs writes: $(cat "$M/fake/other-writes")"
n=$(ls "$M/home/r4a-out/full/a-pb" | grep -c 'kpoke\.txt\.gz'); [ "$n" = 5 ] && ok "  the armed kpokes read after every job are kept (5 in a-pb)" || bad "  kpoke files: $n"
zcat < "$D2T/out/full/a-pb/pb-p3a-twin.dmesg.gz" | grep -q 'kpoke par:26=0x00000000 applied' && ok "  the job's kmsg slice keeps the applied lines" || bad "  applied lines not in the slice"
for wv in "field|^SUMMARY: Q285: H-FIELD.*(4 of 4 rows decided)" "q030|^SUMMARY: Q285: cannot tell.*Q030" "both|^SUMMARY: Q285: cannot tell.*both effects" \
	"mixed|^SUMMARY: Q285: cannot tell.*p3 mixed" "p2-notapplied|^SUMMARY: Q285: controls FAILED.*pb-p2-own11" "p2-armed|^SUMMARY: Q285: controls FAILED.*pb-p2-own11" \
	"p3-short|^SUMMARY: Q285: cannot tell" "p4-other|^SUMMARY: Q285: cannot tell.*matched no hypothesis"; do
	wn=${wv%%|*}; want=${wv#*|}
	drive "$wn"
	[ $RC = 0 ] && echo "$VERDICT" | grep -q "$want" && ok "world $wn: driver rc 0, verdict as predicted" || { bad "world $wn: rc $RC, verdict: $VERDICT"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
done
drive ctl-k2
[ $RC = 0 ] && echo "$OUT" | grep -q 'SKIPPED: a-pb' && echo "$VERDICT" | grep -q '^SUMMARY: Q285: not run' && grep -q 'closed.*FAIL' "$D2T/out/full/gate-a-pb.txt" \
	&& ok "world ctl-k2 (controls give one-render values): the gate closes, a-pb is skipped cleanly, Q285 not run" || { bad "world ctl-k2: rc $RC: $VERDICT"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
! grep -q 'kpoke-render' "$M/fake.log" && ok "  no poke job ran with the gate closed" || bad "  a poke job ran"
drive ctl-nodata
[ $RC = 0 ] && echo "$OUT" | grep -q 'SKIPPED: a-pb' && grep -q 'closed.*pb-p0-te60' "$D2T/out/full/gate-a-pb.txt" && [ "$(rgn_now)" = 0 ] \
	&& ok "world ctl-nodata: p0 prints only its echo (rc 0): p0 does not pass, the gate closes, a-pb is skipped, the knob is back at 0" \
	|| { bad "world ctl-nodata: rc $RC"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
! grep -q 'kpoke-render' "$M/fake.log" && ok "  no poke job ran with the gate closed" || bad "  a poke job ran"
drive p4-hang
[ $RC = 4 ] && echo "$OUT" | grep -q 'hang in pb-p4a-ffff' && ! grep -q '^pb-p4b-ffff' "$M/home/r4a-out/full/a-pb/cases.tsv" && [ "$(rgn_now)" = 0 ] \
	&& ok "world p4-hang: a hang stops the stage after p4a (rc 4), p4b does not run, the knob is back at 0" || { bad "world p4-hang: rc $RC"; echo "$OUT" | tail -4 | sed 's/^/     /'; }
cp -R "$M/home/r4a-out/full/a-pb" "$D2T/out/full/a-pb" 2>/dev/null
v=$("$PY" "$D2T/score/score_a.py" verdict "$D2T/out/full" 2>&1)
echo "$v" | grep -q '^SUMMARY: Q285: cannot tell' && ok "  scored from the kept stage: Q285 cannot tell" || bad "  p4-hang verdict: $v"

# ---- 2. the runner's rules -------------------------------------------------------------------------------------------
stopcase() { local nm=$1 want=$2 st=$3; shift 3; world "${WN:-old}"; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
world old; rc=$(runst "$P" a-pb0)
seq=$(grep -o 'resgx545 r4a [a-z-]* pb-d0-te40' "$M/kmsg" | awk '{print $3}' | tr '\n' ' ')
[ "$rc" = 0 ] && grep -q 'resgx545 r4a rgn pb-d0-te40 1' "$M/kmsg" && grep -q 'resgx545 r4a knobs-read pb-d0-te40 hold_recovery=N render_rgn_arrays=0x00000001' "$M/kmsg" \
	&& grep -q 'resgx545 r4a rgn-back pb-d0-te40 0' "$M/kmsg" && ok "rgn:1 is written after the job's reset, read back before it and put back to 0 after it ($seq)" || bad "rgn sequence: rc $rc: $seq"
awk '/SGX reset/ && !g {r=NR} /resgx545 r4a rgn pb-p0-te60 1/ {g=NR} END {exit !(r && g && r < g)}' "$M/kmsg" && ok "  the reset comes before the knob write" || bad "  order of reset and knob"
[ "$(grep -c . "$M/fake/resets")" -ge 5 ] && ok "  a reset before every job and before the end health ($(grep -c . "$M/fake/resets") resets)" || bad "  resets: $(grep -c . "$M/fake/resets")"
grep -q 'resgx545 r4a health begin fill' "$M/kmsg" && grep -q 'resgx545 r4a health begin tri' "$M/kmsg" && ok "  the begin health runs a fill and a triangle" || bad "  begin health"
# without the knob the fake kernel refuses TE 0x40: the session needs rgn:1 (or --aa4)
world old; C=$W/norgn; mkdir -p "$C"; cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"
sed -i '' 's/|rgn:1 expectdiff|/|expectdiff|/' "$C/tables/a-pb0.txt"; (cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" a-pb0); [ "$rc" = 4 ] && grep -q 'unexplained failure in pb-d0-te40' "$M/log/a-pb0.log" && ok "without rgn:1 the a2788bd8 rule refuses TE 0x40 (-EINVAL): the stage stops (rc 4)" || bad "no rgn: rc $rc"
# the knob does not read back: stop, and it is still put back to 0
WN=old stopcase "render_rgn_arrays does not read back 1" 19 a-pb0 FAKE_RGN_STUCK=1
FAKE_RGN_INIT=1 stopcase "preflight: render_rgn_arrays not 0 (the new default) at the start" 1 a-pb0; FAKE_RGN_INIT=0
[ ! -f "$M/fake/resets" ] && [ ! -f "$M/fake/rgn-writes" ] && ok "  nothing touched (no reset, no knob write)" || bad "  the failed preflight touched the GPU"
WN=old stopcase "render_rgn_arrays does not go back to 0 after a job" 19 a-pb0 FAKE_RGN_STUCK_AT0=1
stopcase "fatal kernel message in a row" 3 a-pb0 FAKE_RULES='cmd:1=0x60000000|fatal'
[ "$(rgn_last)" = 0 ] && ok "  after the fatal stop the knob is still written back to 0 (no reset)" || bad "  knob after fatal: last write $(rgn_last)"
stopcase "a row does not return (freeze)" 6 a-pb0 FAKE_RULES='cmd:1=0x60000000|timeout'
[ "$(rgn_now)" = 0 ] && ok "  after the freeze stop the knob reads 0" || bad "  knob after freeze: $(rgn_now)"
stopcase "a fault stops the stage (fault limit 1)" 4 a-pb FAKE_RULES='par:12=|fault'
grep -q '^pb-p3a-twin' "$(KD a-pb)/cases.tsv" && ! grep -q '^pb-p3b-twin' "$(KD a-pb)/cases.tsv" && grep -q 'resgx545 r4a health pb-p3a-twin fill' "$M/kmsg" \
	&& ok "  the faulting row is recorded, no later row ran, a reset and health followed" || bad "  stop after a fault"
stopcase "an unexplained failure (rc 1, no diff line) stops" 4 a-pb0 FAKE_RULES='cmd:1=0x60000000|nodiff'
stopcase "the pre-job reset fails" 13 a-pb0 FAKE_RESET_FAIL_FROM=2
stopcase "health: the first failed recovery stops (begin)" 5 a-pb0 FAKE_HEALTH_BAD=1
stopcase "registers unreadable" 12 a-pb0 FAKE_SNAP_FAIL=1
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' stopcase "a fault latched before the job (snap 0)" 14 a-pb0 FAKE_STUCK=1; FAKE_STATE_INIT=idle
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
WN=old stopcase "the kernel's reset information lines inside a job are not bad" 0 a-pb0 FAKE_RULES='cmd:1=0x60000000|resetinfo'
awk -F'\t' '$1 == "pb-p0-te60" && $9 == "ok" {f=1} END {exit !f}' "$(KD a-pb0)/cases.tsv" && zcat < "$(KD a-pb0)/pb-p0-te60.dmesg.gz" | grep -q 'after the fault clear' && ok "  p0 is class ok with both reset lines in its slice" || bad "  reset info class"
# the slice starts at the case marker: a fault line before it is not the job's (never a line count)
world old; printf 'gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20008062 (PD 0x0) stalls job 3, recovering\n' >> "$M/kmsg"
rc=$(runst "$P" a-pb0); [ "$rc" = 0 ] && ! zcat < "$(KD a-pb0)/pb-d0-te40.dmesg.gz" | grep -q 'stalls job 3' && ok "a fault line logged before the first case marker is not in any job's slice (rc 0)" || bad "slice by marker: rc $rc"
for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kpoke; do
	world old; mv "$M/dbgreal/$f" "$M/dbgreal/$f.gone"; rc=$(runst "$P" a-pb0)
	[ "$rc" = 1 ] && grep -q "has no debugfs $f" "$M/log/a-pb0.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $f: rc 1, nothing touched" || bad "preflight without $f: rc $rc"
done
world old; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" a-pb0)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/a-pb0.log" && ok "srcversion loaded != installed: rc 1" || bad "srcversion: rc $rc"
world old; rc=$(K_SRCV_EXPECT=99CD90DA26E3AFF9C450517 runst "$P" a-pb0)
[ "$rc" = 1 ] && grep -q 'is not the expected build (99CD90DA26E3AFF9C450517)' "$M/log/a-pb0.log" && ok "installed = loaded but not 99CD90DA...: rc 1" || bad "expected build: rc $rc"
grep -q '^SRCV_EXPECT=99CD90DA26E3AFF9C450517$' "$P/run/k.env" && ok "k.env pins srcversion 99CD90DA26E3AFF9C450517 (fork a2788bd8)" || bad "k.env srcversion"
grep -q '^TOOL_SHA=e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a$' "$P/run/k.env" && ok "k.env pins ~/sgxfive-test-rgn4 e6951558..." || bad "k.env tool"
world old; rc=$(K_TOOL_SHA=0000 runst "$P" a-pb0); [ "$rc" = 1 ] && grep -q "the tool is not the rgn4 build" "$M/log/a-pb0.log" && ok "preflight: another tool: rc 1" || bad "tool sha: rc $rc"
world old; rc=$(FSHA=0000 runst "$P" a-pb0); [ "$rc" = 1 ] && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha: rc $rc"
world old; rc=$(runst "$P" a-pb0); rc2=$(runst "$P" a-pb0)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: $rc $rc2"
world old
env $(envw) bash "$P/run/run_stage.sh" a-pb0 "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
[ "$rc" = 0 ] && grep -q '^## end' "$(KD a-pb0)/runner.log" && ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc"

# ---- 3. the guard ----------------------------------------------------------------------------------------------------
copytree() { C=$W/tree$N$RANDOM; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/gen" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }
"$P/run/guard_k.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"
for inj in 'echo 1 | sudo -n tee "$D/kreg"' 'echo 1 | sudo -n tee "$D/kregnow"' 'echo par:11=0 | sudo -n tee "$D/kpoke"' 'echo 1 | sudo -n tee "$D/kicker"' \
	'until false; do :; done' 'x=$(cat f | tail -1)' 'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' \
	'dbg_write alias_skip 1' 'dbg_write hold_recovery N' 'dbg_write render_rgn_arrays 4' 'echo 4 | sudo -n tee "$D/render_rgn_arrays"' 'echo x | sudo -n tee "$KMSG"' \
	'echo x | sudo -n tee /dev/kmsg' 'git status' 'rm -f x' 'reboot' 'echo 1 > /sys/x/clkgate' 'echo x >> own_arm' 'sed -n 5,9p "$JW/dmesg.all"'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_k.sh"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
for tl in 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kreg x' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render 1:par:11=0x1' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render 2:ta:11=0x1' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render 2:par:11^=0x1' \
	'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --fault' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --poke ta:1=2' \
	'm-9|heldout|risky|rgn:4 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|held expectdiff|-|tri --keep-going' 'm-9|heldout|risky|rgn:1 expectdiff|0x0118|tri --keep-going' \
	'm-9|heldout|risky|rgn:1 stophang|-|tri --keep-going' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --aa4' 'm-9|heldout|risky|rgn:1 expectdiff|-|tri --keep-going --kpoke-render2 2:par:1=0x1'; do
	copytree; printf '%s\n' "$tl" >> "$C/tables/a-pb.txt"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed the table line: $tl" || ok "guard: refuses the table line '${tl#m-9|heldout|risky|}'"
done
for kn in held bif rgn:4 rgn:0 hypo:g:2 noreset; do
	world old; copytree
	printf '#stage a-mock\nm-1|heldout|risky|%s expectdiff|-|tri --keep-going --width 64 --height 64\n' "$kn" > "$C/tables/a-mock.txt"
	(cd "$C" && run/freeze_k.sh freeze > /dev/null)
	rc=$(runst "$C" a-mock)
	[ "$rc" = 7 ] && [ ! -f "$M/fake/resets" ] && ok "the knob '$kn' is refused before anything runs (rc 7)" || bad "knob $kn: rc $rc"
done
for nm in "hold_recovery N" "render_rgn_arrays 4" "kpoke x" "kregnow 0x0c04=0x1"; do
	world old; copytree
	printf '\ndbg_write %s\n' "$nm" >> "$C/run/lib_k.sh"
	(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" a-pb0)
	[ "$rc" = 7 ] && grep -q "dbg_write: ${nm} is not allowed" "$M/log/a-pb0.log" && ok "dbg_write $nm is refused at run time: rc 7" || bad "dbg_write $nm: rc $rc"
done

# ---- 4. the driver: dry run, a knob left behind, gate without a-pb0, restaging --------------------------------------
d=$(K_ATT=attX SGX_DRY_RUN=1 bash "$P/run/k.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_a.py gate a-pb' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh a-pb0 $fs attX" && echo "$d" | grep -q "r4a-out/attX/a-pb .*/out/attX/a-pb" && echo "$d" | grep -q 'r4a-run' \
	&& ok "driver dry run: the a-pb gate, bounded ssh/scp, the frozen sha256, one directory an attempt, the r4a directories" || { bad "driver dry run"; echo "$d" | head -12 | sed 's/^/     /'; }
! echo "$d" | grep -q 'r3k\|r4b\|r3x' && ok "no other session's laptop directory in the commands" || bad "foreign directory in the dry run"
world old; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=leak FAKE_KNOB_LEAK=1 bash "$D2T/run/k.sh" --only a-pb0 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_rgn_arrays is 0x00000004 after a-pb0' && ok "render_rgn_arrays read as 4 after a stage stops the driver (rc 42)" || { bad "knob after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world old; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=g1 bash "$D2T/run/k.sh" --only a-pb 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'SKIPPED: a-pb' && ok "no kept a-pb0 closes the gate: a-pb skipped cleanly (rc 0)" || { bad "gate: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
world old; fakehome; out=$(env $(drvenv) bash "$P/run/stage_k.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not the rgn4 build" && ok "staging refuses a laptop whose tool is not e6951558..." || bad "staging with a foreign tool: rc $rc"
num_eq 0x00000000 0 && num_eq 0x00000001 1 && ! num_eq 0x00000004 1 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"
echo "work dir (kept for inspection): $W"
exit $fail
