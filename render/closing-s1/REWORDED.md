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
  the kept `out/score-STAGE.txt` in 14 of 14 stages.
- The offline tests pass (`tests/test_scorers.py`, `tests/emit_checks.py`, `tests/run_mock.sh`).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `gen/s1geo3.py` | 63c6c719717117cf | 47986a25ac8bcba2 | yes |
| `run/lib_s1.sh` | 01cc3c0680f0e9ea | 20ea52909a01c64e | yes |
| `score/score_geo.py` | 91684ccd2efbc4df | 6c135e70c32401cd | yes |
| `score/score_pix.py` | 29094a9c90cef81a | 86433c5ab9dc1b89 | yes |
| `TABLES.md` | ff54c7a4c7b24a11 | 225915feba405050 | yes |
| `PREFLIGHT.md` | 8280d2d71a93fd25 | aad5f75ed0e2a18e | no |
| `tests/run_mock.sh` | bef64420835da36b | d2041d9ec510f870 | no |
| `FROZEN.sha256` | 3bd6bc6de772707d | 45f489634672ae78 | (the freeze) |

Every change replaces one line by one line, so line numbers cited elsewhere still hold.
