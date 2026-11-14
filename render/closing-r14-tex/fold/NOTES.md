# r14-tex fold notes (2026-11-14, after the run)

Attempt `out/20261114-054258`, rc 0, no stop, fault or hang. The frozen scorer re-run on the kept
files is byte-identical (`fold/reproduce.sh`, `fold/reproduce.out`). Logs: `fold/run-r14t.log`,
`fold/stage-r14t.log`.

Records: E1038 srgb4 (Q282), E1039 addr5 (Q177).

## Verdicts

- srgb4: the three controls passed. TRI-G15 held 7 of 7 trilinear rows (TRI-G15-NF 6 of 7: the
  dark row's 224 flushed pixels; TRI-RNTU 4 of 7: 7, 6 and 137 parting pixels missed); Q-FLOOR
  (every QN- form 0 of 2048 at LOD 1.2); B2-FTZ-OUT and A-LIN 3 of 3 (A-SRGB 0, A-BYTE 207 to 225
  pixels).
- addr5: both controls passed; C-LOG4 and IN-M, LR-M, AB-M 6 of 6; the type references replicated
  E567 (3 of 3); T-MODE0 and T-OFFSET 0 of 3.

## Post hoc (after the scores were read; fitted, not held out)

- `fold/types_post.py`: the type rows with u mode 4 print 0x68xxxxxx on every pixel, the 32 rows
  alike, 9 distinct values; every pixel is a named dword with each byte halved, rounded up
  ((b + 1) >> 1, a 50/50 blend with zero [infer]): names 675 to 691 (types 1 and 3, the same
  image) and 659 to 675 (type 4), rising along x.
- `fold/sim_points.py`: the kept pixels the sgx-sim tests hold (one a region a uv5 shape; six and
  the parting pixels of three trilinear rows).

## R14-6 (the lead confirms)

- Q282: retirement proposed. Both clauses (the trilinear level lerp, bytes 2 and 3) are decided by
  held-out rows with passing controls; negative values void [infer] (E1025).
- Q177: narrowed, not retired. The corner base is decided (C-LOG4 6 of 6); "why these constants"
  is reworded to the held-out formulas [infer]; types 1, 3 and 4 in u modes 4 to 7 stay open
  (neither frozen form held).

## Sim and vectors

sgx-sim tex.rs models the trilinear sRGB level lerp (E1038, `srgb_level_lerp`, the fraction
floored) and mode 5 past the texture on 32-bit twiddled textures (E1039: sides, above, below,
corners), admits 256 x 32 tiles and E1038's chain words; it refuses the sRGB second register (named
E1038) and raster types in u modes 4 to 7 (named E1039). Tests hold kept pixels of every region
and shape and of three trilinear rows (`fold/sim_points.out`). The pixel tables
`vectors/closing/r14-tex/pixels/{srgb4,addr5}.table.json` are written refused (the kit's texture
kind: digests, not a row-by-row replay).
