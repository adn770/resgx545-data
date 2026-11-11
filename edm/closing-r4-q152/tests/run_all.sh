#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh [--prefreeze]: every offline test of R4b, in order; stops at the first failure (exit 1).  --prefreeze: the freeze
# checks (step 2 and run_mock's first check) are expected to fail and are skipped: used once, before run/freeze_r4b.sh freeze.
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
export PYTHON=$PY PY
PRE=0; [ "${1:-}" = "--prefreeze" ] && PRE=1
mkdir -p debug
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
echo "=== guard_r4b.sh"; run/guard_r4b.sh || fail guard_r4b.sh
if [ $PRE = 0 ]; then echo "=== freeze verify"; run/freeze_r4b.sh verify || fail "freeze verify"; fi
echo "=== test_gen_r4b.py"; "$PY" tests/test_gen_r4b.py > debug/gen.out 2>&1 || { grep -v '^ok' debug/gen.out; fail test_gen_r4b.py; }
echo "gen checks: $(grep -c '^ok' debug/gen.out)"
echo "=== test_score_r4b.py"; "$PY" tests/test_score_r4b.py > debug/score.out 2>&1 || { grep -v '^ok' debug/score.out; fail test_score_r4b.py; }
echo "scorer checks: $(grep -c '^ok' debug/score.out)"
echo "=== run_mock.py"
"$PY" tests/run_mock.py > debug/mock.out 2>&1; rc=$?
if [ $PRE = 1 ]; then
	nf=$(grep -c '^FAIL ' debug/mock.out)
	[ "$nf" = 1 ] && grep -q '^FAIL the frozen files of this directory verify' debug/mock.out && rc=0
fi
tail -1 debug/mock.out
[ $rc = 0 ] || { grep '^FAIL ' debug/mock.out | head; fail run_mock.py; }
echo "mock checks: $(grep -c '^ok' debug/mock.out)"
echo "RUN_ALL PASSED"
