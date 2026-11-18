# r35-sa fold notes (builder, 2026-11-18)

- Records reserved: E1144 (stage a, Q129; cite E484, E1106, E1139, E1140) and E1145 (stage t,
  Q193; cite E484, E593, E1140). Built on main eea6d2a, data 1f5ebe6b6 (r34-sa0b's fold, E1140,
  was not on main then: cited in prose only, not pinned).
- Scoring: `score.py a out/ATT/a`, `score.py t out/ATT/t`, `score.py q129 out/ATT`, `score.py
  q193 out/ATT`. If Q129 is RETIRE-CAPABLE, the lead confirms NOT THE LINE; the why goes to Q098
  (R35-3a). Q193 narrows whatever reads (R35-5a).
- Deviations from the plan sketch: W_157 uses iaddu32 for all three sa (same form as the singles,
  not E484's mov); held-out n = 2-15 (sa0-sa15), two replicates for 2, 3, 5, 7, 15 and 157, one for
  the rest (40 jobs against ~42); t3 has a frozen rival H-RESETCLR; t4 runs once.
- Replay: refused (carried state; instance positions not modelled).
