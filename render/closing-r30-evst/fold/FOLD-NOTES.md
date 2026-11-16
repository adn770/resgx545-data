# r30-evst fold notes

Attempt 20261116-123552 (fold/lead-run.log, fold/lead-stage.log): rc 0, 47 jobs, every job exact,
no fault, no hang, no stop. The scores reproduce byte for byte (fold/reproduce.out against the
run's score-STAGE.txt). The laptop's clock ran about 2 h 50 min behind (the lead): the kept wall
times are the laptop's; every reading here is a regtimeline offset, not a wall time.

## The controls that failed: the builder's error

e2, e3 and e4 print "controls FAILED" for every hypothesis. Every one of their five controls
(e2-c1, e2-c2, e3-c1, e3-c2, e4-c1) read diff 0, idle 0x20000000, idle2 0x400, se16 1 and an
ivl inside its frozen window (1406 to 1542 ns with 4 registers, 8989 to 9234 ns with 27); the
one key that failed is `cache`, CR_CACHE_CTRL (0x0804) in the first sample: 0x0000ffff, frozen
0x1000ffff. The frozen value was wrong, a builder error, not a reading of the hardware against a
right premise: I took 0x1000ffff from E258's register-timelines output, read mid-session after
earlier jobs with no reset between them, while the kit resets the GPU before every row. The
kit's own snapshots already said so: every published kit session's `snap0.regs` (after the
reset) reads `reg 0x0804 0x0000ffff` and its `snap9.regs` (after the job) `0x1000ffff`
(r29-kreg s0, and this run's), and hw_spec's boot table writes 0xffff. The sampling density was
not the cause: every ivl was inside its window. Because the frozen controls failed, e2, e3 and e4
decide nothing; their readings below are post hoc (fold/posthoc.py, posthoc.txt).

## Decided (frozen, controls passed: e1 4 of 4 reads, e5 likewise)

- e1 (0x012c alone, 541 ns a sample): H-IDLE 14 of 14 rows (fit 6, held 8): 0x012c reads
  0x20000000 outside the job. H-ALONE held (8 rows with bit 26, 13 episodes): every sample with
  bit 26 reads 0x24000000. H-BEFORE held (first rise 87.7 to 118.7 us before the first rise of
  bit 18 or 0, fallen before it). H-SUB held 14 of 14 (bits 6, 9, 20 never seen at 541 ns).
  H-SW held where decided (11 rows). H-EVERY FAILED, H-PART held: bit 26 seen in 8 of 14 rows.
  H-WIDE held on the fit rows, FAILED on the held rows (3 of 8: a second episode of 4.2 and 4.4
  us in e1-07 and e1-11, and a 21.1 us one in e1-12): the first episodes are 55.1 to 92.8 us but
  an episode can be 4 to 21 us.
- e5 (-n 3, 0x012c alone): H-ALONE 5 of 5, H-IDLE 5 of 5, H-SW 5 of 5; H-ONCE and H-EACH both
  refuted as frozen (multi = 1: e5-05 alone has two episodes; the README called 1 "cannot tell",
  the frozen windows 0..0 and 2..5 refute both: the windows rule). Every e5 row shows bit 26
  exactly once except e5-05; in e5-02 and e5-03 it comes after an earlier render's end (lead
  -10036 and -5348 us), 8.3 and 4.0 us wide. H-SUB fails on e5-02's fit row (bit 20 seen once).

## Post hoc (not frozen; fold/posthoc.txt)

- CR_CACHE_CTRL: 0x0000ffff after the reset; bit 28 sets at the job's first activity, 21 to 40
  us before bit 26 rises in 7 of the 10 rows where both show (e3-01 114.7 us; in e2-01 and e2-02
  bit 26 rises 16.7 and 21.1 ms after it), and stays to the end of the run in all 24 rows that
  sample it.
- Bit 26 with CR_CACHE_CTRL sampled: 4.9 to 7.6 us (7 episodes, 4 registers) and 11.8 to 12.6
  (3, 27 registers), against e1's 4.2 to 92.8 (median 57.7). [infer] sampling 0x0804 (or the
  other registers) shortens bit 26's visible pulse; e3's seen fraction 2 of 8 against e1's 8 of
  14 fits neither H-DENSITY nor H-INDEP (0.32).
- CR_USE0_SERV_EVENT: 9 to 11 counts beyond the ticks over a plain triangle in all 24 rows that
  sample it, the tick rate 0.9975 to 1.0004 a ms before the job, bit 16 clear in 0 to 6 samples of
  the job (H-SE-EVENTS would hold 19 of 19 non-control rows).
- 0x0118 left 0x400 in 6 of 19 non-control rows.

## What lands

- E1115 (e1, e5 decided; Q111 narrowed: bit 26's word, order against the render end, not seen
  in every job at 541 ns, episode widths 4 to 93 us; bits 6, 9, 20 under 541 ns in a triangle).
- E1116 (e2, e3, e4: readings only, "controls FAILED: the builder's frozen cache value", every
  reading post hoc).
- sgx-sim hw.rs: a landed rule for 0x012c before the first served event other than a tick
  (0x20000000, E1115's H-IDLE with E547); after a kick the read is still refused, its refusal
  naming E1115 (the bit 26 word is known, when it shows after the CACHE_CTRL write is not).
  0x0b14 across kicks stays refused (E1116 is post hoc).
