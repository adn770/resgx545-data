# r41-n3f-h4 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-161718, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel
  423b436e7f80, no rebuild, no boot). Session H4 of closing29/n3f/design.md section 3.5: stage t
  (row T, blob emitsb_sbc43s, `form=sbc43`, sideband 0xc43, crumb3 at fw14), one job (command 1,
  timer pass), the gate in the order triangle then fill (`gate_order = "tri,fill"`). Kit and blob:
  resgx545 e516a7aa.
- Rescored by hand with the frozen scorer (fold/reproduce-t-*.out): the same bytes as the kept
  out/20261120-161718/score-t.txt.
- Every control passed (BIF_FAULT 0 in snap9). `Q128-N3F-T RULE: T-OTHER`. The prediction
  T-HEAD (the triangle faults at page 0x01555000, the render queue's head sa15) FAILED; T-OTHER
  held: the triangle faulted `BIF fault 0xd0400 at 0x4300f (PD 0x0) stalls job 139, recovering`,
  page 0x00043000 = post sa13, the same page as the fills of B11, X and Y; the devcoredump alike.
- The fill after the watchdog's recovery reset was exact (`diff: 0 of 2048 pixels`), on the
  stock firmware, disarmed; fill and triangle ok after the kit's reset
  (closing29/r41-n3f-logs/health-r41-n3f-h4.log).
- Readings (printed, not scored): post sa as H2's but sa12-sa27 = this entry's pa0-pa15 (pa12
  0x5a5a3a18, pa14 0x5a5a3a1a, land's markers from H3's row LC, which ran before this session:
  [post hoc] the started entry's pa hold words of earlier runs across the resets).
- So a render faults at the same page as a transfer, sa13's, not at the render queue's head sa15.
- Records: E1177.
