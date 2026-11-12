#!/bin/bash
# tests/run_mock.sh (R5-dpm, from R3-geo's run_mock.sh): every stage runs end to end through run/run_stage.sh against the fake tool, the
# fake regtimeline, the fake fwtask_run.py, a plain-directory debugfs and shims for sudo/dmesg/timeout/modinfo.  The WORLD
# (tests/world_r5.py) answers each job from its argv and the knob the runner wrote, never from the case name.  Checks: the whole session
# (82 jobs, 7 stages, rc 0 each), every kept file named by r5read.kept_name and found by the scorer (no NODATA), the derived cells read
# from the calibration (a world whose steps are shifted moves them), the P column against the Python twin (r5plan's rule on the world's
# steps), the scorer's verdict for each hypothesis world (pend, block, noise; the count rule; H-BITS from the sim-written page), and the
# stops: a control off (rc 10, CTLFAIL, later stages refused), a knob proof off, a non-monotone calibration, a hang (rc 4), a void
# B scene (its cells skipped), one EDM stall (reset, goes on) and two (rc 11), a failed arm (rc 12), the preflight refusals
# (srcversion, tool, regtimeline), every timeout with -k, the knob restored, the guard's refusals.
# Needs a current freeze (run/freeze_r5.sh freeze): the runner compares its tables and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run.XXXXXX")
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" KMSG="$W/kmsg" SRCV_PATH="$W/srcv"
export SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" EXPECT_SRCV=MOCKSRCV RESET_WAIT=0 HEALTH_WAIT=0 TMPDIR="$P/debug/tmp"
export FAKE_LOG="$W/fake.log" FAKE_TRI_COUNT="$W/tri.count" PYTHONDONTWRITEBYTECODE=1 RUNNER_PY=python3
export FWTASK_RUN="$P/tests/fake_fwtask_run.py" R5_SCORE_NOFREEZE=1
export EXPECT_TOOL=$(shasum -a 256 "$P/tests/fake_tool.sh" | cut -d' ' -f1) EXPECT_RT=$(shasum -a 256 "$P/tests/fake_rt.sh" | cut -d' ' -f1)
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
mkdbg() { # DIR: a fresh fake debugfs and staging directory
	mkdir -p "$1/dbg" "$1/stage" "$1/out"
	for f in reset render_pb_pages regs buf09 render_param render_tadata own_code own_res load boot status miscinfo; do : > "$1/dbg/$f"; done
	echo 0x00000422 > "$1/dbg/render_pb_pages"; echo off > "$1/dbg/own_arm"
	cp "$P"/bins/p1139-green.bin "$P"/bins/oomring.blob "$1/stage/"
}
runst() { # WDIR STAGE [ENV...]: the stage's exit status; log in WDIR/out/STAGE.log, kept in WDIR/out/STAGE, state in WDIR/state
	wd=$1; st=$2; shift 2
	env "$@" SGXFIVE_DEBUGFS="$wd/dbg" SGXFIVE_PROBE_BINS="$wd/stage" OUTROOT="$wd/out" STATE="$wd/state" KEEP="$wd/out/$st" \
		bash "$P/run/run_stage.sh" "$st" > "$wd/out/$st.log" 2>&1
	echo $?
}
session() { # WDIR WORLD: every stage in order; "st:rc ..." up to the first non-zero
	wd=$1; wo=$2; res=""
	for st in $(cat "$P/stages.txt"); do
		rc=$(runst "$wd" "$st" FAKE_WORLD="$wo"); res="$res $st:$rc"
		[ "$rc" = 0 ] || break
	done
	echo "$res"
}
score() { "$PY" "$P/score/score_r5.py" "$2" "$1/out/$2" --ctl "$1/out/d-a0" 2>&1 | grep '^SUMMARY'; }
# ---------------------------------------------------------------------------------------------------------- the H-PEND world, whole
A=$W/a; mkdbg "$A"
res=$(session "$A" "hyp=pend")
[ "$res" = " d-a0:0 d-a1:0 d-a2:0 d-a2b:0 d-t:0 d-b:0 d-a3:0" ] && ok "pend world: the seven stages run to the end ($res)" || bad "pend world: $res"
nj=$(cat "$A"/out/d-*/cases.tsv | grep -vc '^name')
nr=$(cat "$A"/out/d-*/cases.tsv | awk -F'\t' '$10 == "ok"' | wc -l | tr -d ' ')
[ "$nj" = 82 ] && [ "$nr" = 82 ] && ok "82 rows in cases.tsv, 82 jobs ran (none skipped)" || bad "rows $nj, ran $nr"
pb=$(cat "$A/dbg/render_pb_pages")
[ "$pb" = 0x00000422 ] && ok "render_pb_pages back at 0x422 after the session" || bad "render_pb_pages $pb"
grep -q "timeout without -k" "$W/fake.log" && bad "a timeout without -k" || ok "every timeout ran with -k"
miss=0
for d in "$A"/out/d-*; do
	[ -d "$d" ] || continue
	for n in $(awk -F'\t' 'NR > 1 && $10 == "ok" {print $1}' "$d/cases.tsv"); do
		for k in out dmesg buf09 regs; do f=$(python3 "$P/run/r5read.py" kept "$n" "$k"); [ -f "$d/$f" ] || { miss=$((miss + 1)); echo "  missing $d/$f"; }; done
		case "$n" in a3-*) for k in page status; do f=$(python3 "$P/run/r5read.py" kept "$n" "$k"); [ -f "$d/$f" ] || miss=$((miss + 1)); done ;; esac
	done
