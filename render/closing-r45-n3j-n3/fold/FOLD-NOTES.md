# r45-n3j-n3 fold notes (folder, 2026-11-25)

- One attempt, out/20261124-210651, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87; no rebuild or boot before N1-N4), the third session of round 45, after N2
  (closing29/r45-n3j-logs/runone-N3.out, run rc 4: lt's planned stop). Session N3 of
  closing29/n3j/design.md (sections 3.1 and 3.5; decisions A=a, B=a, C=a, D=b, E=c, F=a). Kit and
  blob: resgx545 94f9e501 (K9).
- Stage wh (row W, image mark, one job): rc 0, scored by the driver (score-wh.txt). Rescored by
  hand (fold/reproduce-wh-20261124-210651.out): the same bytes. `Q128-N3J-WH RULE: W-QUIET,
  W-SA1, W-SA13`; every control passed; every prediction held (W-FAULT failed as predicted).
- Stage lt (row LT, image land, begin draws tri, jobs as lf2): exited 4 at its one row (class
  hang), the planned end; the driver did not score it. Scored with the frozen scorer after the
  run (closing29/r45-n3j-logs/score-r45-n3j-n3-lt.txt) and again by hand
  (fold/reproduce-lt-20261124-210651.out): the same bytes. `Q128-N3J-LT RULE: LT-PAGE, LT-SA1,
  LT-TRIPLE`; PLANT, PG, E0, T0, J1, DR and DK passed, B and J2 FAILED (read by LT-PAGE, which
  names the stop). Every prediction held: LT-SA1, LT-TRIPLE and LT-PAGE held; LT-ONE, LT-HIST and
  LT-SERVE failed as predicted; LT-AOTHER (printed) read failed.
- Readings (printed): lt's job 1 done (9 ticks), post sa0 0x00000000, sa1 0x02400000, sa2
  0x01048c28 (sa02kind TRIPLE), sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400,
  BIF_FAULT 0x0000000f (page 0; the scorer names job 1's post sa0), post, snap9 and the stop dump
  the same; job 2 never served; the tick stopped. KC begin delta 8 (one triangle, ok); the end KC
  cannot tell (the stop). Kernel: lt's arm after the triangle "2 events seen". The kit's reset and
  both draws recovered it (health ok, closing29/r45-n3j-logs/health-r45-n3j-n3.log).
- Post sa3-sa31 and pa0-pa15 equal in wh and lt, and equal to N2's (printed).
- LT-ONE failed as predicted (sa0 is 0, not V0), so LT-PAGE against LT-HIST is not the split of
  H-SA0 from H-HIST the design hoped for: both name page 0 here.
- [post hoc, infer] A triangle alone leaves (0, 0x02400000, a timer word) in sa0-sa2, H-KC's triple
  of its 3:22 entry; with sa0 0 the stop faults at page 0 as LC's did (E1176, E1178).
- Records: E1214 (wh), E1215 (lt).
