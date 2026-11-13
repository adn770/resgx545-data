#!/bin/bash
# SPDX-License-Identifier: MIT
# tests/run_all.sh: every offline test of r9-k1, in order; stops at the first failure.
#   0. debug/asm: usse-asm and pds-asm built from `git archive` of the pinned resgx545 commit (once;
#      test_gen.py regenerates bins/ with them);
#   1. the kit's static guard;  2. the session's own tests (tests/test_*.py: the generator current
#   and pinned, the argv twin and the library-mock replay, the scorer on kept records it must hold
#   on and must fail on);  3. the mock: every row through t9's library mock with its knob words,
#   then the staged tree on a fake laptop under env -i, every world of mock/world.py;
#   4. the freeze, once frozen (pins at their commits).
cd "$(dirname "$0")/.." || exit 1
# the repo's .venv has pytest and numpy, never a scratch one
PY=${PY:-$HOME/src/resgx545/.venv/bin/python}
[ -x "$PY" ] || PY=python3
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
if [ ! -x debug/asm/tools/usse-asm/usse-asm ] || [ ! -x debug/asm/tools/usse-asm/pds-asm ]; then
	rev=$("$PY" -c 'import tomllib; print(tomllib.load(open("session.toml", "rb"))["freeze"]["resgx545"])') || exit 1
	rm -rf debug/asm && mkdir -p debug/asm || exit 1
	git -C "$MAIN" archive "$rev" tools/usse-asm tools/usse-dis | tar -x -C debug/asm || exit 1
	make -s -C debug/asm/tools/usse-asm usse-asm pds-asm >/dev/null || exit 1
fi
"$PY" kit/session.py guard . || exit 1
for t in tests/test_*.py; do
	[ -f "$t" ] || continue
	"$PY" -B -m pytest -q -p no:cacheprovider "$t" || exit 1
done
"$PY" -B kit/session.py mock . || exit 1
if [ -f FROZEN.sha256 ]; then "$PY" kit/session.py verify . || exit 1; fi
echo "RUN_ALL PASSED"
