#!/bin/bash
# tests/run_mock.sh (R7-dpm, from R6-dpm's run_mock.sh): every stage runs end to end through the STAGED runner tree (stage_r7.sh --local)
# under env -i against the fake tool, the fake regtimeline, the fake fwtask_run.py, a plain-directory debugfs and shims for
# sudo/dmesg/timeout/modinfo/python3.  The WORLD (tests/world_r7.py) answers each job from its argv and the knob the runner wrote, never
# from the case name, and with no wall-clock margin anywhere (sample times are its own numbers; RESET_WAIT and HEALTH_WAIT are 0; nothing
# waits for a process to start).  Checks: both sets end to end (87 + 10 jobs, rc 0 each), on the module of each set only; every kept file
# named by r7read.kept_name; sessioncheck.py kept (score_r7.py's REQUIRED, and no undeclared file read) on every stage; the P column
# against the Python twin; the scorer's verdicts in the H-SPAN / walk64 world and in the rival worlds (E874-B, row order, reversed
# operands, the page counts off); a calibration off the model re-picks its cells; the laptop rule (~/scratch/r7d, work directories
# ~/scratch/tmp/r7d.*, none left); and the stops: a control off (class, pages left, count, peaks: rc 10, later stages refused), a control
# WITHOUT A READING (rc 10 at the premise, never a gate), a knob proof, a non-monotone calibration, a hang (rc 4), a void s-b scene,
# s-k's premise (the rungs' counts), one EDM stall and two (rc 11), a failed arm (rc 12), a capture cut and a missing tri dump (rc 13),
# set B on set A's module and back (rc 1), the preflight refusals, every timeout with -k, the knob restored, the guard's refusals.
# LOAD=1 runs set A with 8 `yes` processes beside it.  Needs a current freeze (run/freeze_r7.sh freeze AB).
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run.XXXXXX")
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
# the fake laptop binaries' own needs (not the runner's): the world's sgx-sim (pysgx, built by cargo) finds its toolchain through these
export CARGO_HOME=${CARGO_HOME:-$HOME/.cargo} RUSTUP_HOME=${RUSTUP_HOME:-$HOME/.rustup}
export PATH="$P/tests/shims:$CARGO_HOME/bin:/usr/bin:/bin:/usr/sbin:/sbin" SGXFIVE_TEST="$P/tests/fake_tool.sh" KMSG="$W/kmsg" SRCV_PATH="$W/srcv"
export SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" EXPECT_SRCV_A=MOCKSRCVA EXPECT_SRCV_B=MOCKSRCVB RESET_WAIT=0 HEALTH_WAIT=0 TMPDIR="$P/debug/tmp"
export FAKE_LOG="$W/fake.log" FAKE_TRI_COUNT="$W/tri.count" PYTHONDONTWRITEBYTECODE=1 RUNNER_PY=python3
export FWTASK_RUN="$P/tests/fake_fwtask_run.py" R7_SCORE_NOFREEZE=1
export EXPECT_TOOL=$(shasum -a 256 "$P/tests/fake_tool.sh" | cut -d' ' -f1) EXPECT_RT=$(shasum -a 256 "$P/tests/fake_rt.sh" | cut -d' ' -f1)
: > "$W/kmsg"
LAP=$W/lap
bash "$P/run/stage_r7.sh" --local "$LAP" > "$W/stage-local.out" 2>&1 || { echo "FAIL stage_r7.sh --local"; cat "$W/stage-local.out"; exit 1; }
RUNNER_SH=$LAP/scratch/r7d/run/run/run_stage.sh
MOCKVARS="CARGO_HOME RUSTUP_HOME PY PYTHONDONTWRITEBYTECODE SGXFIVE_TEST KMSG SRCV_PATH SGXFIVE_REGTIMELINE EXPECT_SRCV_A EXPECT_SRCV_B RESET_WAIT HEALTH_WAIT FAKE_LOG FAKE_TRI_COUNT RUNNER_PY FWTASK_RUN EXPECT_TOOL EXPECT_RT"
lapenv() {
	e="PATH=$PATH HOME=${LAPHOME:-$LAP}"
	for v in $MOCKVARS; do eval "e=\"\$e $v=\${$v}\""; done
	echo "$e"
}
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
mkdbg() {
	mkdir -p "$1/dbg" "$1/stage" "$1/out" "$1/tmproot"
	for f in reset render_pb_pages regs buf09 render_param render_tadata own_code own_res load boot status miscinfo; do : > "$1/dbg/$f"; done
	echo 0x00000422 > "$1/dbg/render_pb_pages"; echo off > "$1/dbg/own_arm"
	cp "$P"/bins/p1139-green.bin "$P"/bins/oomring2.blob "$1/stage/"
}
module() { echo "$1" > "$W/srcv"; }       # the module "loaded" (and installed): MOCKSRCVA (set A) or MOCKSRCVB (set B)
runst() { # WDIR STAGE [ENV...]
	wd=$1; st=$2; shift 2
	# shellcheck disable=SC2046
	env -i $(lapenv) SGXFIVE_DEBUGFS="$wd/dbg" SGXFIVE_PROBE_BINS="$wd/stage" OUTROOT="$wd/out" STATE="$wd/state" KEEP="$wd/out/$st" \
		TMPROOT="$wd/tmproot" "$@" bash "$RUNNER_SH" "$st" > "$wd/out/$st.log" 2>&1
	echo $?
}
session() { # WDIR WORLD STAGES
	wd=$1; wo=$2; res=""
	for st in $3; do
		case "$st" in s-k) module MOCKSRCVB ;; *) module MOCKSRCVA ;; esac
		rc=$(runst "$wd" "$st" FAKE_WORLD="$wo"); res="$res $st:$rc"
		[ "$rc" = 0 ] || break
	done
	module MOCKSRCVA
	echo "$res"
}
SETA=$(cat "$P/stages.txt" | tr '\n' ' '); SETB=$(cat "$P/stagesB.txt" | tr '\n' ' ')
score() { "$PY" "$P/score/score_r7.py" "$2" "$1/out/$2" --ctl "$1/out/s-a0" 2>&1 | grep '^SUMMARY'; }
# ------------------------------------------------------------------------------------------------ the H-SPAN / walk64 world, whole
A=$W/a; mkdbg "$A"
if [ "${LOAD:-0}" = 1 ]; then for i in 1 2 3 4 5 6 7 8; do yes > /dev/null & done; echo "(under load: 8 yes processes)"; fi
res=$(session "$A" "" "$SETA $SETB")
if [ "${LOAD:-0}" = 1 ]; then kill $(jobs -p) 2>/dev/null; wait 2>/dev/null; fi
[ "$res" = " s-a0:0 s-m:0 s-b:0 s-v:0 s-k:0" ] && ok "H-SPAN/walk64 world: both sets run to the end ($res)" || { bad "world a: $res"; tail -5 "$A"/out/s-*.log; }
nj=$(cat "$A"/out/s-*/cases.tsv | grep -vc '^name')
nr=$(cat "$A"/out/s-*/cases.tsv | awk -F'\t' '$10 == "ok"' | wc -l | tr -d ' ')
[ "$nj" = 97 ] && [ "$nr" = 97 ] && ok "97 rows in cases.tsv (set A 87, set B 10), 97 jobs ran (none skipped)" || bad "rows $nj, ran $nr"
pb=$(cat "$A/dbg/render_pb_pages")
[ "$pb" = 0x00000422 ] && ok "render_pb_pages back at 0x422 after the session" || bad "render_pb_pages $pb"
grep -q "timeout without -k" "$W/fake.log" && bad "a timeout without -k" || ok "every timeout ran with -k"
[ -z "$(ls "$A/tmproot")" ] && ok "no work directory left under the work root (one a job, removed once kept)" || bad "work directories left"
ls "$TMPDIR" | grep -q '^r7d\.' && bad "a work directory under TMPDIR" || ok "no work directory under TMPDIR"
miss=0
for d in "$A"/out/s-*; do
	[ -d "$d" ] || continue
	for n in $(awk -F'\t' 'NR > 1 && $10 == "ok" {print $1}' "$d/cases.tsv"); do
		for k in out dmesg buf09 regs; do f=$("$PY" "$P/run/r7read.py" kept "$n" "$k"); [ -f "$d/$f" ] || { miss=$((miss + 1)); echo "  missing $d/$f"; }; done
		case "$n" in k-*) for k in page status; do f=$("$PY" "$P/run/r7read.py" kept "$n" "$k"); [ -f "$d/$f" ] || miss=$((miss + 1)); done ;; esac
		case "$n" in v-cal-*) f=$("$PY" "$P/run/r7read.py" kept "$n" param); [ -s "$d/$f" ] || miss=$((miss + 1)) ;; esac
		case "$n" in b-cal-s22) f=$("$PY" "$P/run/r7read.py" kept "$n" ttadata); [ -s "$d/$f" ] || miss=$((miss + 1)) ;; esac
	done
