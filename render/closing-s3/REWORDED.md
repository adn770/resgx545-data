# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments, docstrings and the scorers'
printed status word (now `NODATA`); in the post hoc script `analysis/a4_model_dumpmasks.py` the
four sample offsets it read from msaa_model (resgx545-data texture/p1141/recompute) are now a
named local table with the same values. No logic, no prediction and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's.
- `out/` (everything the laptop produced and the scorers printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` is the freeze as it stood before the run; `FROZEN.sha256` is the
  freeze regenerated after the rewording (`run/freeze_s3.sh freeze`).
- The reworded scorer, run on the kept stages, prints the same `SUMMARY` line as the kept
  `score-STAGE.txt` in 3 of 3 (s3-e1-ctl, s3-e1, s3-xfer).
- The offline tests pass (`tests/test_scorers.py` 81 ok, `tests/run_mock.sh`).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `run/lib_s3.sh` | 67c38a7982459215 | 2a13a13dba508cc0 | yes |
| `score/s3lib.py` | b938bd2247564d3e | 5ead682f4dac3671 | yes |
| `score/score_s3.py` | 72ce7e5fd9c209fd | afc64e6cc49e8dad | yes |
| `PREFLIGHT.md` | b92947d4fa5d58ec | 1c239a29306c00d1 | no |
| `tests/test_scorers.py` | 9f6ea773d9a89a1e | 958db271f8b0a468 | no |
| `analysis/a4_model_dumpmasks.py` | 900fef5defde5788 | 07676a3a9bd2a93e | no |
| `FROZEN.sha256` | f05507765733cc7d | b8bc0bbc34c1a76e | (the freeze) |
