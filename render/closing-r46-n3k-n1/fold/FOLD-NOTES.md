# r46-n3k-n1 fold notes (folder, 2026-11-25)

- One attempt, out/20261125-160752 (16:07:52), the third session of round 46, after B6
  (closing29/r46-n3k-logs/runone-N1.out, run rc 4: lff2's planned stop). Session N1 of
  closing29/n3k/design.md (sections 4.2-4.4, 10.3; decision C (a)). Kit: resgx545 eaee04a4 (branch
  r46-n3k: K10's `pds=landr|landp`, unused here), the blob emitsb_sbc43s, `form=sbc43` (sideband
  0xc43) at fw14.
- Stage wa (row W, image mark, one job): rc 0, scored by the driver (score-wa.txt). Rescored by hand
  (fold/reproduce-wa-20261125-160752.out): the same bytes. `Q128-N3K-WA RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 9 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2. Record E1236. WA is the build control on the new module
  (section 10.3): it held every outcome.
- Stage zff2 (row ZFF2, image crumbz, begin draws fill,fill, one job): rc 0, scored by the driver
  (score-zff2.txt) and rescored by hand (fold/reproduce-zff2-20261125-160752.out): the same bytes.
  `Q128-N3K-ZFF2 RULE: ZFF2-QUIET`; every control passed, PLANT, DR, DK and SV included. **ZFF2-KEEP
  FAILED** (predicted held: sa1 M1 and sa2 a timer word, but sa0 0x00040000, not 2); ZFF2-FILL2 and
  ZFF2-FAULT failed as predicted; ZFF2-OTHER (printed) read held. Readings (printed): job 1 9 ticks,
  post sa0 0x00040000, sa1 0x005d1000, sa2 0x010204c4 (sa02kind OTHER), sa3-sa31 and pa0-pa15 equal
  WA's (sa3-sa12 the plant's float-like words and V0, V2, printed in every plant of the session); KC
  6 and 10 ok. Record E1237.
- Stage wb (row W, image mark, one job): rc 0, scored by the driver (score-wb.txt). Rescored by hand
  (fold/reproduce-wb-20261125-160752.out): the same bytes. `Q128-N3K-WB RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 8 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2. Record E1238.
- Stage lff2 (row LFF2, image land, begin draws fill,fill, jobs as LF2): exited 4 at its one row
  (class hang), the planned end; the driver did not score it. Scored with the frozen scorer after
  the run (closing29/r46-n3k-logs/score-r46-n3k-n1-lff2.txt) and again by hand
  (fold/reproduce-lff2-20261125-160752.out): the same bytes. PLANT, PG, E0, T0, J1, DR, DK and SV
  passed, B and J2 FAILED (read by the outcomes that name the stop). `Q128-N3K-LFF2 RULE: LFF2-KEEP,
  LFF2-SA0`; LFF2-KEEP and LFF2-SA0 held; **LFF2-PAGE0 FAILED** (predicted held: the fault is at
  M1's page, not page 0); LFF2-FILL2, -FILL1, -TRIPLE and -SERVE failed as predicted. Readings
  (printed): job 1 done (9 ticks), post sa0 0x00000002, sa1 = M1 0x005d1000, sa2 0x01015e75
  (sa02kind LF), sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT
  0x005d100f (page 0x005d1000; the scorer names job 1's post sa1), post, snap9 and the stop dump the
  same; job 2 never served; the tick stopped. KC begin delta 6 (ok); the end KC cannot tell. The
  kit's reset and both draws recovered it (health ok, closing29/r46-n3k-logs/health-r46-n3k-n1.log).
  Record E1239.
- Post sa3-sa31 and pa0-pa15 equal in wa, zff2 and wb; lff2's equal them but for sa24, sa26, pa12
  and pa14, land's markers Ma and Mb (printed).
- [post hoc, infer] Two fills left M1 with crumbz and with land in the same session; LFF's
  0x04000010 (E1217) did not come back. ZFF2's sa0 0x00040000 is a word no read had shown (bit 18
  alone); one read.
- [post hoc, infer] With sa0 2 and M1 in sa1, LF and LF2 (one fill, module 079DD0D1) stopped at page
  0, and every stop of this round with that bank (two or three fills, module 10BBF3BF) stopped at
  M1's page. The fill count and the module changed together; no row of rounds 44-46 splits them.
