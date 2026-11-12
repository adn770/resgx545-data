#!/bin/bash
# tests/run_all.sh: every offline test of R6-pixel, in the order that needs the least: the sim harness, the generated tables and the
# argv-twin check, the scorers replayed on R5's and R4's kept files (must hold / must fail), the stage scorers and programs on mock
# worlds (readback, predicate, L3, S; 1/w), mock acceptance of every command by the landed tool, then the runner, driver and staging
# end to end against the argv-driven fake tool, and the static guard.  Needs a current freeze (run/freeze_r6.sh freeze after gen/r6gen.py) for the last two and for the
# scorers' own freeze check.  Environment: PY (the scratch venv python), RESGX545_MAIN (default ~/src/resgx545), RESGX545_DATA (default
# ~/src/resgx545-data).  Exit 1 if any test failed.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PY
mkdir -p "$P/debug/tmp"
fail=0
for t in test_sim test_gen test_replay test_rd test_rw6; do
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
"$P/run/guard_r6.sh" > /dev/null 2>&1 && echo "== guard_r6: clean" || { echo "== guard_r6: FAIL"; fail=1; }
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
