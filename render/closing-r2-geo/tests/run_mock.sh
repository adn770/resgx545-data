#!/bin/bash
# tests/run_mock.sh (R2): every table runs end to end through run_stage.sh against a fake tool and a fake regtimeline, a
# plain-directory debugfs and shims for sudo/dmesg/timeout; checks job counts, markers, kept DUMPS (a fake that writes
# param, tadata and words files: the runner must KEEP them: the `set -f` regression), the pre/after STATUS2 files, rc/class/note
# columns, knob restore, the stop rules (every hang or fault stops; rc 3 "scene overflowed" is the normal class), the sweep
# stop (bit 7 skips the rest of the ladder), the stuck-job watchdog of the poke rows, the poke rules (only pb:11, only with
# kpoke and wd:S), the table rules (a tri row without expectdiff, a multi-render tri row without --keep-going), the ONLY
# filter, the staged-tool check, the guard (including unprivileged debugfs access in every form and a kpoke write), the driver
# and staging dry runs (no build), and the scorers on fake data (cannot tell, never a verdict).
# Needs a current freeze (run/freeze_r2.sh freeze): the runner compares its table and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run.XXXXXX")
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg"
export SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" SGXFIVE_PROBE_BINS="$W/stage"
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log" TOOL_SHA_FILE="$W/TOOL.sha256" PYTHONDONTWRITEBYTECODE=1
export FAKE_PEAKS="19,29" FAKE_TRI_COUNT="$W/tri.count" TMPDIR="$P/debug/tmp"
shasum -a 256 "$P/tests/fake_tool.sh" > "$W/TOOL.sha256"
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
for f in reset render_pb_pages regs buf09 render_param render_tadata kpoke; do : > "$W/dbg/$f"; done
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
	rm -f "$W/tri.count"
	rc=$(runst "$name" "" A=1)
	got=$(grep -c '^== ' "$W/out/$name.log"); kept=$(wc -l < "$W/out/$name/raw.sha256" | tr -d ' ')
	pb=$(cat "$W/dbg/render_pb_pages")
	nd=$(grep -v '^#' "$t" | grep -c -- '--dump-render'); kd=$(ls "$W/out/$name" | grep -c 'param\.bin\.gz')
	nw=$(grep -v '^#' "$t" | grep -c -- '--words'); kw=$(ls "$W/out/$name" | grep -c 'words\.0\.txt\.gz')
	ns2=$(awk -F'|' '!/^#/ && $5 ~ /(^| )s2( |$)/ {n++} END{print n+0}' "$t"); kp=$(ls "$W/out/$name" | grep -c 'pre\.regs\.txt\.gz')
	ka=$(ls "$W/out/$name" | grep -c 'after\.regs\.txt\.gz')
	nc=$(( $(wc -l < "$W/out/$name/cases.tsv") - 1 ))
	cols=$(awk -F'\t' 'NR>1 && (NF != 11 || $9 == "" || $10 == "" || $11 == "") {x++} END{print x+0}' "$W/out/$name/cases.tsv")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && [ "$pb" = 0x00000422 ] \
		&& [ "$kd" = "$nd" ] && [ "$kw" = "$nw" ] && [ "$kp" = "$ns2" ] && [ "$ka" = "$n" ] && [ "$nc" = "$n" ] && [ "$cols" = 0 ] \
		&& ok "$name: $got of $n jobs, $kept kept files, $kd param dumps, $kw words dumps, $kp pre and $ka after regs files kept, $nc rows with rc/class/note, knob back" \
		|| bad "$name: rc $rc, $got of $n jobs, kept $kept, param dumps $kd of $nd, words $kw of $nw, pre regs $kp of $ns2, after $ka, cases rows $nc (bad cols $cols), pb $pb"
