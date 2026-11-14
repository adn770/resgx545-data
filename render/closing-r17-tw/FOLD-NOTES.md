# r17-tw fold notes (builder, before the run)

- Record: E1067 (tw17, Q078) only. Draft its method with `tools/records/new_record.py --session
  DIR`; appended corrections only.
- Score: `python3 score/score.py tw17 out/ATT/tw17`. LEFTWRAP and RIGHTWRAP lines per row, the
  `SUMMARY: tw17: LEFT-WRAP:` verdict (R17-3 a rule); READING lines for every ok image.
- H-WIDE is post hoc on E1049 and E1058 (gen/derive.py, fit/derive.out): cite these, not the
  planner's `plan/calc/`. The held-out rows are tw17's; say "fitted on E1049 and E1058, held out
  on E1067".
- Retire (R17-3 a, the lead confirms) if H-WIDE (or exactly one rival) holds 7 of 7 bilinear rows,
  the LEFT-WRAP line names one column, H-WIDE-NEXT is FAILED (or H-WIDE is) where they part, one
  point form 3 of 3, and bl64leftr and the references PASS. H-WIDE-G's SUMMARY is within 1 and
  is H-WIDE's image: do not count it as a held rival (README deviation 3). bl256corner tests the
  right and v edges only.
- If H-WIDE-PT wins: restate the point clause as floor(W' frac u); no correction to E1049's or
  E1058's point claims (on the grid the two forms are one [infer]); say so in E1067.
- If the session stops before the new widths (a reference's sentinel, a fault): the W <= 128 rows
  still decide the left wrap (93 pixels >= 64) but not the right wrap (no row parts H-WIDE-NEXT
  there): Q078 narrows.
- If a fault ends the session: read its BIF page against reach() (gen/tw17.py); a fault inside
  the scratch means the mapping premise failed (t14), not bit 14. bl2048edge is the first 2048-
  wide texture: a fault there narrows "widths" only.
- Replay: if the forms hold, a `tex` table `tw17` (closing_tables.py, sgx545-tables) from the
  kept files and predictions/tw17/; sgx-sim tex.rs gains the bilinear bit-14 sample (H-WIDE),
  replayed by sgx-pipe tests/texture_t3b14.rs.
- Kit needs (report, do not change shared tools): none found.
