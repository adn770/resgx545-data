# r40-d0-survey fold notes (folder, 2026-11-19)

- One attempt, out/20261119-191743, on module 0CDFCDB73D76F39FE9E593C (fork f9453424bf71), the
  r39-n3d-z boot, no rebuild. Row D0, a landing survey: blob emitsb14d (resgx545 555d8eb, branch
  r40-d0, merged into the fold branch for this fold), arm `slots=0x1 entry=0 pds=crumb3 pdsat=fw14
  form=fw14` (sideband 0x843, s2 0), timer pass, no kick; the design is closing29/n3e/design.md
  sections 1.2 and 3.1. emitsb14d is emitsb14 plus stores only: sa0-sa31 before the emit, and
  sa0-sa31 and pa0-pa15 in the entry the emitted program started (555d8eb).
- The frozen scorer (score-own.txt; fold/reproduce-own.out the same bytes): every control passed
  (PG, E0, T0, B, P0, P1), `Q128-D0 RULE: D0-HID: all ran; landing HID`, predicted and held.
  X0 0x5a5a3303, T 0x005a3305, S1 0x5a5a3304, M4 0x5a5a3302 and run id 1, state 2; 8 ticks
  from the command write (37.9 ms). Post exact (triangle and fill diff 0).
- SURVEY (printed, not scored): sa0-sa31 identical pre and post. sa0-sa2 0x32004000 0x32005000
  0x32002000, sa3-sa21 and sa24-sa31 zero, sa22 0x32000000, sa23 0x05f17000. pa0-pa15 of the started
  task hold no V0 or V2 (pa0 = V0 no, pa2 = V2 no).
- Inferred, not read: crumb3's douta landed nowhere D0 can see. The only secondaries that hold
  its values are sa0 and sa2, which held the same values before, so a write there is not told
  apart from no write.
- Records: E1161 (this session).
