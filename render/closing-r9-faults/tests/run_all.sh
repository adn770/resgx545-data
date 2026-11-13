#!/bin/bash
# SPDX-License-Identifier: MIT
# tests/run_all.sh: every offline test of r9-faults, in order; stops at the first failure.
#   0. debug/libmock: the tool's source (TOOLSRC.sha256: the commit and the sha256 of
#      sgxfive-test.c, the source of the laptop's ~/sgxfive-test-rgn4) built against libsgxfive's
#      in-process mock from `git archive` of that commit, the source hash checked first (once);
#      mock/world.py and tests/test_twin.py replay every row through it;
#   1. the kit's static guard;  2. the session's own tests (tests/test_*.py: the generator
#   current, the argv twin and the library-mock replay of every row, the scorer on kept records
#   it must hold on and must fail on, the hardware controls);  3. the mock: the staged tree on a
#   fake laptop under env -i, every world of mock/world.py;  4. the freeze, once frozen.
# PY: a python3 >= 3.11 with pytest (default: the resgx545 venv's).
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-/Users/jtorra/src/resgx545/.venv/bin/python}
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
if [ ! -x debug/libmock/sgxfive-test ]; then
	read -r want spec < TOOLSRC.sha256 || exit 1
	rev=${spec%%:*}; src=${spec#*:}
	got=$(git -C "$MAIN" show "$rev:$src" | shasum -a 256 | cut -d' ' -f1)
	[ "$got" = "$want" ] || { echo "$rev:$src is $got, not $want"; exit 1; }
	rm -rf debug/libmock && mkdir -p debug/libmock/src || exit 1
	git -C "$MAIN" archive "$rev" userspace/libsgxfive include/uapi | tar -x -C debug/libmock/src || exit 1
	make -s -C debug/libmock/src/userspace/libsgxfive build/sgxfive-test >/dev/null || exit 1
	cp debug/libmock/src/userspace/libsgxfive/build/sgxfive-test debug/libmock/sgxfive-test || exit 1
fi
"$PY" kit/session.py guard . || exit 1
for t in tests/test_*.py; do
	[ -f "$t" ] || continue
	"$PY" -B -m pytest -q -p no:cacheprovider "$t" || exit 1
done
"$PY" -B kit/session.py mock . || exit 1
if [ -f FROZEN.sha256 ]; then "$PY" kit/session.py verify . || exit 1; fi
echo "RUN_ALL PASSED"