done
echo "case markers: $(grep -c 'resgx545 case' "$W/kmsg"), knob markers: $(grep -c 'resgx545 r2 readback' "$W/kmsg")"
# ---------------------------------------------------------------------------------------------------------- the sweep stop
rc=$(runst g-t5v "-sweep" "FAKE_B7=t5v-i(55|110|220|440|880|1760|3520|7040)")
ran=$(grep -c '^== t5v-i' "$W/out/g-t5v-sweep.log"); skp=$(awk -F'\t' 'NR>1 && $10 == "skipped" {n++} END{print n+0}' "$W/out/g-t5v-sweep/cases.tsv")
last=$(awk -F'\t' 'NR>1 && $10 == "ok" {n=$1} END{print n}' "$W/out/g-t5v-sweep/cases.tsv")
[ "$rc" = 0 ] && [ "$skp" = 7 ] && grep -q "sweep t5v: STATUS2 .* has bit 7 set" "$W/out/g-t5v-sweep.log" && [ "$last" = t5v-i55 ] \
	&& ! grep -q '^== t5v-i110 set=heldout risk=' "$W/out/g-t5v-sweep.log" \
	&& ok "sweep: bit 7 after t5v-i55 skips the 7 longer lengths (recorded as class skipped, no job run), rc 0" || bad "sweep stop rc $rc skipped $skp last $last"
