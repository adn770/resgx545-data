# r34-sa0b fold (E1140)

- One attempt, out/20261117-005911: 54 jobs of stage s, 00:59:11 to about 01:08:28 on 2026-11-17,
  rc 0, no stop, fault or lead decision. Every control passed (16 writers, 6 colour fills).
  fold/reproduce.out equals the attempt's score-s.txt byte for byte; fold/q136-rule.out is the
  frozen rule: RETIRE-CAPABLE, (a) H-ONEJOB 16 of 16, (b) H-PREV 4 of 4 with H-FIXED 0 of 4.
- Every reader now read one uniform value, or the triangle's two colours. Readers after a writer
  read 2048 of 2048 pixels at its marker; readers after a job read that job's colour. After the
  t10 triangle, sa0 and pa0 readers alike read 0xff00ff00 x1536 and 0xff203040 x512.
- H-ONEJOB was formed post hoc from E1139 (r34-sa0) and is held out here on new rows. The lead
  confirmed the retirement.
- sgx-sim: refused, not modelled. A per-job replay takes sa and pa as the vector's inputs, so a
  value carried from the job before would be an input, not a model. E1140 is cited at the sa
  field as session state.
