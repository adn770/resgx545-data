# r16-tex fold notes (2026-11-14, after the run)

Attempt `out/20261114-090305`, rc 0, no stop, fault or hang (15 jobs). The frozen scorer re-run on
the kept file is byte-identical (`fold/reproduce.sh`). Logs: `fold/run-r16t.log`,
`fold/stage-r16t.log`.

Record: E1065 ty2 (Q177).

## Verdicts (frozen scorer, as printed)

The control passed (E1055's ty-ty1u4r rerun, 2048 of 2048). H-HALF 9 of 9 and H-FLAT 2 of 2 held.
**E1055's two-point fit of the name failed at the new sizes:** N13 0 of 3 (8 x 8, 64 x 64, 64 x 16),
N4 1 of 2 (held at 8 x 8, failed at 64 x 64), NQ13 0 of 3, NQ4 0 of 2, N13-H 0 of 1, L13 and LQ13 0
of 2 (modes 6 and 7 at 64 x 64), H-AS-U4 0 of 4, H-MODE0 0 of 9, H-WHOLE 0 of 5. References: R-W 3
of 5 (type 1 held at 8 x 8, 64 x 64 and 64 x 16; it failed as a rival on type 4), R-32 1 of 5 (type
4 at 8 x 8 held, at 64 x 64 failed; it failed as a rival on type 1), R-16 0 of 5, R-2W 0 of 2; type 4 at
64 x 64 read no frozen stride (R-32 on 1024 of 2048 pixels).

## Post hoc (after the scores were read; fitted, not held out)

`fold/types_post.py` and `fold/types_post.out`:

- Mode 4 names (halving's ambiguity: the lowest of each pair, the other 256 above it): type 1 reads
  c + (x mod W) with c = 172 (8 x 8), 676 or 420 (16 x 16, E1055), 1300 (32 x 32, E1055), 4596 (64 x
  64) and 1524 (64 x 16); type 4 c = 340 (8 x 8), 660 (16 x 16), 1300 (32 x 32) and, at 64 x 64, no
  one c: 3347 + (x mod 32) for x < 32 and 4371 + (x mod 32) from 32, two 32-wide blocks 1024 apart.
- Type 1 fits **W H + 7 W + 52 + (x mod W)** on every size seen (8, 16, 32, 64, and 64 x 16: the
  product W H, not max(W, H)^2); five sizes, three free numbers: not held out.
- Mode 5 (type 1) one value: 107 (8 x 8), 163 (16 x 16, E1055), 499 (64 x 64): 7 W + 51. Modes 6 and
  7 at 64 x 64 one value, 4403 or 4659 = mode 4's last column W H + 7 W + 52 + 63.
- References: type 1 dword W (y mod H) + (x mod W) at 8 x 8, 64 x 64 and 64 x 16; type 4 at 8 x 8
  32 (y mod 8) + (x mod 8); type 4 at 64 x 64 the 32 x 32 blocks (E941): 1024 (x div 32) + 32 y + (x
  mod 32).

All of it is for a later held-out round (R16-7 b), none of it for a retirement.

## Sim and vectors

sgx-sim tex.rs refuses types 1, 3 and 4 in u modes 4 to 7 at 8 x 8, 64 x 64 and 64 x 16 naming
E1065 (test `e1065_the_two_size_fit_of_the_name_is_refused_at_the_sizes_it_failed_at`, written
first); the name at 16 x 16 and 32 x 32 is now the two measured values, not the formula 39 W + 52
that those two sizes gave. The pixel table `vectors/closing/r16-tex/pixels/ty.table.json` is
written refused.
