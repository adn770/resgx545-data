#!/bin/bash
# tests/run_mock.sh (R6-dpm, from R5-dpm's run_mock.sh): every stage runs end to end through run/run_stage.sh against the fake tool, the
# fake regtimeline, the fake fwtask_run.py, a plain-directory debugfs and shims for sudo/dmesg/timeout/modinfo.  The WORLD
# (tests/world_r6.py) answers each job from its argv and the knob the runner wrote, never from the case name, and with no wall-clock
# margin anywhere (its sample times are its own numbers; RESET_WAIT and HEALTH_WAIT are 0; nothing waits for a process to start).
# Checks: the whole session (97 jobs, 6 stages, rc 0 each) and every kept file named by r6read.kept_name and found by the scorer (no
# NODATA); the derived cells read from the calibrations (S:, E:, M:) against the Python twin; the scorer's verdict in each world (CAP
# and PAGE for r-v, row and column order for r-b, the creep cell's operand order); a calibration off the model re-picks its cells;
# the round 6 laptop rule (every file under HOME/scratch/r6d, a work directory per job under HOME/scratch/tmp/r6d.*, none left, none
# under TMPDIR, the free-space stop); and the stops: a control off (class, pages left, count: rc 10, later stages refused), a knob
# proof, a non-monotone calibration, a hang (rc 4), a void r-b scene, r-v's premise (its cells skipped, the stage goes on), one EDM
# stall and two (rc 11), a failed arm (rc 12), a capture cut and a missing r-v dump (rc 13), the preflight refusals, every timeout
# with -k, the knob restored, the guard's refusals.  LOAD=1 runs the whole-session world with 8 `yes` processes beside it.
# Needs a current freeze (run/freeze_r6.sh freeze): the runner compares its tables and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run.XXXXXX")
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" KMSG="$W/kmsg" SRCV_PATH="$W/srcv"
export SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" EXPECT_SRCV=MOCKSRCV RESET_WAIT=0 HEALTH_WAIT=0 TMPDIR="$P/debug/tmp"
export FAKE_LOG="$W/fake.log" FAKE_TRI_COUNT="$W/tri.count" PYTHONDONTWRITEBYTECODE=1 RUNNER_PY=python3
export FWTASK_RUN="$P/tests/fake_fwtask_run.py" R6_SCORE_NOFREEZE=1
export EXPECT_TOOL=$(shasum -a 256 "$P/tests/fake_tool.sh" | cut -d' ' -f1) EXPECT_RT=$(shasum -a 256 "$P/tests/fake_rt.sh" | cut -d' ' -f1)
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
# freeze 2: the runner runs from the tree stage_r6.sh gives the laptop (its own file list, --local), never from run/ here, and with
# only the laptop's environment: env -i, PATH (the shims, then the system's), HOME, and the variables that stand in for the laptop's
# binaries and debugfs (attempt a1: run/lib_check.sh was not staged and num_eq was "command not found"; the old mock ran run/)
LAP=$W/lap
bash "$P/run/stage_r6.sh" --local "$LAP" > "$W/stage-local.out" 2>&1 || { echo "FAIL stage_r6.sh --local"; cat "$W/stage-local.out"; exit 1; }
RUNNER_SH=$LAP/scratch/r6d/run/run/run_stage.sh
# the fake laptop binaries' own needs (not the runner's): the world's sgx-sim build (cargo) finds its toolchain through these
export CARGO_HOME=${CARGO_HOME:-$HOME/.cargo} RUSTUP_HOME=${RUSTUP_HOME:-$HOME/.rustup}
MOCKVARS="CARGO_HOME RUSTUP_HOME PY PYTHONDONTWRITEBYTECODE SGXFIVE_TEST KMSG SRCV_PATH SGXFIVE_REGTIMELINE EXPECT_SRCV RESET_WAIT HEALTH_WAIT FAKE_LOG FAKE_TRI_COUNT RUNNER_PY FWTASK_RUN EXPECT_TOOL EXPECT_RT"
lapenv() { # the laptop's environment: nothing inherited but PATH, HOME and the stand-ins
	e="PATH=$PATH HOME=${LAPHOME:-$LAP}"
	for v in $MOCKVARS; do eval "e=\"\$e $v=\${$v}\""; done
	echo "$e"
}
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
mkdbg() { # DIR: a fresh fake debugfs and staging directory
	mkdir -p "$1/dbg" "$1/stage" "$1/out" "$1/tmproot"
	for f in reset render_pb_pages regs buf09 render_param render_tadata own_code own_res load boot status miscinfo; do : > "$1/dbg/$f"; done
	echo 0x00000422 > "$1/dbg/render_pb_pages"; echo off > "$1/dbg/own_arm"
	cp "$P"/bins/p1139-green.bin "$P"/bins/oomring.blob "$1/stage/"
}
runst() { # WDIR STAGE [ENV...]: the stage's exit status; log in WDIR/out/STAGE.log, kept in WDIR/out/STAGE, state in WDIR/state
	wd=$1; st=$2; shift 2
	# shellcheck disable=SC2046
	env -i $(lapenv) SGXFIVE_DEBUGFS="$wd/dbg" SGXFIVE_PROBE_BINS="$wd/stage" OUTROOT="$wd/out" STATE="$wd/state" KEEP="$wd/out/$st" \
		TMPROOT="$wd/tmproot" "$@" bash "$RUNNER_SH" "$st" > "$wd/out/$st.log" 2>&1
	echo $?
}
session() { # WDIR WORLD [STAGES]: the stages in order; "st:rc ..." up to the first non-zero
	wd=$1; wo=$2; res=""
	for st in ${3:-$(cat "$P/stages.txt")}; do
		rc=$(runst "$wd" "$st" FAKE_WORLD="$wo"); res="$res $st:$rc"
		[ "$rc" = 0 ] || break
	done
	echo "$res"
}
score() { "$PY" "$P/score/score_r6.py" "$2" "$1/out/$2" --ctl "$1/out/r-a0" 2>&1 | grep '^SUMMARY'; }
# ---------------------------------------------------------------------------------------------------------- the CAP / row world, whole
A=$W/a; mkdbg "$A"
if [ "${LOAD:-0}" = 1 ]; then for i in 1 2 3 4 5 6 7 8; do yes > /dev/null & done; echo "(under load: 8 yes processes)"; fi
res=$(session "$A" "vmode=cap,order=row")
if [ "${LOAD:-0}" = 1 ]; then kill $(jobs -p) 2>/dev/null; wait 2>/dev/null; fi
[ "$res" = " r-a0:0 r-m:0 r-n:0 r-v:0 r-b:0 r-k:0" ] && ok "CAP/row world: the six stages run to the end ($res)" || { bad "CAP/row world: $res"; tail -5 "$A"/out/r-*.log; }
nj=$(cat "$A"/out/r-*/cases.tsv | grep -vc '^name')
nr=$(cat "$A"/out/r-*/cases.tsv | awk -F'\t' '$10 == "ok"' | wc -l | tr -d ' ')
[ "$nj" = 97 ] && [ "$nr" = 97 ] && ok "97 rows in cases.tsv, 97 jobs ran (none skipped)" || bad "rows $nj, ran $nr"
pb=$(cat "$A/dbg/render_pb_pages")
[ "$pb" = 0x00000422 ] && ok "render_pb_pages back at 0x422 after the session" || bad "render_pb_pages $pb"
grep -q "timeout without -k" "$W/fake.log" && bad "a timeout without -k" || ok "every timeout ran with -k"
left=$(ls "$A/tmproot" | wc -l | tr -d ' ')
[ "$left" = 0 ] && ok "no work directory left under the work root after six stages (one a job, removed once kept)" || bad "$left work directories left"
nw=$(grep -c '^== ' "$A"/out/r-*.log | awk -F: '{s += $2} END {print s}')
[ "$nw" = 97 ] && ok "97 jobs started, each with its own work directory" || bad "$nw jobs started"
ls "$TMPDIR" | grep -q '^r6d\.' && bad "a work directory under TMPDIR" || ok "no work directory under TMPDIR (/tmp on the laptop)"
miss=0
for d in "$A"/out/r-*; do
	[ -d "$d" ] || continue
	for n in $(awk -F'\t' 'NR > 1 && $10 == "ok" {print $1}' "$d/cases.tsv"); do
		for k in out dmesg buf09 regs; do f=$(python3 "$P/run/r6read.py" kept "$n" "$k"); [ -f "$d/$f" ] || { miss=$((miss + 1)); echo "  missing $d/$f"; }; done
		case "$n" in k-*) for k in page status; do f=$(python3 "$P/run/r6read.py" kept "$n" "$k"); [ -f "$d/$f" ] || miss=$((miss + 1)); done ;; esac
		case "$n" in v-cal-*) f=$(python3 "$P/run/r6read.py" kept "$n" param); [ -s "$d/$f" ] || miss=$((miss + 1)) ;; esac
	done
