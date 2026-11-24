# r44-n3i-n2 fold notes (folder, 2026-11-24)

- One attempt, out/20261124-010001, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87; no rebuild or boot for round 44), the second session of round 44, after N1
  (closing29/r44-n3i-logs/runone-N2.out, run rc 4: lm's planned stop). Session N2 of
  closing29/n3i/design.md (sections 3.1 and 3.4; decisions A-E all (a), 2026-11-23). Kit and blob:
  resgx545 ce01a0c4.
- Stage wl (row W, image mark, one job): rc 0, scored by the driver (score-wl.txt). Rescored by
  hand (fold/reproduce-wl-20261124-010001.out): the same bytes. `Q128-N3I-WL RULE: W-QUIET,
  W-SA1, W-SA13`; every control passed; every prediction held (W-FAULT failed as predicted).
- Stage lm (row LM, image land, begin draws none, job 1 the emit with the tick running, job 2
  command 6 on the next tick pass): exited 4 at its one row (class hang), the planned end; the
  driver did not score it. Scored with the frozen scorer after the run
  (closing29/r44-n3i-logs/score-r44-n3i-n2-lm.txt) and again by hand
  (fold/reproduce-lm-20261124-010001.out): the same bytes. `Q128-N3I-LM RULE: LM-EARLY1,
  LM-KEEP, LM-V0`; PLANT, PG, E0, T0, J1 and DR passed, B and J2 FAILED (read by LM-EARLY1, which
  names the stop, the frozen rule); every prediction held (LM-OTHER, printed, read failed).
- Readings (printed): lm's job 1 done, post sa0 = V0 0x32004000, sa1 = M1 0x005d1000, sa2 = V2
  0x32002000, sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT
  0x005d100f (list 15, page 0x005d1000 = job 1's post sa1), post the same, snap9 and the stop dump
  the same; job 2 never served (cmd_after 6, dwords 224-255 0xdeadc0de); the tick stopped. Kernel:
  lm's arm with no draws "0 events seen"; the recovery's reset after both draws "3 events seen".
  The kit's reset and both draws recovered it (health ok,
  closing29/r44-n3i-logs/health-r44-n3i-n2.log).
- [post hoc, infer] land with V's bank (sa0 = V0, sa1 = M1) stops exactly as landv: at sa1's
  page. H-IMG fails; the image did not cause LC's page 0.
- Records: E1197 (wl), E1198 (lm).
