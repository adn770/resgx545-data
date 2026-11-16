# r31-cc fold notes

Attempt 20261116-144402 (fold/lead-run.log, fold/lead-stage.log): rc 0, 52 jobs in five stages,
every job drew exactly, no fault, no hang, no stop; every control PASS (ivl 540 to 542 ns with
0x0804 alone, 849 to 864 with two registers, 1766 to 1789 with five, 1447 to 1457 with c5's
four). The scores reproduce byte for byte (fold/reproduce.out against the run's score-STAGE.txt).

**Record numbers.** The frozen README reserves E1122 provisionally; the lead's decision: this
session folds as **E1122** (c1, c2, c3) and **E1123** (c4, c5).

**Data base.** The freeze pins data dc838e60f; data main was rewritten on 2026-11-16 (tip
650ec7c6c). dc838e60f is still an object of the data repository, off every branch, and every
pinned path is the same at 650ec7c6c (`git diff --stat dc838e60f 650ec7c6c -- PATHS` is empty).

## Frozen verdicts (all rows held out)

- **H-CC-ONE** held in every stage (24 + 30 + 30 + 24 + 18 clauses: one change, 0x0000ffff to
  0x1000ffff, held to the end). **H-CC-LAT** held 36 of 36 (c1 18.3 to 23.0 ms, c2 18.7 to 23.5,
  c3 20.4 to 25.2, c4 19.0 to 25.1). **H-CCFIRST** held (c4 8 of 8, c5 6 of 6).
- **H-CNT-LAG** held (c2 18 of 20 clauses, c2-08 cannot tell: a tick near the change; c4 16 of 16;
  c5 12 of 12); **H-CNT-LEAD** refuted (c2 9 FAILED, c4 8, c5 6). The next served count came 0 to
  8.8 us after the change (c2 4.4 to 8.8 in 8 rows, the change's sample in 1; c4 5.4 to 7.5 in 7,
  0 in 1; c5 5.0 to 7.4 in 4, 0 in 2).
- **H-DMS** held (c4 8 of 8: CR_DMS_CTRL 0x00208200 to 0x50208200 31.0 to 43.6 us after the
  change). **H-CC-26** cannot tell (no c4 row showed bit 26 before a render end). **H-NOWAIT**
  "held" 1 of 8, H-WAIT FAILED 1: c4-05's bit 26 rose 5.09 ms after the change, after the render
  end, so its dms26 = 0 compares the TA path's write with a late bit 26; read it as undecided
  (the frozen clause did not require bit 26 before the render end, as cc26 does).
- **H-CC-XFER** held (c5 18 of 18), **H-CC-TA** refuted (6 FAILED): a fill's kick changes
  CR_CACHE_CTRL as a triangle's does, 5.6 to 6.8 ms after the tool starts.
- **CR_BIF_CTRL.** c3: H-BIF-HIDDEN held (no row decided at 0.85 us a sample), H-BIF-FIRST and
  H-BIF-LATER cannot tell. c4: H-BIF-VISIBLE and H-BIF-FIRST held, 1 of 8 decided (c4-04),
  H-BIF-LATER FAILED there; c5 the same, 1 of 6 (c5-01). Across the stages 2 of 24 rows decide,
  both "pre", none "post".

## Whose BIF word (the lead's question)

The word is 0x00000008 in all four sightings (fold/posthoc.txt): bit 3, which both the host and
the firmware write. The host (fork 8bc0877e8603, read only): gma500's `mmu.c`
(`psb_mmu_flush_pd_locked`, `psb_mmu_flush`: bit 3 or bit 2 set, `wmb()`, cleared at once, then a
read back), reached from `gem.c`'s pin and unpin of gma500's own GEM objects, and sgxfive's
`sgx_seq.c` (`inval_dc` at the boot's reset, `sgx_seq_bif_flush` for debugfs `bif_flush`, which
no row writes). sgxfive's job paths call neither. The firmware: E013's dataflow writes
CR_BIF_CTRL `| 0x4` and `| 0x8` in the routine the kick pass calls for cache control bits 0
and 1, before bit 3's CR_CACHE_CTRL write. The readings:

- c4-04 and c5-01: 0x8 from 5.7 and 6.8 us before the change, gone in the change's own sample:
  set 3.9 to 7.4 and 5.3 to 8.2 us. The host's set-and-clear is two back-to-back MMIO writes; a
  run that long would need the CPU taken away between them, and then twice ending in the very
  sample the firmware's own write shows. In both rows the next served count comes at or after the
  change (5.4 us, 0 us).
- c4-05 (5.07 ms after the change) and c3-01 (44.6 ms): 0x8 for 3.5 to 7.1 and 4.0 to 5.7 us
  inside the job, no CR_CACHE_CTRL change (already set); in c4-05 a served count 5.5 us after it
  clears. Our kernel sends later commands with only the BIF bits (the reaper's
  PROCESS_QUEUES, `sgxfive.c` 935, 957, 1075 and 994 at 8bc0877e8603) [infer].

**Verdict: the firmware's** [infer: on the code paths of fork 8bc0877e8603, the duration, and the
word clearing in the change's sample twice; the word alone cannot tell]. So in the two decided
rows a firmware response to the kick (its BIF invalidation) precedes the CR_CACHE_CTRL change:
H-CC-HW as stated (the change precedes any firmware response) is refuted in 2 of 2 decided rows,
22 rows cannot tell. Kept dmesg: only the kit's own marks (`resgx545 r31c snap ...`), no kernel
line at the job.

## The fwsim read after a kick

The firmware's CR_CACHE_CTRL read sits between its BIF calls and its write (E013); the hardware
read 0x0000ffff with the BIF word set (the sample before the change, 2 of 2) and 0x1000ffff from
the sample in which the BIF word is gone. Whether the read itself, inside that last sample gap,
saw the change is still not a measured reading, but the value it feeds is: E013 gives it no test,
only `| 0x10000000` and the write, so both possible answers make the same write, 0x1000ffff, the
word every row then reads until the reset (E1120, E1122, E1123). The fold lands that:
CR_CACHE_CTRL after a kick answers the reset word until the run writes it, then the run's
write, which hw.rs accepts only as 0x1000ffff (anything else stays refused); the M2 kick now goes
on to the next refusal.

## Post hoc (not frozen)

fold/posthoc.txt: the BIF runs with their bounds. c5's fill adds 2 to 4 served counts beyond the
ticks (a triangle 9 to 11, E1120; c2 to c4 here 9 to 11).