done
[ "$miss" = 0 ] && ok "every kept file the scorer reads is where r6read.kept_name says (out, dmesg, buf09, regs; page and status in r-k; r-v's param dump)" || bad "$miss kept files missing"
nod=$(for st in $(cat "$P/stages.txt"); do "$PY" "$P/score/score_r6.py" "$st" "$A/out/$st" --ctl "$A/out/r-a0"; done | grep -c 'NODATA')
[ "$nod" = 0 ] && ok "the scorer found every job's files (no NODATA in any stage)" || bad "$nod NODATA rows"
"$PY" "$P/tests/twin.py" "$A/out" "vmode=cap,order=row" > "$W/twin-a.log" 2>&1 && ok "P column of every stage = the Python twin ($(tail -1 "$W/twin-a.log"))" || { bad "twin"; head -5 "$W/twin-a.log"; }
s=$(score "$A" r-a0); case "$s" in *"premise holds on rgn4"*"rows decided"*) ok "r-a0: ${s:0:110}" ;; *) bad "r-a0: $s" ;; esac
s=$(score "$A" r-m); case "$s" in *"H-PHASE at the new bands"*"(15 of 15 rows decided)"*"rival E-TL"*"FAILED"*) ok "r-m: H-PHASE 15 of 15; the E-TL rival fails where it differs" ;; *) bad "r-m: $s" ;; esac
s=$(score "$A" r-n); case "$s" in *"H-STEPMODEL at 2048x1024"*"rows decided"*"H-STEPMODEL at 1024x2048"*"rows decided"*"H-STEPMODEL at 1536x1536"*"rows decided"*) ok "r-n: H-STEPMODEL and H-PHASE at the three targets" ;; *) bad "r-n: $s" ;; esac
s=$(score "$A" r-v); case "$s" in *"vtx-coords 4: L 127"*"H-BURST-CAP"*"vtx-coords 8: L 187"*"H-BURST-CAP"*) ok "r-v CAP world: L read from the dumps (127, 187), H-BURST-CAP at both" ;; *) bad "r-v: $s" ;; esac
s=$(score "$A" r-b); case "$s" in *"four g-qf controls repeat"*"H-REPLAY (row order) counts on s262"*"(8 of 8 rows decided)"*"s179"*"(8 of 8 rows decided)"*) ok "r-b row world: H-REPLAY row 8 of 8 on the four scenes" ;; *) bad "r-b: $s" ;; esac
s=$(score "$A" r-k); case "$s" in *"R-5's sa8 bits"*"rows decided"*"source 1 minus source 2"*"cannot tell (oomring2 refused"*) ok "r-k: R-5's bits held, the creep cell pins the operand order (from the sim-written page)" ;; *) bad "r-k: $s" ;; esac
grep -q "passes of the four stubs" "$A/out/r-k.log" && ok "r-k start: arm, fill and triangle exact, passes counted" || bad "r-k arm check"
na=$(grep -c '^arm' "$A/dbg/fw.log"); nw=$(grep -c '^write' "$A/dbg/fw.log")
[ "$na" = 9 ] && [ "$nw" = 16 ] && ok "r-k: 9 arms (the start + 8 jobs), 16 ring clears" || bad "r-k arms $na clears $nw"
grep -vqE '^(arm|write|page|status) ' "$A/dbg/fw.log" && bad "fwtask_run.py called with another subcommand" || ok "fwtask_run.py called only with arm, write, page, status"
# ---------------------------------------------------------------------------------------------------------- PAGE, column order, reversed operands
B=$W/b; mkdbg "$B"; res=$(session "$B" "vmode=page,order=col,isub=rev" "r-a0 r-v r-b r-k")
s=$(score "$B" r-v); case "$s" in *"vtx-coords 4"*"H-BURST-PAGE"*"vtx-coords 8"*"H-BURST-PAGE"*) ok "PAGE world: r-v says H-BURST-PAGE ($res)" ;; *) bad "PAGE r-v: $s ($res)" ;; esac
s=$(score "$B" r-b); case "$s" in *"H-REPLAY (row order) counts on s262 (HU1 U = 262) is not supported"*"H-REPLAY-COL 8 held, 0 FAILED"*) ok "column world: row order refuted, column order 8 of 8 at s262" ;; *) bad "col r-b: $s" ;; esac
s=$(score "$B" r-k); case "$s" in *"the other way round"*) ok "reversed-operand world: the creep cell reads 0x180" ;; *) bad "rev r-k: $s" ;; esac
# ---------------------------------------------------------------------------------------------------------- a calibration off the model
H=$W/h; mkdbg "$H"; res=$(session "$H" "shift=c15:3" "r-a0 r-n")
grep -q "calibration c15: OFF the model" "$H/out/r-n.log" && [ "$(grep -c 'cell re-picked by the timeline rule' "$H/out/r-n.log")" = 4 ] \
	&& ok "c15 shifted by 3 pages: its calibration is off the model, its 4 M cells re-picked ($res)" || bad "shift: $res"
