#!/bin/bash
# tests/run_mock.sh (R1): every table runs end to end through run_stage.sh against a fake tool and a fake regtimeline, a
# plain-directory debugfs and shims for sudo/dmesg/timeout; checks job counts, markers, kept DUMPS (a fake that writes
# param, tadata and words files: the runner must KEEP them: the `set -f` regression), rc/class/note columns, knob
# restore, the stop rules (every hang or fault stops; rc 3 "scene overflowed" is the normal class), the table rules
# (a tri row without expectdiff, a multi-render tri row without --keep-going), the 0x072c gate in ten variants, the ONLY
# filter, the staged-tool check, the guard (including unprivileged debugfs access in every form), the driver and staging
# dry runs, and the scorers on fake data (cannot tell, never a verdict).
# Needs a current freeze (run/freeze_r1.sh freeze): the runner compares its table and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg"
export SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" SGXFIVE_PROBE_BINS="$W/stage"
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log" TOOL_SHA_FILE="$W/TOOL.sha256" PYTHONDONTWRITEBYTECODE=1
export GATE_FILE="$W/gate072c.state" FAKE_PEAKS="19,29" FAKE_TRI_COUNT="$W/tri.count"
shasum -a 256 "$P/tests/fake_tool.sh" > "$W/TOOL.sha256"
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
for f in reset render_pb_pages regs buf09 render_param render_tadata; do : > "$W/dbg/$f"; done
echo 0x00000422 > "$W/dbg/render_pb_pages"; echo 0x00000000 > "$W/dbg/alias_skip"
cp "$P"/bins/*.bin "$W/stage/"
. "$P/run/lib_check.sh"
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
runst() { # STAGE SUFFIX [ENV...]: the stage's exit status
	st=$1; sf=$2; shift 2
	env "$@" FAKE_STATE="$W/state-$st$sf" bash -c "KEEP=$W/out/$st$sf bash $P/run/run_stage.sh $st > $W/out/$st$sf.log 2>&1; echo \$?"
}
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	n=$(grep -vc '^#' "$t")
	rm -f "$GATE_FILE" "$W/tri.count"
	rc=$(runst "$name" "" A=1)
	got=$(grep -c '^== ' "$W/out/$name.log"); kept=$(wc -l < "$W/out/$name/raw.sha256" | tr -d ' ')
	pb=$(cat "$W/dbg/render_pb_pages")
	nd=$(grep -v '^#' "$t" | grep -c -- '--dump-render'); kd=$(ls "$W/out/$name" | grep -c 'param\.bin\.gz')
	nw=$(grep -v '^#' "$t" | grep -c -- '--words'); kw=$(ls "$W/out/$name" | grep -c 'words\.0\.txt\.gz')
	nc=$(( $(wc -l < "$W/out/$name/cases.tsv") - 1 ))
	cols=$(awk -F'\t' 'NR>1 && (NF != 11 || $9 == "" || $10 == "" || $11 == "") {x++} END{print x+0}' "$W/out/$name/cases.tsv")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && [ "$pb" = 0x00000422 ] \
		&& [ "$kd" = "$nd" ] && [ "$kw" = "$nw" ] && [ "$nc" = "$n" ] && [ "$cols" = 0 ] \
		&& ok "$name: $got of $n jobs, $kept kept files, $kd param dumps and $kw words dumps kept, $nc rows with rc/class/note, knob back" \
		|| bad "$name: rc $rc, $got of $n jobs, kept $kept, param dumps $kd of $nd, words $kw of $nw, cases rows $nc (bad cols $cols), pb $pb"
done
echo "case markers: $(grep -c 'resgx545 case' "$W/kmsg"), knob markers: $(grep -c 'resgx545 r1 readback' "$W/kmsg")"
# ---------------------------------------------------------------------------------------------------------- the gate
gatecase() { # NAME STAGE EXPECTED_STATE EXPECT_SAMPLED_COUNT [ENV...]
	nm=$1; st=$2; want=$3; wants=$4; shift 4
	rm -f "$GATE_FILE" "$W/tri.count"
	rc=$(runst "$st" "-$nm" "$@")
	state=$(cut -d' ' -f1 "$GATE_FILE" 2>/dev/null)
	ns=$(awk -F'\t' 'NR>1 && $11 == "072c=sampled" {n++} END{print n+0}' "$W/out/$st-$nm/cases.tsv")
	nr=$(awk -F'\t' 'NR>1 && $7 ~ /0x0720-0x072c/ {n++} END{print n+0}' "$W/out/$st-$nm/cases.tsv")
	[ "$rc" = 0 ] && [ "$state" = "$want" ] && [ "$ns" = "$wants" ] && [ "$nr" = "$wants" ] \
		&& ok "gate $nm: state $state, $ns jobs sampled 0x072c (rt widened in $nr rows)" \
		|| bad "gate $nm: rc $rc state '$state' (want $want), sampled $ns/$nr (want $wants): $(cat "$W/out/$st-$nm/gate072c.txt" | tr '\n' '|')"
}
NU=$(grep -vc '^#' "$P/tables/g-u1.txt")
gatecase pass g-u1 pass "$NU" A=1
gatecase bad-value g-u1 fail 1 FAKE_BAD072C=1
gatecase peak-mismatch g-u1 fail 1 FAKE_PEAKS=20,29
gatecase second-fails g-u1 fail 2 FAKE_PEAKS=19,30
gatecase implausible-count g-u1 fail 1 FAKE_COUNT=200
gatecase stuck-at-zero g-u1 fail 1 FAKE_STUCK0=1
gatecase few-rows g-u1 fail 1 FAKE_FEWROWS=1
gatecase kernel-log-line g-u1 fail 1 "FAKE_KLOG=x" "FAKE_KLOG_JOB=-n 1 --keep-going"
gatecase triangle-needs-reset g-u1 fail 1 FAKE_TRI_FAIL_NTH=2
grep -q "G5" "$W/out/g-u1-peak-mismatch/gate072c.txt" && grep -q "G4" "$W/out/g-u1-bad-value/gate072c.txt" \
	&& grep -q "G2" "$W/out/g-u1-kernel-log-line/gate072c.txt" && grep -q "G6" "$W/out/g-u1-triangle-needs-reset/gate072c.txt" \
	&& grep -q "G3" "$W/out/g-u1-few-rows/gate072c.txt" && ok "the gate names the criterion that failed (G2 G3 G4 G5 G6)" || bad "gate reasons"
# a gate that failed leaves the rest of the DPM stages without 0x072c; a stale pass counts as untested; a fresh one samples
echo "fail $(date +%s)" > "$GATE_FILE"; rc=$(runst g-c1 "-gfail" A=1)
ns=$(awk -F'\t' 'NR>1 && $11 == "072c=sampled" {n++} END{print n+0}' "$W/out/g-c1-gfail/cases.tsv")
[ "$rc" = 0 ] && [ "$ns" = 0 ] && ok "g-c1 after a failed gate: no job samples 0x072c" || bad "g-c1 after fail: rc $rc, sampled $ns"
echo "pass $(date +%s)" > "$GATE_FILE"; rc=$(runst g-c1 "-gpass" A=1)
ns=$(awk -F'\t' 'NR>1 && $11 == "072c=sampled" {n++} END{print n+0}' "$W/out/g-c1-gpass/cases.tsv"); nc=$(grep -vc '^#' "$P/tables/g-c1.txt")
[ "$rc" = 0 ] && [ "$ns" = "$nc" ] && ok "g-c1 after a passed gate: all $ns jobs sample 0x072c" || bad "g-c1 after pass: rc $rc, sampled $ns of $nc"
echo "pass 1000" > "$GATE_FILE"; rc=$(runst g-c1 "-gstale" A=1)
ns=$(awk -F'\t' 'NR>1 && $11 == "072c=sampled" {n++} END{print n+0}' "$W/out/g-c1-gstale/cases.tsv")
[ "$rc" = 0 ] && [ "$ns" = 0 ] && ok "g-c1 with a stale pass (older than GATE_MAX_AGE): untested, no sampling" || bad "stale gate: rc $rc, sampled $ns"
rm -f "$GATE_FILE"; rc=$(runst g-c1 "-guntested" A=1)
ns=$(awk -F'\t' 'NR>1 && $11 == "072c=sampled" {n++} END{print n+0}' "$W/out/g-c1-guntested/cases.tsv")
[ "$rc" = 0 ] && [ "$ns" = 0 ] && ok "g-c1 with no gate state: no sampling" || bad "untested gate: rc $rc, sampled $ns"
# a hang in the first trial job: the stage stops (4) and the gate is recorded as failed
rm -f "$GATE_FILE" "$W/tri.count"; rc=$(runst g-u1 "-trialhang" FAKE_HANG="-n 1 --keep-going")
[ "$rc" = 4 ] && [ "$(cut -d' ' -f1 "$GATE_FILE")" = fail ] && ok "a hang in the first trial job stops the stage (rc 4) and fails the gate" || bad "trial hang rc $rc"
# ---------------------------------------------------------------------------------------------------------- stop rules
check() { # NAME EXPECTED_RC TABLE ENV...
	nm=$1; want=$2; tb=$3; shift 3
	rm -f "$GATE_FILE" "$W/tri.count"
	rc=$(runst "$tb" "-x$nm" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || bad "$nm: rc $rc, wanted $want"
}
check unexpected-hang 4 g-t1 FAKE_HANG=0x42800000                # o-x64's viewport word
check hang-in-pcs 4 p-c2 FAKE_HANG=r1c-k1-x
check fault-stops 4 g-t2 FAKE_FAULT=z-slab
check fatal-kernel 3 g-t7 "FAKE_FATAL=tri-unit 10"               # the first fine-grid row
check freeze 6 g-t5 FAKE_TIMEOUT=t5-ctl-sq
check unexplained-failure 4 g-t6 FAKE_NODIFF=t6-c-6e5
check overflow-is-the-normal-class 0 g-c1 FAKE_OVERFLOW=--vertices
check overflow-rc3-in-u2 0 g-u2 FAKE_OVERFLOW=4096
check tri-reference-mismatch-with-expectdiff 0 g-u1 FAKE_DIFF=--move
check tri-reference-mismatch-without-diff-line 4 g-u1 FAKE_NODIFF=--move
# the table rules and the staged tool (a copy of the runner and tables in a scratch tree)
mkdir -p "$W/tree/run" "$W/tree/tables"; cp "$P"/run/*.sh "$W/tree/run/"; cp "$P/FROZEN.sha256" "$W/tree/"
sed 's/ expectdiff//' "$P/tables/g-u2.txt" > "$W/tree/tables/g-u2.txt"
rc=$(KEEP=$W/out/xo bash "$W/tree/run/run_stage.sh" g-u2 > "$W/out/xo.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "a tri row without expectdiff" "$W/out/xo.log" && ok "a tri row without expectdiff is refused" || bad "expectdiff rule rc $rc"
sed 's/ --keep-going//' "$P/tables/g-u1.txt" > "$W/tree/tables/g-u1.txt"
rc=$(KEEP=$W/out/xk bash "$W/tree/run/run_stage.sh" g-u1 > "$W/out/xk.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "without --keep-going" "$W/out/xk.log" && ok "a multi-render tri job without --keep-going is refused" || bad "keep-going rule rc $rc"
sed 's/0x0720-0x0724/0x0724/g' "$P/tables/g-c1.txt" > "$W/tree/tables/g-c1.txt"
rc=$(KEEP=$W/out/xr bash "$W/tree/run/run_stage.sh" g-c1 > "$W/out/xr.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "072c row that does not list" "$W/out/xr.log" && ok "a 072c row without the base range is refused" || bad "072c rule rc $rc"
sed 's/stophang s072c/stophang hypo:g:1/' "$P/tables/g-c1.txt" > "$W/tree/tables/g-c1.txt"
rc=$(KEEP=$W/out/xh bash "$W/tree/run/run_stage.sh" g-c1 > "$W/out/xh.log" 2>&1; echo $?)
[ "$rc" = 1 ] || [ "$rc" = 7 ] && ok "a changed table (not frozen) or an unknown knob is refused (rc $rc)" || bad "unknown knob rc $rc"
echo "0000 x" > "$W/TOOL.bad"
rc=$(TOOL_SHA_FILE=$W/TOOL.bad KEEP=$W/out/xt bash "$P/run/run_stage.sh" g-t1 > "$W/out/xt.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "not the staged one" "$W/out/xt.log" && ok "a tool that is not the staged binary is refused" || bad "tool sha rc $rc"
# ONLY: one row of a table
rc=$(ONLY=f-1500-0x373 KEEP=$W/out/xonly bash "$P/run/run_stage.sh" g-c1f > "$W/out/xonly.log" 2>&1; echo $?)
[ "$rc" = 0 ] && [ "$(grep -c '^== ' "$W/out/xonly.log")" = 1 ] && grep -q "== f-1500-0x373 " "$W/out/xonly.log" \
	&& ok "ONLY=f-1500-0x373 runs exactly that row of g-c1f" || bad "ONLY rc $rc"
rc=$(ONLY=nope KEEP=$W/out/xonly2 bash "$P/run/run_stage.sh" g-c1f > "$W/out/xonly2.log" 2>&1; echo $?)
[ "$rc" = 1 ] && ok "ONLY naming no row is refused" || bad "ONLY nope rc $rc"
# preflight: the kmsg marker must arrive (KMSG to nowhere: the shim's dmesg shows nothing)
rc=$(KMSG=/dev/null KEEP=$W/out/xm bash "$P/run/run_stage.sh" g-t1 > "$W/out/xm.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "kmsg marker did not arrive" "$W/out/xm.log" && ok "preflight refuses when its kmsg marker does not arrive" || bad "kmsg marker rc $rc"
# health: the first failed recovery stops
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"; shasum -a 256 "$W/badtool.sh" > "$W/TOOL.badtool"
rc=$(SGXFIVE_TEST="$W/badtool.sh" TOOL_SHA_FILE="$W/TOOL.badtool" bash -c "KEEP=$W/out/xb bash $P/run/run_stage.sh g-t1 > $W/out/xb.log 2>&1; echo \$?")
[ "$rc" = 5 ] && grep -q "first failed recovery" "$W/out/xb.log" && ok "the first failed health recovery stops (rc 5)" || bad "health stop rc $rc"
num_eq 0x00000000 0 && num_eq 0x0 0 && num_eq 0x00000422 0x422 && ! num_eq 0x6 0 && ! num_eq abc 0 \
	&& ok "numeric knob compare (the kernel prints 0x%08x)" || bad "num_eq"
# the debugfs directory is the FIRST of dri/*/sgx: the real node has three names (S1b's preflight wanted exactly one)
mkdir -p "$W/fs/dri/0/sgx" "$W/fs/dri/0000:00:02.0/sgx" "$W/fs/dri/128/sgx"
first=$(sh -c "ls -d $W/fs/dri/*/sgx" | head -n 1)
[ "$(ls -d "$W"/fs/dri/*/sgx | wc -l | tr -d ' ')" = 3 ] && [ -n "$first" ] && grep -q "head -n 1" "$P/run/lib_r1.sh" \
	&& ok "three dri/*/sgx names: the runner takes the first (head -n 1), never 'exactly one'" || bad "dri names"
# ---------------------------------------------------------------------------------------------------------- scorers on fake data
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_r1; print(score_r1.run_stage('$name', '$W/out/$name'))" 2>&1 | grep '^SUMMARY:')
	case "$s" in *"cannot tell"*|*"METHOD BROKEN"*) ok "scorer $name on fake data: ${s:0:70}" ;; *) bad "scorer $name gave: ${s:-no SUMMARY}" ;; esac
