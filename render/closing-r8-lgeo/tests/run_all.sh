#!/bin/bash
# SPDX-License-Identifier: MIT
# tests/run_all.sh: every offline test of r8-lgeo, in order; stops at the first failure.
#   0. debug/asm: usse-asm and usse-dis built from `git archive` of the pinned resgx545 commit (once;
#      test_gen.py regenerates the programs with it and disassembles them);
#   1. the kit's static guard;  2. the session's own tests (tests/test_*.py: the generator current
#   and pinned, the models on published data, the argv twin, the scorer replayed on kept records it
#   must hold on and must fail on);  3. the mock: the staged tree on a fake laptop under env -i,
#   every world of mock/world.py (about 8 minutes);  4. the freeze, once frozen (pins at their
#   commits).
# PY: a python3 >= 3.11 with pytest (default: the resgx545 venv's).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-/Users/jtorra/src/resgx545/.venv/bin/python}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
if [ ! -x debug/asm/tools/usse-asm/usse-asm ] || [ ! -x debug/asm/tools/usse-dis/usse-dis ]; then
	rev=$("$PY" -c 'import tomllib; print(tomllib.load(open("session.toml", "rb"))["freeze"]["resgx545"])') || exit 1
	rm -rf debug/asm && mkdir -p debug/asm || exit 1
	git -C "$MAIN" archive "$rev" tools/usse-asm tools/usse-dis | tar -x -C debug/asm || exit 1
	make -s -C debug/asm/tools/usse-asm usse-asm >/dev/null || exit 1
	make -s -C debug/asm/tools/usse-dis usse-dis >/dev/null || exit 1
fi
"$PY" kit/session.py guard . || exit 1
for t in tests/test_*.py; do
	[ -f "$t" ] || continue
	"$PY" -B -m pytest -q -p no:cacheprovider "$t" || exit 1
done
"$PY" -B kit/session.py mock . || exit 1
if [ -f FROZEN.sha256 ]; then "$PY" kit/session.py verify . || exit 1; fi
echo "RUN_ALL PASSED"
