# r15-zls fold notes (builder; this file is frozen, post-run notes go to fold/)

- Records: E1050 (Q297: rows zp-, in zpass and zbits3's zp-e-st), E1051 (Q298: zv-, zovl), E1053
  (Q071: zb3-, zbits3), E1054 (Q120: zl2-, zflat2). Draft with
  `tools/records/new_record.py --session DIR`; a record citing rows of two stages names each
  stage's attempt directory. Cite E467, E664, E831, E977, E988, E995, E1029, E1040 (E1050); E287,
  E411, E465, E490, E977, E981, E987, E991, E996, E1041 (E1051); E284, E988, E1042 (E1053);
  E1031, E1043 (E1054).
- Retirement (R15-6 (a), the lead confirms): Q297 if H-EDGE (or one edge rival) holds on both
  edge rows, one bit-19 model on both rows, one integer model on both rows and H-PASS-Z or
  H-PASS-LE on the four depth rows, the zpass controls and zb3-c-base passing. Q298 if one owner
  model holds on all four overlaps, one integer model on all four rows, one pitch model on G 5, 9
  and 17 and one bit-25 model. Keep question-line edits to these clauses.
- zpass: the READING lines list each row's store values; deviation 3 (0.125, 0.375 for 0.1, 0.3)
  goes into E1050's "What it does not show" (no non-dyadic pass depth ran). Write the pass model
  into sgx-pipe `zls::pass` test first (gen/z15.py pass_model is the frozen statement).
- zbits3: the READING lines give the read byte by x mod 16 for every row; if H23-MOD16 fails,
  fit post hoc from them and say [post hoc]. zb3-c-ref1 failing voids zb3-b15-r1 (gated).
- zflat2: the twins' READING lines say whether a plane is one float; the f6 rows' READING give
  block 0's bytes. A plane that is flat but not FL-REC0 refutes both models: fit post hoc.
- zovl: zv-r-hi's READING is the float above 1 (1.25 expected); with H-INT-SAT that places the
  clamp in the conversion. The sized rows' READING give the pages written.
- Replay tables (README): zp-, zv-, zb3- into sgx-pipe zls.rs, test first; zl2- refused unless a
  rule held. Delete any `.pytest_cache` and `__pycache__` before publishing.
