#!/bin/bash
# tests/run_all.sh: every offline test of R2, in the order that needs the least: models, generated tables, templates, the
# vertex loop in sgx-sim, scorers, mock acceptance of every command, then the runner end to end.  Needs a current freeze for
# test_gen.py and run_mock.sh (run/freeze_r2.sh freeze after gen/r2gen.py).  Scratch files go under debug/tmp.  Exit 1 if any
# test failed.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$P/debug/tmp"
export TMPDIR="$P/debug/tmp"
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
fail=0
for t in test_models test_gen test_templates test_t5loop test_scorers_r2; do
	out=$("$PY" "$P/tests/$t.py" 2>&1); rc=$?
	echo "== $t: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
	echo "$out" | grep '^FAIL'
	[ $rc = 0 ] || fail=1
done
out=$(python3 "$P/tests/mock_all.py" 2>&1); rc=$?
echo "== mock_all: $(echo "$out" | grep -c 'commands accepted') stages, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep '^FAIL'
[ $rc = 0 ] || fail=1
out=$(bash "$P/tests/run_mock.sh" 2>&1); rc=$?
echo "== run_mock: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep '^FAIL'
[ $rc = 0 ] || fail=1
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
