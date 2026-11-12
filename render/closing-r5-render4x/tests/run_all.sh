#!/bin/bash
# tests/run_all.sh: every offline test of r5-render4x: the generated tables and predictions against the plan and the kept records
# (test_gen), the argv-twin test (test_twin), the scorer on argv-driven worlds (test_scorers_r), the fixed scorers replayed on round 4's
# kept files (test_replay), mock acceptance of every command by the rgn4 tool with the scene check (mock_all), then the runner and
# driver end to end against the argv-driven fake (run_mock) and the guard.  Needs a current freeze (run/freeze_k.sh freeze).  Exit 1 if
# any test failed.  Takes a few minutes.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
case "$PY" in /*) ;; *) echo "PY must be absolute"; exit 2 ;; esac
export PY
fail=0
for t in test_gen test_twin test_scorers_r test_replay; do
	out=$("$PY" "$P/tests/$t.py" 2>&1); rc=$?
	echo "== $t: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
	echo "$out" | grep -E '^FAIL|Error|Traceback' | head -20
	[ $rc = 0 ] || fail=1
done
out=$("$PY" "$P/tests/mock_all.py" 2>&1); rc=$?
echo "== mock_all: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep -E '^FAIL|Error' | head
[ $rc = 0 ] || fail=1
out=$(bash "$P/tests/run_mock.sh" 2>&1); rc=$?
echo "== run_mock: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep -E '^FAIL' | head -30
[ $rc = 0 ] || fail=1
"$P/run/guard_k.sh" > /dev/null 2>&1 && echo "== guard_k: clean" || { echo "== guard_k: FAIL"; fail=1; }
"$P/run/freeze_k.sh" verify > /dev/null 2>&1 && echo "== freeze: verified" || { echo "== freeze: FAIL (FROZEN FILES CHANGED)"; fail=1; }
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
