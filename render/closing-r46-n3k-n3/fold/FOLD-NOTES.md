# r46-n3k-n3 fold notes (folder, 2026-11-25)

- One attempt, out/20261125-161049 (16:10:49), the fifth session of round 46, after N2
  (closing29/r46-n3k-logs/runone-N3.out, run rc 4: lf3f's planned stop). Session N3 of
  closing29/n3k/design.md (sections 4.2, 4.5). Kit: resgx545 eaee04a4 (branch r46-n3k: K10's
  `pds=landr|landp`, unused here), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14.
- Stage wd (row W, image mark, one job): rc 0, scored by the driver (score-wd.txt). Rescored by hand
  (fold/reproduce-wd-20261125-161049.out): the same bytes. `Q128-N3K-WD RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 9 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2. Record E1242.
- Stage lf3f (row LF3F, image land, begin draws fill,fill,fill, jobs as LF2): exited 4 at its one
  row (class hang), the planned end; the driver did not score it. Scored with the frozen scorer
  after the run (closing29/r46-n3k-logs/score-r46-n3k-n3-lf3f.txt) and again by hand
  (fold/reproduce-lf3f-20261125-161049.out): the same bytes. PLANT, PG, E0, T0, J1, DR, DK and SV
  passed, B and J2 FAILED (read by the outcomes that name the stop). `Q128-N3K-LF3F RULE: LF3F-KEEP;
  FAULT: BIF_FAULT is not 0 after the row and no outcome names it` (the design gave LF3F no
  other-page outcome); LF3F-KEEP held; **LF3F-PAGE0 FAILED** (predicted held: the fault is at M1's
  page); LF3F-SECOND, -LAST, -FIRST and -SERVE failed as predicted. Readings (printed): job 1 done
  (10 ticks), post sa0 0x00000002, sa1 = M1 0x005d1000, sa2 0x01043ca1 (sa02kind LF), sa13 = pa1 =
  M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT 0x005d100f (page 0x005d1000; the
  scorer names job 1's post sa1), post, snap9 and the stop dump the same; job 2 never served; the
  tick stopped. KC begin delta 8 (ok); the end KC cannot tell. The kit's reset and both draws
  recovered it (health ok, closing29/r46-n3k-logs/health-r46-n3k-n3.log). Record E1243.
- Post sa3-sa31 and pa0-pa15 equal in wd and lf3f (printed).
- [post hoc, infer] With sa0 2 and M1 in sa1, LF and LF2 (one fill, module 079DD0D1) stopped at page
  0, and every stop of this round with that bank (two or three fills, module 10BBF3BF) stopped at
  M1's page. The fill count and the module changed together; no row of rounds 44-46 splits them.