rc=$(runst g-t5v "-sweepn" "FAKE_B7=NOMATCH")
skp=$(awk -F'\t' 'NR>1 && $10 == "skipped" {n++} END{print n+0}' "$W/out/g-t5v-sweepn/cases.tsv")
[ "$rc" = 0 ] && [ "$skp" = 0 ] && ok "sweep: no bit 7 anywhere runs all 13 jobs, nothing skipped" || bad "sweep none rc $rc skipped $skp"
rc=$(runst g-t5v "-sweepc" "FAKE_B7=t5v-n3")
skp=$(awk -F'\t' 'NR>1 && $10 == "skipped" {n++} END{print n+0}' "$W/out/g-t5v-sweepc/cases.tsv")
[ "$rc" = 0 ] && [ "$skp" = 0 ] && ok "sweep: a bit 7 on a control (no sweep knob) does not stop the ladder" || bad "sweep control rc $rc skipped $skp"
# ---------------------------------------------------------------------------------------------------------- stop rules
check() { # NAME EXPECTED_RC TABLE ENV...
	nm=$1; want=$2; tb=$3; shift 3
	rm -f "$W/tri.count"
	rc=$(runst "$tb" "-x$nm" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || bad "$nm: rc $rc, wanted $want"
}
check hang-in-t4 4 g-t4 FAKE_HANG=t4-m5p3-7
check hang-in-t5v 4 g-t5v FAKE_HANG=t5v-i110
check fault-stops 4 g-t3 FAKE_FAULT=t3-w-neg
check fatal-kernel 3 g-t4 FAKE_FATAL=t4-m0p83
check freeze 6 g-t5v FAKE_TIMEOUT=t5v-n1
check unexplained-failure 4 g-t3 FAKE_NODIFF=t3-nocut
check overflow-is-the-normal-class 0 g-c3 FAKE_OVERFLOW=--vertices
check overflow-rc3-in-c2 0 g-c2 FAKE_OVERFLOW=4096
check tri-reference-mismatch-with-expectdiff 0 g-c2 FAKE_DIFF=--kpoke-render
check tri-reference-mismatch-without-diff-line 4 g-c2 FAKE_NODIFF=--kpoke-render
check hang-in-c2 4 g-c2 FAKE_HANG=pb:11=0x351
grep -q "STOP: hang in k-1500-0x351" "$W/out/g-c2-xhang-in-c2.log" && ok "a hang in a poke row names the row and stops the stage after the reset and health" || bad "c2 hang log"
# a hung row's class is recorded and later rows are not run
n=$(grep -c '^== ' "$W/out/g-c2-xhang-in-c2.log"); [ "$n" = 5 ] && ok "g-c2 stops at the hung row (5 jobs started: two controls, 0x300, 0x33e, 0x351)" || bad "c2 stop count $n"
# ---------------------------------------------------------------------------------------------------------- the stuck-job watchdog
mkdir -p "$W/tree/run" "$W/tree/tables"; cp "$P"/run/*.sh "$W/tree/run/"
sed 's/wd:75/wd:1/' "$P/tables/g-c2.txt" > "$W/tree/tables/g-c2.txt"
grep -v '  tables/g-c2.txt$' "$P/FROZEN.sha256" > "$W/tree/FROZEN.sha256"; (cd "$W/tree" && shasum -a 256 tables/g-c2.txt >> FROZEN.sha256)
wdrun() { # SUFFIX ENV...: g-c2 with wd:1 from the scratch tree
	sf=$1; shift
	env "$@" FAKE_STATE="$W/state-wd$sf" bash -c "KEEP=$W/out/wd$sf bash $W/tree/run/run_stage.sh g-c2 > $W/out/wd$sf.log 2>&1; echo \$?"
}
cp "$P/FROZEN.sha256" "$W/FROZEN.main"
rc=$(wdrun a FAKE_SLEEP=3 FAKE_SLEEP_JOB=pb:11=0x300)
grep -q "WATCHDOG: the tool had not returned after 1 s" "$W/out/wda.log" && grep -q "STOP: hang in k-1500-0x300" "$W/out/wda.log" \
	&& awk -F'\t' '$1 == "k-1500-0x300" && $10 == "hang" && $11 == "watchdog fired" {f=1} END{exit !f}' "$W/out/wda/cases.tsv" \
	&& [ "$rc" = 4 ] && ok "watchdog: a poke row that does not return in wd seconds gets the kernel's debugfs reset written, ends as class hang, the stage stops (rc 4)" \
	|| bad "watchdog rc $rc: $(grep -E 'WATCHDOG|STOP' "$W/out/wda.log" | tr '\n' '|')"
rc=$(wdrun b A=1)
! grep -q "WATCHDOG" "$W/out/wdb.log" && [ "$rc" = 0 ] && ok "watchdog: quick poke rows are not reset (the background subshell is killed when the tool returns)" || bad "watchdog quiet rc $rc"
rc=$(wdrun c FAKE_TIMEOUT=pb:11=0x300)
grep -q "even after the watchdog's reset: reset and health first" "$W/out/wdc.log" && [ "$rc" = 6 ] \
	&& ok "watchdog: a poke row that never returns (rc 124): the kernel's reset and a health triangle first, then rc 6" || bad "watchdog freeze rc $rc"
# the poke rules (the checks come before the frozen-table check)
mk_tbl() { sed "$1" "$P/tables/g-c2.txt" > "$W/tree/tables/g-c2.txt"; }
pokecase() { # NAME SEDEXPR WANT_RC
	mk_tbl "$2"; rc=$(KEEP=$W/out/pk$1 bash "$W/tree/run/run_stage.sh" g-c2 > "$W/out/pk$1.log" 2>&1; echo $?)
	[ "$rc" = "$3" ] && grep -q "a poke that is not exactly pb:11" "$W/out/pk$1.log" && ok "poke rule: $1 refused (rc $rc)" || bad "poke rule $1 rc $rc"
}
pokecase other-word 's/pb:11=0x300/ta:11=0x300/' 1
pokecase other-index 's/--kpoke-render 1:pb:11=0x80/--kpoke-render 1:pb:12=0x80/' 1
pokecase no-wd 's/ wd:75//' 1
pokecase no-kpoke-knob 's/ kpoke / /' 1
pokecase flip-form 's/pb:11=0x351/pb:11^=0x351/' 1
pokecase second-poke 's/--kpoke pb:11=0x352/--kpoke pb:11=0x352 --kpoke ctx:1=2/' 1
# ---------------------------------------------------------------------------------------------------------- table rules and the staged tool
mkdir -p "$W/tree2/run" "$W/tree2/tables"; cp "$P"/run/*.sh "$W/tree2/run/"; cp "$P/FROZEN.sha256" "$W/tree2/"
sed 's/ expectdiff//' "$P/tables/g-c2.txt" > "$W/tree2/tables/g-c2.txt"
rc=$(KEEP=$W/out/xo bash "$W/tree2/run/run_stage.sh" g-c2 > "$W/out/xo.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "a tri row without expectdiff" "$W/out/xo.log" && ok "a tri row without expectdiff is refused" || bad "expectdiff rule rc $rc"
sed 's/-n 1 --keep-overflow/-n 2 --keep-overflow/' "$P/tables/g-c2.txt" > "$W/tree2/tables/g-c2.txt"
rc=$(KEEP=$W/out/xk bash "$W/tree2/run/run_stage.sh" g-c2 > "$W/out/xk.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "without --keep-going" "$W/out/xk.log" && ok "a multi-render tri job without --keep-going is refused" || bad "keep-going rule rc $rc"
sed 's/stophang s2/stophang hypo:g:1/' "$P/tables/g-t5v.txt" > "$W/tree2/tables/g-t5v.txt"
rc=$(KEEP=$W/out/xh bash "$W/tree2/run/run_stage.sh" g-t5v > "$W/out/xh.log" 2>&1; echo $?)
[ "$rc" = 1 ] || [ "$rc" = 7 ] && ok "a changed table (not frozen) or an unknown knob is refused (rc $rc)" || bad "unknown knob rc $rc"
echo "0000 x" > "$W/TOOL.bad"
rc=$(TOOL_SHA_FILE=$W/TOOL.bad KEEP=$W/out/xt bash "$P/run/run_stage.sh" g-t3 > "$W/out/xt.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "not the staged one" "$W/out/xt.log" && ok "a tool that is not the staged binary is refused" || bad "tool sha rc $rc"
rc=$(ONLY=k-1500-0x351 KEEP=$W/out/xonly bash "$P/run/run_stage.sh" g-c2 > "$W/out/xonly.log" 2>&1; echo $?)
[ "$rc" = 0 ] && [ "$(grep -c '^== ' "$W/out/xonly.log")" = 1 ] && grep -q "== k-1500-0x351 " "$W/out/xonly.log" \
	&& ok "ONLY=k-1500-0x351 runs exactly that row of g-c2" || bad "ONLY rc $rc"
rc=$(ONLY=nope KEEP=$W/out/xonly2 bash "$P/run/run_stage.sh" g-c2 > "$W/out/xonly2.log" 2>&1; echo $?)
[ "$rc" = 1 ] && ok "ONLY naming no row is refused" || bad "ONLY nope rc $rc"
# restaging: the runner keeps no state file between stages (R1's gate file is gone): a second run of a stage starts clean
ls "$W/out/g-t3" | grep -q gate && bad "a gate file exists" || ok "no gate state file exists (R1's gate passed; restaging cannot reset one)"
# preflight: the kmsg marker must arrive (KMSG to nowhere: the shim's dmesg shows nothing)
rc=$(KMSG=/dev/null KEEP=$W/out/xm bash "$P/run/run_stage.sh" g-t3 > "$W/out/xm.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "kmsg marker did not arrive" "$W/out/xm.log" && ok "preflight refuses when its kmsg marker does not arrive" || bad "kmsg marker rc $rc"
# preflight: srcversion of the loaded module against modinfo; a different loaded one stops
echo OTHERSRCV > "$W/srcv"
rc=$(KEEP=$W/out/xs bash "$P/run/run_stage.sh" g-t3 > "$W/out/xs.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "loaded module is not the installed one" "$W/out/xs.log" && ok "preflight compares /sys/module/gma500_gfx/srcversion with modinfo -F srcversion (a different loaded module stops)" || bad "srcversion rc $rc"
echo MOCKSRCV > "$W/srcv"
# preflight: g-c2 needs the debugfs kpoke file
mv "$W/dbg/kpoke" "$W/dbg/kpoke.off"
rc=$(KEEP=$W/out/xkp bash "$P/run/run_stage.sh" g-c2 > "$W/out/xkp.log" 2>&1; echo $?)
mv "$W/dbg/kpoke.off" "$W/dbg/kpoke"
[ "$rc" = 1 ] && grep -q "no debugfs kpoke" "$W/out/xkp.log" && ok "g-c2's preflight needs the debugfs kpoke file" || bad "kpoke preflight rc $rc"
# health: the first failed recovery stops
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"; shasum -a 256 "$W/badtool.sh" > "$W/TOOL.badtool"
rc=$(SGXFIVE_TEST="$W/badtool.sh" TOOL_SHA_FILE="$W/TOOL.badtool" bash -c "KEEP=$W/out/xb bash $P/run/run_stage.sh g-t3 > $W/out/xb.log 2>&1; echo \$?")
[ "$rc" = 5 ] && grep -q "first failed recovery" "$W/out/xb.log" && ok "the first failed health recovery stops (rc 5)" || bad "health stop rc $rc"
num_eq 0x00000000 0 && num_eq 0x0 0 && num_eq 0x00000422 0x422 && ! num_eq 0x6 0 && ! num_eq abc 0 \
	&& ok "numeric knob compare (the kernel prints 0x%08x)" || bad "num_eq"
# the debugfs directory is the FIRST of dri/*/sgx: the real node has three names
mkdir -p "$W/fs/dri/0/sgx" "$W/fs/dri/0000:00:02.0/sgx" "$W/fs/dri/128/sgx"
first=$(sh -c "ls -d $W/fs/dri/*/sgx" | head -n 1)
[ "$(ls -d "$W"/fs/dri/*/sgx | wc -l | tr -d ' ')" = 3 ] && [ -n "$first" ] && grep -q "head -n 1" "$P/run/lib_r2.sh" \
	&& ok "three dri/*/sgx names: the runner takes the first (head -n 1), never 'exactly one'" || bad "dri names"
# ---------------------------------------------------------------------------------------------------------- scorers on fake data
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_r2; print(score_r2.run_stage('$name', '$W/out/$name'))" 2>&1 | grep '^SUMMARY:')
	case "$s" in *"cannot tell"*|*"METHOD BROKEN"*|*"no 2048 cell"*|*"NODATA in every cell"*) ok "scorer $name on fake data: ${s:0:70}" ;; *) bad "scorer $name gave: ${s:-no SUMMARY}" ;; esac
