# r17-tw (round 17: Q078 T3 bit 14, the bilinear sample at both edges, H-WIDE held out)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 c2180e64ecda (kit/ is that commit's blobs, the same
bytes as r16-tw's b2b5288 kit) and resgx545-data af46e80770ac. Plan `closing17/plan/rank-round17.md`
sections 2 ("r17-tw") and 3; decisions `closing17/DECISIONS-R17.md`: R17-1 to R17-4 (a), **SAFE
CLASS**, H-WIDE frozen after the builder re-derived it from the kept files, the left wrap decided by
the pre-declared exact-byte rule, the widths never run with bit 14 last, `on_stop = "end"`. Built
offline; nothing here touched the laptop, cachix or a git repository. Record E1067 is reserved for
its fold (the builder folds it). Predecessor: r16-tw tw16 and its fold E1058
(`render/closing-r16-tw`
in resgx545-data, `fold/bilin_post.py`).

## What runs: 14 jobs, one stage, about 5 minutes

Laptop: module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is
written (only `reset`). Files under `~/scratch/r17w/`.

- t14 = `~/sgxfive-test-t14` (sha256 aa550b94...), bound by source to resgx545 c58f9f9
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 9cef7a20...), recipe
  `data:render/closing-r14-flag/lead/build_tool14.sh` (copied to `lead/build_tool14.sh`; the lead's
  build line: closing14/k14/TOOL14.built), as r16-tw. Every row: `probe --temps 32 --coords
  --pixels --scratch-pages 256 "$S/bins/NAME.bin"`.
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06: the health pair only.

| # | stage | jobs | #limit | tool | what | controls |
|---|---|---|---|---|---|---|
| 1 | tw17 | 14 | 0 | t14 | 7 bilinear rows (left wrap, right wrap, both, on and off the 1/4096 grid, v edge), 3 off-grid point rows | E1058's bl64left rerun, bit-clear 256 x 32, 512 x 16, 2048 x 16 |

Rows in run order (the plan's; reach = the farthest dword any frozen form reads, gen/tw17.py
`reach()`): bl64leftr (control, 68093), bl16left (131583), bl64grid (133119), bl128off3 (135167),
pt128off (68183), ref256 (8191), ref512h16 (8191), pt256off (861), pt512off (757), bl256edge
(139349), bl512edge (147541), bl256corner (139349), ref2048h16 (32767), bl2048edge (98389). The
scratch holds dwords 0 to 262143: every rival's farthest read on every row is below 150000
(147541, H-WIDE-NEXT on bl512edge), inside E1058's 224351, so no range is read for the first time
(tests/test_gen.py `test_safe_class_every_rival_inside_the_scratch`, `test_reach_per_rival`). The
widths never run with bit 14 (256, 512, 2048) come last, each after its bit-clear reference.

### tw17 (Q078, E1067): the frozen forms (gen/tw17.py)

E1058's form: E566's tx_map (scratch dword i reads 0xD0000000 | i), a twiddled 32-bit texture
(T1 12 << 24 | (W - 1) << 12 | (H - 1)) at the scratch's first dword, T0 0x07FE1400 (bilinear) or
0x07FE0000 (point), T3 0x00800800 | bit 14. W' = W + 4096; E561's tiles of 16 x min(H, 16) texels
with a tile row of W' texels (E1058). X = floor(W frac(u) - 1/2), m = floor(4096 frac(u)); rows y0
and y0 + 1 mod H (E1058). Every bilinear row has whole-64th weights under every form (tests).

- **H-WIDE** (frozen, post hoc, re-derived by gen/derive.py from the kept files of E1049 and
  E1058, output `fit/derive.out`: 16384 of 16384 kept pixels within 1, 12408 exact): the sample
  is taken over a texture W' texels wide at frac(u): fx = W' frac(u) - 1/2, columns floor(fx) and
  + 1 mod W' (column -1 reads W' - 1, column W' reads 0), kx = 64 (fx - floor(fx)).
