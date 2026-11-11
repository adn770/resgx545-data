#!/bin/bash
# tests/run_mock.sh (R3GC): every table runs end to end through run_stage.sh against a fake tool and a fake regtimeline, a
# plain-directory debugfs and shims for sudo/dmesg/timeout; checks job counts, markers, kept DUMPS (the fake writes depth, param,
# tadata and words files: the runner must KEEP them), the rc/class/note columns, knob restore, the stop rules (every hang or fault
# stops; rc 3 "scene overflowed" is the normal class), the table rules (a tri row without expectdiff, a multi-render tri row without
# --keep-going), the ONLY filter, the staged-tool check, the srcversion pin, the guard (the one allowed poke, every other form
# refused, unprivileged debugfs access in every form), the driver and staging dry runs (no build), and the scorers on fake data
# (cannot tell, never a verdict).
# Needs a current freeze (run/freeze_r3.sh freeze): the runner compares its table with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/run.XXXXXX")
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg"
export SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" SGXFIVE_PROBE_BINS="$W/stage" WANT_SRCV=MOCKSRCV
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log" TOOL_SHA_FILE="$W/TOOL.sha256" PYTHONDONTWRITEBYTECODE=1
export FAKE_PEAKS="19,29" FAKE_TRI_COUNT="$W/tri.count" TMPDIR="$P/debug/tmp"
shasum -a 256 "$P/tests/fake_tool.sh" > "$W/TOOL.sha256"
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
for f in reset render_pb_pages regs buf09 render_param render_tadata; do : > "$W/dbg/$f"; done
echo 0x00000422 > "$W/dbg/render_pb_pages"; echo 0x00000000 > "$W/dbg/alias_skip"
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
	nd=$(grep -v '^#' "$t" | grep -c -- '--depth-dump'); kd=$(ls "$W/out/$name" | grep -c 'depth\.1\.bin\.gz')
	nw=$(grep -v '^#' "$t" | grep -c -- '--words'); kw=$(ls "$W/out/$name" | grep -c 'words\.0\.txt\.gz')
	nc=$(( $(wc -l < "$W/out/$name/cases.tsv") - 1 ))
	cols=$(awk -F'\t' 'NR>1 && (NF != 11 || $9 == "" || $10 == "" || $11 == "") {x++} END{print x+0}' "$W/out/$name/cases.tsv")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && [ "$pb" = 0x00000422 ] \
		&& [ "$kd" = "$nd" ] && [ "$kw" = "$nw" ] && [ "$nc" = "$n" ] && [ "$cols" = 0 ] \
		&& ok "$name: $got of $n jobs, $kept kept files, $kd depth dumps, $kw words dumps, $nc rows with rc/class/note, knob back" \
		|| bad "$name: rc $rc, $got of $n jobs, kept $kept, depth dumps $kd of $nd, words $kw of $nw, cases rows $nc (bad cols $cols), pb $pb"
