#!/bin/bash
# tests/run_all.sh: every offline test of r7-geo: the generated tables, predictions and programs (test_gen), the argv-twin test
# (test_twin), the scorers on argv-driven worlds (test_scorers), the scorers replayed on kept records they must hold on and must
# fail on (test_replay), mock acceptance of every command by its own tool's mock (mock_all), then the runner and driver end to end
# against the argv-driven fake, with sessioncheck.py staged, envi and kept on the mock output (run_mock), the guard and the freeze.
# Builds the pinned assembler and disassembler first (git archive of resgx545 1c64f3a tools/usse-asm, usse-dis, sweep into
# debug/asm) when missing.  Exit 1 if any test failed.  Takes about 15 minutes.
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
case "$PY" in /*) ;; *) echo "PY must be absolute"; exit 2 ;; esac
export PY
if [ ! -x "$P/debug/asm/tools/usse-asm/usse-asm" ] || [ ! -x "$P/debug/asm/tools/usse-dis/usse-dis" ]; then
	mkdir -p "$P/debug/asm"
	git -C /Users/jtorra/src/resgx545 archive 1c64f3a tools/usse-asm tools/usse-dis tools/sweep | tar -x -C "$P/debug/asm" \
		&& make -s -C "$P/debug/asm/tools/usse-asm" && make -s -C "$P/debug/asm/tools/usse-dis" || { echo "building the pinned assembler failed"; exit 1; }
fi
fail=0
for t in test_gen test_twin test_scorers test_replay mock_all; do
	out=$("$PY" -B "$P/tests/$t.py" 2>&1); rc=$?
	echo "== $t: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
	echo "$out" | grep -E '^FAIL|Error|Traceback' | head -20
	[ $rc = 0 ] || fail=1
done
out=$(bash "$P/tests/run_mock.sh" 2>&1); rc=$?
echo "== run_mock: $(echo "$out" | grep -c '^ok') ok, $(echo "$out" | grep -c '^FAIL') FAIL (rc $rc)"
echo "$out" | grep -E '^FAIL' | head -30
[ $rc = 0 ] || fail=1
"$P/run/guard_g.sh" > /dev/null 2>&1 && echo "== guard_g: clean" || { echo "== guard_g: FAIL"; fail=1; }
"$P/run/freeze_g.sh" verify > /dev/null 2>&1 && echo "== freeze: FROZEN.sha256 and PREDICTIONS.sha256 verified" || { echo "== freeze: FAIL (FROZEN FILES CHANGED)"; fail=1; }
echo "ALL TESTS: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