- Rivals: **H-WIDE-G** (column -1 at W - 1; names 65536 apart, parts by exact bytes only: the
  LEFT-WRAP rule), **H-WIDE-NEXT** (column W' unwrapped, the next tile row's first column; parts by
  names), **UNWRAP-G** (E1058's post hoc reading: columns X + m, X + 1 + m, weights from W
  frac(u), -1 at W - 1), **F-FRAC** (E1049's form, refuted by E1058, carried), **H-POINT** (the
  filter dropped: H-WIDE-PT's image).
- Point rows: **H-WIDE-PT** (column floor(W' frac(u)), frozen) and **H-TWP** (floor(W frac(u)) +
  m, E1049's and E1058's H-TWP-H). On the 1/4096 grid they are one image (every kept point pixel
  of both rounds, `fit/derive.out`); the three point rows are off it.
- **LEFT-WRAP rule** (R17-3 a, pre-declared, score/score.py): over every held-out bilinear row
  that ended ok with its gate open, at the pixels where H-WIDE's and H-WIDE-G's frozen images
  differ, the winner is byte-exact on at least 90 % and the loser on at most 10 %, with at least 64
  such pixels; anything else is cannot tell. Kept fit set: 124 of 128 against 0 of 128. This
  stage has 189 such pixels (93 on the W <= 128 rows alone).
- Controls that can fail: **bl64leftr** (E1058's bl64left program byte for byte, its kept image
  within 1 a byte: gates every held-out row), **ref256**, **ref512h16**, **ref2048h16** (bit-clear
  point images of the new widths read across the u edge, E561's law: each gates its width's rows,
  and hook_check stops the stage unless it prints its sentinel dword).

Parting (tests/test_gen.py `PARTS`; bilinear: pixels past both tolerances, H-WIDE-G: exact):

| row | W x H | H-WIDE-G (exact) | H-WIDE-NEXT | UNWRAP-G | F-FRAC | H-POINT | H-TWP |
|---|---|---|---|---|---|---|---|
| bl16left | 16 x 32 | 31 | 0 | 0 | 0 | 1106 | |
| bl64grid | 64 x 32 | 31 | 0 | 0 | 0 | 808 | |
| bl128off3 | 128 x 32 | 31 | 0 | 544 | 640 | 800 | |
| pt128off | 128 x 32 | | | | | | 512 |
| pt256off | 256 x 16 | | | | | | 768 |
| pt512off | 512 x 16 | | | | | | 896 |
| bl256edge | 256 x 32 | 31 | 32 | 832 | 1184 | 830 | |
| bl512edge | 512 x 32 | 32 | 64 | 736 | 1216 | 802 | |
| bl256corner | 256 x 32 | 1 | 32 | 821 | 1167 | 1912 | |
| bl2048edge | 2048 x 16 | 32 | 320 | 1280 | 1280 | 844 | |

Retire Q078 (R16-6 a as R17-3 a; the lead confirms) if: H-WIDE (or exactly one rival) holds within
1 on all seven bilinear rows; the LEFT-WRAP line names one column; the right wrap is decided by
names (H-WIDE against H-WIDE-NEXT, RIGHTWRAP lines); one point form holds on all three point rows;
and the four controls pass. If H-WIDE-PT wins, the question line's point clause is restated as
floor(W' frac u), with no correction to E1049's and E1058's point claims (they held on the grid,
where the two forms are one [infer]).

## Stops

- Any fault or hang (no row has `expectfault`, `#limit 0`): the stage stops (4) and the session
  with it. A fault inside the scratch means the mapping premise failed (r15-tw FOLD-NOTES), not
  bit 14.
- hook_check (24, `on_stop = "end"` ends the session): an ok row without its 32 pixel rows or
  `scratch at A (1024 KiB)`, and a reference without its sentinel (ref256 and ref512h16
  `d0001fff`, ref2048h16 `d0007fff`, the texel (W - 1, H - 1) E561's law names): its width's rows
  then do not run.
- A control without its reading stops the session (25). Strict health after any fault (the kit's).
- Stop budget: zero faults, zero hook stops; the first of either ends the session.

## The mock's worlds (mock/world.py, kit/session.py mock)

model (H-WIDE-PT, H-WIDE: 0, 0), wideg (H-WIDE-G: 0, 0), next (H-WIDE-NEXT: 0, 0), unwrap (H-TWP,
UNWRAP-G: 0, 0), ffrac (H-TWP, F-FRAC: 0, 0), point (H-POINT: 0, 0), reflaw (ref256 without its
sentinel: 24, ends after 6 jobs), ctlfault (the first row faults: 4, 4), rowfault (bl2048edge, the
last, faults: 4, 4), rowhang (bl128off3 hangs: 4, 4), nopix (bl64leftr prints no rows: 24), short
(bl512edge prints 31 rows: 24), small (bl256edge prints a 64 KiB scratch line: 24). The kit's
library-mock replay runs all 14 rows on t14's pinned source ("program not simulated").

## Replay vectors

tw17: `refused` until the fold: if the forms hold, the seven bilinear and three point images
become a `tex` table `tw17` (`tools/usse-asm/closing_tables.py` format `sgx545-tables`, pinned) for
sgx-sim's texture address (`crates/sgx-sim/src/tex.rs`, pinned: it refuses the bilinear bit-14
sample now, Q078; the fold adds H-WIDE's footprint), replayed by sgx-pipe's
`tests/texture_t3b14.rs` (pinned) as E1047's, E1049's and E1058's tables are; the fold builds it
from the kept files and predictions/tw17/.

## Layout

gen/make.py writes tables/, predictions/ and bins/ from gen/tw17.py (gen/law.py, gen/pins.py,
gen/tex.py r16-tw's, tests check them); gen/derive.py (H-WIDE re-derived on the kept files, output
fit/derive.out); score/score.py; run/hooks.sh (the sentinel words, checked by tests);
mock/world.py; tests/ (test_gen.py, test_twin.py, test_score.py); lead/build_tool14.sh (t14's
recipe); PREFLIGHT.md; FOLD-NOTES.md. Publishable: everything (our own programs, tables, scorer and
mock, and kept data of our own sessions; no firmware-derived file). **Nothing is marked for
data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check` (the generator current);
  `python3 gen/derive.py` (the re-derivation).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r17-tw-run.log`).
- Score again on a kept attempt: `python3 score/score.py tw17 out/ATT/tw17`.

## Deviations from the plan (the lead may object before staging)

1. **W 2048 pair added (14 jobs, not 12)**: the plan's [check] asks to widen the right-wrap band.
   At W 256 and 512 the float32-exact u steps with whole-64th weights give only 32 and 64 parting
   pixels (one or two a pixel row; u is a ramp of x only). bl2048edge (2048 x 16, u step 1/131072,
   kx steps 3) gives 320, gated by its own bit-clear reference ref2048h16, both after every other
   row. Reach 98389 (W' x 16 = 98304 plus H-WIDE-NEXT's next tile row). The widest texture any
   session has sampled; a wrong layout at that width reads somewhere unmodelled, so it is last
   and any fault ends the session with everything else done. The lead may drop the pair (12 jobs,
   the plan's rows; the right wrap then rests on 128 pixels).
2. **Refs read across the u edge**: ref256, ref512h16 and ref2048h16 read columns W - 32 to W - 1
   and 0 to 31 (point, bit clear), the u range the bit-14 rows sample, not the whole texture.
3. **H-WIDE-G's within-1 image is H-WIDE's**: its SUMMARY line is not a decision; the LEFT-WRAP
   line is. bl256corner's left-wrap pixels part on 1 pixel only (the v edge's tap names absorb the
   difference in rounding), so the corner row tests the right and v edges, not the left wrap.
4. **H-POINT** is H-WIDE-PT's point image (r16-tw's was H-TWP-H's; one image on the grid).