done
# ---------------------------------------------------------------------------------------------------------- guard
"$P/run/guard_r2.sh" > "$W/out/guard.log" 2>&1 && ok "guard" || { bad "guard"; cat "$W/out/guard.log"; }
cp "$P/run/guard_r2.sh" "$W/tree/run/"; cp "$P"/tables/*.txt "$W/tree/tables/"
for bad_line in '\tcat "$D/regs" > "$W/regs.txt"' '\t[ -e "$D/reset" ] && echo y' '\tfor f in "$D"/*; do echo $f; done' \
	'\tls /sys/kernel/debug/dri/0/sgx'; do
	cp "$P/run/lib_r2.sh" "$W/tree/run/lib_r2.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r2.sh"
	"$W/tree/run/guard_r2.sh" > "$W/out/guard2.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "UNPRIVILEGED DEBUGFS ACCESS" "$W/out/guard2.log" && ok "the guard refuses: ${bad_line:2:44}" || bad "guard sudo rule: $bad_line"
done
for bad_line in '\tsudo -n tee "$D/kreg" < x' '\tsudo -n tee "$D/kpoke" < x' '\techo pb:11=1 | sudo -n tee -a "$D/kpoke"' '\techo x > /dev/mem'; do
	cp "$P/run/lib_r2.sh" "$W/tree/run/lib_r2.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r2.sh"
	"$W/tree/run/guard_r2.sh" > "$W/out/guard3.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "FORBIDDEN" "$W/out/guard3.log" && ok "the guard refuses a script line: ${bad_line:2:40}" || bad "guard forbidden rule: $bad_line"
done
cp "$P/run/lib_r2.sh" "$W/tree/run/lib_r2.sh"
cp "$P/tables/g-t3.txt" "$W/tree/tables/g-t3.txt"
printf 'x|heldout|safe|-|stophang|-|probe --tri pixel --poke gen:1=2 "$S/x.bin"\n' >> "$W/tree/tables/g-t3.txt"
"$W/tree/run/guard_r2.sh" > "$W/out/guard4.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "FORBIDDEN option in a table" "$W/out/guard4.log" && ok "the guard refuses a poke option in a table" || bad "guard table rule"
cp "$P/tables/g-t3.txt" "$W/tree/tables/g-t3.txt"
printf 'x|heldout|safe|0x422|stophang kpoke wd:75|-|probe --tri pixel --kpoke pb:11=0x10 "$S/x.bin"\n' >> "$W/tree/tables/g-t3.txt"
"$W/tree/run/guard_r2.sh" > "$W/out/guard5.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "a poke outside g-c2" "$W/out/guard5.log" && ok "the guard refuses pb:11 outside g-c2" || bad "guard poke outside c2"
cp "$P/tables/g-t3.txt" "$W/tree/tables/g-t3.txt"; cp "$P/tables/g-c2.txt" "$W/tree/tables/g-c2.txt"
sed -i.bak 's/pb:11=0x300/pb:7=0x300/' "$W/tree/tables/g-c2.txt"
"$W/tree/run/guard_r2.sh" > "$W/out/guard6.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "a poke that is not pb:11" "$W/out/guard6.log" && ok "the guard refuses another word than pb:11 inside g-c2" || bad "guard other poke"
grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$P"/run/*.sh | grep -v '^[^:]*:[0-9]*:[[:space:]]*#' | grep -v 'guard_r2.sh' && bad "a loop that waits"
# ---------------------------------------------------------------------------------------------------------- driver and staging
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r2.sh" > "$W/out/dry.log" 2>&1; d=$?
[ $d = 0 ] && [ "$(grep -c 'bounded' "$W/out/dry.log")" -ge "$(( 3 * $(wc -l < "$P/stages.txt") ))" ] \
	&& ok "r2.sh dry run: every ssh/scp/health bounded by an alarm" || bad "r2.sh dry run status $d"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r2.sh" --cell g-c3f c3f-2048x1536-0x372 > "$W/out/dry2.log" 2>&1; d=$?
[ $d = 0 ] && grep -q "ONLY=c3f-2048x1536-0x372 bash ~/r2/run/run_stage.sh g-c3f" "$W/out/dry2.log" \
	&& ok "r2.sh --cell passes ONLY=JOB to the stage" || bad "r2.sh --cell status $d"
order=$(tr '\n' ' ' < "$P/stages.txt")
[ "$order" = "g-t3 g-t4 g-t5v g-c3 g-c2 " ] && ok "session order: T3, T4, T5 (vertex loop), C3, C2 last" || bad "stage order: $order"
grep -q '  TOOL.sha256$' "$P/FROZEN.sha256" && grep -q '  TOOLSRC.sha256$' "$P/FROZEN.sha256" && grep -q '^bf4f8be2d8a8fe50034559450928e05695dc96d396d4892f9b00ea6bc0d4f053 ' "$P/TOOL.sha256" \
	&& ok "the freeze covers TOOL.sha256 (R1's laptop tool bf4f8be2...) and TOOLSRC.sha256" || bad "tool pin not frozen"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_r2.sh" > "$W/out/st1.log" 2>&1; s=$?
[ $s = 0 ] && grep -q "sha256sum ~/sgxfive-test-r1 ~/regtimeline" "$W/out/st1.log" && ! grep -qi "deploy-tool\|build\|cc -O2" "$W/out/st1.log" \
	&& ok "staging dry run: copies the runner, tables and programs, checks the pinned tool and regtimeline, builds nothing" || bad "stage dry run status $s"
echo "work dir (kept for inspection): $W"
exit $fail
