#!/bin/bash
# tests/run_all.sh: every offline test of R7-dpm, in order; stops at the first failure (exit 1).  Needs current freezes of both sets
# (gen/r7plan.py, gen/gen_oomring2.py, then run/freeze_r7.sh freeze AB): the runner mock compares its tables with FROZEN*.sha256.
#   1. guard_r7.sh        the session's static guard (runner, tables, oomring2.blob; the staged sessioncheck.py and scorekit.py are
#                         the landed files byte for byte)
#   2. freeze verify      FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits (set A) and the -B files (set B)
#   3. test_gen.py        tables and predictions = the generator's; the frozen constants = the frozen offline rules now (about five
#                         minutes: the scene search); the ARGV TWIN against the plan's rows and R6-dpm's kept commands
#   4. test_read.py       the one reader on real records (R3-geo's dpm3, E852's steps, the 21 grows, F1's brackets, F7's peaks,
#                         KEPT_2X4, H-WALK64 on the kept u-2048 dump, the ring of R6's kept pages)
#   5. test_controls.py   every control readable and able to fail on REAL kept jobs (R6-dpm's r-a0 and r-k); planted copies FAIL or
#                         read NO READING with a premise STOP; G8 (R6-dpm's attempt through this gate); the generator's refusal
#   6. test_scorer.py     the scorer on R6-dpm's kept r-m cells (H-SPAN held, E874-B failed), R5-dpm's d-a0, a planted cell, the
#                         creep cell's scene check against the kept 2048x4096 steps
#   7. test_oomring.py    oomring2: the landed verifier accepts, the OLD list refuses; the host builds of the forks' verifiers: 664fd0d0
#                         (module 37EC97AB) accepts, 3f0b3e74 (module 41E2F5C7, loaded now) refuses; sgx-sim with the page counts
#   8. mock_all.py        every command against the rgn4 tool's own --mock (the new sizes and tri targets echoed)
#   9. test_staged.sh     sessioncheck.py STAGED on stage_r7.sh's list (and FAILS R6's a1 tree and every list with a file left out);
#                         sessioncheck.py ENVI: s-a0 from the staged tree under env -i
#  10. run_mock.sh        the staged runner end to end on argv-answering fake worlds, both sets; sessioncheck.py KEPT on the mock
#                         output of every stage (score_r7.py's REQUIRED, no undeclared file read); the stops; the guard's refusals
# PY: the scratch venv (numpy-free); RESGX545_MAIN the landed tree (read only); RESGX545_LINUX the fork home (read only).
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
export PY=${PY:-/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
export RESGX545_MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545} RESGX545_LINUX=${RESGX545_LINUX:-/Volumes/linux/linux-sgx}
mkdir -p debug/tmp
export TMPDIR=$PWD/debug/tmp
step() { echo "=== $*"; }
fail() { echo "RUN_ALL FAILED at: $*"; exit 1; }
step "guard_r7.sh"; bash run/guard_r7.sh || fail guard_r7.sh
step "freeze verify"; bash run/freeze_r7.sh verify AB || fail "freeze verify"
for t in test_gen test_read test_controls test_scorer test_oomring mock_all; do
	step "$t.py"
	"$PY" "tests/$t.py" > "debug/$t.out" 2>&1; rc=$?
	echo "$(grep -c '^ok' "debug/$t.out") ok, $(grep -c '^FAIL' "debug/$t.out") FAIL (rc $rc)"
	[ $rc = 0 ] || { grep '^FAIL' "debug/$t.out" | head; tail -3 "debug/$t.out"; fail "$t.py"; }
done
for t in test_staged run_mock; do
	step "$t.sh"
	bash "tests/$t.sh" > "debug/$t.out" 2>&1; rc=$?
	echo "$(grep -c '^ok' "debug/$t.out") ok, $(grep -c '^FAIL' "debug/$t.out") FAIL (rc $rc)"
	[ $rc = 0 ] || { grep '^FAIL' "debug/$t.out" | head; fail "$t.sh"; }
done
grep -q "sessioncheck staged: ok" debug/test_staged.out && grep -q "sessioncheck envi: s-a0" debug/test_staged.out \
	&& [ "$(grep -c '^ok   sessioncheck kept s-' debug/run_mock.out)" = 5 ] || fail "sessioncheck staged + envi + kept (5 stages) not all seen"
echo "RUN_ALL PASSED"
