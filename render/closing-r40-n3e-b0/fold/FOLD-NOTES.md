# r40-n3e-b0 fold notes (folder, 2026-11-20)

- One attempt, out/20261119-230303, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row B0 of closing29/n3e/design.md section 3.3: blob emitsb14d (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=crumb3
  pdsat=fw14 form=fw14` (sideband 0x843, word 0xfb20b10800c08184, s2 0), timer pass, no kick.
- The frozen scorer (score-own.txt; fold/reproduce-own.out the same bytes): every control passed
  (PG, E0, T0, B), `B0-DONE` held as predicted (H-DM and H-ALL RUN). X0 0x5a5a3303, T 0x005a3305, S1
  0x5a5a3304, M4 0x5a5a3302 and run id 1, state 2; 9 ticks (38.8 ms). The new build reproduces ST
  and D0. Post exact; the owntask gate after the ok end passed.
- SURVEY (printed): sa0-sa31 the same pre and post; pa0-pa15 of the started entry as D0's and B0's:
  no V0 or V2 (pa0 0x00000000, pa2 0x3727c5ac), the same 16 words as D0's.
- Records: E1162 (this session).
