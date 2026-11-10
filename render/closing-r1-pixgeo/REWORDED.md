# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments, docstrings, the T7 table
description (the fine-grid steps are now "step indices"), a test label and the scorers' printed
status word (now `NODATA`). No logic, no prediction and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Regenerated with `gen/r1gen.py`, the tables, predictions and programs
  match the edited files byte for byte (TABLES.md rewraps the reworded sentence).
- `out/` (everything the laptop produced and the scorers printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` is the freeze as it stood before the run; `FROZEN.sha256` is the
  freeze regenerated after the rewording (`run/freeze_r1.sh freeze`).
- The reworded scorers, run on the kept stages, print the same `SUMMARY` line as the kept
  `out/score-STAGE.txt` in 10 of 10 (p-c2, g-u1, g-c1, g-c1f, g-t1, g-t2, g-t7, g-u2, g-t5, g-t6).
- The offline tests pass (`bash tests/run_all.sh`: ALL TESTS: PASS).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `gen/r1_geo.py` | 0f763a323c0f6258 | 2dfd7e844129924a | yes |
| `run/lib_r1.sh` | 59a9e01f818491ed | 451a16beb670714b | yes |
| `score/score_geo2.py` | d0902d7386a6cf81 | ba0c40bf82f5550c | yes |
| `score/score_q276.py` | a7828fa4ac6e4673 | 56549b5714a621d4 | yes |
| `tables/g-t7.txt` | 086e8b27a761c97f | 1be3f0bed73e0a88 | yes (comment line) |
| `TABLES.md` | 25f3eb62bd11731a | c56d415f2767d86e | yes |
| `tests/test_scorers_r1.py` | b68d5ac5a86eabab | c67fee605dadb858 | no |
| `FROZEN.sha256` | d78388582e8a99b0 | c34d7e3494ab7dce | (the freeze) |