done
[ "$miss" = 0 ] && ok "every kept file where r7read.kept_name says (out, dmesg, buf09, regs; page, status in s-k; dumps in s-v and b-cal-s22)" || bad "$miss kept files missing"
for st in $SETA $SETB; do
	"$PY" "$P/run/sessioncheck.py" kept "$P/score/score_r7.py" "$st" "$A/out/$st" --call score_files > "$W/kept-$st.out" 2>&1 \
		&& ok "sessioncheck kept $st: $(cut -c1-110 "$W/kept-$st.out")" || { bad "sessioncheck kept $st"; head -3 "$W/kept-$st.out"; }
done
nod=$(for st in $SETA $SETB; do "$PY" "$P/score/score_r7.py" "$st" "$A/out/$st" --ctl "$A/out/s-a0"; done | grep -c 'NODATA\|NO READING')
[ "$nod" = 0 ] && ok "the scorer found every job's files and every control's reading (no NODATA, no NO READING)" || bad "$nod NODATA / NO READING rows"
"$PY" "$P/tests/twin.py" "$A/out" "" > "$W/twin-a.log" 2>&1 && ok "P column of every stage = the Python twin ($(tail -1 "$W/twin-a.log"))" || { bad "twin"; head -5 "$W/twin-a.log"; }
s=$(score "$A" s-a0); case "$s" in *"premise holds"*"rows decided"*) ok "s-a0: ${s:0:100}" ;; *) bad "s-a0: $s" ;; esac
s=$(score "$A" s-m); case "$s" in *"H-SPAN at 3072x3072 ("*"rows decided"*"H-SPAN at 1024x1024 ("*"rows decided"*"discriminating cells"*"19 held, 0 FAILED"*) ok "s-m: H-SPAN held at the five targets, the 19 discriminating cells held" ;; *) bad "s-m: $s" ;; esac
s=$(score "$A" s-b); case "$s" in *"H-REPLAY64 counts and run peaks on s44a"*"rows decided"*"s17"*"rows decided"*"H-WALK64 on the dump of b-cal-s22"*"(1 of 1 rows decided)"*) ok "s-b: H-REPLAY64 on the five scenes, H-WALK64 on the dump" ;; *) bad "s-b: $s" ;; esac
s=$(score "$A" s-v); case "$s" in *"vtx-coords 4"*"held"*"vtx-coords 8"*) ok "s-v: the two calibrations read (exploration)" ;; *) bad "s-v: $s" ;; esac
s=$(score "$A" s-k); case "$s" in *"R-5's sa8 bits"*"rows decided"*"H-PASS"*"rows decided"*"source 1 minus source 2"*) ok "s-k: R-5's bits, H-PASS and the creep cell (from the sim-written oomring2 page)" ;; *) bad "s-k: $s" ;; esac
grep -q "passes of the four stubs" "$A/out/s-k.log" && ok "s-k start: arm, fill and triangle exact, passes counted" || bad "s-k arm check"
na=$(grep -c '^arm' "$A/dbg/fw.log"); nw=$(grep -c '^write' "$A/dbg/fw.log")
[ "$na" = 11 ] && [ "$nw" = 20 ] && ok "s-k: 11 arms (the start + 10 jobs), 20 ring clears, all of oomring2.blob" || bad "s-k arms $na clears $nw"
grep '^arm' "$A/dbg/fw.log" | grep -vq oomring2.blob && bad "an arm of another blob" || ok "every arm names oomring2.blob"
# ------------------------------------------------------------------------------------------------ the rival worlds
B=$W/b; mkdbg "$B"; res=$(session "$B" "span=b,order=row,isub=rev,pass=off" "$SETA $SETB")
s=$(score "$B" s-m); case "$s" in *"discriminating cells"*"0 held, 19 FAILED"*) ok "E874-B world: the 19 discriminating cells FAIL H-SPAN ($res)" ;; *) bad "E874-B s-m: $s ($res)" ;; esac
s=$(score "$B" s-b); case "$s" in *"H-REPLAY64 counts and run peaks on s44a"*"is not supported"*"H-WALK64 on the dump"*"is not supported"*) ok "row-order world: H-REPLAY64 and H-WALK64 refuted" ;; *) bad "row s-b: $s" ;; esac
s=$(score "$B" s-k); case "$s" in *"H-PASS"*"is not supported"*"the other way round"*) ok "reversed operands and counts off: H-PASS refuted, the creep cell reads 0x180" ;; *) bad "rev s-k: $s" ;; esac
# ------------------------------------------------------------------------------------------------ a calibration off the model
H=$W/h; mkdbg "$H"; res=$(session "$H" "shift=c25:3" "s-a0 s-m")
grep -q "calibration c25: OFF the model" "$H/out/s-m.log" && [ "$(grep -c 'm-c25-.*cell re-picked' "$H/out/s-m.log")" = 7 ] \
	&& ok "c25 shifted by 3 pages: its calibration is off the model, its 7 cells re-picked ($res)" || bad "shift: $res"
