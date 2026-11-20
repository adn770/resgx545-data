# r40-n3e-b2 fold notes (folder, 2026-11-20)

- One attempt, out/20261119-230639, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B2 of closing29/n3e/design.md section 3.3: blob emitsb_sb841 (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=sb841` (sideband 0x841, word 0xfb20b10800408184, s2 0), timer pass, no kick.
- The frozen scorer (reproduced by hand, fold/reproduce-own.out): control B FAILED, `Q128-B2 RULE:
  FAULT`: BIF_FAULT (0x0c08) 0x30011010 in snap9 and in the stop dump. X0, S1 and M4 the fill
  (0xdeadc0de: the issuer did not store past the emit), state 0; T running (0x01053cd1, 0x010607af).
  The runner stopped (class hang, rc 4); the kit's reset and health recovered it (fill and triangle
  ok, c1-a.health2, c1-a.fill2). Post not run.
- 0x30011010 is #14's page (0x30011000) + 0x10, 0xf0 below our image at 0x30011100 (the arm line).
  Facts only.
- SURVEY (printed): the post slots kept the fill (the entry never stored them); pre sa0-sa31 as
  B0's.
- Records: E1165 (this session).
