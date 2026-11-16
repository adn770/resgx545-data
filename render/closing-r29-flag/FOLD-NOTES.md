# r29-flag fold notes (builder, before the run)

- Records: E1108 f1 (Q108), E1109 f2 (Q139), E1112 h1 + q010-p2 (Q010), E1113 h2 + O29-2 (Q163,
  `fit/o29_2.py`, `fit/o29_2.out`). E1110 (f3, Q241) and E1111 (f4, Q112) are not used: f3 was not
  built (O29-1 found no candidate, `fit/o29_1.out`; the fold may cite it in Q241's question line
  as an offline note, no record of its own unless the lead assigns one), f4 not built (its
  control's premise contradicts Q042). Draft each method with `tools/records/new_record.py
  --session DIR`; appended corrections only.
- f1: Q108 narrows (the flags together on a read). H-PASS would need a `zls` load table of
  E1046's store (r18-flag f2's form).
- f2: Q139 narrows. The kind (H-KIND) is a third and fourth held-out word for E1073; the page
  parts H-AXIS from H-SIZE only; H-AXIS and "region base + 0x4000 / 0xc000" stay one form at n = 2
  (README.md deviation 3). If a row faults 0x90004, note whether its health passed at the first
  try (E509's 640 x 480 rows did not).
- Q010: `score.py q010 out/ATT` gives R29-3 (a)'s verdict; retire only with all six controls
  passing and the three copies on one hypothesis. q010-af follows four planned faults (f1, f2),
  p1 and p2 one hang each. Under H-KEEP the answer keeps the power-on state as [infer].
- Q163: H-PREV16 is post hoc on all 18 kept jobs (E1035 was read before it was formed); h2 is its
  first held-out test. The fold states each triple's c and the job before.
- Kit needs (report, do not change shared tools): a stage's `#limit` reached with rows left stops
  the stage even when the rows left are safe readings (copies after the last planned hang); a kit
  word "after the limit, only rows without expectfault" would let a reading follow its event
  without splitting it across stages.
