# r44-n3i-n3 fold notes (folder, 2026-11-24)

- One attempt, out/20261124-010057, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87; no rebuild or boot for round 44), the third session of round 44, after N2
  (closing29/r44-n3i-logs/runone-N3.out, run rc 4: lf's planned stop). Session N3 of
  closing29/n3i/design.md (sections 3.1 and 3.5; decisions A-E all (a), 2026-11-23). Kit and blob:
  resgx545 ce01a0c4.
- Stage wf (row W, image mark, one job): rc 0, scored by the driver (score-wf.txt). Rescored by
  hand (fold/reproduce-wf-20261124-010057.out): the same bytes. `Q128-N3I-WF RULE: W-QUIET,
  W-SA1, W-SA13`; every control passed; every prediction held (W-FAULT failed as predicted).
- Stage lf (row LF, image land, begin draws fill, job 1 the emit with the tick running, job 2
  command 6 on the next tick pass): exited 4 at its one row (class hang), the planned end; the
  driver did not score it. Scored with the frozen scorer after the run
  (closing29/r44-n3i-logs/score-r44-n3i-n3-lf.txt) and again by hand
  (fold/reproduce-lf-20261124-010057.out): the same bytes. `Q128-N3I-LF RULE: LF-EARLY0`; PLANT,
  PG, E0, T0, J1 and DR passed, B and J2 FAILED (read by LF-EARLY0, which names the stop).
  **LF-SA1 FAILED** (predicted held: post sa1 is M1, not 0x01000000); **LF-EVT FAILED**
  (predicted held: post sa0 is 2, not 0); LF-EARLY0 held as predicted; LF-TICK, LF-ONE,
  LF-EARLY1 and LF-SERVE failed as predicted; LF-AOTHER (printed) read held.
- Readings (printed): lf's job 1 done, post sa0 0x00000002, sa1 = M1 0x005d1000, sa2 0x01049b60
  (sa02kind OTHER), sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT
  0x0000000f (list 15, page 0; the scorer names job 1's post sa0), post, snap9 and the stop dump
  the same; job 2 never served; the tick stopped. Kernel: lf's arm after the one fill "1 events
  seen". The kit's reset and both draws recovered it (health ok,
  closing29/r44-n3i-logs/health-r44-n3i-n3.log).
- LM-V0 held in N2, so LF's attribute-0 and -2 outcomes are not cannot-tell (the design's
  fold-time rule).
- [post hoc, infer] One fill after the plant left attribute 1's M1 (as two fills in N1's ff) and
  changed sa0 to 2 and sa2 to 0x01049b60; with sa0 below a page the stop faulted at page 0, with
  sa1 = M1 unmapped too. Together with lm (sa0 = V0: sa1's page) this fits a stop through sa0,
  then sa1 (H-SA0).
- Records: E1199 (wf), E1200 (lf).
