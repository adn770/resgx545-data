#!/bin/bash
# tests/run_mock.sh (R3): every table runs end to end through run_stage.sh against a fake tool and a fake regtimeline, a plain-directory
# debugfs and shims for sudo/dmesg/timeout.  Depth tables: job counts, markers, kept DUMPS (the `set -f` regression), the case columns, knob
# restore.  DPM tables: the synthetic world of tests/world_r3.py (FAKE_WORLD) answers the jobs, so the runner's DYNAMIC rows run for real: the
# bisect picks, the L:/F: references, the fit gate, the calibration gate, the control stop; the kept P column of every stage is compared with
# the Python twin (tests/compare_twin.py) and the scorers read the kept directories (the whole chain: runner -> kept files -> scorer).
# Also: the stop rules (every hang or fault stops; rc 3 "scene overflowed" is the normal class), a failed control (rc 10, state/CTLFAIL, a
# later DPM stage refused), the preflight (srcversion loaded = installed = expected, the pinned tool, free space, the kmsg marker, the
# debugfs files), the table rules, the ONLY filter, the guard (including unprivileged debugfs access in every form and a poke), the driver
# and staging dry runs (no build, laptop directory prefix ~/r3g), and the scorers on fake data.
# Needs a current freeze (run/freeze_r3.sh freeze): the runner compares its table and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run.XXXXXX")
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg"
export SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" SGXFIVE_PROBE_BINS="$W/stage" EXPECT_SRCV=MOCKSRCV
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log" TOOL_SHA_FILE="$W/TOOL.sha256" PYTHONDONTWRITEBYTECODE=1
export FAKE_TRI_COUNT="$W/tri.count" TMPDIR="$P/debug/tmp"
shasum -a 256 "$P/tests/fake_tool.sh" > "$W/TOOL.sha256"
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
for f in reset render_pb_pages regs buf09 render_param render_tadata; do : > "$W/dbg/$f"; done
echo 0x00000422 > "$W/dbg/render_pb_pages"; echo 0x00000000 > "$W/dbg/alias_skip"
cp "$P"/bins/*.bin "$W/stage/"
. "$P/run/lib_check.sh"
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
runst() { # STAGE SUFFIX [ENV...]: the stage's exit status (state files in $W/st-SUFFIX unless STATE is given)
	st=$1; sf=$2; shift 2
	env "$@" STATE="${STATE_OVERRIDE:-$W/st$sf}" bash -c "KEEP=$W/out/$st$sf bash $P/run/run_stage.sh $st > $W/out/$st$sf.log 2>&1; echo \$?"
}
# ---------------------------------------------------------------------------------------------------------- depth tables end to end
for name in g-da g-db g-dc g-dd; do
	t="$P/tables/$name.txt"
	n=$(grep -vc '^#' "$t")
	rm -f "$W/tri.count"
	rc=$(runst "$name" "" A=1)
	got=$(grep -c '^== ' "$W/out/$name.log"); kept=$(wc -l < "$W/out/$name/raw.sha256" | tr -d ' ')
	pb=$(cat "$W/dbg/render_pb_pages")
	nd=$(grep -v '^#' "$t" | grep -c -- '--dump-render'); kd=$(ls "$W/out/$name" | grep -c 'param\.bin\.gz')
	nc=$(( $(wc -l < "$W/out/$name/cases.tsv") - 1 ))
	cols=$(awk -F'\t' 'NR>1 && (NF != 11 || $9 == "" || $10 == "" || $11 == "") {x++} END{print x+0}' "$W/out/$name/cases.tsv")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && [ "$pb" = 0x00000422 ] && [ "$kd" = "$nd" ] && [ "$nc" = "$n" ] && [ "$cols" = 0 ] \
		&& ok "$name: $got of $n jobs, $kept kept files, $kd param dumps, $nc rows with rc/class/note, knob back" \
		|| bad "$name: rc $rc, $got of $n jobs, kept $kept, param dumps $kd of $nd, cases rows $nc (bad cols $cols), pb $pb"
done
echo "case markers: $(grep -c 'resgx545 case' "$W/kmsg")"
# ---------------------------------------------------------------------------------------------------------- DPM stages: the LT world end to end
run_chain() { # SUFFIX WORLD: g-c4, g-d36, g-c6, g-c5, g-c7 in order, one state directory, the exit status of each on one line
	sf=$1; wd=$2; res=""
	for st in g-c4 g-d36 g-c6 g-c5 g-c7; do
		rc=$(STATE_OVERRIDE="$W/st-$sf" runst "$st" "-$sf" FAKE_WORLD="$wd")
		res="$res $st:$rc"
	done
	echo "$res"
}
res=$(run_chain lt "lim2048=0xd4")
case "$res" in " g-c4:0 g-d36:0 g-c6:0 g-c5:0 g-c7:0") ok "LT world: the five DPM stages run to the end (rc 0 each)" ;; *) bad "LT chain: $res" ;; esac
b4=$(awk -F'\t' 'NR>1 && $1 ~ /^c4-b/ {print $5}' "$W/out/g-c4-lt/cases.tsv" | tr '\n' ' ')
want="0x102 0xf2 0xfa 0xf6 0xf8 0xf7 "
[ "$b4" = "$want" ] && ok "g-c4: the bash runner picked 0x102 0xf2 0xfa 0xf6 0xf8 0xf7 (thr0 0xe0 0xd0 0xd8 0xd4 0xd6 0xd5 + 0x22) from the kept observations" || bad "g-c4 picks $b4 (wanted $want)"
"$PY" "$P/tests/compare_twin.py" "$W/out" lt "lim2048=0xd4" > "$W/out/twin-lt.log" 2>&1; rc=$?
[ $rc = 0 ] && ok "LT world: P, class and skip columns of all five DPM stages equal the Python twin's ($(tail -1 "$W/out/twin-lt.log"))" || { bad "LT chain differs from the twin"; head -8 "$W/out/twin-lt.log"; }
for st in g-c4 g-d36 g-c6 g-c5 g-c7; do
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_r3; print(score_r3.run_stage('$st', '$W/out/$st-lt', ctl_dir='$W/out/g-c4-lt'))" 2>&1 | grep '^SUMMARY:')
	case "$st:$s" in
	g-c4:*"LT HOLDS"*) ok "scorer g-c4 on the bash runner's kept files: LT HOLDS" ;;
	g-d36:*"H-last HOLDS"*|g-c6:*"H-target HOLDS"*|g-c5:*"consistent with all three"*|g-c7:*"H-target HOLDS"*) ok "scorer $st on the kept files: ${s:0:90}" ;;
	*) bad "scorer $st on the kept files gave: ${s:-no SUMMARY}" ;;
	esac
done
fit=$(grep -c 'skipped' "$W/out/g-c6-lt/cases.tsv")
[ "$fit" -ge 1 ] && grep -q "2 thr0" "$W/out/g-c6-lt.log" && ok "g-c6: the fit gate skipped a cell whose 2 thr0 is not below the page need (c6-0x120)" || bad "fit gate: $fit skipped"
# a different world: the flip at 0xc8, the full-target scene flipping at 0xa0
res=$(run_chain w2 "lim2048=0xc8,full=0xc0")
b4=$(awk -F'\t' 'NR>1 && $1 ~ /^c4-b/ {print $5}' "$W/out/g-c4-w2/cases.tsv" | tr '\n' ' ')
"$PY" "$P/tests/compare_twin.py" "$W/out" w2 "lim2048=0xc8,full=0xc0" > "$W/out/twin-w2.log" 2>&1; rc=$?
[ $rc = 0 ] && ok "world flip 0xc8 / scene 0xc0: kept P columns equal the twin's (picks $b4)" || { bad "world 2 differs from the twin"; head -8 "$W/out/twin-w2.log"; }
s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_r3; print(score_r3.run_stage('g-c7', '$W/out/g-c7-w2', ctl_dir='$W/out/g-c4-w2'))" 2>&1 | grep '^SUMMARY:')
case "$s" in *"H-scene"*) ok "scorer g-c7 on the bash runner's kept files of world 2: H-scene" ;; *) bad "g-c7 world 2: $s" ;; esac
# the calibration gate of g-c7: more than 3 partial renders at P 0x422 end the stage after one job
res=$(run_chain gate "lim2048=0xd4,needfull=6000")
sk=$(awk -F'\t' 'NR>1 && $10 == "skipped"' "$W/out/g-c7-gate/cases.tsv" | wc -l | tr -d ' ')
ran=$(grep -c '^== c7' "$W/out/g-c7-gate.log")
grep -q "GATE CLOSED" "$W/out/g-c7-gate.log" && [ "$sk" = 10 ] && ok "g-c7 gate: 5 partial renders at P 0x422 > 3: the stage ends after the calibration job (10 rows skipped, rc 0)" || bad "gate: skipped $sk, log $(grep -c 'GATE' "$W/out/g-c7-gate.log")"
# a failed control stops the session (rc 10), writes state/CTLFAIL, and a later DPM stage is refused
rc=$(STATE_OVERRIDE="$W/st-cf" runst g-c4 "-cf" FAKE_WORLD="lim2048=0xd4,lim4096=0x300")
[ "$rc" = 10 ] && grep -q "STOP: control c3-4096-0x372 read class N" "$W/out/g-c4-cf.log" && [ -s "$W/st-cf/CTLFAIL" ] \
	&& ok "a control (4096x4096 0x372 raise) that reads none stops the session (rc 10) and writes state/CTLFAIL" || bad "control stop rc $rc"
rc=$(STATE_OVERRIDE="$W/st-cf" runst g-d36 "-cf" FAKE_WORLD="lim2048=0xd4,lim4096=0x300")
[ "$rc" = 1 ] && grep -q "is refused" "$W/out/g-d36-cf.log" && ok "after a failed control a later DPM stage is refused (rc 1)" || bad "refusal rc $rc"
rc=$(STATE_OVERRIDE="$W/st-cf" runst g-da "-cf" A=1)
[ "$rc" = 0 ] && ok "a depth stage still runs (it has no DPM controls)" || bad "depth after control failure rc $rc"
rc=$(STATE_OVERRIDE="$W/st-cf" runst g-d36 "-cfo" FAKE_WORLD="lim2048=0xd4,lim4096=0x300" CTL_OVERRIDE=1)
[ "$rc" = 0 ] && ok "CTL_OVERRIDE=1 runs the stage after a failed control" || bad "override rc $rc"
# g-c6 without g-c4's state: the derived cells are skipped (no raise cell in the group), the fixed ones run
rc=$(STATE_OVERRIDE="$W/st-none" runst g-c6 "-none" FAKE_WORLD="lim2048=0xd4")
sk=$(awk -F'\t' 'NR>1 && $10 == "skipped"' "$W/out/g-c6-none/cases.tsv" | wc -l | tr -d ' ')
[ "$rc" = 0 ] && [ "$sk" -ge 2 ] && ok "g-c6 without g-c4's state: the L:/F: cells are skipped (no raise cell in the group), nothing is invented" || bad "no-state rc $rc skipped $sk"
# ---------------------------------------------------------------------------------------------------------- stop rules
check() { # NAME EXPECTED_RC TABLE ENV...
	nm=$1; want=$2; tb=$3; shift 3
	rm -f "$W/tri.count"
	rc=$(runst "$tb" "-x$nm" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || bad "$nm: rc $rc, wanted $want"
}
check hang-in-da 4 g-da FAKE_HANG=da-in3
check fault-stops 4 g-db FAKE_FAULT=db-q2
check fatal-kernel 3 g-dc FAKE_FATAL=dc-wn1
check freeze 6 g-dd FAKE_TIMEOUT=dd-m1
check unexplained-failure 4 g-da FAKE_NODIFF=da-hi1
check overflow-is-the-normal-class 0 g-d36 FAKE_WORLD="lim2048=0xd4"
check hang-in-dpm 4 g-d36 FAKE_WORLD="lim2048=0xd4" FAKE_HANG=--width
grep -q "STOP: hang in" "$W/out/g-d36-xhang-in-dpm.log" && ok "a hang in a DPM row names the row and stops the stage after the reset and health" || bad "dpm hang log"
n=$(grep -c '^== ' "$W/out/g-da-xhang-in-da.log"); [ "$n" = 14 ] && ok "g-da stops at the hung row (14 jobs started)" || bad "da stop count $n"
# ---------------------------------------------------------------------------------------------------------- table rules, ONLY, preflight
mkdir -p "$W/tree/run" "$W/tree/tables"; cp "$P"/run/*.sh "$P"/run/*.awk "$W/tree/run/"; cp "$P/FROZEN.sha256" "$W/tree/"
sed 's/stophang/stophang hypo:g:1/' "$P/tables/g-da.txt" > "$W/tree/tables/g-da.txt"
rc=$(KEEP=$W/out/xh bash "$W/tree/run/run_stage.sh" g-da > "$W/out/xh.log" 2>&1; echo $?)
[ "$rc" = 1 ] || [ "$rc" = 7 ] && ok "a changed table (not frozen) or an unknown knob is refused (rc $rc)" || bad "unknown knob rc $rc"
sed 's/--vertices 1500/--vertices 1500 --kpoke pb:11=0x80/' "$P/tables/g-c4.txt" > "$W/tree/tables/g-c4.txt"
rc=$(KEEP=$W/out/xp bash "$W/tree/run/run_stage.sh" g-c4 > "$W/out/xp.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "a poke (R3 has none)" "$W/out/xp.log" && ok "a poke in a table is refused by the runner (R3 has none)" || bad "poke rule rc $rc"
echo "0000 x" > "$W/TOOL.bad"
rc=$(TOOL_SHA_FILE=$W/TOOL.bad KEEP=$W/out/xt bash "$P/run/run_stage.sh" g-da > "$W/out/xt.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "not the pinned one" "$W/out/xt.log" && grep -q "STOP and ask" "$W/out/xt.log" && ok "a tool whose hash is not the pinned one stops the stage (stop and ask: nothing is rebuilt)" || bad "tool sha rc $rc"
rc=$(ONLY=da-in3 KEEP=$W/out/xonly bash "$P/run/run_stage.sh" g-da > "$W/out/xonly.log" 2>&1; echo $?)
[ "$rc" = 0 ] && [ "$(grep -c '^== ' "$W/out/xonly.log")" = 1 ] && grep -q "== da-in3 " "$W/out/xonly.log" && ok "ONLY=da-in3 runs exactly that row of g-da" || bad "ONLY rc $rc"
rc=$(ONLY=nope KEEP=$W/out/xonly2 bash "$P/run/run_stage.sh" g-da > "$W/out/xonly2.log" 2>&1; echo $?)
[ "$rc" = 1 ] && ok "ONLY naming no row is refused" || bad "ONLY nope rc $rc"
rc=$(KMSG=/dev/null KEEP=$W/out/xm bash "$P/run/run_stage.sh" g-da > "$W/out/xm.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "kmsg marker did not arrive" "$W/out/xm.log" && ok "preflight refuses when its kmsg marker does not arrive" || bad "kmsg marker rc $rc"
echo OTHERSRCV > "$W/srcv"
mkdir -p "$W/sh3"; cp "$P"/tests/shims/* "$W/sh3/"; printf '#!/bin/sh\necho OTHERSRCV\n' > "$W/sh3/modinfo"; chmod +x "$W/sh3/modinfo"
rc=$(PATH="$W/sh3:$PATH" KEEP=$W/out/xs bash "$P/run/run_stage.sh" g-da > "$W/out/xs.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "loaded module OTHERSRCV is not the expected" "$W/out/xs.log" && ok "preflight: a loaded = installed module that is not the expected srcversion (B21FDA82...) stops" || bad "expected srcversion rc $rc"
rc=$(PATH="$W/sh3:$PATH" EXPECT_SRCV=any KEEP=$W/out/xs2 bash "$P/run/run_stage.sh" g-da > "$W/out/xs2.log" 2>&1; echo $?)
[ "$rc" = 0 ] && ok "EXPECT_SRCV=any accepts another module that is loaded = installed" || bad "any srcversion rc $rc"
rc=$(KEEP=$W/out/xs3 bash "$P/run/run_stage.sh" g-da > "$W/out/xs3.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "loaded module is not the installed one" "$W/out/xs3.log" && ok "preflight: srcversion of the loaded module against modinfo (a different loaded one stops)" || bad "srcversion rc $rc"
echo MOCKSRCV > "$W/srcv"
for f in render_param buf09; do
	mv "$W/dbg/$f" "$W/dbg/$f.off"
	rc=$(KEEP=$W/out/xf bash "$P/run/run_stage.sh" g-da > "$W/out/xf.log" 2>&1; echo $?)
	mv "$W/dbg/$f.off" "$W/dbg/$f"
	[ "$rc" = 1 ] && grep -q "no debugfs $f" "$W/out/xf.log" && ok "preflight needs the debugfs file $f" || bad "debugfs $f rc $rc"
done
rc=$(MIN_FREE_KB=999999999999 KEEP=$W/out/xd bash "$P/run/run_stage.sh" g-da > "$W/out/xd.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "not enough free space" "$W/out/xd.log" && ok "preflight checks the free space for the dumps" || bad "free space rc $rc"
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"; shasum -a 256 "$W/badtool.sh" > "$W/TOOL.badtool"
rc=$(SGXFIVE_TEST="$W/badtool.sh" TOOL_SHA_FILE="$W/TOOL.badtool" bash -c "KEEP=$W/out/xb bash $P/run/run_stage.sh g-da > $W/out/xb.log 2>&1; echo \$?")
[ "$rc" = 5 ] && grep -q "first failed recovery" "$W/out/xb.log" && ok "the first failed health recovery stops (rc 5)" || bad "health stop rc $rc"
num_eq 0x00000000 0 && num_eq 0x0 0 && num_eq 0x00000422 0x422 && ! num_eq 0x6 0 && ! num_eq abc 0 \
	&& ok "numeric knob compare (the kernel prints 0x%08x)" || bad "num_eq"
mkdir -p "$W/fs/dri/0/sgx" "$W/fs/dri/0000:00:02.0/sgx" "$W/fs/dri/128/sgx"
[ "$(ls -d "$W"/fs/dri/*/sgx | wc -l | tr -d ' ')" = 3 ] && grep -q "head -n 1" "$P/run/lib_r3.sh" \
	&& ok "three dri/*/sgx names: the runner takes the first (head -n 1), never 'exactly one'" || bad "dri names"
# the tool messages are searched in the WHOLE output: a hang line at the head of a long output still counts
rc=$(runst g-da "-longhang" FAKE_HANG=da-lo1)
[ "$rc" = 4 ] && ok "a hang message anywhere in the output is found (whole-output search)" || bad "hang search rc $rc"
# ---------------------------------------------------------------------------------------------------------- scorers on fake data
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	case "$name" in g-da|g-db|g-dc|g-dd) dir="$W/out/$name" ;; *) dir="$W/out/$name-xhang-in-dpm"; [ -d "$dir" ] || dir="$W/out/$name-w2" ;; esac
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_r3; print(score_r3.run_stage('$name', '$dir'))" 2>&1 | grep '^SUMMARY:')
	case "$s" in *"cannot tell"*|*"NODATA"*|*"gate closed"*) ok "scorer $name on fake data: ${s:0:70}" ;; *) [ "$name" = g-c4 ] && ok "scorer $name on a world: ${s:0:70}" || bad "scorer $name gave: ${s:-no SUMMARY}" ;; esac
done
# ---------------------------------------------------------------------------------------------------------- guard
"$P/run/guard_r3.sh" > "$W/out/guard.log" 2>&1 && ok "guard" || { bad "guard"; cat "$W/out/guard.log"; }
cp "$P/run/guard_r3.sh" "$W/tree/run/"; cp "$P"/tables/*.txt "$W/tree/tables/"
for bad_line in '\tcat "$D/regs" > "$W/regs.txt"' '\t[ -e "$D/reset" ] && echo y' '\tfor f in "$D"/*; do echo $f; done' \
	'\tls /sys/kernel/debug/dri/0/sgx'; do
	cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r3.sh"
	"$W/tree/run/guard_r3.sh" > "$W/out/guard2.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "UNPRIVILEGED DEBUGFS ACCESS" "$W/out/guard2.log" && ok "the guard refuses: ${bad_line:2:44}" || bad "guard sudo rule: $bad_line"
done
for bad_line in '\tsudo -n tee "$D/kreg" < x' '\tsudo -n tee "$D/kpoke" < x' '\techo pb:11=1 | sudo -n tee -a "$D/kpoke"' '\techo x > /dev/mem' '\tsudo -n tee "$D/trc_hazard"'; do
	cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r3.sh"
	"$W/tree/run/guard_r3.sh" > "$W/out/guard3.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "FORBIDDEN" "$W/out/guard3.log" && ok "the guard refuses a script line: ${bad_line:2:40}" || bad "guard forbidden rule: $bad_line"
done
cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"
printf '\tmkdir -p $HOME/r3p-x\n' >> "$W/tree/run/lib_r3.sh"
"$W/tree/run/guard_r3.sh" > "$W/out/guard7.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "ANOTHER SESSION'S DIRECTORY" "$W/out/guard7.log" && ok "the guard refuses another session's directory (~/r3p-*)" || bad "guard session rule"
cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"
cp "$P/tables/g-da.txt" "$W/tree/tables/g-da.txt"
printf 'x|heldout|safe|0x422|stophang|-|probe --tri pixel --kpoke pb:11=0x10 "$S/x.bin"\n' >> "$W/tree/tables/g-da.txt"
"$W/tree/run/guard_r3.sh" > "$W/out/guard4.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "FORBIDDEN option in a table" "$W/out/guard4.log" && ok "the guard refuses a poke option in any table" || bad "guard table rule"
cp "$P/tables/g-da.txt" "$W/tree/tables/g-da.txt"
grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$P"/run/*.sh | grep -v '^[^:]*:[0-9]*:[[:space:]]*#' | grep -v 'guard_r3.sh' && bad "a loop that waits"
# ---------------------------------------------------------------------------------------------------------- driver and staging
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r3.sh" > "$W/out/dry.log" 2>&1; d=$?
[ $d = 0 ] && [ "$(grep -c 'bounded' "$W/out/dry.log")" -ge "$(( 3 * $(wc -l < "$P/stages.txt") ))" ] && grep -q "bash ~/r3g/run/run_stage.sh g-c7" "$W/out/dry.log" \
	&& ok "r3.sh dry run: every ssh/scp/health bounded by an alarm, laptop directory ~/r3g" || bad "r3.sh dry run status $d"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r3.sh" --cell g-c4 c4-b1 > "$W/out/dry2.log" 2>&1; d=$?
[ $d = 0 ] && grep -q "ONLY=c4-b1 bash ~/r3g/run/run_stage.sh g-c4" "$W/out/dry2.log" && ok "r3.sh --cell passes ONLY=JOB to the stage" || bad "r3.sh --cell status $d"
order=$(tr '\n' ' ' < "$P/stages.txt")
[ "$order" = "g-da g-db g-dc g-dd g-c4 g-d36 g-c6 g-c5 g-c7 " ] && ok "session order (R3-G9): g-da, g-db, g-dc, g-dd, g-c4, g-d36, g-c6, g-c5, g-c7" || bad "stage order: $order"
grep -q '  TOOL.sha256$' "$P/FROZEN.sha256" && grep -q '  TOOLSRC.sha256$' "$P/FROZEN.sha256" && grep -q '^bf4f8be2d8a8fe50034559450928e05695dc96d396d4892f9b00ea6bc0d4f053 ' "$P/TOOL.sha256" \
	&& ok "the freeze covers TOOL.sha256 (R1's laptop tool bf4f8be2...) and TOOLSRC.sha256" || bad "tool pin not frozen"
grep -q '  run/dpm_read.awk$' "$P/FROZEN.sha256" && grep -q '  run/bis.awk$' "$P/FROZEN.sha256" && ok "the freeze covers the awk readers (dpm_read.awk, bis.awk)" || bad "awk not frozen"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_r3.sh" > "$W/out/st1.log" 2>&1; s=$?
[ $s = 0 ] && grep -q "sha256sum ~/sgxfive-test-r1 ~/regtimeline" "$W/out/st1.log" && ! grep -qi "deploy-tool\|build\|cc -O2" "$W/out/st1.log" && grep -q "r3g-stage" "$W/out/st1.log" \
	&& ! grep -qE 'r3p-|r3xev' "$W/out/st1.log" && ok "staging dry run: copies the runner, awk readers, tables and programs to ~/r3g*, checks the pinned tool and regtimeline, builds nothing" || bad "stage dry run status $s"
echo "work dir (kept for inspection): $W"
exit $fail