done
[ "$miss" = 0 ] && ok "every kept file the scorer reads is where r5read.kept_name says (out, dmesg, buf09, regs; page and status in A3)" || bad "$miss kept files missing"
nod=$(for st in $(cat "$P/stages.txt"); do "$PY" "$P/score/score_r5.py" "$st" "$A/out/$st" --ctl "$A/out/d-a0"; done | grep -c 'NODATA')
[ "$nod" = 0 ] && ok "the scorer found every job's files (no NODATA in any stage)" || bad "$nod NODATA rows"
"$PY" "$P/tests/twin.py" "$A/out" "hyp=pend" > "$W/twin-a.log" 2>&1 && ok "P column of every stage = the Python twin ($(tail -1 "$W/twin-a.log"))" || { bad "twin"; head -5 "$W/twin-a.log"; }
s=$(score "$A" d-a0); case "$s" in *"premise holds on rgn4"*"rows decided"*) ok "d-a0: $s" ;; *) bad "d-a0: $s" ;; esac
s=$(score "$A" d-a1); case "$s" in *"H-GREQ held (5 of 5)"*"H-NOISE refuted"*) ok "d-a1: ${s:0:120}" ;; *) bad "d-a1: $s" ;; esac
s=$(score "$A" d-a2); case "$s" in *"S cells: H-PEND"*) ok "d-a2 pend world: H-PEND" ;; *) bad "d-a2: $s" ;; esac
s=$(score "$A" d-a2b); case "$s" in *"H-GREQ: 6 held, 0 FAILED"*) ok "d-a2b: ${s:0:110}" ;; *) bad "d-a2b: $s" ;; esac
s=$(score "$A" d-t); case "$s" in *"H-TAIL: 8 held, 0 FAILED"*) ok "d-t: H-TAIL 8 held" ;; *) bad "d-t: $s" ;; esac
s=$(score "$A" d-b); case "$s" in *"g-qf controls repeat"*"H-CNT on scene s119"*"(10 of 10 rows decided)"*"H-CNT on scene s198"*"(10 of 10 rows decided)"*) ok "d-b: H-CNT 10 of 10 on both scenes" ;; *) bad "d-b: $s" ;; esac
s=$(score "$A" d-a3); case "$s" in *"H-BITS"*"rows decided"*"H-PEND on the rungs: 7 held, 0 FAILED"*"H-BLOCK on the rungs: 3 held, 4 FAILED"*) ok "d-a3: H-BITS held, the rungs say PEND (from the sim-written page)" ;; *) bad "d-a3: $s" ;; esac
grep -q "passes of the four stubs" "$A/out/d-a3.log" && ok "A3 start: arm, fill and triangle exact, passes counted" || bad "A3 arm check"
na=$(grep -c '^arm' "$A/dbg/fw.log"); nw=$(grep -c '^write' "$A/dbg/fw.log")
[ "$na" = 9 ] && [ "$nw" = 16 ] && ok "A3: 9 arms (the start + 8 jobs), 16 ring clears" || bad "A3 arms $na clears $nw"
grep -vqE '^(arm|write|page|status) ' "$A/dbg/fw.log" && bad "fwtask_run.py called with another subcommand" || ok "fwtask_run.py called only with arm, write, page, status"
# ---------------------------------------------------------------------------------------------------------- the H-BLOCK and noise worlds
B=$W/b; mkdbg "$B"; res=$(session "$B" "hyp=block")
s=$(score "$B" d-a2); case "$s" in *"S cells: H-BLOCK"*) ok "block world: d-a2 says H-BLOCK" ;; *) bad "block d-a2: $s ($res)" ;; esac
s=$(score "$B" d-a3); case "$s" in *"H-PEND on the rungs: 3 held, 4 FAILED"*"H-BLOCK on the rungs: 7 held, 0 FAILED"*) ok "block world: d-a3 rungs say H-BLOCK (sa9 bit 8 at the end of render)" ;; *) bad "block d-a3: $s" ;; esac
N=$W/n; mkdbg "$N"; res=$(session "$N" "hyp=noise")
s=$(score "$N" d-a1); case "$s" in *"H-GREQ refuted (0 of 5)"*"H-NOISE consistent"*) ok "noise world: H-GREQ refuted, H-NOISE consistent" ;; *) bad "noise d-a1: $s" ;; esac
s=$(score "$N" d-a2); case "$s" in *"void for PEND/BLOCK"*) ok "noise world: d-a2 S cells void for PEND/BLOCK" ;; *) bad "noise d-a2: $s" ;; esac
# ---------------------------------------------------------------------------------------------------------- the steps are READ
H=$W/h; mkdbg "$H"; res=$(session "$H" "hyp=pend,shift=3")
p1=$(awk -F'\t' '$1 == "a1-s4m1" {print $5}' "$H/out/d-a1/cases.tsv"); p2=$(awk -F'\t' '$1 == "a2-44-s3a" {print $5}' "$H/out/d-a2/cases.tsv")
[ "$p1" = 0x10c ] && [ "$p2" = 0x265 ] && ok "shifted world: the runner read S4 = 0xeb and S3(4096) = 0x243 from the calibrations (P 0x10c, 0x265)" || bad "shift picks $p1 $p2 ($res)"
"$PY" "$P/tests/twin.py" "$H/out" "hyp=pend,shift=3" > "$W/twin-h.log" 2>&1 && ok "shifted world: P column = the twin" || { bad "twin shifted"; head -5 "$W/twin-h.log"; }
s=$(score "$H" d-a0); case "$s" in *"controls FAILED"*|*"not supported"*) ok "shifted world: the premise (section 1's steps) FAILS in the scorer" ;; *) bad "shifted d-a0: $s" ;; esac
s=$(score "$H" d-a1); case "$s" in *GATED*) ok "shifted world: d-a1 gated by the failed premise" ;; *) bad "shifted d-a1: $s" ;; esac
# ---------------------------------------------------------------------------------------------------------- the stops
C=$W/c; mkdbg "$C"
rc=$(runst "$C" d-a0 FAKE_WORLD="flip=--width 2048,flipP=0x104")
[ "$rc" = 10 ] && [ -e "$C/state/CTLFAIL" ] && grep -q "control a0-c4-b5 read class N" "$C/out/d-a0.log" && ok "a control off: rc 10, CTLFAIL" || bad "control off: rc $rc"
rc=$(runst "$C" d-a1 FAKE_WORLD=""); [ "$rc" = 1 ] && grep -q "is refused" "$C/out/d-a1.log" && ok "after a failed premise d-a1 is refused (rc 1)" || bad "d-a1 after CTLFAIL: rc $rc"
K=$W/k; mkdbg "$K"; rc=$(runst "$K" d-a0 FAKE_WORLD="kskew=2")
[ "$rc" = 10 ] && grep -q "its own 0x0624 read" "$K/out/d-a0.log" && ok "a knob proof off: rc 10" || bad "knob proof: rc $rc"
M=$W/m; mkdbg "$M"; rc=$(runst "$M" d-a0 FAKE_WORLD="skip2=1")
[ "$rc" = 10 ] && grep -q "steps not monotone" "$M/out/d-a0.log" && ok "a non-monotone calibration in A0: rc 10" || bad "non-monotone: rc $rc"
G=$W/g; mkdbg "$G"; rc=$(runst "$G" d-a0 FAKE_WORLD="")
rc=$(runst "$G" d-a1 FAKE_WORLD="" FAKE_HANG="--width 2048" FAKE_HANG_P=0x10a)
[ "$rc" = 4 ] && grep -q "STOP: hang in a1-rep1" "$G/out/d-a1.log" && ok "a hang stops the stage (rc 4)" || bad "hang: rc $rc"
V=$W/v; mkdbg "$V"; runst "$V" d-a0 FAKE_WORLD="" >/dev/null
rc=$(runst "$V" d-b FAKE_WORLD="uoff=s119:2")
ns=$(awk -F'\t' '$1 ~ /^b-s119-/ && $10 == "skipped"' "$V/out/d-b/cases.tsv" | wc -l | tr -d ' ')
[ "$rc" = 0 ] && [ "$ns" = 10 ] && ok "a B scene whose page need is not HU1's: its 10 cells skipped as void, the stage goes on" || bad "void scene: rc $rc skipped $ns"
s=$(score "$V" d-b); case "$s" in *"controls FAILED: b-cal-s119 need: FAILED"*"H-CNT on scene s198"*"(10 of 10 rows decided)"*) ok "scorer: scene s119's calibration FAILED (no headline), s198 scored" ;; *) bad "void scene score: $s" ;; esac
runst "$V" d-a0 FAKE_WORLD="" >/dev/null
rc=$(runst "$V" d-a3 FAKE_WORLD="stall=2"); [ "$rc" = 0 ] && grep -q "EDM stall after a3-b6a (the first): reset once" "$V/out/d-a3.log" && ok "one EDM stall: reset once, A3 goes on" || bad "one stall: rc $rc"
rm -f "$V/dbg/armed_jobs"
rc=$(runst "$V" d-a3 FAKE_WORLD="stall=2+4"); [ "$rc" = 11 ] && ok "a second EDM stall ends A3 (rc 11)" || bad "two stalls: rc $rc"
rc=$(runst "$V" d-a3 FAKE_WORLD="" FAKE_ARM_FAIL=1); [ "$rc" = 12 ] && ok "a failed arm ends A3 (rc 12)" || bad "arm fail: rc $rc"
rc=$(runst "$V" d-a1 FAKE_WORLD="" EXPECT_SRCV=OTHER); [ "$rc" = 1 ] && grep -q "not the rgn4 build" "$V/out/d-a1.log" && ok "preflight: another module refused" || bad "srcv: rc $rc"
rc=$(runst "$V" d-a1 FAKE_WORLD="" EXPECT_TOOL=0000); [ "$rc" = 1 ] && grep -q "not the pinned rgn4 tool" "$V/out/d-a1.log" && ok "preflight: another tool refused" || bad "tool: rc $rc"
rc=$(runst "$V" d-a1 FAKE_WORLD="" EXPECT_RT=0000); [ "$rc" = 1 ] && grep -q "regtimeline is not the pinned" "$V/out/d-a1.log" && ok "preflight: another regtimeline refused" || bad "rt: rc $rc"
rm -f "$V/dbg/own_code"; rc=$(runst "$V" d-a3 FAKE_WORLD=""); [ "$rc" = 1 ] && grep -q "no debugfs own_code" "$V/out/d-a3.log" && ok "preflight: A3 needs the own-task debugfs files" || bad "own_code: rc $rc"
# ---------------------------------------------------------------------------------------------------------- attempt 1's failure (freeze 2)
X=$W/x; mkdbg "$X"
rc=$(runst "$X" d-a0 FAKE_WORLD="" FAKE_BIG="--width 4096" FAKE_DUMPFAIL="--width 4096" FAKE_CUT="--width 4096 --height 4096:4096")
[ "$rc" = 13 ] && grep -q "STOP: the capture of a0-cal-4096 is not whole" "$X/out/d-a0.log" && [ ! -e "$X/state/CTLFAIL" ] \
	&& ! grep -q "its own 0x0624 read" "$X/out/d-a0.log" && awk -F'\t' '$1 == "a0-cal-4096" && $10 == "capture"' "$X/out/d-a0/cases.tsv" | grep -q . \
	&& ok "attempt 1 reproduced (>4 KiB text, dump error, text cut at 4096 bytes mid-line): rc 13 'capture not whole', no premise read, no CTLFAIL" \
	|| bad "cut capture: rc $rc"
