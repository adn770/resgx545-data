# r14-zls fold notes (builder; this file is frozen, post-run notes go to fold/)

- Records: E1040 (Q243: rows zg-, in zgran and zbits2), E1041 (Q242: zo-, in zodd), E1042 (Q071:
  zb2-, in zbits2, zgran's zb2-d12, zodd's zb2-c-r16 and zb2-f2-16), E1043 (Q120: zl-, zflat). Draft
  with `tools/records/new_record.py --session DIR`; a record citing rows of several stages names
  each stage's attempt directory. Cite E058, E465, E977, E995, E1029 (E1040); E411, E490, E831,
  E977, E991, E996 (E1041); E988, E989, E997, E1014, E1030 (E1042); E985, E986, E1015, E1031
  (E1043).
- R14-7 (a): Q243's line drops the integer-format, NaN and equal-depth clauses (E977, E995) in this
  fold. Retirement (R14-6 (a), the lead confirms): Q243 if one granule holds on all five granule
  rows, an I-MOVED model on both integer rows and S-MOVED on zg-s14; Q242 if INT-FLOOR-EXT,
  H-LATE/HDR (both overlap rows) and one of H-NEXTTILE/H-STRAY hold. Keep question-line edits to
  these clauses (other round 14 folds edit the same files).
- zgran: read the controls first. The granule rows' READING gives d. If no granule model holds,
  fit post hoc from the five d values and say [post hoc]. Integer rows: READING lists the stored
  values (0x400000/0xc00000 for format 1, the 16-bit pairs for format 2).
- zodd: the format-0 rows are readings (their floats feed the rivals). A row whose reference is
  missing cannot tell. zo-g3's READING gives the changed pages and values.
- zbits2: Z rows by drawn count; pitch rows by the model-free stencil read (pitch_check). If no
  pitch holds, fit post hoc with fold/ code (rows, offsets) as E1030's look.py did.
- zflat: the READING lines carry each block's bytes: decode the flat form post hoc across the five
  depths (which bytes follow v, which are markers); mark it [post hoc].
- Replay tables (README): zg-, zo-, zb2- into sgx-pipe zls.rs, test first; zl- refused unless a
  rule held. Delete any `.pytest_cache` and `__pycache__` before publishing.
