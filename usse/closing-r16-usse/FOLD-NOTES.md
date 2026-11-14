# r16-usse fold notes (builder, before the run)

For the fold (the lead resumes the builder with the results). Records: E1061 (uadd and urpt,
Q126), E1062 (utest, Q137); no other number.

## What to read from the kept files

- `out/<attempt>/STAGE/score-STAGE.txt` (or re-run `python3 score/score.py STAGE DIR`): one ROW
  line a row with every model's dword count and the dwords that differ from H-RULE (utest) or H-ZX
  (uadd; H-ZX-ADV urpt), and SUMMARY lines per quantity, model and set.
- A utest packed dword is 0x5A5A0000 | bits; bit f = field f set p0. gen/progs.py and gen/rule.py
  rebuild every prediction; `progs.utest_job(NAME)["preds"]` has each model's dwords.
- A row whose values (H-SIM) fail but whose tests read the rule on the observed value is a value
  surprise, not a rule failure: say so, do not explain a frozen row away (DECISIONS-R16).

## Retirement (R16-6 a, the lead confirms)

- Q126: every uadd row H-ZX and both controls PASS: the value zero-extends source 1 with
  immediates, c56, i0 and sa0. urpt: H-ZX-ADV (the mask repeats, sources advanced) or H-NOREP (the
  mask ignored on a test) decides the repeat clause either way, if u-ctl-rpt passes. The test
  clause is not observable (E498: the carry-counted zero is (0, 0) only under both extensions; the
  sign tests read nothing): reworded [infer], Q276 precedent.
- Q137: every utest row H-RULE and both controls PASS. OQ137 (tests/test_gen.py) answers the
  backend clause: the assembler's text names write the raw words byte for byte, and these rows
  ran the text forms. Not run: the two-bit raw fields (3, 7, 0xb-0xf) on lanes, chan fields on
  the shifts and sums, other lane operations; say so in the record.

## Sim and vectors (sim in sync)

- If H-RULE holds: lift sgx-sim's "test X with the join o (not run, E529)" refusal for the forms
  run (usse.rs ~3407) citing E1062, extend canonical_test_word to the shifts and sums (raw fields
  read as their two parts) and add a test replaying this session's vectors; the lane o join too.
- If H-ZX-ADV (or H-NOREP) holds: model the write mask on the test group (usse.rs `write`,
  "write mask on test") citing E1061, else keep the refusal with E1061 named.
- Vectors: sgx545-vectors per stage (README "Replay vectors"), built from kept files + bins/.

## Known limits of this build

- or #7 cannot give a zero result; iaddu32 never tests negative (E498), so its rows cover zero
  and positive.
- The lane rows use one pair (72 tests a program under the 256-word limit).

Post-run notes of the fold go in `fold/` (this file is frozen).
