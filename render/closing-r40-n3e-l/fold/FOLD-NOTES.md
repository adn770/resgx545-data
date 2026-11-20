# r40-n3e-l fold notes (folder, 2026-11-20)

- One attempt, out/20261119-230429, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel 423b436e7f80,
  built on cachix 2026-11-19: red rc 1, series 12 of 12 PASS,
  closing29/r40-n3e-logs/cachix-wait.log; manifest
  closing29/kernel39c/deliver/423b436e7f80/manifest), the one-shot boot of 2026-11-19 (about 23:00),
  post-boot draws ok. Row L of closing29/n3e/design.md section 3.3: blob emitsb14d (resgx545
  b8528c0, branch r40-n3e, merged into the fold branch), arm `slots=0x1 entry=0 pds=land pdsat=fw14
  form=fw14` (sideband 0x843, word 0xfb20b10800c08184, s2 0), timer pass, no kick.
- The frozen scorer: every control passed (PG, E0, T0, B, P0, P1); `Q128-L RULE: L-PA` held,
  predicted failed (L-SA, predicted held, failed). X0 0x5a5a3303, S1 0x5a5a3304, M4 0x5a5a3302 and
  run id 1, state 2; T 0x0100fc26 (running: no tim in the image), 39 ticks (38.1 ms). Post exact;
  the owntask gate passed.
- LAND-L (printed): Ma (0x5a5a3a18, douta control 0x1800, attribute 24) at pa12 only, Mb
  (0x5a5a3a1a, control 0x1a00, attribute 26) at pa14 only; pre and post sa24 and sa26 0; sa0-sa31
  the same pre and post; the other pa0-pa15 as B0's (pa13 0x82e151b5 as before).
- L-TICK (printed): T still counting after a DONE with no tim (bit 24 set, 0x0100fc26).
- Inferred, not read: attribute 24 to pa12 and 26 to pa14 fit pa = n - 12 (two points; n/2 fits 24
  but not 26). With that offset, crumb3's attributes 0 and 2 (crumb3.s: controls 0 and 0x200) fall
  below pa0, which fits D0's and B0's reading (no V0 or V2 in pa0-pa15); n/2 would put V0 at pa0 and
  V2 at pa1, which D0 read as 0x00000000 and 0x00043000. D0's scorer compared pa0 and pa2 (and
  searched pa0-pa15) on the premise that the douta targets sa.
- Records: E1163 (this session).