"$PY" "$P/tests/twin.py" "$H/out" "shift=c25:3" > "$W/twin-h.log" 2>&1 && ok "shifted world: P column = the twin (re-picked cells included)" || { bad "twin shifted"; head -5 "$W/twin-h.log"; }
s=$(score "$H" s-m); case "$s" in *"H-STEPMODEL at 2560x2560 (steps in their brackets, U) is not supported"*"H-SPAN at 2560x2560 ("*"rows decided"*) ok "scorer: H-STEPMODEL refuted at 2560x2560, its re-picked cells scored for H-SPAN" ;; *) bad "shift s-m: $s" ;; esac
# ------------------------------------------------------------------------------------------------ the laptop rule with the default paths
HM=$W/home; mkdir -p "$HM"; D0=$W/d0; mkdbg "$D0"; cp -R "$LAP/scratch" "$HM/"
# shellcheck disable=SC2046
rc=$(env -i $(LAPHOME="$HM" lapenv) FAKE_WORLD="" SGXFIVE_DEBUGFS="$D0/dbg" SGXFIVE_PROBE_BINS="$D0/stage" bash "$HM/scratch/r7d/run/run/run_stage.sh" s-a0 > "$W/home.log" 2>&1; echo $?)
[ "$rc" = 0 ] && [ -s "$HM/scratch/r7d/out/s-a0/cases.tsv" ] && [ -d "$HM/scratch/r7d/out/state" ] && [ -z "$(ls "$HM/scratch/tmp")" ] \
	&& [ "$(ls "$HM")" = scratch ] && ! grep -q "command not found\|No such file" "$W/home.log" && grep -q "## work directories: $HM/scratch/tmp/r7d.XXXXXX" "$W/home.log" \
	&& ok "default paths: kept files in ~/scratch/r7d/out, work directories ~/scratch/tmp/r7d.* (none left), nothing else in ~" || { bad "default paths: rc $rc"; tail -3 "$W/home.log"; }
