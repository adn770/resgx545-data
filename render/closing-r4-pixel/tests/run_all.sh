#!/bin/bash
# tests/run_all.sh: every offline test of R4-pixel, in the order that needs the least: the timeline reader and rules on the kept records of
# round 3, the loop programs in the simulator, the generated tables, the stage scorers on synthetic worlds (Q082, o4, w table), mock acceptance
# of every command by the landed tool, then the runner, driver and staging end to end.  Needs a current freeze (run/freeze_r4.sh freeze after
# gen/r4gen.py) for the last two and for the scorers' own freeze check.  Environment: PY (the scratch venv python), RESGX545_MAIN (the
# resgx545 tree at the pinned commit 5a13042: the landed tool, probe.py, pbdump.py, the templates, sgx-pipe's events.rs; default
# ~/src/resgx545), RESGX545_DATA (default ~/src/resgx545-data).  Exit 1 if any test failed.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PY
fail=0
for t in test_tl test_loops test_gen test_q082 test_o4 test_rw; do
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
"$P/run/guard_r4.sh" > /dev/null 2>&1 && echo "== guard_r4: clean" || { echo "== guard_r4: FAIL"; fail=1; }
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
