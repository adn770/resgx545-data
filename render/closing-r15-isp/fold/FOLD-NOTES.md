# r15-isp fold notes (builder; fold/ is outside the freeze)

Built 2026-11-14 by the r15-isp builder from resgx545 158bdc5, data cddc7b60b, tool t10 (a581c06,
9bedc2d6...). Record: E1056 zcut (Q241) (only this number).

## For the fold (when resumed)

- Score: `python3 score/score.py zcut out/ATTEMPT/zcut` (CONTROL lines first; SUMMARY lines per
  form). Check the three controls PASS before reading a headline.
- Dump check (not in the scorer, deviation 1): for each depth row, every one of the 4608 band
  dwords of `out/ATTEMPT/zcut/NAME.depth.1.bin` against `predictions/zcut/NAME.MODEL.txt` (lines
  after the 40 bitmap rows: `INDEX eq 0xWORD` exact, `INDEX near F` within 2^-10; the engine
  matched E1045's two dumps within 2^-20 in all 4608 dwords). Write it as fold/dumpcheck.py
  (zcut.zparse and a loop over words); H-POLYCLIP's plane through the rounded made vertices may
  deviate from the exact plane by up to about 1e-4: report the maximum deviation per row.
- Q241: narrows only (bit 18, the visibility counter, the offset's units, the pass types and the
  gate pairs stay open); reword the cut clause in the question line (own clauses only; other
  folds edit the same file). A held H-POLYCLIP gives the cut's depth and edge pixels (the clause
  "the depth and the edge pixels of the cut", Q230's made-vertex depth stays open: the cut's
  depth plane is read only within 2^-10). A held H-PIXCUT/H-POLYCLIP-NR pair names the exact cut
  (no rounding of the made vertices): the CLIP-HA rounding of E1037 then does not carry over.
- E065 rows: bits 16, 17 H-NONE expected (E065's xor flips left no pixel); H-EQUIV held would say
  bits 15 to 17 leave the same 48 pixels on the library triangle (READING lines compare the sets).
  E065's 48 pixels: the set is read for the first time here (E065 kept counts only): record it.
- Retire: none expected (R15 section 6: Q241 narrows). The lead confirms any retirement.
- sgx-pipe: `mte::cut_triangle` refuses a triangle cut by z = +-w (Q230, Q241); if H-POLYCLIP
  held, extend with the made vertex rounded half away from zero to 1/256 and replay the six rows
  (table `zcut`, vectors from the kept files; E1045's two rows as the controls); otherwise refuse
  under Q241 as now.
- Deviations: README.md "Deviations" (no dump in the scorer, the pair not parted by a row, E065's
  rows are xor replicates, rows found by a seeded search).
- Before publishing: delete `.pytest_cache` and `__pycache__`; debug/ is scratch (the three
  design scripts, run_all logs and the mock trees: do not publish debug/mock.*).
