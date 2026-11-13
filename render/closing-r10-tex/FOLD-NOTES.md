# r10-tex fold notes (the builder folds after the run)

- Records (DECISIONS-R10.md): E1000 addr3 (Q177), E1001 cube3 ties, E1002 cube3 edges (Q284),
  E1003 t3b (Q078), E1004 srgb2 (Q282). Four-digit E-numbers need the tooling's item 8
  (r10-tooling2) landed before the fold. Draft each method with
  `tools/records/new_record.py --session DIR`.
- Rests on: E957 (8 N + 52, the width rival), E565 (32 x 8 + 308), E932 (mode 5 at 16 x 16),
  E561 (the tile law for every shape), E955/E956 and E930/E931 (cube rule, ties, edges), E975
  (R-4096 post hoc), E566 (the t3 controls), E976/E723 and the offline E982 (R10-BF11).
- What each verdict does: seeds plan section 14 (Q177 retires if one rival holds on the three
  non-square rows and H-B5 on mode 5; Q284's tie clause retires if H-HIGHAXIS holds on the 12 rows
  and the replay repeats nothing, narrows if H-FMADNE; the edge clause retires if H-SEAM-FLOAT
  holds on both; Q078 narrows (bit 14's constant held out; bits 11, 12 and twiddled stay); Q282
  confirmed on hardware past the kept jobs).
- Deviations to state in the records: README.md "Deviations from the plan" (edge along 7.75 and
  8.25, out weight 1/4; k0b with B larger; sub's zero corner; t3b S 256 over u [0, 1/4), off-grid
  4096 u = 64 x + 3/4, clamp base 2048, u16).
- Post hoc for the fold: addr3's printed "read less H-MASK-V" offsets per row; t3b kept - ref
  offsets per pixel (the reading if no rival holds); cube3 lower-read pixels per row with their
  third coordinate; srgb2 misses by k (if any).
- Sim in sync: sgx-sim / sgx-pipe get the offset rule (addr3, if decided), the bit-14 offset
  (t3b) and R10-BF11 (E982) with vectors `vectors/closing/r10-tex/*.table.json` (README).
- Delete any `.pytest_cache` before the fold publishes.