"$PY" "$P/tests/twin.py" "$H/out" "shift=c15:3" > "$W/twin-h.log" 2>&1 && ok "shifted world: P column = the twin (re-picked cells included)" || { bad "twin shifted"; head -5 "$W/twin-h.log"; }
s=$(score "$H" r-n); case "$s" in *"H-STEPMODEL at 1536x1536 (steps in their brackets, U) is not supported"*"re-picked 4 held"*) ok "scorer: H-STEPMODEL refuted at 1536x1536, the re-picked cells scored for H-PHASE only" ;; *) bad "shift r-n: $s" ;; esac
# ---------------------------------------------------------------------------------------------------------- the laptop rule with the default paths
HM=$W/home; mkdir -p "$HM"; D0=$W/d0; mkdbg "$D0"
HL=$HM/lapcopy; mkdir -p "$HL"; cp -R "$LAP/scratch" "$HM/"
# shellcheck disable=SC2046
rc=$(env -i $(LAPHOME="$HM" lapenv) FAKE_WORLD="" SGXFIVE_DEBUGFS="$D0/dbg" SGXFIVE_PROBE_BINS="$D0/stage" bash "$HM/scratch/r6d/run/run/run_stage.sh" r-a0 > "$W/home.log" 2>&1; echo $?)
rmdir "$HL"
[ "$rc" = 0 ] && [ -s "$HM/scratch/r6d/out/r-a0/cases.tsv" ] && [ -d "$HM/scratch/r6d/out/state" ] && [ -d "$HM/scratch/tmp" ] \
	&& [ -z "$(ls "$HM/scratch/tmp")" ] && [ "$(ls "$HM")" = scratch ] && ! grep -q "command not found\|No such file" "$W/home.log" && grep -q "## work directories: $HM/scratch/tmp/r6d.XXXXXX" "$W/home.log" \
	&& ok "default paths: kept files in ~/scratch/r6d/out, work directories ~/scratch/tmp/r6d.* (none left), nothing else in ~" || { bad "default paths: rc $rc"; ls -R "$HM" | head; }
