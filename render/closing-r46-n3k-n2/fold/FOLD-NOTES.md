# r46-n3k-n2 fold notes (folder, 2026-11-25)

- One attempt, out/20261125-160955 (16:09:56), the fourth session of round 46, after N1
  (closing29/r46-n3k-logs/runone-N2.out, run rc 4: lff3's planned stop). Session N2 of
  closing29/n3k/design.md (sections 4.2, 4.4). Kit: resgx545 eaee04a4 (branch r46-n3k: K10's
  `pds=landr|landp`, unused here), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14.
- Stage wc (row W, image mark, one job): rc 0, scored by the driver (score-wc.txt). Rescored by hand
  (fold/reproduce-wc-20261125-160955.out): the same bytes. `Q128-N3K-WC RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 9 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2. Record E1240.
- Stage lff3 (row LFF3, image land, begin draws fill,fill, jobs as LF2): exited 4 at its one row
  (class hang), the planned end; the driver did not score it. Scored with the frozen scorer after
  the run (closing29/r46-n3k-logs/score-r46-n3k-n2-lff3.txt) and again by hand
  (fold/reproduce-lff3-20261125-160955.out): the same bytes. PLANT, PG, E0, T0, J1, DR, DK and SV
  passed, B and J2 FAILED (read by the outcomes that name the stop). `Q128-N3K-LFF3 RULE: LFF3-KEEP,
  LFF3-SA0`; LFF3-KEEP and LFF3-SA0 held; **LFF3-PAGE0 FAILED** (predicted held: the fault is at
  M1's page, not page 0); LFF3-FILL2, -FILL1, -TRIPLE and -SERVE failed as predicted. Readings
  (printed): job 1 done (9 ticks), post sa0 0x00000002, sa1 = M1 0x005d1000, sa2 0x0102298f
  (sa02kind LF), sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT
  0x005d100f (page 0x005d1000; the scorer names job 1's post sa1), post, snap9 and the stop dump the
  same; job 2 never served; the tick stopped. KC begin delta 6 (ok); the end KC cannot tell. The
  kit's reset and both draws recovered it (health ok, closing29/r46-n3k-logs/health-r46-n3k-n2.log).
  Record E1241.
- Post sa3-sa31 and pa0-pa15 equal in wc and lff3, sa24 and sa26 holding Ma and Mb from N1's land
  read (printed).
- [post hoc, infer] With sa0 2 and M1 in sa1, LF and LF2 (one fill, module 079DD0D1) stopped at page
  0, and every stop of this round with that bank (two or three fills, module 10BBF3BF) stopped at
  M1's page. The fill count and the module changed together; no row of rounds 44-46 splits them.
