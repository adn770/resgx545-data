# r41-n3f-h3 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-161633, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel
  423b436e7f80, no rebuild, no boot). Session H3 of closing29/n3f/design.md section 3.4: stage lc
  (row LC, blob emitsb_sbc43s, arm `slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43`, sideband
  0xc43 with the land image, which keeps the timer running and writes no V0 or V2), three jobs:
  command 1 (the emit, timer pass), command 6 on the next tick pass, command 6 after `sleep_ms`
  2000. Kit and blob: resgx545 e516a7aa.
- The stage stopped at its one row: job 1 done, job 2 posted and never served (the runner's "no
  done within 200 ms", class hang, rc 4, `## STOP: unexpected hang in lc1-a`); the kit's reset and
  health recovered it (closing29/r41-n3f-logs/health-r41-n3f-h3.log). The driver did not score it;
  scored by hand with the frozen scorer (fold/reproduce-lc-*.out).
- **Frozen verdict: CANNOT TELL.** `Q128-N3F-LC RULE: CANNOT TELL (control E0 FAILED)`; B failed
  too (BIF_FAULT 0x0000000f in snap9).
- **A design slip in the scorer, not rescored.** E0 reads the page's cmd word (dword 1) at the
  row's end and wants 0 (entry 0 cleared it). In a row of several jobs the page at the end holds
  the last job's command: job 2's command 6 was written and never served once the firmware had
  stopped, so dword 1 read 6. E0 therefore fails whenever a later job of the row is not served,
  which is the LC-EARLY end the design predicted; it does not say that entry 0 did not run job 1
  (J1 passed: X0, S1, M4 with run id 1, done). The frozen rule and its verdict stand as printed.
- Readings (printed, not scored; LC-EARLY-like): the scorer's outcome lines read LC-EARLY held,
  LC-REBASE FAILED, the rest cannot tell. Post sa (job 1's started entry): sa0 0x32004000 ->
  0x00000000, sa1 0x04400000, sa2 0x32002000 -> 0x0104b95b, sa3-sa10 as H2's, sa12-sa27 = pa0-pa15
  (sa13 0x00043000, sa24 and sa26 land's markers 0x5a5a3a18 and 0x5a5a3a1a in pa12 and pa14).
  After job 1: snap9 and the stop dump BIF_INT_STAT 0x000d0400, BIF_FAULT 0x0000000f (list 15,
  page 0); the tick stopped (the runner's alive check: ticks 2129, 2129, 2129, not advancing);
  job 2 not done (dwords 224-255 still 0xdeadc0de); no gate ran.
- [infer] With land, sa0 and sa2 lost TA3DCtl and the kernel CCB control (as section 3.4 (a)
  predicted), and the next pass faulted at page 0 through the EDM's list; that the stale sa0 or sa2
  was the faulting pointer is not read.
- Records: E1176.
