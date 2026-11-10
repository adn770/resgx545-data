# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged two lines
of our own session code (never the laptop's output): a docstring line of `gen/r3models.py` and a
function definition line of `tests/test_scorers_r3.py`. Under the user's standing decision of
2026-11-10 for the closing-pass sessions (publish everything, reword the guard hits), they were
reworded, and only wording changed: the docstring line now says "rounded down", and the test
helper and two of its names were renamed throughout that test file. No logic, no prediction, no
program and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256`,
  `TOOLSRC.sha256` and `.toolsrc.now` too.
- `out/` (everything the laptop produced and the scorers printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` is the freeze as it stood before the run; `FROZEN.sha256` is the
  freeze regenerated after the rewording (`run/freeze_r3.sh freeze`); the two differ in the line
  of `gen/r3models.py` only.
- The scorers, run on the kept stages after the rewording, print output byte-identical to the
  kept `out/score-STAGE.txt` in 9 of 9 stages.
- The offline tests pass on a copy of this directory (`bash tests/run_all.sh`: ALL TESTS: PASS;
  models 17, tables 137, templates 3, scorers 51, awk 4, mock 9 stages, runner 73).
- The unreworded originals stay in the scratch session directory the run used.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `gen/r3models.py` | 19b409566f12cd8e | 24d37cd146cf5aed | yes |
| `tests/test_scorers_r3.py` | 431e0ef13e4049a9 | ddd3d27e97f0c267 | no |
| `FROZEN.sha256` | 841358da233c5013 | 7fabb92b4d88de3f | (the freeze) |
