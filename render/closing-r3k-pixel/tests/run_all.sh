#!/bin/bash
# tests/run_all.sh: every offline test of R3K-pixel, in the order that needs the least: the generated tables, the scorers (round 2's
# kept fault data and synthetic worlds), mock acceptance of every command by the landed tool, then the runner, driver and staging end
# to end against the fakes.  Needs a current freeze (run/freeze_k.sh freeze after gen/kgen.py).  Exit 1 if any test failed.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PY
fail=0
for t in test_gen test_scorers_k; do
	out=$("$PY" "$P/tests/$t.py" 2>&1); rc=$?
	echo "== $t: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
	echo "$out" | grep '^FAIL'
	[ $rc = 0 ] || fail=1
done
out=$(python3 "$P/tests/mock_all.py" 2>&1); rc=$?
echo "== mock_all: $(echo "$out" | grep -c '^ok') commands accepted, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep '^FAIL'
[ $rc = 0 ] || fail=1
out=$(bash "$P/tests/run_mock.sh" 2>&1); rc=$?
echo "== run_mock: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep '^FAIL'
[ $rc = 0 ] || fail=1
"$P/run/guard_k.sh" > /dev/null 2>&1 && echo "== guard_k: clean" || { echo "== guard_k: FAIL"; fail=1; }
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
