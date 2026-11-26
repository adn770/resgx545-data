# r46-n3k-n10 fold notes (folder, 2026-11-26)

- One attempt, out/20261125-231217 (23:12:17), the second session of the addendum, after N9
  (closing29/r46-n3k-logs/runone-N10.out, run rc 4: ltk's planned stop). Kit: resgx545 b4e31c76
  (branch r46-n3k2 on r46-n3k: K10's `pds=landr|landp`, K11's PAD control, armed only in N12, which
  did not run), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14. Module
  10BBF3BFBD51D559106589F (fork r46-kernel c5094783eb88) on round 46's one boot: no rebuild, install
  or boot since N4 (E12 held, sa12 = V0, in every row).
- Stage w10 (row W, image mark, one job): rc 0, scored by the driver (score-w10.txt). Rescored by
  hand (fold/reproduce-w10-20261125-231217.out): the same bytes. `Q128-N3K-W10 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 9 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2; KC begin N0 324, delta 10, end delta 2 (ok). Record E1248.
- Stage ltk (row LTK, image land, begin draws tri, jobs as LF2): exited 4 at its one row (class
  hang), the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n10-ltk.txt) and again by hand
  (fold/reproduce-ltk-20261125-231217.out): the same bytes. `Q128-N3K-LTK RULE: LTK-E12, LTK-PAST`;
  PG, E0, T0, J1, DR, DK, SV and PLANT passed, B and J2 FAILED (read by the outcomes that name the
  stop). LTK-E12 held; **LTK-SA and LTK-SA1 FAILED** (predicted held: sa0 2, not 0, sa1 0x01000000,
  not 0x02400000, and no fault at 0x02400000); **LTK-PAST read held against its prediction
  (failed)**: the fault at neither page 0 nor 0x02400000; LTK-PAGE0 and LTK-SERVE failed as
  predicted. HKC (printed): tri 1: 3:22 K 2 0x02400000; 3:4 K 2 0x02000010. Readings (printed): job
  1 done (9 ticks), post sa0 0x00000002, sa1 0x01000000, sa2 0x01061a74 (sa02kind LF), sa12 = V0,
  sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT 0x0100000f (page
  0x01000000) (the scorer names job 1's post sa1), post, snap9 and the stop dump the same; job 2
  never served; the tick stopped. KC begin N0 339, delta 8 (ok); the arm's stop line '2 events
  seen'; the end KC cannot tell. The kit's reset and both draws recovered it (health ok,
  closing29/r46-n3k-logs/health-r46-n3k-n10.log). Record E1249.
- Post sa3-sa31 and pa0-pa15 equal in both stages of the session and in every stage of the addendum,
  and equal N4's q2's (sa12 = pa0 = V0, sa13 = pa1 = M13, sa24 and sa26 = pa12 and pa14 land's Ma
  and Mb; printed).
- [post hoc, infer] After a triangle land read LFK's shape (2, 0x01000000, a timer word), not LT's
  and ZT's (0, 0x02400000) (E1215, E1221), though HKC printed the triangle's 3:22 entry with
  0x02400000 at K 2 as before. sa2 0x01061a74 differs from LFK's 0x0103cb65: two separate reads, not
  one word kept.