X2=$W/x2; mkdbg "$X2"
rc=$(runst "$X2" d-a0 FAKE_WORLD="" FAKE_BIG="--width" FAKE_DUMPFAIL="--width 2048")
n4=$(gzip -dc "$X2/out/d-a0/$(python3 "$P/run/r5read.py" kept a0-cal-4096 out)" | wc -c | tr -d ' ')
[ "$rc" = 0 ] && [ "$n4" -gt 8192 ] && grep -q "S4=0x35b" "$X2/out/d-a0.log" \
	&& ok "the same job with its text whole (>4 KiB before the timeline, $n4 bytes kept) and a dump error at 2048: d-a0 reads and passes (rc 0)" \
	|| bad "whole capture with a dump error: rc $rc, $n4 bytes"
ls "$TMPDIR" | grep -q '^r5w\.' && bad "a work directory under TMPDIR" || ok "no work directory under TMPDIR (/tmp on the laptop)"
grep -q "## work directory: $X2/out/work\." "$X2/out/d-a0.log" && ok "the work directory is on the kept files' filesystem (OUTROOT/work.*)" || bad "work directory"
rc=$(runst "$X2" d-a1 FAKE_WORLD="" MIN_JOB_KB=999999999999)
[ "$rc" = 13 ] && grep -q "STOP: less than 999999999999 KB free in the work directory before a1-rep1" "$X2/out/d-a1.log" && ! grep -q "^== a1-rep1" "$X2/out/d-a1.log" \
	&& ok "short of space before a job: rc 13, the job is not run" || bad "space before a job: rc $rc"
