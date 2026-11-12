#!/bin/bash
# tests/test_staged.sh (freeze 2): the runner tree the laptop gets is complete.
#   1. attempt a1's tree (freeze1/a1-tree: the five files freeze 1's stage_r6.sh copied, each hashing to freeze1/FROZEN.sha256) run
#      as the laptop runs it (env -i, the mock's stand-ins) FAILS r-a0: "num_eq: command not found" at the ctlleft control, as a1 did
#      on the laptop (its log line 90): the slip is reproduced, so this test can fail;
#   2. the tree stage_r6.sh --local gives now runs r-a0 to the end (rc 0) with no "command not found";
#   3. statically: every file run_stage.sh and lib_r6.sh source or run (. "$HERE_LIB/x", "$HERE_LIB/x.py", the landed fwtask_run.py)
#      is in the staged tree, and every function either script calls is defined in the staged tree (a function defined in a laptop-side
#      script of run/ here and named in a staged script must be defined in a staged file).
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/staged.XXXXXX")
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
SH=$P/tests/shims
for f in lib_r6.sh run_stage.sh r6read.py r6.env fwtask_run.py; do
	h=$(shasum -a 256 "$P/freeze1/a1-tree/$f" | cut -d' ' -f1)
	grep -q "^$h  run/$f\$" "$P/freeze1/FROZEN.sha256" || bad "freeze1/a1-tree/$f is not freeze 1's run/$f"
done
grep -q 'scp -q $OPTS "$R6"/run/lib_r6.sh "$R6"/run/run_stage.sh "$R6"/run/r6read.py "$R6"/run/r6.env "$R6"/run/fwtask_run.py' "$P/freeze1/stage_r6.sh.as-run" \
	&& ! grep -q lib_check "$P/freeze1/stage_r6.sh.as-run" && ok "freeze 1's stage_r6.sh staged those five files and not lib_check.sh" || bad "freeze 1's file list"
layout() { # DIR: the laptop layout around a runner tree DIR/scratch/r6d/run/run (tables, FROZEN, programs)
	mkdir -p "$1/scratch/r6d/run/tables" "$1/scratch/r6d/stage" "$1/scratch/tmp" "$1/dbg"
	cp "$P"/tables/*.txt "$1/scratch/r6d/run/tables/"; cp "$P/FROZEN.sha256" "$1/scratch/r6d/run/"
	cp "$P"/bins/p1139-green.bin "$P"/bins/oomring.blob "$1/scratch/r6d/stage/"
	for f in reset render_pb_pages regs buf09 render_param render_tadata; do : > "$1/dbg/$f"; done
	echo 0x00000422 > "$1/dbg/render_pb_pages"; echo off > "$1/dbg/own_arm"; echo MOCKSRCV > "$1/srcv"; : > "$1/kmsg"
}
run_a0() { # DIR TREEFILE: r-a0 as the laptop runs it; rc
	d=$1
	env -i PATH="$SH:$PATH" HOME="$d" PY="$PY" PYTHONDONTWRITEBYTECODE=1 SGXFIVE_TEST="$P/tests/fake_tool.sh" KMSG="$d/kmsg" SRCV_PATH="$d/srcv" \
		SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" EXPECT_SRCV=MOCKSRCV RESET_WAIT=0 HEALTH_WAIT=0 RUNNER_PY=python3 \
		FWTASK_RUN="$P/tests/fake_fwtask_run.py" FAKE_LOG="$d/fake.log" FAKE_TRI_COUNT="$d/tri.count" FAKE_WORLD="" \
		EXPECT_TOOL=$(shasum -a 256 "$P/tests/fake_tool.sh" | cut -d' ' -f1) EXPECT_RT=$(shasum -a 256 "$P/tests/fake_rt.sh" | cut -d' ' -f1) \
		SGXFIVE_DEBUGFS="$d/dbg" SGXFIVE_PROBE_BINS="$d/scratch/r6d/stage" bash "$d/scratch/r6d/run/run/run_stage.sh" r-a0 > "$d/r-a0.log" 2>&1
	echo $?
}
# 1. attempt a1's tree (its tables are the frozen ones: predictions and tables did not change)
A=$W/a1; mkdir -p "$A/scratch/r6d/run/run"; cp "$P"/freeze1/a1-tree/* "$A/scratch/r6d/run/run/"; layout "$A"
cp "$P/freeze1/FROZEN.sha256" "$A/scratch/r6d/run/"
rc=$(run_a0 "$A")
[ "$rc" != 0 ] && grep -q "num_eq: command not found" "$A/r-a0.log" && grep -q "STOP: control a0-t-s3m7 left 0x2 global pages, frozen 2" "$A/r-a0.log" \
	&& ok "attempt a1's tree FAILS r-a0 as on the laptop (rc $rc: 'num_eq: command not found' at a0-t-s3m7, 'left 0x2, frozen 2')" \
	|| { bad "a1's tree did not reproduce the slip (rc $rc)"; grep -E "STOP|not found" "$A/r-a0.log" | head -3; }
# 2. the tree stage_r6.sh gives now
B=$W/a2; bash "$P/run/stage_r6.sh" --local "$B" > "$W/stage.out" 2>&1 || bad "stage_r6.sh --local"
layout "$B" >/dev/null 2>&1
cp "$P/FROZEN.sha256" "$B/scratch/r6d/run/"
rc=$(run_a0 "$B")
[ "$rc" = 0 ] && ! grep -q "command not found\|No such file" "$B/r-a0.log" && grep -q "## end: 7 jobs of r-a0" "$B/r-a0.log" \
	&& ok "the staged tree of freeze 2 runs r-a0 to the end (7 jobs, rc 0, no command or file missing)" || { bad "freeze 2 tree: rc $rc"; grep -E "STOP|not found|No such" "$B/r-a0.log" | head -3; }
# the a1 tree with lib_check.sh added (nothing else) also passes: that file was the whole slip
cp "$P/run/lib_check.sh" "$A/scratch/r6d/run/run/"; rm -rf "$A/scratch/r6d/out" "$A/scratch/tmp"/*; mkdir -p "$A/scratch/tmp"
rc=$(run_a0 "$A")
[ "$rc" = 0 ] && ok "attempt a1's tree plus lib_check.sh passes r-a0: the missing file was the whole slip" || bad "a1 + lib_check.sh: rc $rc"
# 3. static completeness of the staged tree
T=$B/scratch/r6d/run/run
"$PY" "$P/tests/staged_static.py" "$P/run" "$T" || fail=1
"$PY" "$P/tests/staged_static.py" "$P/run" "$P/freeze1/a1-tree" > "$W/a1static.out" 2>&1 \
	&& bad "the static check passes attempt a1's tree" || ok "the static check FAILS attempt a1's tree: $(grep -c '^FAIL' "$W/a1static.out") findings (lib_check.sh not staged, num_eq undefined)"
rm -rf "$W"
echo "ALL: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
