# r32-kreg3 fold notes

Attempt 20261116-183256 (out/20261116-183256/run.log, out/stage.log): rc 0, 194 jobs (s0 49,
kl10 145) from 18:32:57 to 18:56 laptop time, no fault, no stall, no stop; the gates of k10, k20,
k40, kl20 and kl40 were shut by s0's pick (SKIPPED); 0x0a78 read back 0x2c after the run (the
lead). Every score and every gate reproduces byte for byte (fold/reproduce.out). Records E1128
(s0, the calibration) and E1129 (kl10), as the lead assigned.

## Frozen verdicts

- **s0 (E1128):** `s0's references draw; picked form l10 (48 of 48 rows decided)`. Every
  reference drew one image a form. Spread of the eight references (IQR, percent of their
  median; the pick bound 0.8): 64x64 at 10 renders 4.420, at 20 renders 3.276, at 40 renders
  3.503 (none qualifies); 1024x768 at 10 renders 0.324, 20 renders 0.195, 40 renders 0.161 (all
  three qualify; the first in order, l10, is picked). BOUND = max(1, 3 x 0.324) = 1.000 percent.
- **kl10 (E1129): H0 held, 64 of 64 values decided.** "CR_PDS_REG_0A78 at every value 0x00-0x3f
  leaves the render time of 500 triangles (1500 vertices) at 1024x768, 10 renders a job within
  1.00 percent of 0x2c's on two shuffled passes". The 16 controls lay -0.35 to +0.23 percent of
  s0's 22072.5 us (no outlier), their spread 0.295 percent (at most 0.5); the farthest value
  0x1d at 0.48 percent; no reading over 1 percent on either pass. E141's slow values read 0x01
  -0.11 / -0.05 and 0x20 +0.39 / -0.17 percent.
- `score.py q024 out/20261116-183256` prints `Q024: RETIRE (...)`. Its text calls the load "many
  small triangles", the frozen wording of the scorer; the load it timed is 500 triangles at
  1024x768, each about a quarter of the target, not small [infer, below].

## Post hoc (fold/posthoc.py, posthoc.txt; readings, no verdict)

- The 64x64 load: within-job spread of renders 2-N 7.8 to 10.1 percent at the median, job medians
  699-784 us; more renders did not bring the eight job medians under 3 percent (10: 4.42, 20:
  3.28, 40: 3.50), so the noise is mostly between jobs [infer], as E1125's drift suggested.
- The 1024x768 load: a render about 22.07 ms; within one job 0.23-0.27 percent; the 128 kl10
  value rows -0.29 to +0.48 percent of the controls' median, IQR 0.36 percent.
- Images (hardware): 64x64 `o0 mixed 0xff00ff00 x2296 0xff203040 x1800` (as E1125); 1024x768
  `o0 mixed 0xff203040 x547615 0xff00ff00 x238817`, one image in every job. The green covers 30.4
  percent of the 1024x768 target and 56 percent of the 64x64 one: the triangle is drawn in the
  target's coordinates and its 499 copies move at most 31 pixels, so at 1024x768 each triangle
  covers about a quarter of the target [infer: from the union's area and the copies' offsets].

## What it does to Q024

Narrows, by the user's decision of 2026-11-16: two loads are answered, the 256x256 triangle (E1124)
and 500 triangles at 1024x768, ten renders a job (E1129); the open clause is only a
sub-millisecond load of many small triangles (64x64), which cannot be timed to 1 percent today
(E1125 8.27 percent at six renders, E1128 4.42, 3.28 and 3.50 percent at 10, 20 and 40). The
frozen `q024` RETIRE line is not taken: the user ruled that large triangles do not answer the
small-triangle clause. No sim change (no simulator keeps a clock; SIM_UNMODELLED entries for
E1128 and E1129).

The published copy leaves out debug/ (the library-mock builds, mock trees, the hand probe) and
the bytecode caches.
