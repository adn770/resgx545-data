# r40-n3e-b3 fold notes (folder, 2026-11-20)

- One attempt, out/20261119-230732, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B3 of closing29/n3e/design.md section 3.3: blob emitsb_sb842 (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=sb842` (sideband 0x842, word 0xfb20b10800808184, s2 0), timer pass, no kick.
- The frozen scorer: every control passed; `B3-DONE` held (H-DM predicted NEVER: failed; H-ALL
  NEVER: failed). X0 0x5a5a3303, T 0x005a3305, S1, M4 and run id 1, state 2; 8 ticks. Post exact;
  the owntask gate passed.
- SURVEY (printed): sa0-sa31 the same pre and post; pa0, pa4, pa8 and pa12 read V0 (0x32004000) and
  pa2, pa6, pa10 and pa14 read V2 (0x32002000); the odd pa read what they read in B0 (pa1
  0x00043000, pa3 0x01555620, ...); LANDING 'pa0 = V0 yes, pa2 = V2 yes'.
- Records: E1166 (this session).
