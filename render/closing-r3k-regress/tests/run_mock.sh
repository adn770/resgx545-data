#!/bin/bash
# tests/run_mock.sh: the R3K-regress runner end to end against a fake tool and a fake debugfs whose directory is mode 000 (only the
# sudo shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard, staging and the whole
# driver (k.sh) with fake ssh/scp/health.  Needs a current freeze (run/freeze_k.sh freeze).  Nothing is deleted: every run writes
# into a new mktemp directory, printed at the end.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
W=$(mktemp -d)
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_k.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_k.sh freeze)"; exit 1; }
N=0
world() {
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/stage" "$M/out" "$M/log" "$M/home"
	for f in reset regs render_param render_tadata kpoke kicker kregnow; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_RGN_INIT:-1}" > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"; echo 0 > "$M/fake/ctrl"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${NOBINS:-}" ] || cp "$P"/bins/*.bin "$M/stage/"
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh"
export K_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") K_SRCV_EXPECT=MOCKSRCV PY
export RESET_WAIT=0 HEALTH_WAIT=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log K_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }
nowrites() { [ ! -s "$M/fake/hold-writes" ] && [ ! -f "$M/fake/rgn-writes" ] && [ ! -f "$M/fake/kregnow-writes" ]; }

# 1. both stages, the frozen tables, the default outcomes: every job runs and is kept
world
for st in rg-ctl rg-pb; do
	rc=$(runst "$P" "$st")
	t=$P/tables/$st.txt; n=$(grep -vc '^#' "$t"); k=$(KD "$st")
	got=$(grep -c '^== ' "$M/log/$st.log"); nc=$(( $(wc -l < "$k/cases.tsv") - 1 ))
	nd=$(awk -F'\t' 'NR > 1 && $9 == "ok" && $7 ~ /--dump-render/' "$k/cases.tsv" | grep -c .); kd=$(ls "$k" | grep -c 'tadata\.bin\.gz')
	ns=$(ls "$k" | grep -c 'snap0\.regs\.gz')
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$nc" = "$n" ] && [ "$kd" = "$nd" ] && [ "$ns" = "$n" ] && grep -q '^## end' "$k/runner.log" \
		&& ok "$st: $got of $n jobs, $nc rows, $ns snapshots, $kd of $nd TA dumps kept, runner.log kept" \
		|| bad "$st: rc $rc, $got of $n jobs, rows $nc, snapshots $ns, dumps $kd of $nd"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg")
