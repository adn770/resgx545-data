# r34-ev fold (E1137 Q111, E1138 Q036)

- Run 2026-11-17 by the lead, attempt out/20261117-001058, rc 0, no stop, fault or hang; every
  control of e0, e1, e2c, e2, d0 passed (@snap0 and @cal read, none remembered). d1 skipped: its
  gate closed on the measured interval (d0: 4131.5 ns median for 0x0660 + 0x0748, above the
  frozen 3500 ns bound for E1057's 4 us bit 2 pulse).
- fold/reproduce.out: every score reproduced byte for byte by the frozen scorer, the three gates
  re-read. fold/posthoc.py -> fold/posthoc.txt: every kept row as readings by stage, form and PB
  size (post hoc, no verdict changed).
- Readings (post hoc): the out-of-memory bit follows the PB size: no bit 1 or 2 at 0x2b6 and
  0x1c2 (0 of 5 rows), bit 1 at 0xe2 and 0x82 (6 of 6, one or two episodes), bit 2 31 us after a bit
  1
  episode at 0xe2 in e1 (2 of 2) and not in e2 (0 of 1). Copies: bit 18 a single 60 to 206 us
  episode in 10 of 14 copy and large-copy rows, no bit 0 in any. 0x012c alone sampled at 3.1 to 3.9
  us in these
  job windows, not E1115's 541 ns.
- T1: worked as intended. Every premise was read from the row's snap0 or a same-set calibration,
  no stage voided, and the one interval that did not fit (d1) shut its gate before a job ran.
