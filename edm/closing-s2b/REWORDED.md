# Reworded after the run (2026-11-10)

Before publishing this session in resgx545-data, the project's clean-room guard flagged words in
our own session code and notes (never in the laptop's output). On the user's decision of
2026-11-10 they were reworded, and only wording changed: comments and docstrings, the scorer's
printed status word (now `NODATA`) and the runner's name for the stop class of a tool that gives
no answer (now `no-answer`; no record of this session carries it). No logic, no prediction and no
laptop data changed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's.
- `out/` (everything the laptop produced and the scorer printed then) is byte-identical.
- `FROZEN.pre-reword.sha256` and `LAPTOP.pre-reword.sha256` are the hash files as they stood
  before the run; `FROZEN.sha256` and `LAPTOP.sha256` are regenerated after the rewording
  (`run/freeze_s2.sh freeze`). LAPTOP.sha256 changes because it covers the runner as laid out on
  the laptop.
- The reworded scorer, run on the kept stages, prints the same `SUMMARY` line as the kept
  `out/score-STAGE.txt` for e4c, e4l, e4m, e5c and e5t (5 of 5).
- The offline tests pass (`tests/test_scorer.py`, `tests/sim_s2.py`, `tests/run_mock.py` 17 of
  17). One mock check ("e4m: the pa2 signature and the window count 10/10") reads the mock's
  timer and failed in 2 of 5 runs after the rewording and passed in the other 3; the rewording did
  not touch the mock or its timer.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `run/guard_py.py` | 167acf98242fb2f3 | 7f9c4654ca058994 | yes |
| `run/guard_s2.sh` | ff862601a1b9b21b | bf50640618550b70 | yes |
| `run/s2_run.py` | 6e97a39243d41735 | 12fbb5e2cb407330 | yes |
| `score/score_s2.py` | f56ab266c177ca9c | aa156a0129e05a49 | yes |
| `tests/run_mock.py` | 23f7572dbd0f79d6 | 89d9388f15026c40 | no |
| `tests/test_scorer.py` | 79c45aebb91455bf | 688a62649503a3da | no |
| `FROZEN.sha256` | 66ff3a60dd5fe627 | 25d2911bbe5bef06 | (hash file) |
| `LAPTOP.sha256` | c059e2339c0bc992 | b9e35713ac2e4858 | (hash file) |