done
# ---------------------------------------------------------------------------------------------------------- guard
"$P/run/guard_r1.sh" > "$W/out/guard.log" 2>&1 && ok "guard" || { bad "guard"; cat "$W/out/guard.log"; }
cp "$P/run/guard_r1.sh" "$W/tree/run/"; cp "$P"/tables/*.txt "$W/tree/tables/"
for bad_line in '\tcat "$D/regs" > "$W/regs.txt"' '\t[ -e "$D/reset" ] && echo y' '\tfor f in "$D"/*; do echo $f; done' \
	'\tls /sys/kernel/debug/dri/0/sgx'; do
	cp "$P/run/lib_r1.sh" "$W/tree/run/lib_r1.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r1.sh"
	"$W/tree/run/guard_r1.sh" > "$W/out/guard2.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "UNPRIVILEGED DEBUGFS ACCESS" "$W/out/guard2.log" && ok "the guard refuses: ${bad_line:2:44}" || bad "guard sudo rule: $bad_line"
done
cp "$P/run/lib_r1.sh" "$W/tree/run/lib_r1.sh"; printf '\tsudo -n tee "$D/kreg" < x\n' >> "$W/tree/run/lib_r1.sh"
"$W/tree/run/guard_r1.sh" > "$W/out/guard3.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "FORBIDDEN" "$W/out/guard3.log" && ok "the guard refuses a kreg write" || bad "guard kreg rule"
cp "$P/run/lib_r1.sh" "$W/tree/run/lib_r1.sh"; cp "$P/tables/g-t1.txt" "$W/tree/tables/g-t1.txt"
printf 'x|heldout|safe|-|stophang|-|probe --tri pixel --poke gen:1=2 "$S/x.bin"\n' >> "$W/tree/tables/g-t1.txt"
"$W/tree/run/guard_r1.sh" > "$W/out/guard4.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "FORBIDDEN option in a table" "$W/out/guard4.log" && ok "the guard refuses a poke option in a table" || bad "guard table rule"
grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$P"/run/*.sh | grep -v '^[^:]*:[0-9]*:[[:space:]]*#' | grep -v 'guard_r1.sh' && bad "a loop that waits"
# ---------------------------------------------------------------------------------------------------------- driver and staging
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r1.sh" > "$W/out/dry.log" 2>&1; d=$?
[ $d = 0 ] && [ "$(grep -c 'bounded' "$W/out/dry.log")" -ge "$(( 3 * $(wc -l < "$P/stages.txt") ))" ] \
	&& ok "r1.sh dry run: every ssh/scp/health bounded by an alarm" || bad "r1.sh dry run status $d"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r1.sh" --cell g-c1f f-1500-0x373 > "$W/out/dry2.log" 2>&1; d=$?
[ $d = 0 ] && grep -q "ONLY=f-1500-0x373 bash ~/r1/run/run_stage.sh g-c1f" "$W/out/dry2.log" \
	&& ok "r1.sh --cell passes ONLY=JOB to the stage" || bad "r1.sh --cell status $d"
order=$(tr '\n' ' ' < "$P/stages.txt")
[ "$order" = "p-c2 g-u1 g-c1 g-t1 g-t2 g-t7 g-u2 g-t5 g-t6 " ] && ok "session order: Q276 C2 first, then U1 (0x072c trial), C1, T1, T2, T7, U2, T5, T6" || bad "stage order: $order"
WT=${TOOL_SRC:-$HOME/src/resgx545}
grep -q '  TOOLSRC.sha256$' "$P/FROZEN.sha256" && ok "the freeze covers TOOLSRC.sha256" || bad "TOOLSRC.sha256 not frozen"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_r1.sh" --src "$WT" > "$W/out/st1.log" 2>&1; s=$?
[ $s = 0 ] && grep -q "deploy inputs match the freeze" "$W/out/st1.log" && ok "stage: the frozen source stages (dry run)" || bad "stage frozen src status $s"
mkdir -p "$W/src"; cp -R "$WT/userspace" "$WT/include" "$W/src/"; mkdir -p "$W/src/tools/bringup" "$W/src/tools/sweep"
cp "$WT/tools/gen_tri_progs.py" "$W/src/tools/"; cp "$WT/tools/bringup/deploy-tool.sh" "$W/src/tools/bringup/"
printf '/* changed */\n' >> "$W/src/userspace/libsgxfive/src/render.c"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_r1.sh" --src "$W/src" > "$W/out/st2.log" 2>&1; s=$?
[ $s = 1 ] && grep -q "deploy inputs differ from the freeze" "$W/out/st2.log" && grep -q "render.c" "$W/out/st2.log" \
	&& ok "stage: a changed source refuses to stage (and names the file)" || bad "stage changed src status $s"
echo "work dir (kept for inspection): $W"
exit $fail
