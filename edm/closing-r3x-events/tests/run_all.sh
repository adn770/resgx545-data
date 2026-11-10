#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh [--prefreeze]: every offline test of R3x-events, in order.  Stops at the first failure (exit 1).  With --prefreeze the
# freeze check (t_freeze_and_guard's first check) is expected to fail and is skipped: used once, before run/freeze_r3.sh freeze.
#   1. guard_r3.sh          static checks of the scripts, the runner, the sources and the tables
#   2. tests/sim_r3.py      the blobs in sgx-sim (every command path of alias2.s and ring_end.s)
#   3. tests/test_scorer.py the scorer on E537's and E793's dumps, R3's A0 and B0, S2b's hold page, and one world per hypothesis
#   4. tests/test_guard.py  the guard on assembled code and tables, every limit broken in a copy
#   5. tests/run_mock.py    the whole session on a mock laptop (about 3 minutes; real sleeps, no hardware)
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-../../closing/pixel-faults/.venv/bin/python}
export PYTHON=$PY
PRE=0; [ "${1:-}" = "--prefreeze" ] && PRE=1
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
step "guard_r3.sh"; run/guard_r3.sh || fail guard_r3.sh
if [ $PRE = 0 ]; then step "freeze verify"; run/freeze_r3.sh verify || fail "freeze verify"; fi
step "sim_r3.py"; "$PY" tests/sim_r3.py > debug/sim.out 2>&1 || { tail -20 debug/sim.out; fail sim_r3.py; }; tail -1 debug/sim.out
step "test_scorer.py"; "$PY" tests/test_scorer.py > debug/scorer.out 2>&1 || { grep -v '^ok' debug/scorer.out | tail -20; fail test_scorer.py; }
tail -1 debug/scorer.out; echo "scorer checks: $(grep -c '^ok' debug/scorer.out)"
step "test_guard.py"; "$PY" tests/test_guard.py > debug/guard.out 2>&1 || { grep -v '^ok' debug/guard.out | tail -20; fail test_guard.py; }
tail -1 debug/guard.out; echo "guard checks: $(grep -c '^ok' debug/guard.out)"
step "run_mock.py"
"$PY" tests/run_mock.py > debug/mock.out 2>&1; rc=$?
if [ $PRE = 1 ]; then
	# the only failure allowed before the freeze is the freeze check itself
	nf=$(grep -c '^FAIL ' debug/mock.out)
	[ "$nf" = 1 ] && grep -q '^FAIL the frozen files of this directory verify' debug/mock.out && rc=0
fi
tail -3 debug/mock.out
[ $rc = 0 ] || { grep '^FAIL ' debug/mock.out | head; fail run_mock.py; }
echo "mock checks: $(grep -c '^ok' debug/mock.out)"
echo "RUN_ALL PASSED"
