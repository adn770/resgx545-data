# r33-tim fold notes

Attempt 20261116-211055 (fold/lead-run.log, fold/lead-stage.log): rc 0, 15 jobs in two stages,
every job drew exactly, no fault, no hang, no stop. **Every control FAILED** on its interval:
t1-c1, t1-c2, t1-c3 `ivl` 4897, 4850, 4901 ns against the frozen 700 to 2000; t1d-c1 3696 ns
against 400 to 1200 (t1-c2 also `ten` 0: one sample read exactly 400000). So no frozen verdict
stands: every summary line is "controls FAILED". The scores reproduce byte for byte
(fold/reproduce.out). Record: **E1131**, readings only; E1132 not built (README "t2"); E1133 goes
to the rerun r33-tim2.

## Why the ivl premise was wrong (a builder error)

The frozen intervals came from E1115, E1120 and E1122, whose `ivl` is regtimeline's TOTAL over
its sample count for a 1.5 s window in which the job takes only about 0.11 s: an average over
the idle loop. Those runs stored only changes, but storage is not what slowed this one: this
run's own lead (the 5 ms before t10 starts, every sample stored) is spaced 1213 ns a sample with
three registers (1213 to 1283 median, 11 rows) and 622 ns with 0x0acc alone (622 to 782, 4 rows),
as the earlier averages predict. Once t10 runs, the median spacing is 4.6 to 5.7 us (t1) and 5.2
to 6.2 us (t1d), with single gaps of 0.68 to 2.31 ms in every row (fold/posthoc.txt: `lead`,
`job`, `gmax`) [infer: the sampler shares the CPU with t10 and the kernel during the job]. This
session's windows (60 and 40 ms from 5 ms before the tool) are almost all job time, so their
TOTAL/samples is the job's spacing (3.0 to 4.99 us). The premise took the idle average for the
job's: the builder's error, not a fault of the run or the tool.

## Post-hoc readings (fold/posthoc.py, posthoc.txt; not frozen, no verdict)

- **The timer, 15 of 15 rows**: bit 24 set and bits 31:25 clear in every sample (`tnoen` 0);
  rate 398.96 to 399.01 counts a us and period 1002.497 to 1002.535 us (score.py's piecewise fit
  over 60 or 40 ms); largest count 399960 to 399998, and once (t1-c2) a sample of exactly 400000:
  the reload word itself is read, so bits 23:0 run from 400000 down, not below it (the frozen
  H-TIM-RANGE "below 400000" was off by that one value). snap0 and snap9 read a running count in
  15 of 15 rows (`ten0`, `ten9` 1).
- **The change**: CR_CACHE_CTRL changes once, to 0x1000ffff, 22.93 to 24.10 ms after the tool
  starts (11 of 11; E1122, E1127), bracketed by samples 4.8 to 7.1 us apart.
- **Bit 26** within 200 us of the change: 4 of 11 rows, rising 19.9, 18.8, 0.0 (in the change
  sample) and 107.7 us after it, 6.5, 4.7, 5.9 and 4.7 us wide; at 4.6 to 5.7 us a sample an
  episode can fall between samples [infer].
- **The window against the count's own line** (fitted on the 1 ms before the change, without
  the samples more than 1000 counts off a first fit): the change sample sits within -103 to +137
  counts of the line in 10 of 11 rows (t1-08: -29478, a read about 74 us late; the next sample
  83 us later). In t1-02, t1-04 and t1-07 the window's samples stay within 255 counts (median
  28 to 103); in t1-01, t1-03, t1-05, t1-06 and t1-c3 they step to +568 to +633 counts from 18 to
  40 us after the change and are back within 90 counts 120 to 300 us after it (`s20`, `s120`);
  t1-c1 within 101 but one sample 1603 off; t1-c2 -298 to -347 (its fit dropped 43 samples).
  A counter that stopped or was written would stay off its line; one that comes back does not
  fit that [infer]; a change in the host's read timing does (the rows without the step, t1-04
  and t1-07, are the two with the shortest job spacing, 4.6 us) [infer]. The count drops 399 a
  us across the window as before it within these offsets: counts at bit 26's rise on the line
  399432, 185802, 326108 and 341895, and at its fall 396830, 183941, 323740 and 340039.
- **The count at the change** (line value) across the 11 rows: 7389 to 384863, spread over the
  period (t1-all's smallest arc 225408 over the score's 5 rows).

## For fwsim [infer]

What the readings support, unverdicted: at the kick pass's CR_CACHE_CTRL write the count is
anywhere in the period, and over the next 120 us it drops at 399 counts a us within a few hundred
counts as the host reads it. The rerun r33-tim2 (E1133) freezes these as held-out hypotheses
with the interval premise set from this run.

## sgx-sim, fwsim, vectors

No change: no frozen verdict. No vectors table (no timeline kind in closing_tables.py).