# ------------------------------------------------------------------------------------------------ the stops
C=$W/c; mkdbg "$C"
rc=$(runst "$C" s-a0 FAKE_WORLD="flip=--width 2048,flipP=0x104")
[ "$rc" = 10 ] && [ -e "$C/state/CTLFAIL" ] && grep -q "control a0-c4-b5 read class N" "$C/out/s-a0.log" && ok "a class control off: rc 10, CTLFAIL" || bad "control off: rc $rc"
rc=$(runst "$C" s-m FAKE_WORLD=""); [ "$rc" = 1 ] && grep -q "is refused" "$C/out/s-m.log" && ok "after a failed premise s-m is refused (rc 1)" || bad "s-m after CTLFAIL: rc $rc"
C2=$W/c2; mkdbg "$C2"; rc=$(runst "$C2" s-a0 FAKE_WORLD="left=0xb9:2")
[ "$rc" = 10 ] && grep -q "control a0-t-s3m6 left 0x2 global pages, frozen 1" "$C2/out/s-a0.log" && ok "a pages-left control off: rc 10" || bad "ctlleft: rc $rc"
C3=$W/c3; mkdbg "$C3"; rc=$(runst "$C3" s-a0 FAKE_WORLD="cnt=0xa2:3")
[ "$rc" = 10 ] && grep -q "control a0-qf-0xa2 read 3 partial renders, frozen 2" "$C3/out/s-a0.log" && ok "a count control off: rc 10" || bad "ctlcnt: rc $rc"
C4=$W/c4; mkdbg "$C4"; rc=$(runst "$C4" s-a0 FAKE_WORLD="peaks=0xa2")
[ "$rc" = 10 ] && grep -q "control a0-qf-0xa2 read run peaks 0x80,0xa0,0x3, frozen 0x80,0xa0,0x2" "$C4/out/s-a0.log" && ok "a run-peaks control off: rc 10" || bad "ctlpeaks: rc $rc"
C5=$W/c5; mkdbg "$C5"; rc=$(runst "$C5" s-a0 FAKE_WORLD="noleft=0x105")
[ "$rc" = 10 ] && grep -q "STOP: premise: control a0-c4-b6 has no reading of" "$C5/out/s-a0.log" \
	&& ok "a control WITHOUT A READING (its partial render unsampled: '-'): STOP at the premise, rc 10 (r6-dpm's slip cannot recur)" || { bad "no reading: rc $rc"; grep STOP "$C5/out/s-a0.log"; }
