#!/bin/bash
# tests/run_all.sh: every offline test of r6-misc: the generated tables and predictions against the plan's offline outputs and the
# kept records (test_gen), the argv-twin test (test_twin), the scorers on argv-driven worlds (test_scorers), the scorers replayed on
# kept records they must hold on and must fail on (test_replay), mock acceptance of every command by its own tool's mock with the
# tool-column check (mock_all), then the runner and driver end to end against the argv-driven fake (run_mock), the guard and the
# freeze.  The freeze is verified with the fake t6 hash in run_mock's copies; here the session itself must verify as frozen (the
# TOOL6.sha256 slot is the lead's: `run/freeze_m.sh verify` needs it, so this checks FROZEN and PREDICTIONS only until then).
# Exit 1 if any test failed.  Takes about 5 minutes.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
case "$PY" in /*) ;; *) echo "PY must be absolute"; exit 2 ;; esac
export PY
fail=0
for t in test_gen test_twin test_scorers test_replay mock_all; do
	out=$("$PY" "$P/tests/$t.py" 2>&1); rc=$?
	echo "== $t: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
	echo "$out" | grep -E '^FAIL|Error|Traceback' | head -20
	[ $rc = 0 ] || fail=1
done
out=$(bash "$P/tests/run_mock.sh" 2>&1); rc=$?
echo "== run_mock: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep -E '^FAIL' | head -30
[ $rc = 0 ] || fail=1
"$P/run/guard_m.sh" > /dev/null 2>&1 && echo "== guard_m: clean" || { echo "== guard_m: FAIL"; fail=1; }
# the frozen files (everything but the t6 slot): the same check verify makes, without the hash the lead has not written yet
(cd "$P" && shasum -a 256 -c FROZEN.sha256 --quiet && shasum -a 256 -c PREDICTIONS.sha256 --quiet) > /dev/null 2>&1 \
	&& echo "== freeze: FROZEN.sha256 and PREDICTIONS.sha256 verified ($(cut -d' ' -f1 "$P/TOOL6.sha256" | cut -c1-12)... in TOOL6.sha256)" \
	|| { echo "== freeze: FAIL (FROZEN FILES CHANGED)"; fail=1; }
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
