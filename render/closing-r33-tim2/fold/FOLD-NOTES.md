# r33-tim2 fold notes

Attempt 20261116-213803 (fold/lead-run.log, fold/lead-stage.log): rc 0, 15 jobs in two stages,
every job drew exactly, no fault, no hang, no stop; every control PASS (t1-c1, t1-c2, t1-c3 `ivl`
4875, 4779, 4812 ns; t1d-c1 3094; `ten`, `ten0`, `ten9` 1). The scores reproduce
byte for byte (fold/reproduce.out). Record: **E1133**.

## Frozen verdicts (every row held out)

- **H-TIM-399** held 22 of 22 (t1) and 8 of 8 (t1d), **H-TIM-400** refuted in all of them.
- **H-TIM-EN**, **H-TIM-RANGE** (no count above 400000), **H-TIM-RELOAD** held in every row;
  **H-TIM-24** refuted 11 of 11 (t1) and 4 of 4 (t1d).
- **H-SPACING** held 22 of 22 (t1) and 8 of 8 (t1d); H-TIM-EN, RANGE and RELOAD 11 of 11 (t1) and
  4 of 4 (t1d).
- **H-CC-ONE** 22 of 22, **H-CC-LAT** 11 of 11.
- **H-TIM-ASYNC** held (1 of 1 stage case), **H-TIM-SYNC** refuted.
- **H-TIM-WRITE** refuted 11 of 11: 120 to 300 us after the change no row sits 2000 counts or
  more off its pre-change line (`as120` 5.7 to 345.0).
- **H-TIM-LINE not supported**: 19 held, 3 FAILED of 22 clauses. Its `as120` clause (at most
  400) held in 11 of 11 rows. Its `wmed` clause (the window's median |residual| at most 800)
  failed in 3 rows:
  - t1-01: wmed 69442.7, 86.8 times the bound and above WRITE's 2000; the window holds one
    sample, the change sample, whose residual is -69443.
  - t1-07: wmed 72830.1, the same shape (one sample, -72830).
  - t1-08: wmed 1049.6, 249.6 over the bound and below 2000; three samples, the change sample
    at -74329.
  In those three rows the next sample after the change sample comes 181.5, 190.5 and 193.8 us
  later (fold/posthoc.txt); in the other 8 rows 6.5 to 62.0 us later. The frozen rule counts
  them as failed, and they stay failed.

## Post hoc (fold/posthoc.py, posthoc.txt; not frozen)

- The three failed rows' change-sample residuals (-69443, -72830, -74329 counts) are the size of
  the gaps that follow them (174, 183, 186 us at 399 a us) [infer: the sample's 0x0acc read came
  that long after its timestamp]. E1131 had one such row (t1-08, -29478).
- E1131's +568 to +633 count steps 18 to 40 us after the change (E1131 [infer: host read timing])
  have counterparts here: `wmed` 600.6 to 633.9 and `as20` 397.2 to 636.2 in t1-02, t1-05 and
  t1-c2, inside the 800 bound. Read post hoc only.
- The frozen scorer on E1131's kept rows (fold/posthoc.txt, last block): `as120` 7.3 to 346.7 and
  `wmed` 27.5 to 633.4 in 11 of 11; t1-08's change sample -29478 there too.

## What it decides for fwsim

Decided [HW, frozen]: CR_EVENT_TIMER keeps bit 24 alone in 31:24, bits 23:0 at most 400000 (the
reload word read), 398.9 to 399.1 counts a us, a 1002.40 to 1002.65 us period, at a phase spread
over the period at the kick pass's CR_CACHE_CTRL write, and no write or stop through the pass
(H-TIM-WRITE refuted). Not decided: that the count stays on its line inside the window
(H-TIM-LINE not supported).

The fold gives sgx-sim a caller's running count for a program a task emits (`set_emit_tim`,
refusing a value outside the rule; a stopped timer is still read from the register), pysgx binds
it, and fwsim seeds one such count (seeds.toml [events] emit_tim = 0x01061a70, a [time] input
as kick_tim). Tests first (sgx.rs, crates/pysgx/tests/test_fwsim_m2.py).

Under replay the M2 kick now passes PDS #14's tim read. PDS #14 starts one task (the kick's
second entry), and the run stops on a memory fault at 0x0002007c, an address no placed page
holds. No register read is refused. The stop and the firmware's register writes are the same for
the counts 0x01000000, 0x01030d40, 0x01061a70 and 0x01061a80. In the sim, the emitted program's
douta land in the secondary bank (`Bank::Secondary`): that is the sim's assumption, which t2
would test (README of r33-tim, "t2").
