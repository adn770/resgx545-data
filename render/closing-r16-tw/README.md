# r16-tw (round 16: Q078 T3 bit 14, E1049's bilinear form held out and heights 8, 16 and 64)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 b2b5288c82ed (kit/ is that commit's blobs) and
resgx545-data 62cb03b369ca. Plan `closing16/plan/rank-round16.md` sections 2 ("r16-tw") and 3;
decisions `closing16/DECISIONS-R16.md`: R16-2 (a), **SAFE CLASS**: no bilinear row above H 32, the
H 64 rows last with frac(u) <= 0.4, every frozen model's farthest read inside t14's 1 MiB scratch,
rows in reach order, the round's last session, any fault ends it. Built offline; nothing here
touched the laptop, cachix or a git repository. Record E1058 is reserved for its fold (the builder
folds it). Predecessor: r15-tw tw14 and its fold E1049 (`render/closing-r15-tw` in resgx545-data,
`fold/bilin_forms.py`'s H-FOOT-FR form).

## What runs: 17 jobs, one stage, about 5 minutes

Laptop: module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is
written (only `reset`). Files under `~/scratch/r16w/`.

- t14 = `~/sgxfive-test-t14` (sha256 aa550b94...), bound by source to resgx545 c58f9f9
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 9cef7a20...), recipe
  `data:render/closing-r14-flag/lead/build_tool14.sh` (copied to `lead/build_tool14.sh`; the
  lead's build line: closing14/k14/TOOL14.built), as r15-tw. Every row: `probe --temps 32 --coords
  --pixels --scratch-pages 256 "$S/bins/NAME.bin"`.
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06: the health pair only.

| # | stage | jobs | #limit | tool | what | controls |
|---|---|---|---|---|---|---|
| 1 | tw16 | 17 | 0 | t14 | 6 bilinear rows (inside, left edge, right edge, v edge, H 16), 8 point rows at H 8, 16, 64 | 2 bit-clear references, E1049's tw-bl32 rerun |

Rows in run order (ascending reach, the farthest dword any frozen model reads; gen/tw16.py
`reach()`): ref32h8 (255), ref16h64 (887), pt128h8 (33471), pt128h16 (33535), pt32h8 (65471),
pt32h16 (65535), bl16h16in (98432), bl64left (134568), bl128h16right (135082), bl128vedge
(160384), bl64in (166144), bl32r (198056), bl128right (202666), pt16h64u0 and pt16h64u1 (222551),
pt64h64u0 and pt64h64u1 (224351). The scratch holds dwords 0 to 262143: the farthest read of every
rival on every row is at 86 % of it (tests/test_gen.py
`test_safe_class_reach_inside_the_scratch_and_in_order`). E1049 read up to dword 134143 under its
frozen models; the bilinear rows' far reaches are F-VNEXT's (the second row in tile row 2), and
the H 64 rows read dwords no job has read (199680 to 224351).

### tw16 (Q078, E1058): the frozen forms (gen/tw16.py)

E1049's form: E566's tx_map (scratch dword i reads 0xD0000000 | i), a twiddled 32-bit texture
(T1 12 << 24 | (W - 1) << 12 | (H - 1)) at the scratch's first dword, T0 0x07FE0000 (bilinear
0x07FE1400), T3 0x00800800 | bit 14. s = floor(W u) mod W, t = floor(H v) mod H, m = floor(4096
frac(u)); E561's tiles are min(W, 16) x min(H, 16) texels (16 x 8 at H 8).

- Point rows (pt32h8, pt128h8, pt32h16, pt128h16, pt16h64u0/u1, pt64h64u0/u1), exact images:
  **H-TWP-H** E1049's H-TWP (texel (s + m, t) in a tile row of W + 4096 texels) with E561's tile
  height; H-TWP-T16 (16 x 16 tiles at H 8; parts at H 8); H-MOVEH (move floor(128 H frac(u)),
  tile row W + 128 H [infer]; parts at H 8 and 16, scored there only); H-TWP-V32 (t mod 32; parts
  at H 64); H-TWP-STRIP (one 4096 x H strip after the texture, the plan's [infer]; parts at H 64,
  E1049's kept images refute it already); H-TWP4128 (parts at H 64, refuted by E1049). At one tile
  row (H 8, 16) the pitch rivals are H-TWP-H's own image: the H 8 rows part H-TWP-T16 and H-MOVEH,
  the H 16 rows H-MOVEH only (deviation 3).
- Bilinear rows (bl64in, bl64left, bl128right, bl128vedge, bl16h16in, bl128h16right; each byte
  within 1, texmodel's blend in 64ths): **F-FRAC** (taps at columns X mod W + m and X + 1 + m, X =
  floor(W frac(u) - 1/2), rows y0 and y0 + 1 mod H: E1049's post hoc form, 2048 of 2048 on both of
  its rows); F-VNEXT (the second row H at the v edge, the next tile row); H-FOOT-SHIFT (parts at
  the left edge only); H-FOOT-TW (parts at the right edge only; the plan's F-WRAP2 is this form,
  deviation 2); H-POINT (the filter dropped). Inside the texture the three column forms are one
  image: bl64in and bl16h16in part F-FRAC from H-POINT only.
- Controls that can fail: ref32h8 and ref16h64 (the bit-clear images of the new heights, E561's
  law, the H 8 one its 16 x 8 tile: the plan's [check]); bl32r (E1049's tw-bl32 program byte for
  byte, rebuilt from its spec in the tests, and its kept image within 1 a byte). A held-out row is
  cannot tell unless bl32r and its height's reference (H 8: ref32h8, H 64: ref16h64) passed.

Parting (tests/test_gen.py `PARTS`, pixels past both tolerances): bl64left H-FOOT-SHIFT 736;
bl128right H-FOOT-SHIFT 1024, H-FOOT-TW 690; bl128h16right H-FOOT-SHIFT 1024, H-FOOT-TW 992;
bl128vedge F-VNEXT 1286; H-POINT 745 to 1928 on every bilinear row; the H 8 rows 2048 for
H-TWP-T16 and H-MOVEH, the H 16 rows 2048 for H-MOVEH, the H 64 rows 2048 for H-TWP-V32 and
H-TWP4128, 1040 or 1072 for H-TWP-STRIP.

Retire Q078 (R16-6 a, the lead confirms) if F-FRAC (or exactly one rival) holds on all six
bilinear rows and one height form on all eight point rows, with the three controls passing.
"Heights other than 32" then reads "8, 16 and 64" [infer].

## Stops

- Any fault or hang (no row has `expectfault`, `#limit 0`): the stage stops (4) and the session
  with it; the rows run in reach order, so a stray fault stops at the smallest reach.
- hook_check (24): an ok row without its 32 pixel rows or `scratch at A (1024 KiB)`, and **the H
  16 sentinel**: pt32h16 and pt128h16 must print `d000ffff` and `d00082ff`, H-TWP-H's farthest
  dword there (no H-MOVEH image has it). H-MOVEH at H 64 would read past the scratch (to dword
  445183),
  so without the sentinel the reach proof of every farther row does not hold and the stage stops
  before them. `on_stop = "end"` ends the session.
- A control without its reading stops the session (25). Strict health after any fault (the kit's).

## The mock's worlds (mock/world.py, kit/session.py mock)

model (H-TWP-H, F-FRAC: 0, 0), alt (H-TWP-T16 at H 8, H-TWP-V32 at H 64, H-FOOT-SHIFT: 0, 0), alt2
(H-TWP-STRIP at H 64, H-FOOT-TW: 0, 0), alt3 (H-MOVEH at H 8, H-TWP4128 at H 64, F-VNEXT: 0, 0),
alt4 (H-POINT: 0, 0), moveh (H-MOVEH at H 16: the sentinel stop, 24, ends after 4 jobs), ctlfault
(the first row faults: 4, 4), rowfault (the last row faults: 4, 4), rowhang (bl64in hangs: 4, 4),
nopix (a control prints no rows: 24), short (31 rows: 24), small (a 64 KiB scratch line: 24). The
kit's library-mock replay runs all 17 rows on t14's pinned source ("program not simulated").

## Replay vectors

tw16: `refused` until the fold: if the forms hold, the eight point images and the six bilinear
images become a `tex` table `tw16` (`closing_tables.py` format `sgx545-tables`) for sgx-sim's
texture address (tex.rs: the bilinear footprint and H != 32 added by the fold), replayed by
sgx-pipe's `tests/texture_t3b14.rs` as E1047's and E1049's tables are; the fold builds it from the
kept files and predictions/tw16/. Everything it reads is in this directory or pinned.

## Layout

gen/make.py writes tables/, predictions/ and bins/ from gen/tw16.py (gen/law.py, gen/pins.py,
gen/tex.py r15-tw's, tests check them); score/score.py; run/hooks.sh (the sentinel words, checked
by tests); mock/world.py; tests/ (test_gen.py, test_twin.py, test_score.py); lead/build_tool14.sh
(t14's recipe); PREFLIGHT.md; FOLD-NOTES.md. Publishable: everything (our own programs, tables,
scorer and mock; no firmware-derived file). **Nothing is marked for data-private.** `debug/` is
scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check` (the generator current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r16-tw-run.log`).
- Score again on a kept attempt: `python3 score/score.py tw16 out/ATT/tw16`.

## Deviations from the plan (the lead may object before staging)

1. **Edge rows' widths**: the plan's 16 x 32 left-edge row is 64 x 32 (bl64left), its 32 x 32 v
   edge row 128 x 32 (bl128vedge), and its 16 x 16 right-edge row 128 x 16 (bl128h16right). At
   W 16 the left tap's two candidate columns are one tile apart, so the blends differ by at most
   1 in a byte and part on no pixel (E1049's tw-bl16 held H-FOOT-SHIFT for that reason); the v
   edge's next tile row moves a name by W / 8 in byte 1, which parts only from W 64 up. bl16h16in
   keeps 16 x 16. The right-edge rows straddle the integer (as E1049's), so they cross the left
   edge too.
2. **F-WRAP2 = H-FOOT-TW**: both columns wrapped (X mod W, (X + 1) mod W) is H-FOOT-TW exactly
   (x0 mod W = X mod W): one law (test `test_f_wrap2_is_h_foot_tw`), frozen once.
3. **Point rivals by height**: at H 8 and 16 H-TWP-STRIP and H-TWP4128 are H-TWP-H (one tile
   row); H-TWP-T16 (the plan's [check] on E561's tile below 16) parts at H 8, and H-MOVEH (added:
   the move and widening scaling with H) parts at H 8 and 16. H-MOVEH is not scored at H 64 (its
   reach passes the scratch there): the H 16 sentinel stop guards those rows instead.
4. **F-VNEXT, H-TWP-STRIP and H-TWP4128 are already refuted** by E1049's kept images (F-VNEXT
   on 17 and 9 pixels of the last pixel row, the other two on 1024 pixels of each point row):
   frozen anyway as the plan's rivals (tests/test_gen.py `test_forms_on_e1049s_kept_images`).
5. **Coordinates**: v stays in (0, 1] (t = y div 4 at H 8, y div 2 at H 16, 32 + y at H 64,
   so the H 64 rows read tile rows 2 and 3); u at H 64 is 3 x / 512 + 1/1024 (frac(u) <= 0.37),
   plus 1 on the u1 rows.