s=$(score "$C5" s-a0); case "$s" in *"STOP: premise: control a0-c4-b6 has no reading of"*) ok "the scorer prints the same STOP, not a headline" ;; *) bad "scorer no-reading: $s" ;; esac
K=$W/k; mkdbg "$K"; rc=$(runst "$K" s-a0 FAKE_WORLD="kskew=2")
[ "$rc" = 10 ] && grep -q "its own 0x0624 read" "$K/out/s-a0.log" && ok "a knob proof off: rc 10" || bad "knob proof: rc $rc"
M=$W/m; mkdbg "$M"; rc=$(runst "$M" s-a0 FAKE_WORLD="skip2=1")
[ "$rc" = 10 ] && grep -qE "steps not monotone|off the frozen model|no reading of S[0-9]" "$M/out/s-a0.log" && ok "a calibration without step 2 in s-a0: rc 10" || bad "non-monotone: rc $rc"
G=$W/g; mkdbg "$G"; runst "$G" s-a0 FAKE_WORLD="" >/dev/null
rc=$(runst "$G" s-m FAKE_WORLD="" FAKE_HANG="--width 3072 --height 3072" FAKE_HANG_P=0x34b)
[ "$rc" = 4 ] && grep -q "STOP: hang in m-c33-0x329" "$G/out/s-m.log" && ok "a hang stops the stage (rc 4)" || bad "hang: rc $rc"
[ -z "$(ls "$G/tmproot")" ] && ok "after a stop the job's work directory is removed by the trap" || bad "work directory left after a stop"
V=$W/v; mkdbg "$V"; runst "$V" s-a0 FAKE_WORLD="" >/dev/null
rc=$(runst "$V" s-b FAKE_WORLD="uoff=s44b:2")
ns=$(awk -F'\t' '$1 ~ /^b-s44b-/ && $10 == "skipped"' "$V/out/s-b/cases.tsv" | wc -l | tr -d ' ')
[ "$rc" = 0 ] && [ "$ns" = 6 ] && ok "an s-b scene whose need is not HU1's: its 6 cells skipped as void, the stage goes on" || bad "void scene: rc $rc skipped $ns"
s=$(score "$V" s-b); case "$s" in *"controls FAILED: b-cal-s44b need: FAILED"*"s17"*"rows decided"*) ok "scorer: scene s44b's calibration FAILED (no headline), the others scored" ;; *) bad "void scene score: $s" ;; esac
rc=$(runst "$V" s-b FAKE_WORLD="" FAKE_DUMPFAIL="--width 2048 --height 2048 -n 1 --move 1:0,384")
[ "$rc" = 13 ] && grep -qE "STOP: the capture of b-cal-s22 is not whole \(no tri (param|tadata) dump\)" "$V/out/s-b.log" && ok "b-cal-s22 without its tri dump: rc 13" || bad "tri dump: rc $rc"
module MOCKSRCVB; rc=$(runst "$V" s-a0 FAKE_WORLD=""); module MOCKSRCVA
[ "$rc" = 1 ] && grep -q "is not set A's module" "$V/out/s-a0.log" && ok "set A refused on set B's module (rc 1)" || bad "set A on B: rc $rc"
rc=$(runst "$V" s-k FAKE_WORLD="")
[ "$rc" = 1 ] && grep -q "is not set B's module" "$V/out/s-k.log" && ok "set B (s-k, oomring2) refused on set A's module 41E2F5C7 (rc 1): it waits for the boot" || bad "set B on A: rc $rc"
module MOCKSRCVB
rc=$(runst "$V" s-k FAKE_WORLD="ringoff=1")
[ "$rc" = 10 ] && grep -q "premise k-b6: the rungs' page counts are not inside the host samples\|no reading of ring_counts" "$V/out/s-k.log" && ok "s-k's premise off (rungs with zero counts): rc 10 after k-b6" || { bad "ring premise: rc $rc"; grep STOP "$V/out/s-k.log"; }
rm -f "$V/dbg/armed_jobs"
rc=$(runst "$V" s-k FAKE_WORLD="stall=3"); [ "$rc" = 0 ] && grep -q "EDM stall after k-b3 (the first): reset once" "$V/out/s-k.log" && ok "one EDM stall: reset once, s-k goes on" || bad "one stall: rc $rc"
rm -f "$V/dbg/armed_jobs"
rc=$(runst "$V" s-k FAKE_WORLD="stall=3+5"); [ "$rc" = 11 ] && ok "a second EDM stall ends s-k (rc 11)" || bad "two stalls: rc $rc"
rc=$(runst "$V" s-k FAKE_WORLD="" FAKE_ARM_FAIL=1); [ "$rc" = 12 ] && ok "a failed arm ends s-k (rc 12)" || bad "arm fail: rc $rc"
rm -f "$V/dbg/own_code"; rc=$(runst "$V" s-k FAKE_WORLD=""); [ "$rc" = 1 ] && grep -q "no debugfs own_code" "$V/out/s-k.log" && ok "preflight: s-k needs the own-task debugfs files" || bad "own_code: rc $rc"
module MOCKSRCVA
rc=$(runst "$V" s-m FAKE_WORLD="" EXPECT_TOOL=0000); [ "$rc" = 1 ] && grep -q "not the pinned rgn4 tool" "$V/out/s-m.log" && ok "preflight: another tool refused" || bad "tool: rc $rc"
rc=$(runst "$V" s-m FAKE_WORLD="" EXPECT_RT=0000); [ "$rc" = 1 ] && grep -q "regtimeline is not the pinned" "$V/out/s-m.log" && ok "preflight: another regtimeline refused" || bad "rt: rc $rc"
rc=$(runst "$V" s-m FAKE_WORLD="" MIN_FREE_KB=999999999999); [ "$rc" = 1 ] && grep -q "not enough free space" "$V/out/s-m.log" && ok "preflight: 600 MB free needed" || bad "free space preflight: rc $rc"
X=$W/x; mkdbg "$X"
rc=$(runst "$X" s-a0 FAKE_WORLD="" FAKE_BIG="--width 2048" FAKE_CUT="--width 2048 --height 2048 --vertices 1500:4096")
[ "$rc" = 13 ] && grep -q "STOP: the capture of a0-cal-2048 is not whole" "$X/out/s-a0.log" && [ ! -e "$X/state/CTLFAIL" ] \
	&& ok "a capture cut at 4096 bytes mid-line: rc 13, no premise read, no CTLFAIL" || bad "cut capture: rc $rc"
