# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged one
sentence of our own notes (never the laptop's output): two lines of `PREFLIGHT.md` that named
the closed sources the preparation did not read. Under the user's standing decision of
2026-11-10 for the closing-pass sessions (publish everything, reword the guard hits), the
sentence was reworded to say that no closed source was read. Only wording changed. No logic, no
prediction, no assembled task and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `LAPTOP.sha256` too.
- `out/` (everything the laptop produced and the scorer printed then) is byte-identical.
- `PREFLIGHT.md` is not in the freeze, so `FROZEN.sha256` is unchanged;
  `FROZEN.pre-reword.sha256` is a copy of the freeze the run used (the lead's refreeze before
  the first job; the freeze before that is `FROZEN.pre-l3-refreeze.sha256`), byte-identical to
  `FROZEN.sha256`.
- The scorer, run on the kept stages after the rewording, prints output byte-identical to the
  kept `out/score-STAGE.txt` in 4 of 4 stages (h, c, e, d).
- The offline tests pass on a copy of this directory (`tests/run_all.sh`: RUN_ALL PASSED;
  run_mock.py 17 tests, 127 checks, 0 failed).
- The unreworded original stays in the scratch session directory the run used.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `PREFLIGHT.md` | 9d371a15090c3746 | 8e2135edeab99d88 | no |
