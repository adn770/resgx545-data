# r46-n3k-n13 fold notes (folder, 2026-11-26)

- One attempt, out/20261126-080112 (08:01:12, 2026-11-26), after the user's choice (N13-N16, N12
  skipped), N11 the session before (23:14) on the same boot (closing29/r46-n3k-logs/runone-N13.out,
  run rc 4: r's planned stop). Rows W13 and R of design sections 4.8 and 11.4 (decision I (a)). Kit:
  resgx545 b4e31c76 (branch r46-n3k2 on r46-n3k: K10's `pds=landr|landp`, K11's PAD control, armed
  only in N12, which did not run), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14.
  Module 10BBF3BFBD51D559106589F (fork r46-kernel c5094783eb88) on round 46's one boot: no rebuild,
  install or boot since N4 (E12 held, sa12 = V0, in every row).
- Stage w13 (row W, image mark, one job): rc 0, scored by the driver (score-w13.txt). Rescored by
  hand (fold/reproduce-w13-20261126-080112.out): the same bytes. `Q128-N3K-W13 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 9 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2; KC begin N0 406, delta 10, end delta 2 (ok). Record E1252.
- Stage r (row R, image landr, begin draws none, jobs as LF2): exited 4 at its one row (class hang),
  the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n13-r.txt) and again by hand
  (fold/reproduce-r-20261126-080112.out): the same bytes. `Q128-N3K-R RULE: R-E12, R-LOW, R-WRITE`;
  PG, E0, T0, J1, DR, DK, SV and PLANT passed, B and J2 FAILED (read by the outcomes that name the
  stop). Every prediction held: R-WRITE, R-LOW and R-E12 held; R-SA0, R-SUM and R-SERVE failed as
  predicted; R-OTHER (printed) read failed. PLANT is printed only (landr writes sa0 and sa1 itself).
  Readings (printed): job 1 done (9 ticks), post sa0 0x04400000, sa1 0x005d1000 (M1), sa2 0x32002000
  (V2, sa02kind OTHER), sa12 = V0, sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400,
  BIF_FAULT 0x005d100f (page 0x005d1000) (the scorer names job 1's post sa1), post, snap9 and the
  stop dump the same; job 2 never served; the tick stopped. KC begin N0 421, delta 2 (ok); the arm's
  stop line '0 events seen'; the end KC cannot tell. The kit's reset and both draws recovered it
  (health ok, closing29/r46-n3k-logs/health-r46-n3k-n13.log). Record E1253.
- Post sa3-sa31 and pa0-pa15 equal in both stages of the session and in every stage of the addendum,
  and equal N4's q2's (sa12 = pa0 = V0, sa13 = pa1 = M13, sa24 and sa26 = pa12 and pa14 land's Ma
  and Mb; printed).
- [post hoc, infer] With two pages known unmapped, 0x04400000 in sa0 and M1 in sa1, the stop went to
  the lower, sa1's; not to sa0 + sa12 (0x36404000).
