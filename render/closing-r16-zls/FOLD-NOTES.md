# r16-zls fold notes (builder; this file is frozen, post-run notes go to fold/)

- Records: E1059 (Q297: rows zp2-, zpass2), E1063 (Q071: zb4-, in zbits4, zovp's zb4-20-d12 and
  zoff's zb4-20-640), E1064 (Q299: zo-, in zovp and zbits4's zo-s-64, zo-s-160), E1066 (Q069:
  zw2-, zoff; OQ069 is gen/oq069.out, part of E1066's method). Draft with
  `tools/records/new_record.py --session DIR`; a record citing rows of two stages names each
  stage's attempt directory. Cite E467, E995, E1050, E1054 (E1059); E284, E988, E997, E1030, E1031,
  E1041, E1042, E1053 (E1063); E465, E995, E996, E1050, E1051 (E1064); E287, E981, E987, E1056
  (E1066).
- Retirement (R16-6 (a), the lead confirms): Q297 if H-PASS-TWIN holds on all seven pairs and
  H-PASS-EXACT on the three one-float depths, both zpass2 controls passing. Q071 only if one of
  H23-REF, H23-MASK, H23-BG holds (on its own row, H23-FIXED on the other two), H-B0 4 of 4 and
  H-INERT20 4 of 4 (bits 20 and 27 to 31 then read "no effect on every route run" [infer]). Q299
  and Q069 narrow. Keep question-line edits to these clauses.
- zpass2: READING lines give each twin's floats; a twin of one float equal to the depth makes OWN
  and TWIN agree on that row (say so). zp2-c-z125 failing voids the determinism premise.
- zbits4: the bit-23 READING lines give the read byte by x mod 16; if a rival holds, fit the byte
  rule post hoc from them and say [post hoc]. The format 6 and 7 rows store no stencil (their
  stencil store keeps its fill: E1031), so H-B0 parts from H-B0-NOSTORE there on the depth dump.
- zovp: the pass rows' plane is the kept full-pitch reference's (H-PASS-TWIN [infer]): if zpass2's
  H-PASS-TWIN fails, say what that does to E1064.
- zoff: READING lines give z / t at y 0 and the pixels off the row's H-LIN-S line against BEND.
  BEND is a reading on every row; a fit post hoc of the bend is [post hoc].
- Replay tables (README): zp2-, zb4-, zo- into sgx-pipe zls.rs, test first; zw2- refused unless a
  form held. Delete any `.pytest_cache`, `__pycache__`, `debug/target` and `gen/oq069rs/target`
  before publishing.
