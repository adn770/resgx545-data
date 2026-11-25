# r46-n3k-b6 fold notes (folder, 2026-11-25)

- One attempt, out/20261125-150427 (15:04:27), the second session of round 46
  (closing29/r46-n3k-logs/runone-B6.out, run rc 0). Row B6 of closing29/n3k/design.md section 10.1
  (decision B (b): rebuilt on today's kit with an after-read). Kit: resgx545 eaee04a4 (branch
  r46-n3k). Blob emitsb_sb803s (emitsb_sbc43s with only the sideband changed, 0x803), crumb3 at
  fw14, `form=sb803`.
- Stage b6: rc 0, scored by the driver (score-b6.txt) and rescored by hand
  (fold/reproduce-b6-20261125-150427.out): the same bytes, and the same bytes as
  closing29/r46-n3k-logs/score-r46-n3k-b6-b6.txt. `Q128-N3K-B6 RULE: B6-DONE, B6-GATE, B6-HID,
  B6-QUIET, B6-RUN, B6-SAME`; every control passed; every prediction held.
- Readings (printed): job 1 DONE, 9 ticks; post sa0-sa31 = pre; job 2 done on its GETMISCINFO kick,
  its after-read = pre = post; the gate's fill and triangle exact; K5 BIF_FAULT 0 everywhere; KC 10
  and 10. Post pa0-pa15: V0 at pa0, pa4, pa8, pa12 and V2 at pa2, pa6, pa10, pa14 (landing EVERY4),
  pa1 M13, the odd pa equal B5's word for word.
- [post hoc, infer] Only the even pa changed between B5 and B6, to crumb3's V0 and V2, which fits
  B6's own douta landing as 0x003's do; one read, unscored. N1's plant WA then read the same
  pa0-pa15 as B6.
- Health after the session: fill ok, triangle ok (closing29/r46-n3k-logs/health-r46-n3k-b6.log).
- Records: E1235 (b6).
- Sessions N5-N8 (rows WF, R, WG, P, WH, R2, WI, P2: landr and landp) were built and frozen but not
  run: the user stopped the round after N4. Nothing of them is folded.
