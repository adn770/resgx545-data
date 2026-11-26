# r46-n3k-n15 fold notes (folder, 2026-11-26)

- One attempt, out/20261126-080300 (08:03:00), after N14 (closing29/r46-n3k-logs/runone-N15.out, run
  rc 4: r2's planned stop). Rows W15 and R2, N13 byte for byte but their names (decision J (a)).
  Kit: resgx545 b4e31c76 (branch r46-n3k2 on r46-n3k: K10's `pds=landr|landp`, K11's PAD control,
  armed only in N12, which did not run), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at
  fw14. Module 10BBF3BFBD51D559106589F (fork r46-kernel c5094783eb88) on round 46's one boot: no
  rebuild, install or boot since N4 (E12 held, sa12 = V0, in every row).
- Stage w15 (row W, image mark, one job): rc 0, scored by the driver (score-w15.txt). Rescored by
  hand (fold/reproduce-w15-20261126-080300.out): the same bytes. `Q128-N3K-W15 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 9 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2; KC begin N0 480, delta 10, end delta 2 (ok). Record E1256.
- Stage r2 (row R2, image landr, begin draws none, jobs as LF2): exited 4 at its one row (class
  hang), the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n15-r2.txt) and again by hand
  (fold/reproduce-r2-20261126-080300.out): the same bytes. `Q128-N3K-R2 RULE: R2-E12, R2-LOW,
  R2-WRITE`; PG, E0, T0, J1, DR, DK, SV and PLANT passed, B and J2 FAILED (read by the outcomes that
  name the stop). Every prediction held: R2-WRITE, R2-LOW and R2-E12 held; R2-SA0, R2-SUM and
  R2-SERVE failed as predicted; R2-OTHER (printed) read failed. PLANT is printed only. Readings
  (printed): job 1 done (9 ticks), post sa0 0x04400000, sa1 0x005d1000 (M1), sa2 0x32002000 (V2,
  sa02kind OTHER), sa12 = V0, sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400,
  BIF_FAULT 0x005d100f (page 0x005d1000) (the scorer names job 1's post sa1), post, snap9 and the
  stop dump the same; job 2 never served; the tick stopped. KC begin N0 495, delta 2 (ok); the arm's
  stop line '0 events seen'; the end KC cannot tell. The kit's reset and both draws recovered it
  (health ok, closing29/r46-n3k-logs/health-r46-n3k-n15.log). Record E1257.
- Post sa3-sa31 and pa0-pa15 equal in both stages of the session and in every stage of the addendum,
  and equal N4's q2's (sa12 = pa0 = V0, sa13 = pa1 = M13, sa24 and sa26 = pa12 and pa14 land's Ma
  and Mb; printed).
- [post hoc, infer] R's read and stop a second time: two reads agree.
