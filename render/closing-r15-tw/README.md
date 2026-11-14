# r15-tw (round 15: Q078 T3 bit 14 on twiddled textures at other widths, u16 and bilinear)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 158bdc5455b2 (kit/ is that commit's blobs) and
resgx545-data cddc7b60b8ed. Plan `closing15/plan/rank-round15.md` sections 2 ("r15-tw") and 3;
decisions `closing15/DECISIONS-R15.md`: R15-2 (a), **SAFE CLASS**: H at most 32 so every frozen
model's farthest read lies inside t14's 1 MiB scratch, the rows in reach order, the round's last
session, any fault ends it. Built offline; nothing here touched the laptop, cachix or a git
repository. Record E1049 is reserved for its fold (the builder folds it). Predecessor: r14-flag f1
and its fold E1047 (H-TWP4128 form, `render/closing-r14-flag` in resgx545-data).

## What runs: 14 jobs, one stage, about 5 minutes

Laptop: module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is
written (only `reset`). Files under `~/scratch/r15w/`.

- t14 = `~/sgxfive-test-t14` (sha256 aa550b94...), bound by source to resgx545 c58f9f9
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 9cef7a20...), recipe
  `data:render/closing-r14-flag/lead/build_tool14.sh` (copied to `lead/build_tool14.sh`; the
  lead's build line: closing14/k14/TOOL14.built). Every row: `probe --temps 32 --coords --pixels
  --scratch-pages 256 "$S/bins/NAME.bin"`.
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06: the health pair only.

| # | stage | jobs | #limit | tool | what | controls |
|---|---|---|---|---|---|---|
| 1 | tw14 | 14 | 0 | t14 | bit 14 on twiddled W x 32 at W 16, 64, 128 (u in (0, 1) and past 1), u16 32 x 32, two bilinear rows | 4 bit-clear references, E1047's f1-zero rerun |

Rows in run order (ascending reach: the farthest dword any frozen model reads; gen/tw.py
`reach()`): tw-ref16 (511), tw-refu16 (511), tw-ref64 (2047), tw-ref128 (3071), tw-zero (66133,
E1047's kept image), tw-u16 (131071), tw16-u0 (131327), tw-bl16 (131573), tw16-u1 (131583),
tw-bl32 (132093), tw64-u0 (132607), tw128-u0 (133119), tw64-u2 (133119), tw128-u2 (134143). The
scratch holds dwords 0 to 262143: the farthest read of every model is at 51 % of it
(tests/test_gen.py `test_safe_class_reach_inside_the_scratch_and_in_order`). E1047's rows read up
to dword 131071 and did not fault.

### tw14 (Q078, E1049): the frozen forms (gen/tw.py)

E1047's form: E566's tx_map (scratch dword i reads 0xD0000000 | i), a twiddled texture (T1 FMT <<
24 | (W - 1) << 12 | 31) at the scratch's first dword, T0 0x07FE0000 (bilinear 0x07FE1400), T3
0x00800800 (| bit 14). s = floor(W u) mod W, t = floor(32 v), fr = frac(u), tl(c, t, P) E561's 16 x
16 tiles with a tile row of P texels.

- Point rows (tw16-u0, tw16-u1, tw64-u0, tw64-u2, tw128-u0, tw128-u2), exact images: **H-TWP**
  tl(s + floor(4096 fr), t, W + 4096) (E1047's form with the pitch read as W + 4096); H-TWP4128
  (a constant 4128 tile row); H-CLAMP1 (u clamped to [0, 1]: s + 4096 past 1; E1047's f1-tw32
  already refutes it at W = 32, carried as the plan's rival); H-WRAPW (move floor(128 W u) mod 4096,
  the texel coordinate's 12 bits [infer], equal to H-TWP at W = 32); H-TWP4096 (E1047's refuted
  pitch, a negative). Each pair parts on 1024 or more pixels of every row, but H-TWP and H-CLAMP1
  on the u-below-1 rows (one image there).
- u16 row (tw-u16, 32 x 32 FMT 9; the low 16 bits of the read, texel T the half T & 1 of dword T
  >> 1): **U16-TX** (H-TWP in texels, E1026's u16 tiles); U16-T32 (tiles of 16 x 16 dwords, two
  horizontally adjacent texels a dword); U16-DW (move and widening in dwords). Deviation 2.
- Bilinear rows (tw-bl32, tw-bl16; each byte within 1, texmodel's blend in 64ths): **H-FOOT-TW**
  (each tap the bit-14 address of its own wrapped texel, moved by the sample's u, E1027);
  H-FOOT-SHIFT (the second column unwrapped in the wide layout); H-POINT (the filter dropped).
  Deviation 1.
- Controls that can fail: tw-ref16, tw-ref64, tw-ref128, tw-refu16 (the bit-clear image of the
  shape, E561's law; u16 in texels), tw-zero (E1047's f1-zero program byte for byte, its kept
  image). A held-out row is cannot tell unless tw-zero and its shape's reference passed (tw-bl32:
  tw-zero only).

Retire Q078 (R15-6 a, the lead confirms) if one pitch form and one u form hold on all six point
rows, the u16 row reads one form, and one footprint form holds on both bilinear rows, with every
control passing; "other formats" then reads "the 16-bit format" [infer].

## Stops

- Any fault or hang (no row has `expectfault`, `#limit 0`): the stage stops (4) and the session
  with it; the rows run in reach order, so a stray fault stops at the smallest reach.
- hook_check (24): an ok row without its 32 pixel rows or without `scratch at A (1024 KiB)`;
  `on_stop = "end"` ends the session.
- A control without its reading stops the session (25).
- Strict health after any fault (the kit's).

## The mock's worlds (mock/world.py, kit/session.py mock)

model (H-TWP, U16-TX, H-FOOT-TW: 0, 0), alt (H-TWP4128, U16-T32, H-FOOT-SHIFT: 0, 0), alt2 (H-WRAPW,
U16-DW, H-POINT: 0, 0), ctlfault (the first row faults: 4, 4), rowfault (the last row faults: 4, 4),
rowhang (tw16-u0 hangs: 4, 4), nopix (a control prints no rows: 24, ends), short (31 rows: 24),
small (a 64 KiB scratch line: 24). The kit's library-mock replay runs all 14 rows on t14's pinned
source ("program not simulated").

## Replay vectors

tw14: `refused` until the fold: if one form of each kind holds, the six point images, the u16 and
the bilinear images become a `tex` table `tw14` (`closing_tables.py` format `sgx545-tables`) for
sgx-sim's texture address (tex.rs, the bit-14 geometry widened from 32 x 32), replayed by
sgx-pipe's `tests/texture_t3b14.rs` as E1047's table is; the fold builds it from the kept files and
predictions/tw14/. Everything it reads is in this directory or pinned.

## Layout

gen/make.py writes tables/, predictions/ and bins/ from gen/tw.py (gen/law.py, gen/pins.py,
gen/tex.py r14-flag's, tests check them); score/score.py; run/hooks.sh; mock/world.py; tests/
(test_gen.py, test_twin.py, test_score.py); lead/build_tool14.sh (t14's recipe); PREFLIGHT.md;
FOLD-NOTES.md. Publishable: everything (our own programs, tables, scorer and mock; no
firmware-derived file). **Nothing is marked for data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check` (the generator current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r15-tw-run.log`).
- Score again on a kept attempt: `python3 score/score.py tw14 out/ATT/tw14`.

## Deviations from the plan (the lead may object before staging)

1. **Bilinear coordinates**: the plan's u in (0, 1) at 32 x 32 and (1, 2) at 16 x 32 become u
   ramps that put every footprint across the texture's right edge (tw-bl32 u from 0.984 to 1.015,
   tw-bl16 from 1.969 to 2.031; kx = x). With u a ramp of x alone, a spread of u puts 2 pixels a
   row on the edge, and H-FOOT-SHIFT parts from H-FOOT-TW only there (17 pixels past both
   tolerances; now 523 and 136). Each row still crosses an integer u, so the footprint's move
   jumps inside it.
2. **The u16 tile rival**: "tiles of 32 x 16 texels" under E561's interleave is E561's 16 x 16
   tiles in raster order (one law, 0 pixels apart), so U16-T32 is frozen as the dword-pair layout
   (16 x 16 dwords, two horizontally adjacent texels a dword). A third rival U16-DW (move and
   widening in dwords) is added. Odd texels read the dword's high half 0xd000 (no information),
   so 1024 of the row's pixels decode the address.
3. **H-WRAPW's exact form** (the plan's "[check: the builder writes the exact form]"): the move
   floor(128 W u) mod 4096, 4096 frac(u W / 32) [infer]; it equals H-TWP at W = 32.
4. **H-CLAMP1 is already refuted at W = 32** by E1047's f1-tw32 (tests replay every rival on
   E1047's three kept images: H-TWP, H-TWP4128, H-WRAPW 2048 of 2048 each); frozen anyway as the
   plan's rival.
5. **u steps at most one texel a pixel**: the 128-wide rows sample u in (0, 0.5) and (2, 2.5)
   (texel columns 0 to 63, one a pixel), so the gradient's LOD stays at 0 or below as in E1047's
   rows;
   T3 bits 12:11 stay E566's 01 (the LOD's level).
