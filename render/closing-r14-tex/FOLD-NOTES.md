# r14-tex fold notes (the builder folds after the run)

- Records (DECISIONS-R14.md): E1038 srgb4 (Q282), E1039 addr5 (Q177). Draft each method with
  `tools/records/new_record.py --session DIR`; appended corrections only; folds may propose
  retirement (R14-6 a: every measurable clause decided by held-out rows with passing controls,
  void clauses reworded [infer], the lead confirms). Keep question-line edits to Q282 and Q177.
- Rests on: E1025, E1016, E1004, E982, E723 (srgb4; c2's rule_b.py; fit/tri_fam.py and fit/r11.py
  post hoc, before the run); E1026, E1017, E1000, E983, E565, E567, E561 (addr5).
- What each verdict does: README.md "Predictions". Q282: the trilinear clause decided if exactly
  one TRI family holds on all seven rows (its flush by srgb4-tdark, f by srgb4-t12: Q-FLOOR or
  QN-), the alpha clause if B2-FTZ-OUT and exactly one alpha form hold on all three; negative
  values void [infer] (E1025). Q177: the corner base by C-LOG4 (or a rival) on six shapes, the
  types by T-MODE0 / T-OFFSET per type; "why these constants" reworded to the held-out formulas
  [infer] (R14-6 a).
- Post hoc for the fold: if no TRI form holds, rerun fit/tri_fam.py's family on all seven rows;
  per type row, the reads less the reference's (score line) and, if neither form holds, the read
  against E561's index of the type's mode 0 image; per corner row, the corner reads (score line).
- Sim in sync: sgx-sim tex.rs gets the level lerp (third stage), the alpha decode (byte 3
  linear) and the mode 5 corner base, if decided; vectors `vectors/closing/r14-tex/*.table.json`
  (README.md "Replay vectors").
- Kit or tool needs: none found while building (the library-mock replay ran all 27 rows as
  "program not simulated", no t10p).
- Delete `.pytest_cache` and `__pycache__` before the fold publishes; `debug/` is not published,
  `fit/` is (README.md "Data").