X2=$W/x2; mkdbg "$X2"; runst "$X2" s-a0 FAKE_WORLD="" > /dev/null
rc=$(runst "$X2" s-m FAKE_WORLD="" MIN_JOB_KB=999999999999)
[ "$rc" = 13 ] && grep -q "STOP: less than 999999999999 KB free in the work directory before m-cal-c33" "$X2/out/s-m.log" && ! grep -q "^== m-cal-c33" "$X2/out/s-m.log" \
	&& ok "short of space before a job: rc 13, the job is not run" || bad "space before a job: rc $rc"
rc=$(runst "$X2" s-m FAKE_WORLD="" TMPROOT=/tmp/r7dmock); [ "$rc" = 1 ] && ok "a work root under /tmp is refused (rc 1)" || bad "work root /tmp: rc $rc"
ng=$(grep -v '^#' "$P"/tables/*.txt | grep -- '--dump-render' | grep -vcE -- '--width (2048|1024) --height (2048|1024) ')
[ "$ng" = 0 ] && ok "--dump-render only on targets up to 2048x2048" || bad "$ng dump rows on larger targets"
# ------------------------------------------------------------------------------------------------ the guard refuses
for inj in 'echo 1 | sudo -n tee "$D/kreg" >/dev/null' 'cat "$D/regs"' 'while true; do :; done' 'sudo -n reboot' 'fw kreg 0x0814' \
	'sudo -n timeout 5 true' 'mkdir -p ~/r6d-run' 'W=$(mktemp -d /tmp/r7d.XXXXXX)' 'W=$(mktemp -d)' 'mkdir -p ~/scratch/r7g/out'; do
	G2=$W/guard; rm -rf "$G2"; mkdir -p "$G2"; cp -R "$P/run" "$P/tables" "$P/bins" "$P/asm" "$P/score" "$G2/"
	printf '%s\n' "$inj" >> "$G2/run/lib_r7.sh"
	bash "$G2/run/guard_r7.sh" > "$W/guard.out" 2>&1 && bad "guard accepted: $inj" || ok "guard refuses: $inj"
done
G2=$W/guard; rm -rf "$G2"; mkdir -p "$G2"; cp -R "$P/run" "$P/tables" "$P/bins" "$P/asm" "$P/score" "$G2/"
printf '# x\n' >> "$G2/run/sessioncheck.py"
bash "$G2/run/guard_r7.sh" > "$W/guard.out" 2>&1 && bad "guard accepted a changed sessioncheck.py" || ok "guard refuses a sessioncheck.py that is not the landed one"
bash "$P/run/guard_r7.sh" > "$W/guard.out" 2>&1 && ok "guard: the session itself is clean" || { bad "guard on the session"; cat "$W/guard.out"; }
SGX_DRY_RUN=1 bash "$P/run/r7.sh" > "$W/dry.out" 2>&1
[ "$(grep -c 'ssh .*~/scratch/r7d/run/run/run_stage.sh' "$W/dry.out")" = 4 ] && grep -q 'OUTROOT=\$HOME/scratch/r7d/out/a1 ' "$W/dry.out" && grep -q 'verify A' "$W/dry.out" && ! grep -qE 'make|build|r6d|/tmp' "$W/dry.out" \
	&& ok "driver dry run, set A: 4 stages through ~/scratch/r7d, attempt a1, freeze A verified" || { bad "driver dry run A"; head -5 "$W/dry.out"; }
R7_SET=B SGX_DRY_RUN=1 bash "$P/run/r7.sh" > "$W/dryb.out" 2>&1
[ "$(grep -c 'run_stage.sh s-k' "$W/dryb.out")" = 1 ] && grep -q 'out/b1 ' "$W/dryb.out" && grep -q 'verify B' "$W/dryb.out" \
	&& ok "driver dry run, set B: s-k only, attempt b1, freeze B verified" || { bad "driver dry run B"; head -5 "$W/dryb.out"; }
SGX_DRY_RUN=1 bash "$P/run/stage_r7.sh" > "$W/stage.out" 2>&1
grep -q "mkdir -p scratch/r7d/run/run scratch/r7d/run/tables scratch/r7d/stage scratch/r7d/out scratch/tmp" "$W/stage.out" && ! grep -qE "(^|[ :])/tmp" "$W/stage.out" \
	&& ok "staging dry run: every laptop file under ~/scratch/r7d (and ~/scratch/tmp)" || { bad "staging dry run"; head -5 "$W/stage.out"; }
nf=$(cat "$W"/*/out/*.log 2>/dev/null | grep -c "command not found\|: No such file or directory")
[ "$nf" = 0 ] && ok "no stage log of any world shows a command or file not found" || { bad "$nf 'not found' lines in the stage logs"; cat "$W"/*/out/*.log | grep "command not found\|No such file" | head -3; }
echo "ALL: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