done
echo "case markers: $(grep -c 'resgx545 case' "$W/kmsg"), knob markers: $(grep -c 'resgx545 r3gc readback' "$W/kmsg")"
# ---------------------------------------------------------------------------------------------------------- stop rules
check() { # NAME EXPECTED_RC TABLE ENV...
	nm=$1; want=$2; tb=$3; shift 3
	rm -f "$W/tri.count"
	rc=$(runst "$tb" "-x$nm" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || bad "$nm: rc $rc, wanted $want"
}
check hang-in-gz 4 g-z "FAKE_HANG=--width 36 --height 18"
check fault-stops 4 g-z "FAKE_FAULT=--width 44 --height 18"
check fatal-kernel 3 g-z "FAKE_FATAL=--width 76 --height 18"
check freeze 6 g-z "FAKE_TIMEOUT=--width 20 --height 18"
check unexplained-failure 4 g-z "FAKE_NODIFF=--width 32 --height 18"
check reference-mismatch-with-expectdiff-is-ok 0 g-z "FAKE_DIFF=--tri-full"
check overflow-is-the-normal-class-in-qf 0 g-qf "FAKE_OVERFLOW=--width 4096"
check overflow-is-the-normal-class-in-qh 0 g-qh "FAKE_OVERFLOW=--width 4096"
check hang-in-qf 4 g-qf "FAKE_HANG=--width 4096"
check hang-in-qh 4 g-qh "FAKE_HANG=--move 2:0,1024"
n=$(grep -c '^== ' "$W/out/g-z-xhang-in-gz.log"); [ "$n" = 5 ] && ok "g-z stops at the hung row (5 jobs started: three controls, z-w20, z-w36)" || bad "g-z hang stop after $n jobs"
grep -q "STOP: hang in z-w36" "$W/out/g-z-xhang-in-gz.log" && ok "a hang names the row and stops the stage after the reset and health" || bad "hang log"
# ---------------------------------------------------------------------------------------------------------- table rules and pins
mkdir -p "$W/tree2/run" "$W/tree2/tables"; cp "$P"/run/*.sh "$W/tree2/run/"; cp "$P/FROZEN.sha256" "$W/tree2/"
sed 's/ expectdiff//' "$P/tables/g-z.txt" > "$W/tree2/tables/g-z.txt"
rc=$(KEEP=$W/out/xo bash "$W/tree2/run/run_stage.sh" g-z > "$W/out/xo.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "a tri row without expectdiff" "$W/out/xo.log" && ok "a tri row without expectdiff is refused" || bad "expectdiff rule rc $rc"
sed 's/ --keep-going//' "$P/tables/g-qh.txt" > "$W/tree2/tables/g-qh.txt"
rc=$(KEEP=$W/out/xk bash "$W/tree2/run/run_stage.sh" g-qh > "$W/out/xk.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "without --keep-going" "$W/out/xk.log" && ok "a multi-render tri job without --keep-going is refused" || bad "keep-going rule rc $rc"
sed 's/stophang expectdiff/stophang expectdiff hypo:g:1/' "$P/tables/g-z.txt" > "$W/tree2/tables/g-z.txt"
rc=$(KEEP=$W/out/xh bash "$W/tree2/run/run_stage.sh" g-z > "$W/out/xh.log" 2>&1; echo $?)
[ "$rc" = 1 ] && ok "a changed table (not the frozen one) is refused (rc $rc)" || bad "changed table rc $rc"
echo "0000 x" > "$W/TOOL.bad"
rc=$(TOOL_SHA_FILE=$W/TOOL.bad KEEP=$W/out/xt bash "$P/run/run_stage.sh" g-z > "$W/out/xt.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "not the staged one" "$W/out/xt.log" && ok "a tool that is not the staged binary is refused" || bad "tool sha rc $rc"
rc=$(ONLY=z-w44 KEEP=$W/out/xonly bash "$P/run/run_stage.sh" g-z > "$W/out/xonly.log" 2>&1; echo $?)
[ "$rc" = 0 ] && [ "$(grep -c '^== ' "$W/out/xonly.log")" = 1 ] && grep -q "== z-w44 " "$W/out/xonly.log" \
	&& ok "ONLY=z-w44 runs exactly that row of g-z" || bad "ONLY rc $rc"
rc=$(ONLY=nope KEEP=$W/out/xonly2 bash "$P/run/run_stage.sh" g-z > "$W/out/xonly2.log" 2>&1; echo $?)
[ "$rc" = 1 ] && ok "ONLY naming no row is refused" || bad "ONLY nope rc $rc"
rc=$(KMSG=/dev/null KEEP=$W/out/xm bash "$P/run/run_stage.sh" g-z > "$W/out/xm.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "kmsg marker did not arrive" "$W/out/xm.log" && ok "preflight refuses when its kmsg marker does not arrive" || bad "kmsg marker rc $rc"
echo OTHERSRCV > "$W/srcv"
rc=$(KEEP=$W/out/xs bash "$P/run/run_stage.sh" g-z > "$W/out/xs.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "loaded module is not the installed one" "$W/out/xs.log" && ok "preflight: loaded srcversion differs from modinfo's: stop" || bad "srcversion rc $rc"
echo MOCKSRCV > "$W/srcv"
rc=$(WANT_SRCV=B21FDA82BD5E5CB5A627E3B KEEP=$W/out/xs2 bash "$P/run/run_stage.sh" g-z > "$W/out/xs2.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "the session was built for B21FDA82BD5E5CB5A627E3B" "$W/out/xs2.log" && ok "preflight: loaded = installed but not B21FDA82BD5E5CB5A627E3B: stop" || bad "srcversion pin rc $rc"
grep -q 'B21FDA82BD5E5CB5A627E3B' "$P/run/lib_r3.sh" && ok "the default pin of lib_r3.sh is the E625/E730/E779 module B21FDA82BD5E5CB5A627E3B" || bad "default srcversion pin"
for f in reset render_pb_pages regs buf09 render_param render_tadata; do
	mv "$W/dbg/$f" "$W/dbg/$f.off"
	rc=$(KEEP=$W/out/xd bash "$P/run/run_stage.sh" g-z > "$W/out/xd.log" 2>&1; echo $?)
	mv "$W/dbg/$f.off" "$W/dbg/$f"
	[ "$rc" = 1 ] && grep -q "no debugfs $f" "$W/out/xd.log" && ok "preflight needs the debugfs file $f" || bad "debugfs $f rc $rc"
done
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"; shasum -a 256 "$W/badtool.sh" > "$W/TOOL.badtool"
rc=$(SGXFIVE_TEST="$W/badtool.sh" TOOL_SHA_FILE="$W/TOOL.badtool" bash -c "KEEP=$W/out/xb bash $P/run/run_stage.sh g-z > $W/out/xb.log 2>&1; echo \$?")
[ "$rc" = 5 ] && grep -q "first failed recovery" "$W/out/xb.log" && ok "the first failed health recovery stops (rc 5)" || bad "health stop rc $rc"
# a tool message is searched in the WHOLE output: a failure line in the middle of a long output is found
grep -q 'cat "$W/\$name.out"\|grep -Eq "job \[0-9\]+ hung|hung|timed out waiting" "\$W/\$name.out" "\$W/\$name.dmesg"' "$P/run/run_stage.sh" \
	&& ok "the classifier greps the whole kept output and the kernel slice (no head/tail on the match)" || bad "classifier"
num_eq 0x00000000 0 && num_eq 0x0 0 && num_eq 0x00000422 0x422 && ! num_eq 0x6 0 && ! num_eq abc 0 \
	&& ok "numeric knob compare (the kernel prints 0x%08x)" || bad "num_eq"
[ "$(grep -c 'head -n 1' "$P/run/lib_r3.sh")" -ge 1 ] && ok "the runner takes the first dri/*/sgx (never 'exactly one')" || bad "dri names"
# ---------------------------------------------------------------------------------------------------------- scorers on fake data
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_r3; print(score_r3.run_stage('$name', '$W/out/$name', fit_dir='$W/out/g-qf'))" 2>&1 | grep '^SUMMARY:')
	case "$s" in *"cannot tell"*) ok "scorer $name on fake data: ${s:0:70}" ;; *) bad "scorer $name gave: ${s:-no SUMMARY}" ;; esac
