# r40-s-s2 fold notes (folder, 2026-11-19)

- One attempt, out/20261119-170645 (the lead, user present), on module 0CDFCDB73D76F39FE9E593C
  (fork f9453424bf71), Z's boot (uptime 5593 s at the arm), no rebuild. Row S-S2: against Z only
  the emit word changes, our old word 0xfb20b00000008184 (sideband 0), blob emitsk (K's), armed
  without `form=fw14` (the kernel pairs the word with `form=`) and with `pds2=req`.
- The arm logged `own_code: 684 bytes accepted` and `own task armed: ... emit image 0x30011100
  ... pds=crumb3 pdsat=fw14 pds2=req form=own`; health ok (207, 237, 264). The GETMISCINFO kick
  was answered after 202 us.
- c1-a: no done within 200 ms, runner rc 1 (`firmware hung: the tick stopped`), class `hang`,
  stage rc 4; post did not run (one stop ends the session).
- The frozen scorer, by hand on the kept directory (fold/reproduce-own.out): every control passed
  (PG, K0, K1, T0, B), `Q128-S2 RULE: S2-NEVER: the program never started (T running, S1 fill):
  with the kick and s2 = 0x00020000, #14's sideband is needed`. X0 0x5a5a3303; S1, M4 the fill,
  state 0; T 0x0104f772 in snap9 and 0x01037967 in the stop dump, counting; Δtick 7 from the
  kick, 16 from the command write (252.5 ms); alive false (ticks 2127 three times).
- Read from the kept files: snap0 0x0acc 0x0102c5df; BIF_FAULT 0 throughout; the kit's reset
  after the stop recovered (t30 triangle `diff: 0 of 4096`, fill `diff: 0 of 2048`), and the
  next session (r40-s-pass) ran clean on the same boot and firmware.
- With this row the readings of K (E1155, CANNOT TELL by its band) recur as a scored NEVER.
- Records: E1158 (this session).
