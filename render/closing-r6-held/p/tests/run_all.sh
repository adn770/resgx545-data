#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh [--prefreeze]: every offline test of r6-held part P (R5-events' run_all.sh), in order.  Stops at the first failure (exit 1).  With --prefreeze the freeze
# checks (verify here, t_freeze_and_guard's first and last checks in run_mock.py) are expected to fail and are skipped: used once, before
# run/freeze_p.sh freeze.
#   1. guard_p.sh          static checks of the scripts, the runner, the source, the blob and the tables
#   2. freeze verify         FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits (git show at FROZEN.pin)
#   3. tests/test_gen_r5.py  the tables and predictions are what the generator makes; the plan's numbers
#   4. tests/test_scorer.py  the scorer replayed on the kept round 3, 4 and 5 records (E855's b1p held, peek cannot tell; E823's b1 FAILED) and on
#                            worlds built from them
#   5. tests/run_mock.py     the whole session on a mock laptop (the argv-twin test, every hypothesis world, the stops, the refusals,
#                            the traps, the guard's refusals)
# PY: the scratch venv's python; RESGX545: the repo, read only (default /Users/jtorra/src/resgx545, main).
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PYTHON=$PY PY
export RESGX545=${RESGX545:-/Users/jtorra/src/resgx545}
PRE=0; [ "${1:-}" = "--prefreeze" ] && PRE=1
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
mkdir -p debug
step "guard_p.sh"; run/guard_p.sh || fail guard_p.sh
if [ $PRE = 0 ]; then step "freeze verify"; run/freeze_p.sh verify || fail "freeze verify"; fi
step "test_gen_r5.py"; "$PY" tests/test_gen_r5.py > debug/gen.out 2>&1 || { grep -v '^ok' debug/gen.out | tail -20; fail test_gen_r5.py; }
tail -1 debug/gen.out; echo "generator checks: $(grep -c '^ok' debug/gen.out)"
step "test_scorer.py"; MOCK_DIR=${TMPDIR:-/tmp} "$PY" tests/test_scorer.py > debug/scorer.out 2>&1 || { grep -v '^ok' debug/scorer.out | tail -20; fail test_scorer.py; }
tail -1 debug/scorer.out; echo "scorer checks: $(grep -c '^ok' debug/scorer.out)"
step "run_mock.py"
"$PY" -u tests/run_mock.py > debug/mock.out 2>&1; rc=$?
if [ $PRE = 1 ]; then
	# the only failures allowed before the freeze are the freeze checks themselves (the files verify, FROZEN.commits pins)
	nf=$(grep -a '^FAIL ' debug/mock.out | grep -avc '^FAIL the frozen files of this directory verify\|^FAIL FROZEN.commits pins')
	[ "$nf" = 0 ] && rc=0
fi
tail -2 debug/mock.out
[ $rc = 0 ] || { grep -a '^FAIL \|raised' debug/mock.out | head; fail run_mock.py; }
echo "mock checks: $(grep -c '^ok' debug/mock.out)"
echo "RUN_ALL PASSED"
