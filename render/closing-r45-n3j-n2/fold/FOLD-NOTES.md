# r45-n3j-n2 fold notes (folder, 2026-11-25)

- One attempt, out/20261124-210558, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87; no rebuild or boot before N1-N4), the second session of round 45, after N1
  (closing29/r45-n3j-logs/runone-N2.out, run rc 4: lf2's planned stop). Session N2 of
  closing29/n3j/design.md (sections 3.1 and 3.4; decisions A=a, B=a, C=a, D=b, E=c, F=a). Kit and
  blob: resgx545 94f9e501 (K9).
- Stage wg (row W, image mark, one job): rc 0, scored by the driver (score-wg.txt). Rescored by
  hand (fold/reproduce-wg-20261124-210558.out): the same bytes. `Q128-N3J-WG RULE: W-QUIET,
  W-SA1, W-SA13`; every control passed; every prediction held (W-FAULT failed as predicted).
- Stage lf2 (row LF2, image land, begin draws fill, job 1 the emit with the tick running, job 2
  command 6 on the next tick pass): exited 4 at its one row (class hang), the planned end; the
  driver did not score it. Scored with the frozen scorer after the run
  (closing29/r45-n3j-logs/score-r45-n3j-n2-lf2.txt) and again by hand
  (fold/reproduce-lf2-20261124-210558.out): the same bytes. `Q128-N3J-LF2 RULE: LF2-EARLY0,
  LF2-PAGE, LF2-SA0, LF2-SA1, LF2-SA2`; PLANT, PG, E0, T0, J1, DR and DK passed, B and J2 FAILED
  (read by LF2-EARLY0 and LF2-PAGE, which name the stop). Every prediction held: LF2-SA1, LF2-SA0,
  LF2-SA2, LF2-PAGE and LF2-EARLY0 held; LF2-TICK, LF2-EARLY1 and LF2-SERVE failed as predicted;
  LF2-AOTHER (printed) read failed.
- Readings (printed): lf2's job 1 done (9 ticks), post sa0 0x00000002, sa1 = M1 0x005d1000, sa2
  0x0105bab1 (sa02kind LF), sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400,
  BIF_FAULT 0x0000000f (list 15, page 0; the scorer names job 1's post sa0), post, snap9 and the
  stop dump the same; job 2 never served; the tick stopped. KC begin delta 4 (one fill, ok); the
  end KC cannot tell (the stop: no exit load). Kernel: lf2's arm after the one fill "1 events
  seen". The kit's reset and both draws recovered it (health ok,
  closing29/r45-n3j-logs/health-r45-n3j-n2.log).
- Post sa3-sa31 and pa0-pa15 equal in wg and lf2, but differ from N1's at sa3-sa12, sa14, sa16
  and pa0, pa2, pa4 (sa3 0x04000004, sa4 0x00030001, sa5 0x04000000, sa6-sa9 0x42000000, sa10 and
  sa11 0x3f000000, sa12 0, sa14 = pa2 0x3727c5ac, sa16 = pa4 0, pa0 0), the same in N3 and N4
  (printed, not scored).
- [post hoc, infer] LF's triple (2, M1, a timer word) and its page-0 stop repeat: the two-read rule
  is met for one fill before land.
- Records: E1212 (wg), E1213 (lf2).