# ---------------------------------------------------------------------------------------------------------- the stops
C=$W/c; mkdbg "$C"
rc=$(runst "$C" r-a0 FAKE_WORLD="flip=--width 2048,flipP=0x104")
[ "$rc" = 10 ] && [ -e "$C/state/CTLFAIL" ] && grep -q "control a0-c4-b5 read class N" "$C/out/r-a0.log" && ok "a class control off: rc 10, CTLFAIL" || bad "control off: rc $rc"
rc=$(runst "$C" r-m FAKE_WORLD=""); [ "$rc" = 1 ] && grep -q "is refused" "$C/out/r-m.log" && ok "after a failed premise r-m is refused (rc 1)" || bad "r-m after CTLFAIL: rc $rc"
C2=$W/c2; mkdbg "$C2"; rc=$(runst "$C2" r-a0 FAKE_WORLD="left=0xb9:2")
[ "$rc" = 10 ] && grep -q "control a0-t-s3m6 left 0x2 global pages, frozen 1" "$C2/out/r-a0.log" && ok "a pages-left control off (t-s3m6 leaves 2): rc 10" || bad "ctlleft: rc $rc"
C3=$W/c3; mkdbg "$C3"; rc=$(runst "$C3" r-a0 FAKE_WORLD="cnt=0xa2:3")
[ "$rc" = 10 ] && grep -q "control a0-qf-0xa2 read 3 partial renders, frozen 2" "$C3/out/r-a0.log" && ok "a count control off (g-qf 0xa2 reads 3): rc 10" || bad "ctlcnt: rc $rc"
K=$W/k; mkdbg "$K"; rc=$(runst "$K" r-a0 FAKE_WORLD="kskew=2")
[ "$rc" = 10 ] && grep -q "its own 0x0624 read" "$K/out/r-a0.log" && ok "a knob proof off: rc 10" || bad "knob proof: rc $rc"
M=$W/m; mkdbg "$M"; rc=$(runst "$M" r-a0 FAKE_WORLD="skip2=1")
[ "$rc" = 10 ] && grep -q "steps not monotone" "$M/out/r-a0.log" && ok "a non-monotone calibration in r-a0: rc 10" || bad "non-monotone: rc $rc"
G=$W/g; mkdbg "$G"; rc=$(runst "$G" r-a0 FAKE_WORLD="")
rc=$(runst "$G" r-m FAKE_WORLD="" FAKE_HANG="--width 2048" FAKE_HANG_P=0x198)
[ "$rc" = 4 ] && grep -q "STOP: hang in m-b5-0x176" "$G/out/r-m.log" && ok "a hang stops the stage (rc 4)" || bad "hang: rc $rc"
[ -z "$(ls "$G/tmproot")" ] && ok "after a stop the job's work directory is removed by the trap" || bad "work directory left after a stop"
V=$W/v; mkdbg "$V"; runst "$V" r-a0 FAKE_WORLD="" >/dev/null
rc=$(runst "$V" r-b FAKE_WORLD="uoff=s243:2")
ns=$(awk -F'\t' '$1 ~ /^b-s243-/ && $10 == "skipped"' "$V/out/r-b/cases.tsv" | wc -l | tr -d ' ')
[ "$rc" = 0 ] && [ "$ns" = 8 ] && ok "an r-b scene whose page need is not HU1's: its 8 cells skipped as void, the stage goes on" || bad "void scene: rc $rc skipped $ns"
s=$(score "$V" r-b); case "$s" in *"controls FAILED: b-cal-s243 need: FAILED"*"s179"*"(8 of 8 rows decided)"*) ok "scorer: scene s243's calibration FAILED (no headline), the others scored" ;; *) bad "void scene score: $s" ;; esac
rc=$(runst "$V" r-v FAKE_WORLD="vvoid=1")
nv=$(awk -F'\t' '$1 ~ /^v-c[48]-e3/ && $10 == "skipped"' "$V/out/r-v/cases.tsv" | wc -l | tr -d ' ')
[ "$rc" = 0 ] && [ "$nv" = 4 ] && grep -q "not the 1500-vertex scene: its cells will be skipped" "$V/out/r-v.log" && ok "r-v's premise off (no second global page): its 4 cells skipped, the stage goes on" || bad "vprem: rc $rc skipped $nv"
rc=$(runst "$V" r-v FAKE_WORLD="" FAKE_DUMPFAIL="--vtx-coords 4")
[ "$rc" = 13 ] && grep -q "STOP: the capture of v-cal-c4 is not whole (no param dump)" "$V/out/r-v.log" && ok "an r-v calibration without its dump: rc 13 (L cannot be read)" || bad "r-v dump: rc $rc"
rc=$(runst "$V" r-m FAKE_WORLD="" FAKE_DUMPFAIL="--width 2048")
[ "$rc" = 0 ] && ok "a dump error on a row that reads no dump (r-m): the stage goes on" || bad "r-m dump error: rc $rc"
runst "$V" r-a0 FAKE_WORLD="" >/dev/null
rc=$(runst "$V" r-k FAKE_WORLD="stall=2"); [ "$rc" = 0 ] && grep -q "EDM stall after k-b6 (the first): reset once" "$V/out/r-k.log" && ok "one EDM stall: reset once, r-k goes on" || bad "one stall: rc $rc"
rm -f "$V/dbg/armed_jobs"
rc=$(runst "$V" r-k FAKE_WORLD="stall=2+4"); [ "$rc" = 11 ] && ok "a second EDM stall ends r-k (rc 11)" || bad "two stalls: rc $rc"
rc=$(runst "$V" r-k FAKE_WORLD="" FAKE_ARM_FAIL=1); [ "$rc" = 12 ] && ok "a failed arm ends r-k (rc 12)" || bad "arm fail: rc $rc"
rc=$(runst "$V" r-m FAKE_WORLD="" EXPECT_SRCV=OTHER); [ "$rc" = 1 ] && grep -q "not the rgn4 build" "$V/out/r-m.log" && ok "preflight: another module refused" || bad "srcv: rc $rc"
rc=$(runst "$V" r-m FAKE_WORLD="" EXPECT_TOOL=0000); [ "$rc" = 1 ] && grep -q "not the pinned rgn4 tool" "$V/out/r-m.log" && ok "preflight: another tool refused" || bad "tool: rc $rc"
rc=$(runst "$V" r-m FAKE_WORLD="" EXPECT_RT=0000); [ "$rc" = 1 ] && grep -q "regtimeline is not the pinned" "$V/out/r-m.log" && ok "preflight: another regtimeline refused" || bad "rt: rc $rc"
rc=$(runst "$V" r-m FAKE_WORLD="" MIN_FREE_KB=999999999999); [ "$rc" = 1 ] && grep -q "not enough free space" "$V/out/r-m.log" && ok "preflight: 600 MB free needed on the kept and work filesystems" || bad "free space preflight: rc $rc"
rm -f "$V/dbg/own_code"; rc=$(runst "$V" r-k FAKE_WORLD=""); [ "$rc" = 1 ] && grep -q "no debugfs own_code" "$V/out/r-k.log" && ok "preflight: r-k needs the own-task debugfs files" || bad "own_code: rc $rc"
# r5 attempt 1's failure (a cut capture) and the space stop
X=$W/x; mkdbg "$X"
rc=$(runst "$X" r-a0 FAKE_WORLD="" FAKE_BIG="--width 2048" FAKE_CUT="--width 2048 --height 2048 --vertices 1500:4096")
[ "$rc" = 13 ] && grep -q "STOP: the capture of a0-cal-2048 is not whole" "$X/out/r-a0.log" && [ ! -e "$X/state/CTLFAIL" ] \
	&& awk -F'\t' '$1 == "a0-cal-2048" && $10 == "capture"' "$X/out/r-a0/cases.tsv" | grep -q . \
	&& ok "a capture cut at 4096 bytes mid-line: rc 13 'capture not whole', no premise read, no CTLFAIL" || bad "cut capture: rc $rc"
