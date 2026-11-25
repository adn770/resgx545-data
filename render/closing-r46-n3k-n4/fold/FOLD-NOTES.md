# r46-n3k-n4 fold notes (folder, 2026-11-25)

- One attempt, out/20261125-161145 (16:11:45), the sixth session of round 46, after N3
  (closing29/r46-n3k-logs/runone-N4.out, run rc 4: q2's planned stop). Session N4 of
  closing29/n3k/design.md (sections 4.2, 4.7; decision D (a)). Kit: resgx545 eaee04a4 (branch
  r46-n3k: K10's `pds=landr|landp`, unused here), the blob emitsb_sbc43s, `form=sbc43` (sideband
  0xc43) at fw14.
- Stage we (row W, image mark, one job): rc 0, scored by the driver (score-we.txt). Rescored by hand
  (fold/reproduce-we-20261125-161145.out): the same bytes. `Q128-N3K-WE RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed, SV included; every prediction held. Job 1 8 ticks; post sa1 = M1,
  sa13 = pa1 = M13, sa0 = V0, sa2 = V2. Record E1244.
- Stage q2 (row Q2, image landq, no begin draws, jobs as Q): exited 4 at its one row (class hang),
  the planned end; the driver did not score it. Scored with the frozen scorer after the run
  (closing29/r46-n3k-logs/score-r46-n3k-n4-q2.txt) and again by hand
  (fold/reproduce-q2-20261125-161145.out): the same bytes. `Q128-N3K-Q2 RULE: Q2-SAME, Q2-WRITE`;
  PG, E0, T0, J1, SV and PLANT (printed only) passed, B and J2 FAILED (read by the outcomes that
  name the stop); every prediction held. Readings (printed): job 1 done (9 ticks), post sa0
  0x005d2000, sa1 0x005d1000, sa2 V2, sa13 = M13; job 2's K5 pre already BIF_FAULT 0x005d100f, post,
  snap9 and the stop dump the same; job 2 never served. KC begin 2 (ok). The kit's reset and both
  draws recovered it (health ok, closing29/r46-n3k-logs/health-r46-n3k-n4.log). Record E1245.
- [post hoc, infer] Q's read and stop (E1233, module EC553F41) repeated on 10BBF3BF: the one stop
  shape of rounds 45-46 read on two modules that agreed.
- Sessions N5-N8 (rows WF, R, WG, P, WH, R2, WI, P2: landr and landp) were built and frozen but not
  run: the user stopped the round after N4. Nothing of them is folded.