ng=$(grep -v '^#' "$P"/tables/*.txt | grep -- '--dump-render' | grep -vc -- '--width 2048 --height 2048')
[ "$ng" = 0 ] && ok "freeze 2: --dump-render only on 2048x2048 rows" || bad "$ng dump rows off 2048x2048"
SGX_DRY_RUN=1 bash "$P/run/r5.sh" > "$W/dry2.out" 2>&1
grep -q "OUTROOT=\$HOME/r5d-out/a2 bash ~/r5d-run/run/run_stage.sh d-a0" "$W/dry2.out" && grep -q "r5d-out/a2/d-a0 .*out/a2/" "$W/dry2.out" \
	&& ok "driver: attempt 2 keeps its files in ~/r5d-out/a2 and out/a2 (attempt 1's out/d-a0 untouched)" || bad "driver attempt dirs"
# ---------------------------------------------------------------------------------------------------------- the guard refuses
for inj in 'echo 1 | sudo -n tee "$D/kreg" >/dev/null' 'cat "$D/regs"' 'while true; do :; done' 'sudo -n reboot' 'fw kreg 0x0814' 'sudo -n timeout 5 true' 'mkdir -p ~/r4e-run'; do
	G2=$W/guard; rm -rf "$G2"; mkdir -p "$G2"; cp -R "$P/run" "$P/tables" "$P/bins" "$P/asm" "$G2/"
	printf '%s\n' "$inj" >> "$G2/run/lib_r5.sh"
	RESGX545_MAIN=/Users/jtorra/src/resgx545 bash "$G2/run/guard_r5.sh" > "$W/guard.out" 2>&1 && bad "guard accepted: $inj" || ok "guard refuses: $inj"
done
G2=$W/guard; rm -rf "$G2"; mkdir -p "$G2"; cp -R "$P/run" "$P/tables" "$P/bins" "$P/asm" "$G2/"
printf 'x' >> "$G2/run/fwtask_run.py"
bash "$G2/run/guard_r5.sh" > "$W/guard.out" 2>&1 && bad "guard accepted a changed fwtask_run.py" || ok "guard refuses a fwtask_run.py that is not the landed one"
bash "$P/run/guard_r5.sh" > "$W/guard.out" 2>&1 && ok "guard: the session itself is clean" || { bad "guard on the session"; cat "$W/guard.out"; }
SGX_DRY_RUN=1 bash "$P/run/r5.sh" > "$W/dry.out" 2>&1
[ "$(grep -c 'ssh .*run_stage.sh' "$W/dry.out")" = 7 ] && ! grep -qE 'make|build|r3g|r4e' "$W/dry.out" && ok "driver dry run: 7 stages through ~/r5d, nothing built" || bad "driver dry run"
echo "ALL: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
