# r40-n3e-b10 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-073929, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B10 of closing29/n3e/design.md section 3.3: blob emitsb_sb800 (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=sb800` (sideband 0x800, word 0xfb20b10000008184, s2 0), timer pass, no kick.
- The frozen scorer (reproduced by hand): every control passed; `B10-NEVER` held as predicted. X0
  0x5a5a3303, S1 and M4 the fill, state 0, T running (0x0105227e, 0x01010611); BIF_FAULT 0. The
  runner stopped (class hang, rc 4); recovered (closing29/r40-n3e-logs/health-after-b10.log). Post
  not run.
- SURVEY (printed): the post slots kept the fill (the entry never stored them); pre sa0-sa31 as
  B0's.
- Records: E1170 (this session).
