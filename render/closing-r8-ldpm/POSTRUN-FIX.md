# Scorer fix after the run (2026-11-13, the fold)

One bug of the frozen scorer `score/score.py`, found when the run's scores were read: stage k's five
calibrations (`tri ... -n K --geometry ...` at P 0x422) ended rc 1 with their `diff:` line, which
the runner took as a reading (`expectdiff`, class ok, as R7-dpm's multi-kick calibrations ended),
but the scorer's `readings` took a row as run only when `kitscore.completed` held (rc 0, or the rc
of an `expect:` outcome), so it read them as not completed and printed "cannot tell" for HU1's need
at all five (`out/20261113-021431/score-k.txt`: "k: HU1: cannot tell: no row decided").

- Fix: `completed(c, text)` in `score/score.py`: kitscore.completed, or a class ok row with the
  knob word `expectdiff` that ended rc 1 with a `diff:` line in its output. Nothing else changed.
- Tests, written first (`tests/test_score.py`, section "post-run fix"): a kept k calibration with
  rc 1 and its diff line is read (fails against the frozen scorer), and the same output without
  its diff line stays unread.
- `out/20261113-021431/score-STAGE.txt` is the frozen scorer's output as the run printed it, kept.
  `score-STAGE.fixed.txt` beside each is the fixed scorer's on the same kept stage: byte-identical
  in 6 of 7 stages; k's now reads "k: HU1: HU1 holds (10 of 10 rows decided)" (the five needs and
  their nparts 0); its explore tallies are unchanged.
- `score/score.as-run.py` is the scorer before the fix, byte for byte (its hash is the
  `score/score.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept `out/20261113-021431/score-STAGE.txt` in 7 of 7 stages.
- `FROZEN.pre-fix.sha256` is the freeze the run used (sha256 3d2ef2ec..., the driver's line).
  `FROZEN.sha256` differs from it only in the lines of `score/score.py` and `tests/test_score.py`
  and the new line of `score/score.as-run.py`, and in eight lines appended for the fold's files
  (FOLD.md, POSTRUN-FIX.md, FROZEN.pre-fix.sha256, run-r8l.log, postrun/misses.py and its .out,
  postrun/paths-as-frozen.txt and the pin list it names, which
  keep the freezes' absolute pins as frozen under tools/closing/session_tests.sh), so
  that the kit's verify and the session's own tests (`bash tests/run_all.sh`) pass on the
  published copy. `predictions/`, `PREDICTIONS.sha256` and every file
  of `out/` the run wrote are unchanged.
- The kit's `kitscore.completed` has the same gap (it does not count an `expectdiff` rc 1): a
  shared-tool change for the round's tooling agent, not made here.
