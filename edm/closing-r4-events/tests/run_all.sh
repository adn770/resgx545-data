#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh [--prefreeze]: every offline test of R4-events, in order.  Stops at the first failure (exit 1).  With --prefreeze the freeze
# checks (verify here, t_freeze_and_guard's first check in run_mock.py) are expected to fail and are skipped: used once, before
# run/freeze_r4e.sh freeze.
#   1. guard_r4e.sh         static checks of the scripts, the runner, the sources and the tables
#   2. freeze verify        FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits (git show at 5a13042)
#   3. tests/test_gen_r4.py the tables and predictions are what the generator makes; the plan's numbers
#   3b. tests/sim_r4.py      the blobs in sgx-sim (ring_exit2's tick and kick passes, ring_skip3p's skip-once, ring_hold)
#   4. tests/test_scorer.py the scorers on worlds built from REAL records (E813, E816, E817, E819, E823) and the row engine
#   5. tests/run_mock.py    the whole session on a mock laptop (every hypothesis world, the stops, the refusals, the traps, the guard's refusals)
# PY: the scratch venv's python; RESGX545: the integration tree (default closing4/lead/wt, branch r4-fold-rule at 5a13042).
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PYTHON=$PY PY
export RESGX545=${RESGX545:-/Users/jtorra/src/scratch/resgx545/closing4/lead/wt}
PRE=0; [ "${1:-}" = "--prefreeze" ] && PRE=1
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
mkdir -p debug
step "guard_r4e.sh"; run/guard_r4e.sh || fail guard_r4e.sh
if [ $PRE = 0 ]; then step "freeze verify"; run/freeze_r4e.sh verify || fail "freeze verify"; fi
step "sim_r4.py"; "$PY" tests/sim_r4.py > debug/sim.out 2>&1 || { tail -20 debug/sim.out; fail sim_r4.py; }; tail -1 debug/sim.out
echo "sim checks: $(grep -c '^ok' debug/sim.out)"
step "test_gen_r4.py"; "$PY" tests/test_gen_r4.py > debug/gen.out 2>&1 || { grep -v '^ok' debug/gen.out | tail -20; fail test_gen_r4.py; }
tail -1 debug/gen.out; echo "generator checks: $(grep -c '^ok' debug/gen.out)"
step "test_scorer.py"; MOCK_DIR=${TMPDIR:-/tmp} "$PY" tests/test_scorer.py > debug/scorer.out 2>&1 || { grep -v '^ok' debug/scorer.out | tail -20; fail test_scorer.py; }
tail -1 debug/scorer.out; echo "scorer checks: $(grep -c '^ok' debug/scorer.out)"
step "run_mock.py"
"$PY" -u tests/run_mock.py > debug/mock.out 2>&1; rc=$?
if [ $PRE = 1 ]; then
	# the only failures allowed before the freeze are the freeze checks themselves (the files verify, FROZEN.commits exists)
	nf=$(grep -a '^FAIL ' debug/mock.out | grep -avc '^FAIL the frozen files of this directory verify\|^FAIL FROZEN.commits pins')
	[ "$nf" = 0 ] && rc=0
fi
tail -2 debug/mock.out
[ $rc = 0 ] || { grep -a '^FAIL \|raised' debug/mock.out | head; fail run_mock.py; }
echo "mock checks: $(grep -c '^ok' debug/mock.out)"
echo "RUN_ALL PASSED"