X2=$W/x2; mkdbg "$X2"; runst "$X2" r-a0 FAKE_WORLD="" > /dev/null
rc=$(runst "$X2" r-m FAKE_WORLD="" MIN_JOB_KB=999999999999)
[ "$rc" = 13 ] && grep -q "STOP: less than 999999999999 KB free in the work directory before m-b5-0x174" "$X2/out/r-m.log" && ! grep -q "^== m-b5-0x174" "$X2/out/r-m.log" \
	&& ok "short of space before a job: rc 13, the job is not run" || bad "space before a job: rc $rc"
rc=$(runst "$X2" r-m FAKE_WORLD="" TMPROOT=/tmp/r6dmock)
[ "$rc" = 1 ] && ok "a work root under /tmp is refused (rc 1)" || bad "work root /tmp: rc $rc"
ng=$(grep -v '^#' "$P"/tables/*.txt | grep -- '--dump-render' | grep -vcE -- '--width (2048|1536|1024) --height (2048|1536|1024) ')
[ "$ng" = 0 ] && ok "--dump-render only on targets up to 2048x2048" || bad "$ng dump rows on larger targets"
# ---------------------------------------------------------------------------------------------------------- the guard refuses
for inj in 'echo 1 | sudo -n tee "$D/kreg" >/dev/null' 'cat "$D/regs"' 'while true; do :; done' 'sudo -n reboot' 'fw kreg 0x0814' \
	'sudo -n timeout 5 true' 'mkdir -p ~/r5d-run' 'W=$(mktemp -d /tmp/r6d.XXXXXX)' 'W=$(mktemp -d)' 'mkdir -p ~/scratch/r6p/out'; do
	G2=$W/guard; rm -rf "$G2"; mkdir -p "$G2"; cp -R "$P/run" "$P/tables" "$P/bins" "$P/asm" "$G2/"
	printf '%s\n' "$inj" >> "$G2/run/lib_r6.sh"
	RESGX545_MAIN=/Users/jtorra/src/resgx545 bash "$G2/run/guard_r6.sh" > "$W/guard.out" 2>&1 && bad "guard accepted: $inj" || ok "guard refuses: $inj"
done
G2=$W/guard; rm -rf "$G2"; mkdir -p "$G2"; cp -R "$P/run" "$P/tables" "$P/bins" "$P/asm" "$G2/"
printf 'x' >> "$G2/run/fwtask_run.py"
bash "$G2/run/guard_r6.sh" > "$W/guard.out" 2>&1 && bad "guard accepted a changed fwtask_run.py" || ok "guard refuses a fwtask_run.py that is not the landed one"
bash "$P/run/guard_r6.sh" > "$W/guard.out" 2>&1 && ok "guard: the session itself is clean" || { bad "guard on the session"; cat "$W/guard.out"; }
SGX_DRY_RUN=1 bash "$P/run/r6.sh" > "$W/dry.out" 2>&1
[ "$(grep -c 'ssh .*~/scratch/r6d/run/run/run_stage.sh' "$W/dry.out")" = 6 ] && grep -q 'OUTROOT=\$HOME/scratch/r6d/out/a2 ' "$W/dry.out" && ! grep -qE 'make|build|r5d|/tmp' "$W/dry.out" \
	&& ok "driver dry run: 6 stages through ~/scratch/r6d, attempt a2 (freeze 2), nothing built" || { bad "driver dry run"; head -5 "$W/dry.out"; }
SGX_DRY_RUN=1 bash "$P/run/stage_r6.sh" > "$W/stage.out" 2>&1
grep -q "mkdir -p scratch/r6d/run/run scratch/r6d/run/tables scratch/r6d/stage scratch/r6d/out scratch/tmp" "$W/stage.out" && ! grep -qE "(^|[ :])/tmp" "$W/stage.out" \
	&& ok "staging dry run: every laptop file under ~/scratch/r6d (and ~/scratch/tmp)" || { bad "staging dry run"; head -5 "$W/stage.out"; }
nf=$(cat "$W"/*/out/*.log 2>/dev/null | grep -c "command not found\|lib_check.sh: No such file")
[ "$nf" = 0 ] && ok "no stage log of any world shows a command not found (the staged tree defines every function it calls)" || bad "$nf 'command not found' lines in the stage logs"
echo "ALL: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
