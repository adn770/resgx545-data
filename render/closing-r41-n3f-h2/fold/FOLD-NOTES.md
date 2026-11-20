# r41-n3f-h2 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-161558, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel
  423b436e7f80, no rebuild, no boot). Session H2 of closing29/n3f/design.md section 3.3: stage y
  (row Y, blob emitsb_sb403s, `form=sb403`, sideband 0x403: bit 10 with bits 1:0 = 3, without bits
  6 and 11), crumb3 at fw14, two jobs as H1's row X. Kit and blob: resgx545 e516a7aa.
- Rescored by hand with the frozen scorer (fold/reproduce-y-*.out): the same bytes as the kept
  out/20261120-161558/score-y.txt.
- PG, E0, T0 and J1 passed; B FAILED as in H1's row X: snap9 read BIF_INT_STAT 0x000d0400 and
  BIF_FAULT 0x0004300f (16:16:12), before the gate began (16:16:13). `Q128-N3F-Y RULE: Y-FILL,
  Y-REBASE; FAULT: BIF_FAULT is not 0 after the row and no outcome names it`. Every prediction
  held: Y-REBASE and Y-FILL (`BIF fault 0xd0400 at 0x4300f (PD 0x0) stalls job 125, recovering`,
  the devcoredump alike); Y-HIGH, Y-NONE, Y-OTHER, Y-KICKFAULT and Y-NOKICK failed.
- Readings (printed, not scored): job 2 done on the kick (answered after 196 us). Post sa: sa0 and
  sa2 unchanged; sa1 0x04400000; sa3 0x3f800000, sa4 0x32004000, sa5 0xbec00000, sa6 0x32002000,
  sa7 0x3f800000, sa8 0x32004000, sa9 0x3f400000, sa10 0x32002000, sa11 0; sa12-sa27 = pa0-pa15
  of the started entry (sa13 = pa1 = 0x00043000). The after-read equals the post in all 32. The
  gate's fill fault page 0x00043000 = post sa13; the triangle after the recovery reset exact;
  fill and triangle ok after the kit's reset (closing29/r41-n3f-logs/health-r41-n3f-h2.log).
- So bit 10 is enough: without bits 6 and 11 the same rewrite of sa12-sa27 and the same fault
  page follow.
- [post hoc] Post pa0 0x32004000 and pa2 0x32002000 (V0 and V2) differ from H1's stage x (pa0
  0x00000003, pa2 0x32411000); pa4-pa15 are the words H1 read. Which of them this row's program
  wrote is not told apart from what was there before.
- Records: E1175.
