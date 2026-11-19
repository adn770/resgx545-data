# r38-n3c-s4 fold notes (folder, 2026-11-19)

- One attempt, out/20261119-112618 (the lead, user present), on the r38-kernel module
  88ADCEB5AD9F055D077A99C (fork e1cf9d2b43ab, closing29/kernel38/deliver/e1cf9d2b43ab/manifest;
  KUnit all pass), installed and loaded alike, after the one-shot boot of 2026-11-19. S4 ran
  first on that boot, then r38-n3c-s3 (attempt 20261119-112717) on the same boot.
- The arm logged `own_code: 644 bytes accepted` and `own task armed: slots 0x1, ... emit image
  0x30022000 ... pds=halt pdsat=own`; `own_arm` read `... pds=halt pdsat=own blob=644`; health
  ok, ticks advancing (198, 228, 255) at 962 Hz. The image: v1's 8 data dwords and a lone
  `halt`, control 0x01000100 (2 rows), in the kernel's own read-only image page, as r37.
- c1-a: no done within 200 ms, runner rc 1, the kit classed it `hang` (`firmware hung: the tick
  stopped`), stage rc 4; post did not run (halt has no `doutu`: the job cannot report done, so a
  runner stop was the design's only end for this row).
- The frozen scorer, run on the kept directory (fold/reproduce-own.out): every control passed (PG,
  E0, T0, B), `N3c-H RULE: H-STOP: any program stops the EDM, no instruction needed`; X0
  0x5a5a3303, S1 and M4 the host's fill, state 0; Δtick 9 in a 237.4 ms window; alive false
  (ticks 2554 three times, serv_event 68095 three times).
- Read from the kept files (not frozen): 0x0acc 0x0100c93b at snap0, 0x01059309 in snap9 and
  0x0104a155 in the stop dump, bit 24 set and counting (halt writes no `tim`, so T is no reading
  here); BIF_FAULT 0 throughout; the reset after the stop recovered (t30 triangle `diff: 0 of
  4096`, fill `diff: 0 of 2048`).
- The SIGNATURE line is printed, not scored: USE0_SERV_EVENT bit 16 set at snap0, snap9 and the
  stop dump, count minus tick 5 in each, as in E1148-E1151.
- No vectors table: an owntask row is no table kind. sgx-sim refuses an emit from our own task
  (8754f2d); a test now runs the halt image and cites this record.
- Records: E1153 (this session); E1154 is r38-n3c-s3.
