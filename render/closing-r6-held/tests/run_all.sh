#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh [--prefreeze]: every offline test of r6-held part H (and part P's own tests/run_all.sh), in order.  Stops at the first
# failure (exit 1).  --prefreeze skips the freeze verify (used once, before run/freeze_h.sh freeze).
#   1. guard_h.sh            the session's own static guard
#   2. freeze verify         FROZEN.sha256, PREDICTIONS.sha256
#   3. test_static.py        bash -n; every command word of the laptop runner exists (defined, builtin or on the laptop PATH)
#   4. test_gen.py           the generated files are current; the plan's numbers
#   5. test_twin.py          the argv twin (hand transcription of the plan rows; E848's jobs byte for byte)
#   6. test_replay.py        the scorer on E848's kept files (holds, and must fail)
#   7. run_mock.sh           the staged tree end to end on a fake laptop (worlds, stops, files, timing, guard injections)
#   8. p/tests/run_all.sh    part P (the 0x0694 peek at an EDM tick stop)
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PY
PRE=0; [ "${1:-}" = "--prefreeze" ] && PRE=1
mkdir -p debug
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
step guard_h.sh; run/guard_h.sh || fail guard_h.sh
if [ $PRE = 0 ]; then step "freeze verify"; run/freeze_h.sh verify || fail "freeze verify"; fi
for t in test_static.py test_gen.py test_twin.py test_replay.py; do
	step "$t"; "$PY" -B "tests/$t" > "debug/$t.out" 2>&1 || { grep -v '^ok' "debug/$t.out" | tail -20; fail "$t"; }
	tail -1 "debug/$t.out"
done
step run_mock.sh; bash tests/run_mock.sh > debug/mock.out 2>&1 || { grep '^FAIL' debug/mock.out | head -20; fail run_mock.sh; }
echo "mock checks: $(grep -c '^ok' debug/mock.out)"
if [ -x p/tests/run_all.sh ]; then
	step "part P: p/tests/run_all.sh"; bash p/tests/run_all.sh > debug/p.out 2>&1 || { tail -20 debug/p.out; fail "p/tests/run_all.sh"; }
	tail -1 debug/p.out
else
	fail "part P's p/tests/run_all.sh is missing"
fi
echo "RUN_ALL PASSED"
