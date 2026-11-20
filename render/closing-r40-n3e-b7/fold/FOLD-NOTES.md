# r40-n3e-b7 fold notes (folder, 2026-11-20)

- One attempt, out/20261120-073957, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B7 of closing29/n3e/design.md section 3.3: blob emitsb_sb001 (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=sb001` (sideband 0x001, word 0xfb20b00000408184, s2 0), timer pass, no kick.
- The frozen scorer (reproduced by hand): control B FAILED, `Q128-B7 RULE: FAULT`: BIF_FAULT
  0x30011010 in snap9 and the stop dump, as B2. X0, S1 and M4 the fill (0xdeadc0de), state 0, T
  running (0x0100c33d, 0x0105481f). The runner stopped (class hang, rc 4); recovered
  (closing29/r40-n3e-logs/health-after-b7.log). Post not run.
- SURVEY (printed): the post slots kept the fill (the entry never stored them); pre sa0-sa31 as
  B0's.
- Records: E1171 (this session).
