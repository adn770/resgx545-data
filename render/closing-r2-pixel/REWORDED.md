# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments, docstrings, a test label and
the scorers' printed status word (now `NODATA`). No logic, no prediction and no laptop data
changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's. Regenerated with
  `gen/r2gen.py`, the tables, predictions and the variant program match byte for byte.
- `out/` (everything the laptop produced and the scorers printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` is the freeze as it stood before the run; `FROZEN.sha256` is the
  freeze regenerated after the rewording (`run/freeze_r2.sh freeze`).
- The reworded scorers, run on the kept attempt `out/20261110-105258`, print the same `SUMMARY`
  line as the kept score files in 4 of 4 stages (r2-d-safe, r2-d-fault, r2-a-safe, r2-a-fault)
  and the same verdict lines (verdict.txt).
- The offline tests pass (`bash tests/run_all.sh`: ALL TESTS: PASS).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `run/lib_r2.sh` | 1eedfe1647166cbe | a32ff64a931ce388 | yes |
| `score/r2lib.py` | a165ecc0b1ded3e0 | f973007ab4a7cb8e | yes |
| `score/score_r2.py` | 742945dd55f7ce83 | 4284d8f01bcfdc5b | yes |
| `PREFLIGHT.md` | 5e314f514d9c5ae9 | ec28650133721018 | no |
| `tests/test_scorers_r2.py` | 8325ae72a50e0822 | 02c957a8adc4e566 | no |
| `FROZEN.sha256` | a10173fee22715a9 | 87705cbc68e29d6e | (the freeze) |
