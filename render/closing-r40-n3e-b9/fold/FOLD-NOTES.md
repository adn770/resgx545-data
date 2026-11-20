# r40-n3e-b9 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-073902, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B9 of closing29/n3e/design.md section 3.3: blob emitsb_sb040 (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=sb040` (sideband 0x040, word 0xfb20b00800008184, s2 0), timer pass, no kick.
- The frozen scorer (reproduced by hand): every control passed; `B9-NEVER` held as predicted. X0
  0x5a5a3303, S1 and M4 the fill, state 0, T running (0x0106101a, 0x0100b3d2); BIF_FAULT 0. The
  runner stopped (class hang, rc 4); recovered (closing29/r40-n3e-logs/health-after-b9.log). Post
  not run.
- SURVEY (printed): the post slots kept the fill (the entry never stored them); pre sa0-sa31 as
  B0's.
- Records: E1169 (this session).
