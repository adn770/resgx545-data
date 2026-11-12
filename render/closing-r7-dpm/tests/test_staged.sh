#!/bin/bash
# tests/test_staged.sh (R7-dpm): the runner tree the laptop gets is complete, checked by the LANDED tools/closing/sessioncheck.py
# (copied byte for byte as run/sessioncheck.py):
#   1. sessioncheck.py staged on the tree stage_r7.sh --local gives: every file a staged script sources or runs, every module a staged
#      Python file imports, every function a staged script calls is staged and defined;
#   2. the same check FAILS R6-dpm's attempt a1 tree (closing6/r6-dpm/freeze1/a1-tree: lib_check.sh not staged, num_eq undefined),
#      and FAILS this session's tree with one file left out (each of lib_check.sh, sessioncheck.py, scorekit.py, r7read.py in turn):
#      the check can fail;
#   3. sessioncheck.py envi: s-a0 run from the staged tree under env -i (PATH, HOME and the mock's stand-ins only) exits 0 with no
#      "command not found" / "No such file" line; the same tree without lib_check.sh fails it.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
mkdir -p "$P/debug/tmp"
W=$(mktemp -d "$P/debug/tmp/staged.XXXXXX")
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
SC=$P/run/sessioncheck.py
RUNNER=$(sed -n 's/^RUNNER="\(.*\)"$/\1/p' "$P/run/stage_r7.sh")
[ -n "$RUNNER" ] && ok "stage_r7.sh's one file list: $RUNNER" || bad "no RUNNER list in stage_r7.sh"
L=$W/lap; bash "$P/run/stage_r7.sh" --local "$L" > "$W/stage.out" 2>&1 || bad "stage_r7.sh --local"
T=$L/scratch/r7d/run/run
# 1. the staged tree
# shellcheck disable=SC2086
"$PY" "$SC" staged "$P/run" $RUNNER --entry run_stage.sh > "$W/st.out" 2>&1 && ok "sessioncheck staged: $(cat "$W/st.out")" || { bad "sessioncheck staged on the staged list"; cat "$W/st.out"; }
[ "$(ls "$T" | tr '\n' ' ')" = "$(echo $RUNNER | tr ' ' '\n' | sort | tr '\n' ' ')" ] && ok "the --local tree holds exactly that list" || bad "the --local tree is not the list: $(ls "$T" | tr '\n' ' ')"
# 2. the check can fail
A1=/Users/jtorra/src/scratch/resgx545/closing6/r6-dpm/freeze1/a1-tree
if [ -d "$A1" ]; then
	"$PY" "$SC" staged "$P/../../closing6/r6-dpm/run" $(ls "$A1") --entry run_stage.sh > "$W/a1.out" 2>&1 \
		&& bad "sessioncheck staged passes R6-dpm's a1 tree" || ok "sessioncheck staged FAILS R6-dpm's a1 tree: $(grep -c FAIL "$W/a1.out") findings ($(grep -o 'lib_check.sh' "$W/a1.out" | head -1) not staged)"
else
	bad "R6-dpm's a1 tree not found at $A1"
fi
for drop in lib_check.sh sessioncheck.py scorekit.py r7read.py; do
	# shellcheck disable=SC2086
	"$PY" "$SC" staged "$P/run" $(echo $RUNNER | tr ' ' '\n' | grep -vx "$drop") --entry run_stage.sh > "$W/d.out" 2>&1 \
		&& bad "sessioncheck staged passes the list without $drop" || ok "without $drop the staged check FAILS ($(grep -m1 FAIL "$W/d.out" | cut -c1-90))"
done
# 3. env -i on the staged tree
mk() { # DIR: the laptop around the runner (fake debugfs, programs)
	mkdir -p "$1/dbg"
	for f in reset render_pb_pages regs buf09 render_param render_tadata; do : > "$1/dbg/$f"; done
	echo 0x00000422 > "$1/dbg/render_pb_pages"; echo off > "$1/dbg/own_arm"; echo MOCKSRCV > "$1/srcv"; : > "$1/kmsg"
}
envi() { # HOMEDIR LOG
	"$PY" "$SC" envi --log "$2" --set PATH="$P/tests/shims:/usr/bin:/bin:/usr/sbin:/sbin" --set HOME="$1" --set PY="$PY" \
		--set PYTHONDONTWRITEBYTECODE=1 --set SGXFIVE_TEST="$P/tests/fake_tool.sh" --set KMSG="$1/kmsg" --set SRCV_PATH="$1/srcv" \
		--set SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" --set EXPECT_SRCV_A=MOCKSRCV --set RESET_WAIT=0 --set HEALTH_WAIT=0 \
		--set RUNNER_PY=python3 --set FWTASK_RUN="$P/tests/fake_fwtask_run.py" --set FAKE_LOG="$1/fake.log" --set FAKE_WORLD= \
		--set EXPECT_TOOL="$(shasum -a 256 "$P/tests/fake_tool.sh" | cut -d' ' -f1)" --set EXPECT_RT="$(shasum -a 256 "$P/tests/fake_rt.sh" | cut -d' ' -f1)" \
		--set SGXFIVE_DEBUGFS="$1/dbg" -- bash "$1/scratch/r7d/run/run/run_stage.sh" s-a0
}
mk "$L"
envi "$L" "$W/envi.log" > "$W/envi.out" 2>&1 && grep -q "## end: 6 jobs of s-a0" "$W/envi.log" \
	&& ok "sessioncheck envi: s-a0 from the staged tree under env -i: $(tail -1 "$W/envi.out")" || { bad "envi on the staged tree"; cat "$W/envi.out"; grep -E "STOP|not found|No such" "$W/envi.log" | head -3; }
L2=$W/lap2; bash "$P/run/stage_r7.sh" --local "$L2" > /dev/null 2>&1; rm "$L2/scratch/r7d/run/run/lib_check.sh"; mk "$L2"
envi "$L2" "$W/envi2.log" > "$W/envi2.out" 2>&1 && bad "envi passes a tree without lib_check.sh" || ok "sessioncheck envi FAILS the tree without lib_check.sh ($(grep -m1 -E 'FAIL|STOP' "$W/envi2.out" | cut -c1-80))"
rm -rf "$W"
echo "ALL: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
