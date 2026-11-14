# r15-tex fold notes (the builder folds after the run)

- Records (DECISIONS-R15.md): E1052 chain (Q104), E1055 ty (Q177). Draft each method with
  `tools/records/new_record.py --session DIR`; appended corrections only; folds may propose
  retirement (R15-6 a: every measurable clause decided by held-out rows with passing controls,
  void clauses reworded [infer], the lead confirms). Keep question-line edits to Q104 and Q177.
- Rests on: E562, E441, E276, E561, E1003, E1026 (chain); E1039, E567, E1000, E565 (ty).
- What each verdict does: README.md "Predictions". Q104: retire if A (A-TX) holds on the 1D,
  side-1 and 16-bit rows with both controls passing; the u16 MIPFILTER clause decided if exactly
  one blend holds (A-DW-BL8 and D-TX-BL8 are one image on 32 x 16); "1D" reads smp1dreplace on 64
  x 1 (or W x 1 under smp2d if the 1D rows were cut). Q177 narrows (R15-5 a): the 32 x 32 and mode
  5 to 7 names become the fit for a size form; H-NAME16 (NAME-U against NAME-WRAP) decides the
  16 x 16 map's u dependence.
- Post hoc for the fold: per chain row that misses every model, the levels and offsets read (decode
  each name against levels(), gen/chain.py); per ty form row, score.py's "row 0 lowest names" and
  c of H-LIN1 (the size form's fit: c at 16 x 16 is 660 for types 1 and 3, 644 for 4, or c - 256).
- Sim in sync: sgx-sim tex.rs CHAIN_SIZES and the chain rule (1D, a side of 1, u16 in texels, 64 x
  32, 256 x 32) if A holds, tests holding kept pixels; ty refused (types 1, 3, 4 in u modes 4 to 7),
  naming E1055; vectors `vectors/closing/r15-tex/pixels/*.table.json` (README.md "Replay vectors").
- Kit or tool needs: none found while building (the library-mock replay ran all 33 rows as
  "program not simulated").
- Delete `.pytest_cache` and `__pycache__` before the fold publishes; `debug/` is not published.
