# r34-ev2 fold (E1141 Q036, E1142 Q111)

- Run 2026-11-17 by the lead, attempt out/20261117-004223, rc 0, no stop, fault or hang; 61 jobs;
  every control passed. c0 read 0x0748 alone at a 3762 ns median (under the frozen 3890 ns), so d1
  ran and d1s was skipped; e1 and p1 opened their gates. fold/reproduce.out: every score
  reproduced byte for byte.
- Scorer slip (frozen, not rescued): d1's H-B2PR and H-B1-PR width rows froze the quantities
  `b2wmax` and `b1wmax`, which analyse() never produces (it names them `b2max`, `b1max`), so those
  rows read cannot tell (the test fed the name by hand). Post hoc widths are in fold/posthoc.txt.
- Readings (fold/posthoc.txt): bit 1 of CR_EVENT_STATUS at 0x2b6 1 of 4, 0x1c2 3 of 4, 0xe2 3 of
  4, 0x82 4 of 4; bit 18 in 5 of 6 plain and 4 of 6 large copies; 0x0748 bit 2 clears 0 at PR 0, 1
  and 2 (6 rows), 2 and 1 at PR 4, 0 and 3 at PR 7, each 3.89 to 4.05 us; CR_DPM_3D_PAGE_COUNTS
  0x10060 at 0x82.
- No frozen rule retires a clause of Q036 or Q111 (none was frozen as a retirement rule).
- sgx-pipe dpm.rs models what was decided (test first): the 3D page-count word's low half after
  an overflow and its one write a job, 0x0748 bit 4's one clear a job.