[ "$cases" = 36 ] && ok "kernel log: 36 case markers (36 jobs)" || bad "markers: $cases cases"
grep -q 'resgx545 r3kreg knobs-read ctl-u-1024-n1 hold_recovery=N render_rgn_arrays=0x00000001' "$M/kmsg" && ok "the knobs are read and logged before every job" || bad "knob marker"
grep -q 'resgx545 r3kreg health ctl-u-1024-n1 try\|resgx545 r3kreg health end try' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
nowrites && ok "no write to hold_recovery, render_rgn_arrays or kregnow in the whole session (only the reset)" || bad "a knob or kregnow write: $(cat "$M/fake/hold-writes" "$M/fake/rgn-writes" "$M/fake/kregnow-writes" 2>/dev/null | head -3 | tr '\n' ' ')"
[ "$(grep -c . "$M/fake/resets")" -ge 36 ] && ok "a reset before every job ($(grep -c . "$M/fake/resets") resets)" || bad "resets: $(grep -c . "$M/fake/resets")"
! grep -E 'kreg |kpoke|kicker|--regs|--fault' "$M/fake.log" > /dev/null && ok "no tool command carries kreg, kpoke, kicker, --regs or --fault" || bad "forbidden tool option in $M/fake.log"
awk -F'\t' 'NR > 1 && ($8 == "" || $9 == "") { x++ } END { exit x > 0 }' "$M"/out/"$ATT"/*/cases.tsv && ok "rc and class on every row" || bad "rc/class"
dd=$(ls "$(KD rg-ctl)" | grep -c 'ctl-dd-p1\.dd-p1__0\.\(param\|tadata\)\.bin\.gz'); [ "$dd" = 2 ] && ok "the probe's dumps are kept as NAME.PROGRAM.param/tadata.bin.gz" || bad "probe dumps: $dd"
# the scorer over the mock output: the fake prints no recorded values, so rows FAIL (not NODATA): the chain runs end to end
s=$("$PY" "$P/score/score_rg.py" rg-ctl "$(KD rg-ctl)" | grep '^SUMMARY:'); echo "$s" | grep -q 'NOT PASS' && ok "scorer on the mock output: rows that differ from the record FAIL, SUMMARY printed" || bad "scorer: $s"

# 2. stop rules: stopcase NAME WANTED_RC STAGE ENV...
stopcase() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y stopcase "preflight: hold_recovery Y at the start" 1 rg-ctl; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && nowrites && ok "  another session's hold left as it was: no write, no reset" || bad "  the failed preflight touched the GPU"
FAKE_RGN_INIT=4 stopcase "preflight: render_rgn_arrays not 1 at the start" 1 rg-ctl; FAKE_RGN_INIT=1
[ "$(( $(cat "$M/dbgreal/render_rgn_arrays") ))" = 4 ] && [ ! -f "$M/fake/resets" ] && nowrites && ok "  the knob left as it was (4): nothing written, no reset" || bad "  the failed preflight wrote the knob"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" rg-ctl)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/rg-ctl.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion of the loaded module differs from the installed one: rc 1, nothing touched" || bad "srcversion check: rc $rc"
world; rc=$(K_SRCV_EXPECT=230E0EF50FFFD606C53AE3C runst "$P" rg-ctl)
[ "$rc" = 1 ] && grep -q 'is not the expected build (230E0EF50FFFD606C53AE3C)' "$M/log/rg-ctl.log" && [ ! -f "$M/fake/resets" ] && ok "installed = loaded but not the expected build: rc 1, nothing touched" || bad "expected build check: rc $rc"
grep -q '^SRCV_EXPECT=230E0EF50FFFD606C53AE3C$' "$P/run/k.env" && ok "k.env pins the new module's srcversion 230E0EF50FFFD606C53AE3C" || bad "k.env srcversion pin"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset render_rgn_arrays kregnow kpoke kicker; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" rg-ctl)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/rg-ctl.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; rc=$(K_TOOL_SHA=0000 runst "$P" rg-ctl)
[ "$rc" = 1 ] && grep -q "the tool is not R1's" "$M/log/rg-ctl.log" && ok "preflight: a tool that is not R1's build (rc 1)" || bad "tool sha: rc $rc"
stopcase "fatal kernel message in a row" 3 rg-ctl FAKE_RULES='--width 640 --height 480|fatal'
nowrites && ok "  after the fatal stop still no write" || bad "  write after fatal"
stopcase "a row does not return (freeze)" 6 rg-ctl FAKE_RULES='--width 1280 --height 1024|timeout'
stopcase "a fault in a row stops the stage (no hypothesis group exists)" 4 rg-ctl FAKE_RULES='--width 640 --height 480|fault:0x90004:0x20008062:0x480'
grep -q 'STOP: fault-class event in ctl-u-640x480' "$M/log/rg-ctl.log" && ! grep -q '^ctl-u-1280x1024' "$(KD rg-ctl)/cases.tsv" && grep -q '^ctl-u-640x480' "$(KD rg-ctl)/cases.tsv" && ok "  the faulting row is recorded and no later row ran" || bad "  stop after a fault"
grep -q 'resgx545 r3kreg health ctl-u-640x480 try [0-9]' "$M/kmsg" && ok "  a reset and a health triangle ran after the fault" || bad "  health after fault"
nowrites && ok "  no knob write after the fault either (the kernel's reset only)" || bad "  write after fault"
stopcase "a hang stops the stage" 4 rg-pb FAKE_RULES='--poke cmd:1=0x80000000|hang'
stopcase "unexplained failure (rc 1, no diff line)" 4 rg-ctl FAKE_RULES='--width 512 --height 384|nodiff'
stopcase "a parameter-buffer overflow is class fail: stop" 4 rg-ctl FAKE_RULES='--width 2048|overflow'
stopcase "the pre-job reset fails" 13 rg-ctl FAKE_RESET_FAIL_FROM=2
stopcase "health: the first failed recovery stops (the begin health)" 5 rg-ctl FAKE_HEALTH_BAD=1
stopcase "registers unreadable" 12 rg-ctl FAKE_SNAP_FAIL=1
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' stopcase "a fault latched before the job (snap 0)" 14 rg-ctl FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
NOBINS=1 world
rc=$(runst "$P" rg-ctl); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" rg-ctl)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/rg-ctl.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world; rc=$(FSHA=none runst "$P" rg-ctl); [ "$rc" = 1 ] && ok "no frozen sha256 argument: rc 1" || bad "no sha argument: rc $rc"
world
env $(envw) bash "$P/run/run_stage.sh" rg-pb "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD rg-pb)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 13 ] && grep -q '^## end' "$(KD rg-pb)/runner.log" \
	&& ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc, rows $nc"
world; rc=$(runst "$P" rg-pb); rc2=$(runst "$P" rg-pb)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/rg-pb.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"
ATT=att-second; rc3=$(runst "$P" rg-pb)
[ "$rc3" = 0 ] && [ -f "$M/out/att-second/rg-pb/cases.tsv" ] && ok "a new attempt gets its own directory" || bad "new attempt: rc $rc3"

# 3. a copy of the tree: a changed table, forbidden knobs, a tri row without expectdiff, a bare debugfs access, a forbidden write
copytree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/stages.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }
world; copytree
echo "x-extra|heldout|safe|expectdiff|-|probe" >> "$C/tables/rg-pb.txt"
rc=$(runst "$C" rg-pb)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/rg-pb.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
for kn in held bif idle rgn:4 rgn:1 hypo:g:2 noreset expectnopix kregx; do
	world; copytree
	printf '#stage k-mock\nm-1|heldout|risky|%s expectdiff|-|tri --keep-going --width 64 --height 64\n' "$kn" > "$C/tables/k-mock.txt"
	(cd "$C" && run/freeze_k.sh freeze > /dev/null)
	rc=$(runst "$C" k-mock)
	[ "$rc" = 7 ] && [ ! -f "$M/fake/resets" ] && ok "the knob '$kn' is refused before anything runs (rc 7)" || bad "knob $kn: rc $rc"
done
world; copytree
printf '#stage k-mock\nm-1|heldout|risky|expectdiff|0x0118|tri --keep-going --width 64 --height 64\n' > "$C/tables/k-mock.txt"
(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" k-mock)
[ "$rc" = 7 ] && ok "a regtimeline row is refused (rc 7)" || bad "rt row: rc $rc"
world; copytree
printf '#stage k-mock\nm-1|heldout|risky|stophang|-|tri --keep-going --width 64 --height 64\n' > "$C/tables/k-mock.txt"
(cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" k-mock)
[ "$rc" = 1 ] && grep -q 'a tri row without expectdiff' "$M/log/k-mock.log" && [ ! -f "$M/fake/resets" ] && ok "a tri row without expectdiff is refused before anything runs (rc 1)" || bad "missing expectdiff: rc $rc"
# the allow-list of dbg_write at run time: any other name stops at once (rc 7)
for nm in "hold_recovery N" "render_rgn_arrays 1" "kregnow 0x0c04=0x1" "kpoke x"; do
	world; copytree
	printf '\ndbg_write %s\n' "$nm" >> "$C/run/lib_k.sh"
	(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" rg-ctl)
	[ "$rc" = 7 ] && grep -q "dbg_write: ${nm%% *} is not allowed" "$M/log/rg-ctl.log" && nowrites && ok "dbg_write ${nm%% *} is refused at run time: rc 7, nothing written" || bad "dbg_write $nm: rc $rc"
done
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_k.sh"
(cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" rg-ctl)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_k.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kreg"' 'echo 1 | sudo -n tee "$D/kregnow"' 'echo 1 | sudo -n tee "$D/kpoke"' 'echo 1 | sudo -n tee "$D/kicker"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' 'dbg_write alias_skip 1' 'dbg_write hold_recovery N' 'dbg_write render_rgn_arrays 1' \
	'echo 4 | sudo -n tee "$D/render_pb_pages"' 'echo 1 | sudo -n tee "$D/hold_recovery"' 'echo 4 | sudo -n tee "$D/render_rgn_arrays"' 'echo x | sudo -n tee "$KMSG"' 'echo x | sudo -n tee /dev/kmsg' \
	'git status' 'rm -f x' 'reboot' 'echo 1 > /sys/x/clkgate' 'echo x >> own_arm'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_k.sh"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; sed 's/dbg_write reset/dbg_write reset/; s/^\treset) ;;$/\treset|hold_recovery) ;;/' "$P/run/lib_k.sh" > "$C/run/lib_k.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a dbg_write allow-list widened to hold_recovery" || ok "guard: refuses a dbg_write that allows more than reset"
copytree; grep -v "^trap '' PIPE HUP" "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without trap '' PIPE HUP" || ok "guard: refuses a runner that does not ignore PIPE and HUP"
copytree; grep -v 'modinfo -F srcversion' "$P/run/lib_k.sh" > "$C/run/lib_k.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without the srcversion check" || ok "guard: refuses a runner without the srcversion check"
copytree; grep -v 'knobs_ok ||' "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner that does not read the knobs" || ok "guard: refuses a runner that does not read the knobs before a job"
for tl in 'm-9|heldout|risky|expectdiff|-|tri --kreg x --keep-going' 'm-9|heldout|risky|expectdiff|-|tri --keep-going --kpoke-render 2:par:11=0x1' 'm-9|heldout|risky|expectdiff|-|tri --keep-going --fault' \
	'm-9|heldout|risky|expectdiff|-|tri --keep-going --geometry 4' 'm-9|heldout|risky|expectdiff|-|tri --keep-going --poke ta:1=2' 'm-9|heldout|risky|expectdiff|-|tri --keep-going --regs 0x0200' \
	'm-9|heldout|risky|held expectdiff|-|tri --keep-going' 'm-9|heldout|risky|bif|-|-' 'm-9|heldout|risky|rgn:4 expectdiff|-|tri --keep-going' 'm-9|heldout|risky|hypo:a:1 expectdiff|-|tri --keep-going' \
	'm-9|heldout|risky|expectdiff|0x0118|tri --keep-going' 'm-9|heldout|risky|stophang|-|tri --keep-going' 'm-9|heldout|risky|expectdiff|-|tri --keep-going --dump-each'; do
	copytree; printf '%s\n' "$tl" >> "$C/tables/rg-ctl.txt"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed the table line: $tl" || ok "guard: refuses the table line '${tl#m-9|heldout|risky|}'"
done
"$P/run/guard_k.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"

# 4. the driver: dry run (bounded commands, gate, the frozen sha256, the attempt) and the numeric knob compare
d=$(K_ATT=attX SGX_DRY_RUN=1 bash "$P/run/k.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_rg.py gate rg-pb' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh rg-ctl $fs attX" && echo "$d" | grep -q "r3kreg-out/attX/rg-pb .*/out/attX/rg-pb" && echo "$d" | grep -q 'r3kreg-run' \
	&& ok "driver dry run: the rg-pb gate, bounded ssh/scp, the frozen sha256, one directory an attempt, the r3kreg directories" || bad "driver dry run"
