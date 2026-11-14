# r15-tex fold notes (2026-11-14, after the run)

Attempt `out/20261114-073318`, rc 0, no stop, fault or hang (the three smp1d rows included). The
frozen scorer re-run on the kept files is byte-identical (`fold/reproduce.sh`,
`fold/reproduce.out`). Logs: `fold/run-r15t.log`, `fold/stage-r15t.log`.

Records: E1052 chain (Q104), E1055 ty (Q177).

## Verdicts

- chain: both controls passed. A 11 of 11 (B 0 of 11, D 0 of 9), A-TX 4 of 4 (A-DW, B-TX, D-TX 0
  of 4), A-TX-BL16 1 of 1 (A-TX-BL8 1536 of 2048: the 16-bit blend is one lerp, not per byte; the
  builder's expected BL8 failed).
- ty: both controls passed. H-HALF 10 of 10; NAME-WRAP 1 of 1 (the builder's NAME-U failed: the
  16 x 16 map follows the column inside the texture); H-LIN1 3 of 9 (the 32 x 32 mode 4 rows; the
  mode 5 to 7 rows read one value a row); H-AS-U4 0 of 6; H-MODE0, H-WHOLE 0 of 9; R-W 2 of 2,
  R-32 1 of 1 (R-2W 64 of 2048).

## Post hoc (after the scores were read; fitted, not held out)

- `fold/types_post.py`: at 16 x 16 modes 6 and 7 read mode 4's last column on every pixel (691
  type 1, 675 type 4, or 256 less), mode 5 one other halved name (163 or 164 type 1; 371, 372, 627
  or 628 type 4); at 32 x 32 mode 4 reads 1300 + (x mod 32) (or 256 above) on all three types; the
  32 x 32 references read 32 t + s (types 1, 3: the width; type 4: its block).
- `fold/sim_points.py`: the kept pixels the sgx-sim tests hold.

## R15-6 (the lead confirms)

- Q104: retirement proposed. The 1D, side-1 and 16-bit clauses are decided by held-out rows with
  passing controls (and the long sides E562 did not reach); "1D" reads smp1dreplace on 64 x 1
  [infer].
- Q177: narrowed. The halving form held out on ten rows and the 16 x 16 map's wrap held out; the
  size form, modes 5 to 7 (post hoc only) and the halving's meaning stay open.

## Sim and vectors

sgx-sim tex.rs reads E1052's chains (CHAIN_SIZES, u16 at 32 x 16 and 16 x 64 in texels, its 16-bit
MIPFILTER lerp, 64 x 1 read 1D) and types 1, 3 and 4 at 16 x 16 and 32 x 32 in mode 0 and u mode 4
(E1055's halved names); modes 5 to 7 on these types stay refused, naming E1055. The pixel tables
`vectors/closing/r15-tex/pixels/{chain,ty}.table.json` are written refused (digests, not a
row-by-row replay).
