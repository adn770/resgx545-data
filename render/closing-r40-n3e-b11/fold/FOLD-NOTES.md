# r40-n3e-b11 fold notes (folder, 2026-11-20)

- Two attempts, out/20261120-074024, out/20261120-084102, on module 83FBFD860D4E0D4CE691F48 (fork
  r40-kernel 423b436e7f80, built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B11 of closing29/n3e/design.md section 3.3: blob emitsb_sbc43 (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=sbc43` (sideband 0xc43, word 0xfb20b18800c08184, s2 0), timer pass, no kick.
- Two attempts (the second at the user's choice), the same freeze. Both: every control passed,
  `B11-DONE` held (H-DM RUN: held). X0 0x5a5a3303, T 0x005a3305, S1, M4 and run id 1, state 2; 8
  ticks. Then the kit's owntask gate after the ok end failed both times: fill 'diff: 2048 of 2048
  pixels, first (0, 0) 0xdeadbeef expected 0xff336699', triangle exact; rc 16, the kit's recovery,
  after which fill and triangle were ok (c1-a.health2, c1-a.fill2;
  closing29/r40-n3e-logs/health-after-b11.log). Post not run. Every other DONE row's gate passed
  (B0, B1, B3, B8, L).
- SURVEY (printed), both attempts: the post sa differ from pre at sa1 (0x32005000 -> 0x04400000),
  sa3-sa5, sa7-sa9, sa11 (0x3f800000, 0x3f400000, 0xbec00000 ...), and sa12-sa31, where post sa12+k
  reads what post pa k reads (k = 0-15); sa22 0x32000000 -> 0x32002000. pa: attempt 1 as B1's (V0 at
  pa0, 4, 8, 12, V2 at pa2, 6, 10, 14); attempt 2 the same except pa0 0x00000003 and pa2 0x32411000.
- Inferred, not read: bit 10 leaves state that breaks the next fill until a reset.
- Records: E1172 (this session).
