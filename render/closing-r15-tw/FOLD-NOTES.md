# r15-tw fold notes (builder, before the run)

- Record: E1049 (tw14, Q078) only. Draft its method with `tools/records/new_record.py --session
  DIR`; appended corrections only.
- Score: `python3 score/score.py tw14 out/ATT/tw14`. READING lines decode every ok image (which
  dwords, each model's pixels): decode the full map whatever form holds.
- Retire (R15-6 a, lead confirms) if one point pitch form and one u form hold 6 of 6, one u16
  form 1 of 1 and one footprint form 2 of 2, with all five controls PASS. Then Q078's "other
  formats" reads "the 16-bit format" [infer]; filtered = bilinear on the wrap edge only
  (deviation 1).
- If H-TWP fails but H-TWP4128 holds: the pitch is a constant (E1047 correction: "W + 4096" was
  read from W = 32 only). If H-WRAPW holds: the move is the texel coordinate's 12 bits, not
  frac(u); E1047's text names frac(u) and takes a note.
- H-CLAMP1 is refuted by E1047 already (tests/test_gen.py): its 3 held rows (u below 1) are not
  support; say so in the record.
- If a fault ends the session: read its BIF page against reach() (gen/tw.py); a fault inside the
  scratch means the mapping premise failed (t14), not bit 14.
- Replay: if forms hold, a `tex` table `tw14` (closing_tables.py, sgx545-tables) from the kept
  files and predictions/tw14/, sgx-sim tex.rs widened beyond 32 x 32 (W 16, 64, 128; u16 texels;
  bilinear footprint), replayed by sgx-pipe tests/texture_t3b14.rs.
- Kit needs (report, do not change shared tools): none found.
