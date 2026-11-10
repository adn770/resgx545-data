#!/bin/bash
# SPDX-License-Identifier: MIT
# run_all.sh: every offline test of C3 (the freeze is made only when this passes). Exit 0 when all four pass.
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-../../closing/pixel-faults/.venv/bin/python}
st=0
for t in tests/sim_c3.py tests/test_scorer.py tests/test_guard.py tests/run_mock.py; do
	echo "=== $t"
	out=$("$PY" "$t" 2>&1)
	rc=$?
	printf '%s\n' "$out" | tail -3
	nok=$(printf '%s\n' "$out" | grep -c '^ok ')
	nfail=$(printf '%s\n' "$out" | grep -c '^FAIL ')
	echo "    $t: rc $rc, $nok ok, $nfail FAIL"
	[ $rc = 0 ] || st=1
done
run/guard_c3.sh || st=1
[ $st = 0 ] && echo "run_all: all passed" || echo "run_all: FAILED"
exit $st
