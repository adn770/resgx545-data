#!/bin/bash
# tests/run_all.sh: every offline test of R5-dpm, in order; stops at the first failure (exit 1).  Needs a current freeze
# (run/freeze_r5.sh freeze after gen/r5plan.py and gen/gen_oomring.py): the runner mock compares its tables with FROZEN.sha256.
#   1. guard_r5.sh        the session's static guard (runner, tables, blob)
#   2. freeze verify      FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits (git show at the pinned commits)
#   3. test_gen.py        tables and predictions = the generator's; the ARGV TWIN against the plan's rows and round 3's commands
#   4. test_read.py       the one reader on real records (= R3-geo's dpm3 on 102 jobs; section 1's steps; c4-b3 the only grow)
#   5. test_scorer.py     the scorer replayed on the kept g-c4, g-c5, g-qf (holds) and planted copies (fails); A3 pages from sgx-sim
#   6. test_oomring.py    the own task: landed verifier, THE RGN4 FORK'S VERIFIER (host build at a2788bd86537), sgx-sim
#   7. mock_all.py        every command against the rgn4 tool's own --mock
#   8. run_mock.sh        the runner end to end on argv-answering fake worlds: all stages, the stops, the guard's refusals
# PY: the scratch venv (numpy-free); RESGX545_MAIN the landed tree (read only); RESGX545_LINUX the fork home (read only).
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export RESGX545_MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545} RESGX545_LINUX=${RESGX545_LINUX:-/Volumes/linux/linux-sgx}
mkdir -p debug/tmp
export TMPDIR=$PWD/debug/tmp
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
step "guard_r5.sh"; run/guard_r5.sh || fail guard_r5.sh
step "freeze verify"; run/freeze_r5.sh verify || fail "freeze verify"
for t in test_gen test_read test_scorer test_oomring mock_all; do
	step "$t.py"
	"$PY" "tests/$t.py" > "debug/$t.out" 2>&1; rc=$?
	echo "$(grep -c '^ok' "debug/$t.out") ok, $(grep -c '^FAIL' "debug/$t.out") FAIL (rc $rc)"
	[ $rc = 0 ] || { grep '^FAIL' "debug/$t.out" | head; tail -3 "debug/$t.out"; fail "$t.py"; }
done
step "run_mock.sh"
bash tests/run_mock.sh > debug/run_mock.out 2>&1; rc=$?
echo "$(grep -c '^ok' debug/run_mock.out) ok, $(grep -c '^FAIL' debug/run_mock.out) FAIL (rc $rc)"
[ $rc = 0 ] || { grep '^FAIL' debug/run_mock.out | head; fail run_mock.sh; }
echo "RUN_ALL PASSED"
