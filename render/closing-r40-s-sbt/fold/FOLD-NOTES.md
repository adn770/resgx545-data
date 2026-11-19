# r40-s-sbt fold notes (folder, 2026-11-19)

- One attempt, out/20261119-174746 (the lead, user present), on module 0CDFCDB73D76F39FE9E593C
  (fork f9453424bf71), Z's boot (uptime 8054 s at the arm), no rebuild. Row S-SBT, built after
  SB, S2 and S-PASS: against r40-s-pass only `s2` changes (0), so it is the sideband alone on a
  tick pass with `s2` 0. Blob emitsb14 (c3f9f67), U0 0x080401ef as r40-s-pass. The README calls
  c3f9f67 "main"; it was branch r40-s then (merged into the fold branch for this fold).
- The arm logged `own_code: 644 bytes accepted` and `own task armed: ... emit image 0x30011100
  ... pds=crumb3 pdsat=fw14 pds2=0 form=fw14`; health ok (204, 234, 262).
- The frozen scorer (score-own.txt; fold/reproduce-own.out the same bytes): every control passed
  (PG, E0, T0, B), `Q128-ST RULE: ST-DONE: all ran`. X0 0x5a5a3303, T 0x005a3305 in snap9
  (snap0 0x010541ae), S1 0x5a5a3304, M4 and run id 1, state 2; done after 0.2 ms; Δtick 9 from
  the command write (37.6 ms); alive false by design. Gate and post exact; the disarm reset
  brought the tick back (299, 328, 355).
- LANDING (printed, not scored): as Z's; pa0 and pa2 are not V0 and V2.
- Records: E1160 (this session).
