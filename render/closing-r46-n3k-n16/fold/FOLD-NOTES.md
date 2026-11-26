# r46-n3k-n16 fold notes (folder, 2026-11-26)

- One attempt, out/20261126-080355 (08:03:55), the last session of the addendum, after N15
  (closing29/r46-n3k-logs/runone-N16.out, run rc 4: p2's planned stop). Rows W16 and P2, N14 byte
  for byte but their names (decision J (a)). Kit: resgx545 b4e31c76 (branch r46-n3k2 on r46-n3k:
  K10's `pds=landr|landp`, K11's PAD control, armed only in N12, which did not run), the blob
  emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14. Module 10BBF3BFBD51D559106589F (fork
  r46-kernel c5094783eb88) on round 46's one boot: no rebuild, install or boot since N4 (E12 held,
  sa12 = V0, in every row).
- Stage w16 (row W, image mark, one job): rc 0, scored by the driver (score-w16.txt). Rescored by
  hand (fold/reproduce-w16-20261126-080355.out): the same bytes. `Q128-N3K-W16 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 8 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2; KC begin N0 517, delta 10, end delta 2 (ok). Record E1258.
- Stage p2 (row P2, image landp, begin draws none, jobs as LF2): exited 4 at its one row (class
  hang), the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n16-p2.txt) and again by hand
  (fold/reproduce-p2-20261126-080355.out): the same bytes. `Q128-N3K-P2 RULE: P2-E12, P2-UNMAP,
  P2-WRITE`; PG, E0, T0, J1, DR, DK, SV and PLANT passed, B and J2 FAILED (read by the outcomes that
  name the stop). Every prediction held: P2-WRITE, P2-UNMAP and P2-E12 held; P2-MAPPED and P2-SUM
  failed as predicted; P2-OTHER (printed) read failed. PLANT is printed only. Readings (printed):
  job 1 done (9 ticks), post sa0 0x32004000 (V0), sa1 0x005d2000, sa2 0x32002000 (V2, sa02kind ONE),
  sa12 = V0, sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT 0x005d200f
  (page 0x005d2000) (the scorer names job 1's post sa1), post, snap9 and the stop dump the same; job
  2 never served; the tick stopped. KC begin N0 532, delta 2 (ok); the arm's stop line '0 events
  seen'; the end KC cannot tell. The kit's reset and both draws recovered it (health ok,
  closing29/r46-n3k-logs/health-r46-n3k-n16.log). Record E1259.
- Post sa3-sa31 and pa0-pa15 equal in both stages of the session and in every stage of the addendum,
  and equal N4's q2's (sa12 = pa0 = V0, sa13 = pa1 = M13, sa24 and sa26 = pa12 and pa14 land's Ma
  and Mb; printed).
- [post hoc, infer] P's read and stop a second time: 0x005d2000 unmapped, two reads.
- Session N12 (rows W12 and LFKP, the K pad) was built and frozen but not run: the user skipped it
  after the H-RACE stop. Nothing of it is folded.
