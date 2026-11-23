# r42-n3g-g2 fold notes (folder, 2026-11-23)

- One attempt, out/20261122-163902, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87, the one-shot boot of 2026-11-22), after session G1 (closing29/r42-n3g-logs/
  runone-G2.out). Session G2 of closing29/n3g/design.md (sections 3.3 and 3.4): stage s (row S,
  row C again, blob emitsb14s, `form=fw14`, sideband 0x843, crumb3), then stage q (row Q, blob
  emitsb_sb402s, `form=sb402`, sideband 0x402, crumb3), each one row of two jobs as G1's. Kit and
  blobs: resgx545 c0e2dc36.
- Rescored by hand with the frozen scorer (fold/reproduce-s-*.out, fold/reproduce-q-*.out): the
  same bytes as the kept score-s.txt and score-q.txt.
- Stage s: every control passed; `Q128-N3G-S RULE: C-GATE, C-SAME, S-KEEP` as predicted; S-BACK
  and S-OTHER failed. Job 1's post pa1 = M13 0x005d3000, after G1's row M, its watchdog's and the
  kit's resets and this session's begin reset; the other odd pa as in R-BOOT (G1). The post pa are
  the same 16 words as G1's row M. K5: BIF_FAULT 0 before and after both jobs; the gate exact.
- Stage q: PG, E0, T0, J1 and J2 passed; B FAILED (snap9 BIF_FAULT 0x005d300f), read by the
  outcomes. `Q128-N3G-Q RULE: Q-FILL, Q-REBASE, Q-REP; FAULT: BIF_FAULT is not 0 after the row and
  no outcome names it`. Every prediction held: Q-REBASE, Q-REP and Q-FILL held, Q-NONE failed,
  Q-OTHER (printed) failed. rc 16 at the gate, the planned end.
- Stage q readings: job 1's post pa0, pa4, pa8, pa12 = V0 0x32004000 and pa2, pa6, pa10, pa14 = V2
  0x32002000; stage s's post read 3, 0x32411000, 0x5a5a3a18 and 0x5a5a3a1a at pa0, pa4, pa12 and
  pa14, so this row wrote at least those four; pa1 M13. Job 2's after-read equals job 1's post in
  all 32: sa12-sa27 = pa0-pa15, sa13 = M13; sa4 = sa8 = V0, sa6 = sa10 = V2 (the same words M and
  LV read there, so these four alone do not show 0x402's writing; sa12 and sa14 do); sa0, sa2
  kept; **sa1 0x04400000, not M1** (G1's row M read sa1 = M1).
- Stage q, K5 (printed): job 1 clean; job 2 BIF_FAULT 0 before and 0x005d300f after: the fault
  arose in job 2, as in G1's row M. The gate: `BIF fault 0xd0400 at 0x5d300f (PD 0x0) stalls job
  25, recovering`; devcd6 (manual) before, devcd7 (bif-fault, 0x005d300f) during the fill; the
  triangle after the recovery exact. As in M, the fill's reading alone does not show a fresh fault.
- [post hoc] sa1: M (0xc43, mark) read sa1 = M1, the word mark sent to attribute 1; Q (0x402,
  crumb3, no write to attribute 1) read 0x04400000, the word B11, Y and LC2 read. Either attribute
  1 was rewritten between the rows (by a writer we do not run, or by a reset, where attribute 13
  kept its word), or sa1 is not attribute 1 in every case. So M-SA1 supports H-BLOCK only weakly;
  H-BLOCK stays [infer].
- Health after the session's end: fill and triangle ok (closing29/r42-n3g-logs/health-r42-n3g-g2.log).
- Records: E1181 (stage s), E1182 (stage q).