[ "$(echo "$d" | grep '^#### ' | awk '{print $2}' | tr '\n' ' ')" = "rg-ctl rg-pb " ] && ok "driver order: rg-ctl, rg-pb" || bad "driver order: $(echo "$d" | grep '^####')"
! echo "$d" | grep -q 'r3kpx\|~/r3k-\|r3kev\|K_FAULTS_PRIOR' && ok "no other session's laptop directory in the commands" || bad "foreign directory in the dry run"
num_eq 0x00000000 0 && num_eq 0x00000422 0x422 && num_eq 0x00000001 1 && ! num_eq 0x00000004 1 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"

# 5. the whole driver and the staging against fake ssh / scp / health (the laptop is a directory)
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF2'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF2
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/stages.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$K_TOOL_SHA/" "$P/run/k.env" > "$D2T/run/k.env"
	printf '%s  /home/jtorra/sgxfive-test-r1\n' "$K_TOOL_SHA" > "$D2T/TOOL.sha256"
	(cd "$D2T" && run/freeze_k.sh freeze > /dev/null); }
fakehome() { cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-r1"; }
drvenv() { echo "$(envw) K_OUT=$M/home/r3kreg-out FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-r1 SGXFIVE_PROBE_BINS=$M/home/r3kreg-stage"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_k.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies, compares every file with the Mac's, checks the tool hash" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
[ -f "$M/home/r3kreg-stage/pix_green.bin" ] && [ -f "$M/home/r3kreg-run/run/run_stage.sh" ] && ok "  files landed in ~/r3kreg-run and ~/r3kreg-stage" || bad "  staged files"
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_k.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not R1's" && ok "staging refuses a laptop whose tool is not R1's build" || bad "staging with a foreign tool: rc $rc"
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=full bash "$D2T/run/k.sh" 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage rg-.* done, health ok, render_rgn_arrays 0x00000001')
[ $rc = 0 ] && [ "$nst" = 2 ] && echo "$out" | grep -q '^R3K-regress done:' && ok "driver, whole session in the mock: 2 stages done with health and the knob read back as 1" \
	|| { bad "driver full run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
v=$("$PY" "$D2T/score/score_rg.py" verdict "$D2T/out/full" 2>&1)
case "$v" in *"SUMMARY: rg-ctl:"*"SUMMARY: rg-pb:"*) ok "  the verdict of the kept session prints both SUMMARY lines" ;; *) bad "  verdict: $v" ;; esac
[ -f "$D2T/out/full/score-rg-pb.txt" ] && grep -q SUMMARY "$D2T/out/full/score-rg-pb.txt" && grep -q 'gate rg-pb: open' "$D2T/out/full/gate-rg-pb.txt" && ok "  the gate file and the scorer ran (one SUMMARY kept, gate open)" || bad "  no score or gate file"
nowrites && ok "  the whole driver session wrote no knob and no kregnow" || bad "  a knob write in the driver session"
# a stage that leaves a knob at another value stops the session (rc 42)
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=leak FAKE_KNOB_LEAK=1 bash "$D2T/run/k.sh" --only rg-ctl 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_rgn_arrays is 0x00000004 after rg-ctl' && ok "the knob read as 4 after a stage stops the driver (rc 42)" || { bad "knob after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
# a closed gate skips rg-pb cleanly
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=gate1 bash "$D2T/run/k.sh" --only rg-pb 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'SKIPPED: rg-pb' && echo "$out" | grep -q 'R3K-regress done (skipped: rg-pb)' && ok "no kept rg-ctl closes the gate: rg-pb is skipped cleanly (rc 0)" || { bad "gate: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
# a stage stop prints the knobs and how to continue
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=stop1 FAKE_RULES='--width 640 --height 480|fatal' bash "$D2T/run/k.sh" 2>&1); rc=$?
[ $rc = 3 ] && echo "$out" | grep -q 'knobs after the stop' && echo "$out" | grep -q 'run/k.sh --from rg-ctl' && ok "a fatal kernel message stops the driver (rc 3), prints the knobs and how to continue" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
out=$(env $(drvenv) bash "$D2T/run/stage_k.sh" 2>&1); rc=$?
[ $rc = 0 ] && ok "restaging after a stop works (nothing on the laptop is a gate)" || bad "restage: rc $rc"
echo "work dir (kept for inspection): $W"
exit $fail
