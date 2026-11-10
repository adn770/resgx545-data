# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments, docstrings, table
descriptions and the scorers' printed status word (now `NODATA`). No logic, no prediction and no
laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's.
- `out/` (everything the laptop produced and the scorers printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` is the freeze as it stood before the run; `FROZEN.sha256` is the
  freeze regenerated after the rewording (`run/freeze_s1.sh freeze`).
- The reworded scorers, run on the kept `out/` of every stage, print the same `SUMMARY` line as
  the kept `out/score-STAGE.txt` in 9 of 9 stages.
- The offline tests pass (`tests/test_fixes.py`, `tests/test_review.py`,
  `tests/test_s1b_scorers.py`, `tests/test_scorers.py`, `tests/emit_checks.py`,
  `tests/run_mock.sh`).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `gen/s1geo3.py` | 63c6c719717117cf | 47986a25ac8bcba2 | yes |
| `run/lib_s1.sh` | 85d06b8be1a226a3 | 9bffb6457cebe7bb | yes |
| `score/score_geo.py` | ee59b6a92fd2cd8e | 115c81ca51059ad4 | yes |
| `score/score_pix.py` | 9adfd40f9a33bb87 | 69fe20904c1eaa6e | yes |
| `tests/run_mock.sh` | fbd781492b7fcf03 | fd8a222614464e87 | no |
| `FROZEN.sha256` | 23e36858e0cea99c | 04b65f63ce438412 | (the freeze) |

Every change replaces one line by one line, so line numbers cited elsewhere still hold.
