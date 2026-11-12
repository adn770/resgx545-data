# postrun/: written at the fold, after the run

Written on 2026-11-12 at the fold of R7-dpm into records (E915 to E918), with both freezes
verified (`run/freeze_r7.sh verify AB`: set A and set B files verified, against resgx545 main
1c64f3a's files); nothing in `out/` was changed.

- The frozen scorer re-run at the fold on the kept files (`score/score_r7.py STAGE
  <session>/out/a1/STAGE --out DIR` for s-a0, s-m, s-b and s-v, `out/b1/s-k` for s-k, from the
  session's own directory with the paths the driver gave) prints output byte-identical to the
  kept `out/a1/score-s-a0.txt` to `score-s-v.txt` and `out/b1/score-s-k.txt`.
- The scorer cuts the printed `pred` and `obs` at 24 characters: b-s44a-0x2 shows five of its
  six run peaks (the sixth, `0x1a`, is in `predictions/s-b.tsv`); the state beside it is
  computed on the whole lists.
- `misses.py`, `misses.out` (post hoc, written after the run and its scores were read; the
  session's own reader `run/r7read.py`, no re-scoring): the first timeline rows of b-s17-0x9 (the
  one FAILED row of H-REPLAY64: no sample fell in its first TA run, so the reader's peak of that
  run is 0); the steps of the s-m cells that FAILED and the brackets of three calibrations; the
  head pair offsets of the two s-v calibration dumps; every s-k job's oomring2 rungs (pa1, the
  `sa8` bits 7 to 9, the two page counts) beside the host's samples around each partial render.
  Run from the session directory: `python3 postrun/misses.py > postrun/misses.out`.
- `data-view.txt`: the render sessions of resgx545-data 830641e6, for
  `tools/closing/session_tests.sh` (the tests and the offline rules they import scan
  `render/closing-*`), so that the tests read the corpus as frozen.
- `../sibling-src/b/q210_targets.out`: the round 7 planner's output that `tests/test_gen.py`
  reads beside the session (`closing7/b/`), byte-identical to its published copy
  `cited/closing7/b/q210_targets.out`.
