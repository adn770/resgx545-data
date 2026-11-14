#!/bin/bash
# SPDX-License-Identifier: MIT
# tests/run_all.sh: every offline test of r19-dpm, in order; stops at the first failure.
#   1. the kit's static guard;  2. the session's own tests (tests/test_*.py: the generated tables,
#   the argv twin, the scorer replayed on kept records it must hold on and must fail on);
#   3. the mock: the staged tree on a fake laptop under env -i, every world of mock/world.py;
#   4. the freeze, once frozen (pins checked at their commits).
cd "$(dirname "$0")/.." || exit 1
# the repo's .venv has pytest and numpy, never a scratch one
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
[ -x "$PY" ] || PY=python3
"$PY" kit/session.py guard . || exit 1
for t in tests/test_*.py; do
	[ -f "$t" ] || continue
	"$PY" -m pytest -q -p no:cacheprovider "$t" || exit 1
done
"$PY" kit/session.py mock . || exit 1
if [ -f FROZEN.sha256 ]; then "$PY" kit/session.py verify . || exit 1; fi
echo "RUN_ALL PASSED"
