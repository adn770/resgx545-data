# r45-n3j-n6 fold notes (folder, 2026-11-25)

- One attempt, out/20261125-092604 (09:26:04), on module EC553F41FD8324BB6BF1764 (fork r45-kernel
  b1089172b2e7, the second one-shot boot of 2026-11-25; the laptop event before it is in N5's
  fold notes), the sixth session of round 45, after N5 (closing29/r45-n3j-z-logs/runone-N6.out,
  run rc 4: q's planned stop). Session N6 of closing29/n3j/design.md (section 9.5; decision E
  (c)). Kit: resgx545 cf20aa87.
- Stage wq (row W, image mark, one job; the kit keeps a session's first stage on the default
  begin draws, so N6 plants before q): rc 0, scored by the driver (score-wq.txt). Rescored by hand
  (fold/reproduce-wq-20261125-092604.out): the same bytes. `Q128-N3J-WQ RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held.
- Stage q (row Q, image landq: Q0 0x005d2000 to attribute 0 and M1 0x005d1000 to attribute 1, no
  draws, jobs as lm): exited 4 at its one row (class hang), the planned end; the driver did not
  score it. Scored with the frozen scorer after the run
  (closing29/r45-n3j-z-logs/score-r45-n3j-n6-q.txt) and again by hand
  (fold/reproduce-q-20261125-092604.out): the same bytes. `Q128-N3J-Q RULE: Q-WRITE`; SV, PG, E0,
  T0, J1, DR and DK passed, B and J2 FAILED (the stop). Q-WRITE held as predicted; **Q-SA0
  FAILED** (predicted held: the fault is at 0x005d1000, sa1's page, not 0x005d2000); Q-LOW
  (predicted failed) read held but is scored `cannot tell` by the frozen rule ("a fault at
  0x005d1000 with Q-WRITE held cannot tell 'lowest page' from 'sa0 mapped'"); Q-SERVE failed as
  predicted; Q-OTHER (printed) read failed.
- Readings (printed): q's job 1 done (9 ticks), post sa0 0x005d2000 = Q0, sa1 0x005d1000 = M1,
  sa2 0x32002000 = V2 (wq's plant kept), sa13 = pa1 = M13, sa24 = pa12 Ma 0x5a5a3a18 and sa26 =
  pa14 Mb 0x5a5a3a1a (landq's markers); job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT
  0x005d100f (list 15, page 0x005d1000; the scorer names job 1's post sa1), post, snap9 and the
  stop dump the same; job 2 never served; the tick stopped. KC begin delta 2 (no draws, ok).
  Kernel: q's arm "0 events seen". The kit's reset and both draws recovered it (health ok,
  closing29/r45-n3j-z-logs/health-r45-n3j-n6.log).
- [post hoc, infer] With both sa0 and sa1 holding words our rows never saw mapped, sa0 the higher,
  the stop faulted at sa1's page: H-SA0 as "the pass reads sa0 first and stops at the first
  unmapped word" fails unless 0x005d2000 is mapped. Two readings survive, not told apart: the
  lowest faulting page, and sa0 first with 0x005d2000 mapped.
- Records: E1232 (wq), E1233 (q).
