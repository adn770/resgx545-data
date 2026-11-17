# r34-sa0b fold notes (builder, 2026-11-17)

- Record reserved: E1140 (Q136; cite E1139, E484, E496, E1106). Built on main 914dd23, with data
  a3287ec6a (the r34-fold-sa0-data commit that publishes r34-sa0; the pin of E1139's post hoc
  reading needs it).
- The fix, frozen before the run: readers output the value they read (no key); a reader's dword 0
  must be one of its o0 values (else cannot tell); M = the marker as the most frequent value; the
  rr group is dropped. Fit = E1139's post hoc reading (H-ONEJOB 20 of 20, H-PREV 8 of 8); every
  reader here is held out.
- Scoring: `score.py s out/ATT/s` and `score.py q136 out/ATT`. If RETIRE-CAPABLE, the lead
  confirms the NOT THE LINE list before Q136 retires.
- Replay: refused (carried state), as r34-sa0.
