# r31-kreg2 fold notes

Attempt 20261116-145122 (fold/lead-run.log, fold/lead-stage.log): rc 0, 307 jobs (s0 17, k1 145,
k2 145) from 14:51 to about 15:20 Mac time, no fault, no stall, no stop; 0x0a78 read back 0x2c
after the run (the lead). Every score reproduces byte for byte (fold/reproduce.out).
`score.py q024 out/20261116-145122` prints `Q024: NARROW (decided on k1 only)`.

**Data base.** The freeze pins data dc838e60f; data main was rewritten on 2026-11-16 (tip
4dd4c3833 at the fold). dc838e60f is still an object of the data repository, off every branch,
and every pinned path is the same at 4dd4c3833 (`git diff --stat dc838e60f 4dd4c3833 -- PATHS` is
empty). Records E1124 (k1) and E1125 (k2), as the builder picked (r31-cc took E1122-E1123).

## Frozen verdicts

- s0: 17 of 17 controls passed. REF1 67138 us (r1-r8). L2's v1-v8 drew one image
  (`o0 mixed 0xff00ff00 x2296 0xff203040 x1800`) and read 687-822 us; REF2 719.5 us.
- **k1 (E1124): H0 held, 64 of 64 values decided.** "CR_PDS_REG_0A78 at every value 0x00-0x3f
  leaves the 256x256 triangle's render time within 1.00 percent of 0x2c's on two shuffled
  passes". The 16 0x2c controls lay -0.61 to +0.10 percent of REF1 (no outlier needed), their
  spread 0.332 percent (at most 0.5). Three readings of 128 lay over 1 percent, each on one pass
  only: 0x11 held-out +1.53, 0x2e fit +1.34, 0x15 fit +1.25 percent (their other passes +0.19,
  +0.17, +0.57). E141's slow values read 0x01 +0.34 / -0.22 and 0x20 +0.24 / +0.11 percent.
- **k2 (E1125): cannot tell** by the frozen premise: BOUND2 = 3 x the 8.27 percent spread of
  v1-v8 = 24.8 percent, over the 2.5 percent cap. No value decided. Every k2 row drew v1's image
  (no IMAGE line), c01-c16 and c-end passed, no render failed.

## k2 post hoc (fold/posthoc.py, posthoc.txt; readings, no verdict)

Why BOUND2 went over its cap: the L2 render is short, about 0.72 ms (the builder had no laptop
timing of it; the 256x256 triangle takes 67 ms), so a few tens of microseconds of jitter are
percents.

- s0's v1-v8 medians: 703 774 695 687 750 697 736 822 us (IQR 8.27 percent).
- Per-render noise: all 760 renders 2-6 of L2 have median 739 us, range 606-1751, IQR 10.7
  percent; within one job the five renders' IQR is 6.05 percent at the median (36 at most).
  Render 1 is not slower (median 719.5 us).
- Between jobs: the 16 k2 controls 671-787 us, IQR 8.03 percent; the 144 job medians fall
  over 660-819 us (20 us bins: 3, 17, 27, 30, 22, 32, 11, 2).
- Drift: small against the noise; the median of each 18 rows in run order goes 745.5, 744.5,
  738, 746.5, 732.5, 731, 732.5, 727.5 us (about -2.4 percent over the stage); controls c01-c08
  median 701.5 us, c09-c16 738.5 us.
- Per value (fold/posthoc.txt): every value's two medians lie -6.0 to +11.4 percent of the
  controls' median 722.5 us; the 128 value rows' median is 739 us (+2.3 percent), IQR 7.4
  percent. No value stands apart from the rest on both passes beyond that noise [infer]; at
  this noise a dependence under about 25 percent cannot be seen.

## What a k2-only rerun needs to decide

A load whose render is long enough that BOUND2 comes under 2.5 percent: the v1-v8 spread must be
below about 0.8 percent. Decide before freezing: (1) the form, e.g. the same 1500 vertices on a
larger target (256x256 to 1024x768; E438 completed 1500 vertices at 1024x768 in the default
buffer), or more copies' worth of work, timed so a render is tens of ms like L1; (2) renders per
job and the statistic (more renders per context, median of 2-N); (3) a safe calibration stage
first (no kreg) that times the candidate forms and a frozen rule that picks the first form whose
spread meets the cap, else stops before any flagged row; (4) whether a 64x64 small-triangle load
must stay small (the question's "many small triangles") or a larger target of the same 500
triangles answers it. t30 needs no change for (1)-(3).

## What it does to Q024

Narrows: the 256x256 clause is closed by E1124's frozen verdict (64 of 64, both passes, within 1
percent); the many-small-triangles clause stays open (E1125: cannot tell at L2's noise). Not
retired: the frozen retire rule needs both loads decided. No sim change (no simulator keeps a
clock; SIM_UNMODELLED entries for E1124 and E1125).

The published copy leaves out debug/ (the library-mock builds and mock trees) and the bytecode
caches.
