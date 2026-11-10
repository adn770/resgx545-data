# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments, docstrings, the T7 table
description shared with R1-pixgeo, a comment line of the C3 table and the scorers' printed
status word (now `NODATA`). No logic, no prediction and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Regenerated with `gen/r2gen.py`, the tables, predictions and programs
  match the edited files byte for byte (TABLES.md rewraps the reworded sentence).
- `out/` (everything the laptop produced and the scorers printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` is the freeze as it stood before the run; `FROZEN.sha256` is the
  freeze regenerated after the rewording (`run/freeze_r2.sh freeze`).
- The reworded scorers, run on the kept stages, print the same `SUMMARY` line as the kept
  `out/score-STAGE.txt` in 5 of 5 (g-t3, g-t4, g-t5v, g-c3, g-c2).
- The offline tests pass (`bash tests/run_all.sh`: ALL TESTS: PASS).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `gen/r1_geo.py` | 0f763a323c0f6258 | 2dfd7e844129924a | yes |
| `gen/r2_geo.py` | a99aee174f962b4f | 70db678c9ad10af8 | yes |
| `run/lib_r2.sh` | 52073ab635d87529 | 8cf120e10c5241db | yes |
| `score/score_geo2.py` | d0902d7386a6cf81 | ba0c40bf82f5550c | yes |
| `score/score_r2.py` | 275c1acb564f4b61 | 6667ad144a7d0c40 | yes |
| `tables/g-c3.txt` | e74c2ce1a0ed99f3 | 4fcf11e6a9e30ecb | yes (comment line) |
| `TABLES.md` | df9cd067fc4d53b8 | 36981e4e876c8f94 | yes |
| `PREFLIGHT.md` | 57b4983d52cde001 | 6df27459048822b0 | no |
| `tests/run_mock.sh` | a2088cd01124ff7c | 7404307fc833d0e4 | no |
| `tests/test_scorers_r2.py` | 285d24ac97d6c80f | 531001e27545a3a4 | no |
| `FROZEN.sha256` | 1b06e1c8562d7246 | 39b716ab899ce78b | (the freeze) |
