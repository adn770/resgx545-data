# r7-faults: post-run files (written at the fold, 2026-11-12)

The session ran once, attempt `out/20261112-222800` (log `run-r7f.log`): stages s0, l, d and m
to their ends, every control passing, health ok after each stage, 14 of the budget's 16 timed-out
boots used. Nothing under `out/`, the predictions or the freezes was changed.

- `verdict.txt`: `score/score_f.py verdict out/20261112-222800` (the driver names the command
  and does not write its output).
- The frozen scorer re-run on the kept files at the fold (`score/score_f.py STAGE
  out/20261112-222800/STAGE out/20261112-222800`, `PYTHONDONTWRITEBYTECODE=1`) gave
  `out/20261112-222800/score-{s0,l,d,m}.txt` byte for byte.
- Left out of the published copy: `debug/` (the offline tests' scratch, the mock's kept tree and
  the freeze script's `.verify.out`) and `__pycache__`. Nothing in the session derives from the
  firmware (README.md, "Data-private").
- `paths-as-frozen.txt`: `gen/data/sources.lst` keeps the absolute data paths `gen/fgen.py`
  writes (its check compares them), so `tools/closing/session_tests.sh` leaves the list and its
  freeze lines as frozen.