done
# ---------------------------------------------------------------------------------------------------------- guard
"$P/run/guard_r3.sh" > "$W/out/guard.log" 2>&1 && ok "guard" || { bad "guard"; cat "$W/out/guard.log"; }
mkdir -p "$W/tree/run" "$W/tree/tables"; cp "$P"/run/*.sh "$W/tree/run/"; cp "$P"/tables/*.txt "$W/tree/tables/"
for bad_line in '\tcat "$D/regs" > "$W/regs.txt"' '\t[ -e "$D/reset" ] && echo y' '\tfor f in "$D"/*; do echo $f; done' \
	'\tls /sys/kernel/debug/dri/0/sgx'; do
	cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r3.sh"
	"$W/tree/run/guard_r3.sh" > "$W/out/guard2.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "UNPRIVILEGED DEBUGFS ACCESS" "$W/out/guard2.log" && ok "the guard refuses: ${bad_line:2:44}" || bad "guard sudo rule: $bad_line"
done
for bad_line in '\tsudo -n tee "$D/kreg" < x' '\tsudo -n tee "$D/kpoke" < x' '\techo pb:11=1 | sudo -n tee -a "$D/kpoke"' '\techo x > /dev/mem'; do
	cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"; printf "$bad_line\n" >> "$W/tree/run/lib_r3.sh"
	"$W/tree/run/guard_r3.sh" > "$W/out/guard3.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "FORBIDDEN" "$W/out/guard3.log" && ok "the guard refuses a script line: ${bad_line:2:40}" || bad "guard forbidden rule: $bad_line"
done
cp "$P/run/lib_r3.sh" "$W/tree/run/lib_r3.sh"
gt() { # NAME LINE FILE WANTTEXT: append LINE to a copy of table FILE, the guard must fail with WANTTEXT
	cp "$P/tables/$3.txt" "$W/tree/tables/$3.txt"
	printf '%s\n' "$2" >> "$W/tree/tables/$3.txt"
	"$W/tree/run/guard_r3.sh" > "$W/out/guard-$1.log" 2>&1; g=$?
	[ $g = 1 ] && grep -q "$4" "$W/out/guard-$1.log" && ok "the guard refuses $1" || bad "guard $1 (rc $g)"
	cp "$P/tables/$3.txt" "$W/tree/tables/$3.txt"
}
gt other-poke 'x|heldout|safe|-|stophang expectdiff|-|tri --width 64 --height 64 --poke gen:1=2' g-z "a poke other than blk:1=0x00400200"
gt blk-poke-other-word 'x|heldout|safe|-|stophang expectdiff|-|tri --width 64 --height 64 --poke blk:2=0x00400200' g-z "a poke other than blk:1"
gt poke-outside-gz 'x|heldout|safe|0x422|stophang expectdiff|-|tri --width 64 --height 64 --poke blk:1=0x00400200' g-qf "a poke outside g-z"
gt kpoke 'x|heldout|safe|0x422|stophang expectdiff|-|tri --width 64 --height 64 --kpoke-render 1:pb:11=0x80' g-qf "FORBIDDEN option in a table"
gt kreg 'x|heldout|safe|-|stophang expectdiff|-|tri --width 64 --height 64 --kreg-render 1:0x10=1' g-z "FORBIDDEN"
gt ctx2 'x|heldout|safe|-|stophang expectdiff|-|tri --width 64 --height 64 --ctx2' g-z "FORBIDDEN option in a table"
grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$P"/run/*.sh | grep -v '^[^:]*:[0-9]*:[[:space:]]*#' | grep -v 'guard_r3.sh' && bad "a loop that waits"
# the generator refuses the same pokes
"$PY" - <<PYEOF > "$W/out/gen.log" 2>&1
import sys; sys.path.insert(0, "$P/gen")
import pathlib
import rcommon as C
C.TABLES = pathlib.Path("$W/out/tabs")        # never the real tables
C.TABLES.mkdir(exist_ok=True)
for stage, args in (("g-z", "tri --poke blk:2=1"), ("g-qf", "tri --poke blk:1=0x00400200"), ("g-z", "tri --kpoke-render 1:pb:11=0x80")):
    try:
        C.write_table(stage, [C.Row("x", "heldout", "safe", "-", "stophang expectdiff", "-", args)], [], "h")
        print("accepted", stage, args)
    except AssertionError as e:
        print("refused", stage, args)
PYEOF
[ "$(grep -c '^refused' "$W/out/gen.log")" = 3 ] && ok "write_table refuses a blk poke other than word 1, the poke outside g-z and any kpoke" || { bad "write_table poke rules"; cat "$W/out/gen.log"; }
# ---------------------------------------------------------------------------------------------------------- driver and staging
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r3.sh" > "$W/out/dry.log" 2>&1; d=$?
[ $d = 0 ] && [ "$(grep -c 'bounded' "$W/out/dry.log")" -ge "$(( 3 * $(wc -l < "$P/stages.txt") ))" ] \
	&& ok "r3.sh dry run: every ssh/scp/health bounded by an alarm" || bad "r3.sh dry run status $d"
grep -q "bash ~/r3gc/run/run_stage.sh g-z" "$W/out/dry.log" && grep -q "scp -r .*:r3gc-out/g-qh" "$W/out/dry.log" && ok "the driver uses the ~/r3gc, ~/r3gc-out prefix" || bad "r3gc prefix"
! grep -q '~/r3g/\|~/r3p-\|~/r3xev\|~/r2' "$W/out/dry.log" && ok "no collision with ~/r3g, ~/r3p-, ~/r3xev or round 2's ~/r2" || bad "prefix collision"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/r3.sh" --cell g-z z-w44 > "$W/out/dry2.log" 2>&1; d=$?
[ $d = 0 ] && grep -q "ONLY=z-w44 bash ~/r3gc/run/run_stage.sh g-z" "$W/out/dry2.log" && ok "r3.sh --cell passes ONLY=JOB to the stage" || bad "r3.sh --cell status $d"
order=$(tr '\n' ' ' < "$P/stages.txt")
[ "$order" = "g-z g-qf g-qh " ] && ok "session order: g-z (C1), g-qf (C2 fit), g-qh (C2 held out)" || bad "stage order: $order"
grep -q '  TOOL.sha256$' "$P/FROZEN.sha256" && grep -q '  TOOLSRC.sha256$' "$P/FROZEN.sha256" && grep -q '^bf4f8be2d8a8fe50034559450928e05695dc96d396d4892f9b00ea6bc0d4f053 ' "$P/TOOL.sha256" \
	&& ok "the freeze covers TOOL.sha256 (R1's laptop tool bf4f8be2...) and TOOLSRC.sha256" || bad "tool pin not frozen"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_r3.sh" > "$W/out/st1.log" 2>&1; s=$?
[ $s = 0 ] && grep -q "sha256sum ~/sgxfive-test-r1 ~/regtimeline" "$W/out/st1.log" && ! grep -qi "deploy-tool\|build\|cc -O2\|bins" "$W/out/st1.log" \
	&& ok "staging dry run: copies the runner and tables, checks the pinned tool and regtimeline, builds nothing, no programs" || bad "stage dry run status $s"
echo "work dir (kept for inspection): $W"
exit $fail
