# r16-tw fold notes (builder, before the run)

- Record: E1058 (tw16, Q078) only. Draft its method with `tools/records/new_record.py --session
  DIR`; appended corrections only.
- Score: `python3 score/score.py tw16 out/ATT/tw16`. READING lines decode every ok point image
  (which dwords, each model's pixels); the bilinear images are blends (no dword decode).
- Retire (R16-6 a, lead confirms) if F-FRAC (or exactly one rival) holds 6 of 6 bilinear rows and
  one height form (H-TWP-H expected) 8 of 8 point rows, with ref32h8, ref16h64 and bl32r PASS.
  Then "heights other than 32" reads "8, 16 and 64" [infer]; say which rivals each height parts
  (H 16 parts only H-MOVEH; H-TWP-STRIP, H-TWP4128, F-VNEXT were already refuted by E1049's kept
  images, so their FAILED rows are not new support).
- Inside rows (bl64in, bl16h16in) part F-FRAC from H-POINT only: they test the move and the blend,
  not the edge rule. The edge rule rests on bl64left (left), bl128right and bl128h16right (both
  edges), bl128vedge (v edge).
- If the sentinel stop (24) ends the session at pt32h16 or pt128h16: the H 16 move is not
  4096 frac(u); score what ran, decode the H 16 image (READING) and do not plan H 64 rows on the
  current reach proof.
- If a fault ends the session: read its BIF page against reach() (gen/tw16.py); a fault inside the
  scratch means the mapping premise failed (t14), not bit 14.
- Replay: if the forms hold, a `tex` table `tw16` (closing_tables.py, sgx545-tables) from the kept
  files and predictions/tw16/, sgx-sim tex.rs widened (bilinear footprint, H 8, 16, 64), replayed
  by sgx-pipe tests/texture_t3b14.rs.
- Kit needs (report, do not change shared tools): none found.
