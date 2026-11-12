#!/bin/bash
# tests/run_all.sh: every offline test of R6-dpm, in order; stops at the first failure (exit 1).  Needs a current freeze
# (run/freeze_r6.sh freeze after gen/r6plan.py and gen/gen_oomring2.py): the runner mock compares its tables with FROZEN.sha256.
#   1. guard_r6.sh        the session's static guard (runner, tables, blob)
#   2. freeze verify      FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits (git show at the pinned commits)
#   3. test_gen.py        tables and predictions = the generator's; the frozen constants = the frozen offline rules now (about a
#                         minute: b_scenes); the ARGV TWIN against the plan's rows and the kept commands of the same cells
#   4. test_read.py       the one reader on real records (= R3-geo's dpm3; E852's steps; the 21 grows; F1's brackets, F4's burst
#                         ends, F7's run peaks; `model` refuses c5b-cal against the model)
#   5. test_scorer.py     the scorer replayed on R5-dpm's kept attempt (E860-E864, a2b-cal-4x2 held under H-IV), on real-record
#                         r-a0, r-b and r-k directories (hold) and planted copies (fail); L from a real dump
#   6. test_oomring.py    the own task: landed verifier, THE RGN4 FORK'S VERIFIER (host build at a2788bd86537), sgx-sim; oomring2
#                         refused by both (the plan's fallback to R5-dpm's oomring)
#   7. mock_all.py        every command against the rgn4 tool's own --mock (new sizes, --vtx-coords, moves in y)
#   8. test_staged.sh     freeze 2: attempt a1's staged tree fails r-a0 (num_eq not found) and the static check; the tree
#                         stage_r6.sh --local gives passes both
#   9. run_mock.sh        the runner end to end on argv-answering fake worlds: all stages, the laptop paths, the stops, the guard
# PY: the scratch venv (numpy-free); RESGX545_MAIN the landed tree (read only); RESGX545_LINUX the fork home (read only).
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export RESGX545_MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545} RESGX545_LINUX=${RESGX545_LINUX:-/Volumes/linux/linux-sgx}
mkdir -p debug/tmp
export TMPDIR=$PWD/debug/tmp
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
step "guard_r6.sh"; run/guard_r6.sh || fail guard_r6.sh
step "freeze verify"; run/freeze_r6.sh verify || fail "freeze verify"
for t in test_gen test_read test_scorer test_oomring mock_all; do
	step "$t.py"
	"$PY" "tests/$t.py" > "debug/$t.out" 2>&1; rc=$?
	echo "$(grep -c '^ok' "debug/$t.out") ok, $(grep -c '^FAIL' "debug/$t.out") FAIL (rc $rc)"
	[ $rc = 0 ] || { grep '^FAIL' "debug/$t.out" | head; tail -3 "debug/$t.out"; fail "$t.py"; }
done
step "test_staged.sh"
bash tests/test_staged.sh > debug/test_staged.out 2>&1; rc=$?
echo "$(grep -c '^ok' debug/test_staged.out) ok, $(grep -c '^FAIL' debug/test_staged.out) FAIL (rc $rc)"
[ $rc = 0 ] || { grep '^FAIL' debug/test_staged.out | head; fail test_staged.sh; }
step "run_mock.sh"
bash tests/run_mock.sh > debug/run_mock.out 2>&1; rc=$?
echo "$(grep -c '^ok' debug/run_mock.out) ok, $(grep -c '^FAIL' debug/run_mock.out) FAIL (rc $rc)"
[ $rc = 0 ] || { grep '^FAIL' debug/run_mock.out | head; fail run_mock.sh; }
echo "RUN_ALL PASSED"
