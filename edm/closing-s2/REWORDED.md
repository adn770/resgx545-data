# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments and docstrings, the scorer's
printed status word (now `NODATA`), the runner's name for the stop class of a tool that gives no
answer (now `no-answer`; no record of this session carries it) and two sentences of README.md and
PREFLIGHT.md about the slot filter. No logic, no prediction and no laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's.
- `out/` (everything the laptop produced and the scorer printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` and `LAPTOP.pre-reword.sha256` are the hash files as they stood
  before the run; `FROZEN.sha256` and `LAPTOP.sha256` are regenerated after the rewording
  (`run/freeze_s2.sh freeze`). LAPTOP.sha256 changes because it covers the runner as laid out on
  the laptop.
- The reworded scorer, run on the kept stages, prints the same `SUMMARY` line as the kept
  `out/score-STAGE.txt` for e1c, e1j, e2r, e2w, e4c, e4h, e4l and e5c (8 of 8). The kept
  `out/score-e1c.run2.txt` cannot be rescored with the session's tables as they stand: its run
  used the e1c table that run 3 replaced, and the scorer refuses data whose table hash differs
  (it did so before the rewording too).
- The offline tests pass (`tests/test_scorer.py`, `tests/sim_s2.py`, `tests/run_mock.py` 28 of
  28).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `run/guard_py.py` | 167acf98242fb2f3 | 7f9c4654ca058994 | yes |
| `run/guard_s2.sh` | 88b3e0e64d5db378 | 37f5180ac8004a17 | yes |
| `run/s2_run.py` | bfc58e827b2891da | dcd95be45e82be4b | yes |
| `score/score_s2.py` | 0de79beabfa8ea20 | 265fae1ea4328cc0 | yes |
| `PREFLIGHT.md` | 04133d917a9a45fc | f5e57fb4ac4ca557 | no |
| `README.md` | 69cc101c2fb7bbbd | 27f219a90c89aaad | no |
| `tests/run_mock.py` | e061491fc0df402d | 7ad8552002125518 | no |
| `tests/test_scorer.py` | 0398976126adb6de | 7d53d4bcc751bece | no |
| `FROZEN.sha256` | 6873e29665afb5b0 | cbbdc353673384a9 | (hash file) |
| `LAPTOP.sha256` | 3312ac861cae8df9 | 45a32b55f8d0a4b3 | (hash file) |
