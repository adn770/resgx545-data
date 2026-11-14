# r16-tex fold notes (the builder folds after the run)

- Record (DECISIONS-R16.md): **E1065** ty2 (Q177). Draft the method with
  `tools/records/new_record.py
  --session DIR`; appended corrections only; keep question-line edits to Q177's clauses (other
  round 16 folds may edit the same question files).
- Rests on: E1055 (the fit N13 / N4, halving, modes 5 to 7 at 16 x 16, the references), E1039, E567,
  E1000 (the map form).
- What each verdict does: README.md "What each verdict does". R16-7 a: narrow; a failed frozen row
  is not explained away post hoc for a retirement; post hoc fits (a new size form from three sizes,
  mode 5's constant) go in fold/NOTES.md as post hoc, held out in a later round (R16-7 b).
- Post hoc for the fold: per mode 4 row the lowest names of row 0 and c of H-LIN1 (score.py prints
  them); fit N(W) on 8, 16, 32, 64 (and H at 64 x 16); mode 5's constant at 8, 16, 64.
- Sim in sync: sgx-sim tex.rs types at the new sizes if N13 / N4 hold on every mode 4 row; modes 5
  to 7 stay refused (E1055 named; add E1065); vectors `vectors/closing/r16-tex/pixels/ty.table.json`
  (README.md "Replay vectors"; refused with digests when the form does not hold).
- Kit or tool needs: none found while building (the library-mock replay ran all 15 rows as
  "program not simulated").
- Delete `.pytest_cache` and `__pycache__` before the fold publishes; `debug/` is not published.
