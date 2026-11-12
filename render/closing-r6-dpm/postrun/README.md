# postrun/: written at the fold, after the run

Written on 2026-11-12 at the fold of R6-dpm into records (E881 to E883), with the freeze verified
(`run/freeze_r6.sh verify`: files verified, against resgx545 main d9b2969's files); nothing in
`out/` was changed.

- The frozen scorer re-run at the fold on the kept files of attempt a2
  (`score/score_r6.py STAGE out/a2/STAGE --out DIR`, each stage) gives output byte-identical to
  the kept `out/a2/score-r-a0.txt` to `score-r-k.txt`. Attempt a1 was never scored (it stopped in
  r-a0 before the driver's scoring step).
- Every headline of a2 printed "cannot tell", gated by one r-a0 control, `a0-cal-2048f grow`,
  which has no reading by construction: the full calibration runs at knob `0x400` and never takes
  a partial render, so the reader has no grow to read. The builder froze it as a control by
  mistake (a design slip found at the fold); the job's own steps S2 to S7 and need held, and so did
  every other r-a0 control.
- `ungated.py`, `ungated.out` (post hoc, written after the run and its scores were read): the
  held / FAILED / cannot tell states the frozen scorer printed line by line, tallied per stage,
  model, quantity and scene without the gate (no re-scoring); the two r-k creep jobs read by the
  frozen reader without the scene check that voided them (their 2048x4096 S3 at `0x12c` against
  the frozen model's `0x129`, E874's own miss); the head-pair periods of the two r-v calibration
  dumps; the first thr0 of each r-m band that left one global page. Standard library plus the
  session's own `score/score_r6.py`; run from the session directory.
- `data-view.txt`: the render sessions of resgx545-data e5cdaf0a, for
  `tools/closing/session_tests.sh` (the offline rules the tests import scan `render/closing-*`).
