# r46-n3k-n9 fold notes (folder, 2026-11-26)

- One attempt, out/20261125-231114 (23:11:14), the first session of round 46's addendum
  (closing29/n3k/design.md section 11, decisions G-K all (a)), after N4 (16:12) on the same boot
  (closing29/r46-n3k-logs/runone-N9.out, run rc 4: lfk's planned stop). Kit: resgx545 b4e31c76
  (branch r46-n3k2 on r46-n3k: K10's `pds=landr|landp`, K11's PAD control, armed only in N12, which
  did not run), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14. Module
  10BBF3BFBD51D559106589F (fork r46-kernel c5094783eb88) on round 46's one boot: no rebuild, install
  or boot since N4 (E12 held, sa12 = V0, in every row).
- The addendum ran N9, N10, N11, then (after the design's section 11.8 stop: LFK and LFK2 disagreed,
  H-RACE) the user's choice, N13, N14, N15, N16; N12 (LFKP, the K pad) was skipped and is not
  folded. N5-N8 stay frozen and unrun.
- Stage w9 (row W, image mark, one job): rc 0, scored by the driver (score-w9.txt). Rescored by hand
  (fold/reproduce-w9-20261125-231114.out): the same bytes. `Q128-N3K-W9 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 10 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2; KC begin N0 285, delta 10, end delta 2 (ok). Record E1246.
- Stage lfk (row LFK, image land, begin draws fill, jobs as LF2): exited 4 at its one row (class
  hang), the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n9-lfk.txt) and again by hand
  (fold/reproduce-lfk-20261125-231114.out): the same bytes. `Q128-N3K-LFK RULE: LFK-E12`; PG, E0,
  T0, J1, DR, DK, SV and PLANT passed, B and J2 FAILED (read by the outcomes that name the stop).
  LFK-E12 held; **LFK-SA and LFK-M1 FAILED** (predicted held: sa1 0x01000000, not M1, and the fault
  at its page); LFK-PAGE0 and LFK-SERVE failed as predicted; LFK-OTHER (printed) read held. HKC
  (printed): fill 1: 3:4 K 2 0x02000010. Readings (printed): job 1 done (10 ticks), post sa0
  0x00000002, sa1 0x01000000, sa2 0x0103cb65 (sa02kind LF), sa12 = V0, sa13 = pa1 = M13; job 2's K5
  pre already BIF_INT_STAT 0x000d0400, BIF_FAULT 0x0100000f (page 0x01000000) (the scorer names job
  1's post sa1), post, snap9 and the stop dump the same; job 2 never served; the tick stopped. KC
  begin N0 300, delta 4 (ok); the arm's stop line '1 events seen'; the end KC cannot tell. The kit's
  reset and both draws recovered it (health ok, closing29/r46-n3k-logs/health-r46-n3k-n9.log).
  Record E1247.
- Post sa3-sa31 and pa0-pa15 equal in both stages of the session and in every stage of the addendum,
  and equal N4's q2's (sa12 = pa0 = V0, sa13 = pa1 = M13, sa24 and sa26 = pa12 and pa14 land's Ma
  and Mb; printed).
- [post hoc, infer] One fill on this boot did not stop at page 0 (C-FILL's prediction failed); sa1
  read row F's 0x01000000 (E1187), not M1, and the stop followed it.
