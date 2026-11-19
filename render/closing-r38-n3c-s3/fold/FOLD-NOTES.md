# r38-n3c-s3 fold notes (folder, 2026-11-19)

- One attempt, out/20261119-112717 (the lead, user present), on the r38-kernel module
  88ADCEB5AD9F055D077A99C (fork e1cf9d2b43ab, closing29/kernel38/deliver/e1cf9d2b43ab/manifest;
  KUnit all pass), installed and loaded alike, the same one-shot boot as r38-n3c-s4, which ran
  first (attempt 20261119-112618).
- The arm logged `own_code: 644 bytes accepted` and `own task armed: slots 0x1, ... emit image
  0x30011100 ... pds=crumb3 pdsat=fw14`; `own_arm` read `... pds=crumb3 pdsat=fw14 blob=644`;
  health ok, ticks advancing (217, 246, 274) at 986 Hz. The image: crumb3 (crumb's 8 data
  dwords, four zero dwords, crumb's 7 instructions; 19 dwords), control 0x01800100 (3 rows), at
  offset 0x100 of the firmware's PDS #14 buffer page (page 0x30011000: past #14's 0x68-byte image,
  rounded up to 0x100), with that page's PTE and flags. Only our bytes and the address are
  recorded here; the page's firmware bytes are not read or kept.
- c1-a: no done within 200 ms, runner rc 1, the kit classed it `hang` (`firmware hung: the tick
  stopped`), stage rc 4; post did not run.
- The frozen scorer, run on the kept directory (fold/reproduce-own.out): every control passed (PG,
  E0, T0, B), `N3c-M RULE: M-NEVER: the program never started (T running, S1 fill): page, flags
  and rows are not the cause`; X0 0x5a5a3303, S1 and M4 the host's fill, state 0; T (0x0acc)
  0x0102837d in snap9 and 0x010565ab in the stop dump, bit 24 set and counting; Δtick 9 in a
  237.4 ms window; alive false (ticks 2114 three times, serv_event 67655 three times).
- T reads as E1150's B: crumb3's first instruction is crumb's `movs tim` of a stopped 0, which
  never showed. That reading rests on E1152 (a client program's `movs tim` lands at the host's
  0x0acc at once) and on the inference that an emitted program's would land the same way.
- Read from the kept files (not frozen): snap0 0x0acc 0x0104d5e4; BIF_FAULT 0 throughout; the
  reset after the stop recovered (t30 triangle `diff: 0 of 4096`, fill `diff: 0 of 2048`); the
  disarm's reset rebuilds the firmware's buffers and zeroes the page's slack (README; KUnit
  `fw14_disarm`).
- The SIGNATURE line is printed, not scored: USE0_SERV_EVENT bit 16 set at snap0, snap9 and the
  stop dump, count minus tick 5 in each.
- R6 (`P`, session r38-n3c-s5) and R7 (`W`, r38-n3c-s6) were built but not run: the design runs
  them only after M-T1 .. M-DONE (closing29/n3c/design.md §2.2); after M-NEVER the cause is in
  V4/V5 and the next step is a user decision.
- No vectors table: an owntask row is no table kind. sgx-sim refuses an emit from our own task
  (8754f2d); a test now runs crumb's program with 3 rows from a page past another and cites this
  record.
- Records: E1154 (this session); E1153 is r38-n3c-s4.
