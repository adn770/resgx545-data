# r41-n3f-h1 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-161456, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel
  423b436e7f80, installed since the one-shot boot of 2026-11-19; no rebuild, no boot this round).
  Session H1 of closing29/n3f/design.md section 3.2: stage c (row C, the control, blob emitsb14s,
  `form=fw14`, sideband 0x843), then stage x (row X, blob emitsb_sbc43s, `form=sbc43`, sideband
  0xc43), both crumb3 at fw14, each row two jobs: command 1 (the emit, timer pass) and command 6
  (the after-read of sa0-sa31 into dwords 224-255) on a GETMISCINFO kick. Kit and blobs: resgx545
  e516a7aa (branch r41-n3f). The three blobs passed the fork's KUnit suite on the Mac shim with one
  suite of their own, 43 of 43 (closing29/r41-n3f-logs/shim-r41.log; the negative run,
  shim-r41-neg.log, fails two tests when a form is wrong).
- Rescored by hand with the frozen scorer (fold/reproduce-c-*.out, fold/reproduce-x-*.out): the
  same bytes as the kept out/20261120-161456/score-c.txt and score-x.txt.
- Stage c: every control passed; `Q128-N3F-C RULE: C-GATE, C-SAME` as predicted. Job 2 (cmd 6)
  done on the kick (GETMISCINFO answered after 200 us); its after-read equal to job 1's pre in all
  32 sa; the gate fill and triangle exact; BIF_FAULT 0 in snap9.
- Stage x: PG, E0, T0 and J1 passed; B (BIF_FAULT 0 in snap9) FAILED: snap9 read BIF_INT_STAT
  0x000d0400 and BIF_FAULT 0x0004300f, logged at 16:15:36, before the gate began (16:15:37). The
  frozen rule reads B through the outcomes that name it and prints `Q128-N3F-X RULE: X-FILL,
  X-REBASE; FAULT: BIF_FAULT is not 0 after the row and no outcome names it`. Every prediction
  held: X-REBASE (job 2's after-read = job 1's post sa0-sa31) and X-FILL (the gate's fill line
  `BIF fault 0xd0400 at 0x4300f (PD 0x0) stalls job 117, recovering`, the devcoredump's BIF words
  alike), X-HIGH, X-NONE, X-OTHER, X-KICKFAULT and X-NOKICK failed.
- Readings (printed, not scored), stage x: job 2 done on the kick (GETMISCINFO answered after
  139 us), so the kick and command 6 were served with the rewritten bank. Post sa: sa0 0x32004000
  and sa2 0x32002000 unchanged; sa1 0x04000010 (B11: 0x04400000, both attempts); sa3-sa5, sa7-sa9
  0x3f800000, 0x3f400000, 0xbec00000, 0x3f800000, 0xbec00000, 0x3f400000; sa6, sa10, sa11 0;
  sa12-sa27 = pa0-pa15 of the started entry (sa13 = pa1 = 0x00043000); sa28-sa31 go on in the
  pattern. The after-read equals the post in all 32. The gate's fill fault page 0x00043000 = post
  sa13; the triangle after the watchdog's recovery reset was exact; fill and triangle ok after
  the kit's reset (out/.../x/x1-a.health2, x1-a.fill2;
  closing29/r41-n3f-logs/health-r41-n3f-h1.log).
- [post hoc] Stage c's post pa0-pa15 and stage x's are the same 16 words (pa0 0x00000003, pa1
  0x00043000, pa2 0x32411000, ...): with 0x843 crumb3's attributes 0 and 2 reach no pa of pa0-pa15
  (E1161, E1162), so those words were there before both rows; what they are is not read.
- [post hoc] Since BIF_FAULT was already set at snap9, the fault was taken in the row, after job 1
  and by the end of job 2's kick and command 6; which access took it is not read. In B11 (one job,
  no kick, E1172) and in H4's row T (one job) snap9 read BIF_FAULT 0 and the fault came with the
  gate's first job.
- Records: E1173 (stage c), E1174 (stage x).
