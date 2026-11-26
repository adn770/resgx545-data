# r46-n3k-n11 fold notes (folder, 2026-11-26)

- One attempt, out/20261125-231324 (23:13:24), the third session of the addendum, after N10
  (closing29/r46-n3k-logs/runone-N11.out, run rc 4: lfk2's planned stop). Kit: resgx545 b4e31c76
  (branch r46-n3k2 on r46-n3k: K10's `pds=landr|landp`, K11's PAD control, armed only in N12, which
  did not run), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14. Module
  10BBF3BFBD51D559106589F (fork r46-kernel c5094783eb88) on round 46's one boot: no rebuild, install
  or boot since N4 (E12 held, sa12 = V0, in every row).
- Stage w11 (row W, image mark, one job): rc 0, scored by the driver (score-w11.txt). Rescored by
  hand (fold/reproduce-w11-20261125-231324.out): the same bytes. `Q128-N3K-W11 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 8 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2; KC begin N0 367, delta 10, end delta 2 (ok). Record E1250.
- Stage lfk2 (row LFK2, image land, begin draws fill, jobs as LF2): exited 4 at its one row (class
  hang), the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n11-lfk2.txt) and again by hand
  (fold/reproduce-lfk2-20261125-231324.out): the same bytes. `Q128-N3K-LFK2 RULE: LFK2-E12, LFK2-M1,
  LFK2-SA`; PG, E0, T0, J1, DR, DK, SV and PLANT passed, B and J2 FAILED (read by the outcomes that
  name the stop). Every prediction held: LFK2-E12, LFK2-M1 and LFK2-SA held; LFK2-PAGE0 and
  LFK2-SERVE failed as predicted; LFK2-OTHER (printed) read failed. HKC (printed): fill 1: 3:4 K 2
  0x02000010. Readings (printed): job 1 done (9 ticks), post sa0 0x00000002, sa1 0x005d1000 (M1),
  sa2 0x0101bf25 (sa02kind LF), sa12 = V0, sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT
  0x000d0400, BIF_FAULT 0x005d100f (page 0x005d1000) (the scorer names job 1's post sa1), post,
  snap9 and the stop dump the same; job 2 never served; the tick stopped. KC begin N0 382, delta 4
  (ok); the arm's stop line '1 events seen'; the end KC cannot tell. The kit's reset and both draws
  recovered it (health ok, closing29/r46-n3k-logs/health-r46-n3k-n11.log). Record E1251.
- Post sa3-sa31 and pa0-pa15 equal in both stages of the session and in every stage of the addendum,
  and equal N4's q2's (sa12 = pa0 = V0, sa13 = pa1 = M13, sa24 and sa26 = pa12 and pa14 land's Ma
  and Mb; printed).
- [post hoc, infer] LFK and LFK2, the same stage two minutes apart, disagree on sa1 (0x01000000
  against M1) and on the stop page, which followed sa1 both times; neither stopped at page 0. The
  design's section 11.8 stop (H-RACE) applied to N12-N16: stopped for the user.
