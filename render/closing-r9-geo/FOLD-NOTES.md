# r9-geo fold notes (the builder's, frozen with the session)

The builder folds this session (round process, 2026-11-12). What the fold needs to know:

- Scores: `out/<attempt>/score-<stage>.txt` from score/score.py; SUMMARY lines per hypothesis.
  READ lines: cube2's per-law counts, face ties by the third coordinate's sign, texel ties per
  boundary, the edge out values (the blended dwords: solve the outer tap as in
  `debug/edge_solve.py` of the build, not frozen); addr2's index less H-MASK-V's and per position.
- Records (DECISIONS-R9.md): E953 seam1 (Q141 retires if H-REGION is exact on every held-out
  row and both controls pass), E954 seam4 (a follow-up line of Q141's record, or a new question if
  H-SAME4 fails), E955 cube2 sizes (32, 64, 4), E956 cube2 ties and edges, E957 addr2 (Q177).
  Draft each method with `tools/records/new_record.py --session DIR`.
- Deviations from the plan to state in the records: seam4's E502 row is held out, not a control
  (H-FULL4 parts it), so seam4's controls are j1r and the E504 row; the -y/+z edge was replaced
  by -y/+x (it cannot part the rivals); H-POS is the builder's reading of the plan's H-SIGN
  [infer]; the face-tie sweeps put the tied coordinates at opposite signs so the rivals part.
- In sample before the freeze (`gen/insample.out`): E561's law and H-PAIRSWAP read E930's 32 x 32
  jobs 4831 of 4831 (H-MORTON 2422); on E931's edges H-SEAM-ADJ 0 of 96 (+x/+y) and 64 of 128
  (+z/-x), H-SEAM-WRAP 0: the edge rows are likely readings.
- Inputs not in a repository at the freeze: none; gen/q284_rule.json and gen/o8/ are r8-geo's
  published files (data pins, checked by the tests).
- Things a fold must not do: change kit/, tools/closing, tools/records (report them instead).
- Kit pinned at resgx545 f32dfac (round 9 main at scaffold time).
