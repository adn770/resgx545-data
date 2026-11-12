#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh [--prefreeze]: every offline test of r7-faults, in order.  Stops at the first failure (exit 1).  --prefreeze skips the
# freeze verify (used once, before run/freeze_f.sh freeze).
#   1. guard_f.sh            the session's own static guard
#   2. freeze verify         FROZEN.sha256, PREDICTIONS.sha256
#   3. test_static.py        bash -n; every command word of the laptop runner exists (defined, builtin or on the laptop PATH)
#   4. test_gen.py           the generated files and programs are current; the plan's numbers; the layout against the kept pages;
#                            every control readable from its row (scorekit.refuse_unreadable)
#   5. test_twin.py          the argv twin (hand transcription of the plan rows; E848's jobs byte for byte; the programs' locks)
#   6. test_replay.py        the scorer on kept files (r6-held, E826, E088): holds, and must fail
#   7. run_mock.sh           the staged tree end to end on a fake laptop (worlds, stops, files, timing, sessioncheck staged and
#                            envi, guard injections)
#   8. sessioncheck          staged (the runner files stage_f.sh copies), envi (inside run_mock.sh), and kept on the mock's kept
#                            output of the model world (every stage, --call files_for)
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PY
PRE=0; [ "${1:-}" = "--prefreeze" ] && PRE=1
mkdir -p debug
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
step guard_f.sh; run/guard_f.sh || fail guard_f.sh
if [ $PRE = 0 ]; then step "freeze verify"; run/freeze_f.sh verify || fail "freeze verify"; fi
for t in test_static.py test_gen.py test_twin.py test_replay.py; do
	step "$t"; "$PY" -B "tests/$t" > "debug/$t.out" 2>&1 || { grep -v '^ok' "debug/$t.out" | tail -20; fail "$t"; }
	tail -1 "debug/$t.out"
done
step run_mock.sh; bash tests/run_mock.sh > debug/mock.out 2>&1 || { grep '^FAIL' debug/mock.out | head -20; fail run_mock.sh; }
echo "mock checks: $(grep -c '^ok' debug/mock.out)"
step "sessioncheck staged"
"$PY" -B score/sessioncheck.py staged run $(sed -n 's/^RFILES="\(.*\)"$/\1/p' run/stage_f.sh | sed 's#run/##g') || fail "sessioncheck staged"
step "sessioncheck envi"; grep -q '^ok   sessioncheck envi' debug/mock.out && grep '^ok   sessioncheck envi' debug/mock.out | cut -c1-120 || fail "sessioncheck envi"
step "sessioncheck kept (the mock's model world)"
for st in s0 l d m; do
	"$PY" -B score/sessioncheck.py kept score/score_f.py "$st" "debug/mock-kept/$st" --call files_for || fail "sessioncheck kept $st"
done
echo "RUN_ALL PASSED"
