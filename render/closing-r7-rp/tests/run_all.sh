#!/bin/bash
# tests/run_all.sh: every r7-rp offline test; exit 0 when all pass.  Needs a current freeze (run/freeze_r7.sh freeze).
#   1. the freeze verifies with a hash in the slot's place (the predictions, tables and programs are the frozen ones), and the
#      generators reproduce them byte for byte (gen/r7gen.py into the tree, then verify again);
#   2. score/scorekit.py and score/sessioncheck.py are main's tools/closing/ files byte for byte;
#   3. the session's static guard;
#   4. each area's tests (argv twins, the real tools' mocks, replays on the precedents' kept files, doctored controls, worlds,
#      refuse_unreadable): test_q287.py (s0, q287), test_q291.py and test_sim_q291.py (q291g, q291), test_rd7.py (p7-rdc, p7-rd),
#      test_dump.py (q293, q139), test_q086.py (q086);
#   5. tests/run_mock.sh: the staged tree end to end under env -i (sessioncheck staged, envi and kept on the mock output).
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export PY PYTHONDONTWRITEBYTECODE=1
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
fail=0
step() { local nm=$1; shift; if "$@"; then echo "PASS $nm"; else echo "FAIL $nm"; fail=1; fi; }
frozen_ok() { # the frozen files and predictions unchanged (any t7 hash: TOOL7.sha256 is the slot or the lead's; only the files count)
	(cd "$P" && shasum -a 256 -c FROZEN.sha256 --quiet && shasum -a 256 -c PREDICTIONS.sha256 --quiet); }
regen() { (cd "$P" && "$PY" gen/r7gen.py > debug/r7gen.out 2>&1) || { cat "$P/debug/r7gen.out"; return 1; }; frozen_ok; }
same() { cmp -s "$P/score/scorekit.py" "$MAIN/tools/closing/scorekit.py" && cmp -s "$P/score/sessioncheck.py" "$MAIN/tools/closing/sessioncheck.py"; }
step "the freeze verifies" frozen_ok
step "the generators reproduce the frozen tables, predictions and programs" regen
step "scorekit.py and sessioncheck.py are main's byte for byte" same
step "guard" "$P/run/guard_r7.sh"
for t in test_q287.py test_q291.py test_sim_q291.py test_rd7.py test_dump.py test_q086.py; do
	step "$t" bash -c "cd '$P' && '$PY' tests/$t > debug/$t.out 2>&1 || { grep -E '^FAIL' debug/$t.out | head -10; exit 1; }"
done
step "run_mock" bash -c "'$P/tests/run_mock.sh' > '$P/debug/run_mock.out' 2>&1 || { grep -E '^FAIL' '$P/debug/run_mock.out' | head -20; exit 1; }"
[ $fail = 0 ] && echo "run_all: ALL PASS" || echo "run_all: FAILURES"
exit $fail
