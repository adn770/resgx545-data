# r14-isp (round 14, session r14-isp: Q241, Q261, Q199)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 dddadbd and resgx545-data 3309b5fd9. Plan:
`closing14/plan/rank-round14.md` sections 2 and 3, rows wind, g14 and clipr (decisions R14-1 (a),
R14-2 (a), R14-3 (a) of `closing14/DECISIONS-R14.md`; the user: g14's poked-viewport rows are its
last rows and stop it at the first job not ok, clipr's int32 ends are the session's last rows).
Safe class only: no held reset, no planned fault, `#limit 0` in every table. Built offline;
nothing here touched the laptop, cachix or a git repository. Records E1045 (wind), E1036 (g14) and
E1037 (clipr) are reserved for its fold (the builder folds it; notes in fold/FOLD-NOTES.md).

## What runs, in order: 39 jobs, about 10 minutes

Laptop: module srcversion B60AB0B475DD1E8972419B5 (fork 2a650d74, the test boot); one tool, t10
`~/sgxfive-test-t10` (sha256 9bedc2d6..., built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` sha256 23e1fa76... by resgx545-data
`render/closing-r10-st1/lead/build_tool10.sh`, `TOOLSRC.sha256`), so the kit's library mock
replays every row (39 rows, none refused); files under `~/scratch/r14i/`; no extra laptop file.

| # | stage | jobs | what | frozen | label |
|---|---|---|---|---|---|
| 1 | wind | 8 | E998's ramp (80 x 40) with ISP word 0 bits 15, 16, 17 on the reversed vertex order; a depth above 1 and below 0 under compare always with writes | H-CULL / H-KILL (drawn, hash, dump); H-CLAMP, H-ZCLIP, H-RAW, H-ABS per pixel and tile dword | 3 controls first, 5 held out |
| 2 | g14 | 21 | the quarter guard on 64 x 64 (-x), 128 x 128 (+-x, +-y), 256 x 256 (+-x, +-y), 128 x 64 and 64 x 128 (+x, +y); last, three poked-viewport rows | H-VP, H-TGT, H-MAX4, H-MIN4, H-ABS, H-EXACT per pixel; the side's bound as a family per row | 2 controls (E979's far-ctl first, E1023's t128-1 before the vp rows), 19 held out |
| 3 | clipr | 10 | clip-made vertices on 1/512 ties (64 x 64), vertices inside the guard of 4096 x 16 on ties, a far vertex at 2^24 px there; last, the int32 ends | CLIP-HU/HA/RNE/TR, IN-E607/HU/RNE/TR, the guard models, H-SAT, H-WRAP, H-CULL | 2 controls (far-ctl first, E1024's far-x30p before the int32 rows), 8 held out |

Time: every job a 64 x 64 to 256 x 256 render or a 4096 x 16 one, all under 2 s (E979, E1024,
r7-geo zf); with the reset, health fill and triangle about 6 s a job, 4 minutes; with staging,
three stage preflights and the copy back about 10 minutes.

**Stops.** No fault is planned anywhere: any fault, hang or unexplained failure stops the stage
(rc 4) and the session. A control without its reading stops the session at its stage (rc 25,
premise). A row that read ok without `job: ok`, or without its whole image (H rows of W values),
stops its stage (hook_check, rc 24): after wind or g14 the driver goes on to the next stage; clipr
declares `on_stop = "end"` (it is the last stage: its stop ends the session either way). A file the
scorer reads that was not kept stops it (rc 23). `min_free_mb` 400; `job_timeout` 120 s.
**The untested ground is last in its stage**: g14's three poked-viewport rows after every in-range
row and both controls (R14-2 a; E903 poked words 6 and 7 safely on module 41E2F5C7), clipr's two
int32 ends after both controls (R14-3 a; E1024 drew 2^30 px with no fault).

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

- **wind (Q241; E998, E977, E287, E981, E987).** E977's z242-c-f0 form: 80 x 40, the triangle
  (0,0), (2W,0), (0,2H) (`--tri-v 0,0,40960,0,0,20480`, the tool's 1/256 unit), CR_ISP_ZLSCTL
  0x00171014 (float, pitch G 2), the buffer pre-filled 0xdeadbeef and dumped, ISP word 0 by
  `--poke blk:1`, every row also `--pixels`.
  - Bits 15, 16, 17 each alone on the reversed order ((0,0), (0,2H), (2W,0), depths 1, 1, 0).
    Frozen: H-CULL (each bit removes one winding; E998 removed the forward one: the reversed
    draws E977's ramp: drawn 3200, hash 0xafb12e5a2a9a6725, E977's dump byte for byte) against
    H-KILL (any triangle removed: E998's x-w0b15, drawn 0, hash 0x56053161ef809725, its dump).
  - wind-zhi (depths 1.25, 0.25, 1.25: z = 1.25 - x/160, above 1 for x + 0.5 < 40) and wind-zlo
    (0.25, -0.75, 0.25: below 0 for x + 0.5 > 40), compare always with the depth written (ISP
    word 0 0x01c00200). Frozen per target pixel (drawn) and per tile dword (96 x 48 at E465's
    layout, all inside E730's store band): H-CLAMP (stored 1.0 or 0.0, drawn), H-ZCLIP (removed:
    the background's 1.0, not drawn), H-RAW (the plane's float, drawn), H-ABS (the sign cleared).
    A plane value matches within 2^-20 (E977's ramp: within 2^-23 at every centre, tests); no
    centre lies within 0.003 of 0 or 1.
  - Controls that can fail: wind-ctl-rev (the reversed order unpoked: E977's ramp), wind-ctl-b15
    (E998's x-w0b15 replicate: no pixel), wind-ctl-always (compare always with writes at E977's
    depths 1, 0, 1: E977's ramp; the z rows' premise). H-CULL is gated by the first two, the z
    models by the reversed and the always controls.
- **g14 (Q261; E1023, E1024, E1012).** E1012's clip (c6's engine, q261_rule2.py, a byte copy),
  generalised in gen/guard.py to a W x H target and a viewport (window = offset + scale x the
  float32 clip coordinate the tool sends), each guard bound its own parameter. Frozen per row (the
  vertices as the tool submits them): H-VP (the frozen point hypothesis H-QUARTER-VP: a quarter of
  the viewport past each edge, clip x and y within 1.5 w; on 64 x 64 E1023's [-16, 80]), H-TGT (a
  quarter of the target: parts from H-VP on the vp rows only), H-MAX4 and H-MIN4 (a quarter of
  max(W, H) or min(W, H): part on 128 x 64 and 64 x 128), H-ABS (fixed in pixels: x >= -16, y in
  [-16, 80]), H-EXACT (no clip); and per row the side's bound as a family of integers (READING
  lines, intersected per shape and side: H-PLUSG's one G per target, E1023's 147 on 128 x 128, and
  the lower x bound a = 9 or 16 on 64 x 64). The clip-made vertex rounded half up, then the
  edges exact (E1012).
  - Rows (all held out): 64 x 64 two along -x (each parts a = 9 from 16); 128 x 128 two along +x
    (parting 160 from 147, 173 and 186), two along -x (-32 from -16, -9, -19), one along -y (-32
    from -16), one along +y (160 from 147, 173); 256 x 256 one each way (320 from 275 and 294,
    -64 from -16 and -9); 128 x 64 and 64 x 128 one along +x and one along +y (H-VP from H-MIN4
    and H-MAX4). The far vertices (--tri-unit 5, up to 2^24 px) are designed here (gen/guard.py
    `design`, seeded): one far edge aimed at a pixel centre of the target's far half, so the
    centre's side of the clipped edge is the sign of the clip vertex's rounding error; each image
    depends on its own bound only (tests).
  - Last, the poked-viewport rows (`--poke blk:6` to `blk:9`, x offset, x scale, y offset, y
    scale, each poke offset = scale, so their order does not enter): g14-vp64-px and -py, 128 x 128
    with the viewport 64 x 64 at the origin (32.0 each): H-VP clips at window 80 (columns or rows
    80 to 127 empty), H-TGT draws to 127 (2127 and 2346 pixels apart); g14-vp128-px, 64 x 64 with
    the viewport 128 x 128 (64.0 each): a band pixel parts H-VP's 160 from H-TGT's 80.
  - Controls that can fail: E979's far-ctl (E684's far21d0) first and E1023's q261-t128-1 (G 19
    only) before the vp rows, each against its kept image pixel for pixel.
- **clipr (Q199; E607, E1012, E1024, E914, E943, E683).** The same engine, H-VP's box.
  - The tie rows (64 x 64, --tri-unit 8): the far edge from (16, ya) clipped on x = 80 at y =
    (n + 1/2)/256 exactly (exact in float32 clip space too, tests), the other far edge's clip on
    the grid: clipr-tie-a (y = 41.48, n even, the far vertex at 16400 px), clipr-tie-b (y = 46.5,
    n odd, 16400 px), clipr-tie-c (y = -2.55, a negative tie, n even, the far vertex at (144,
    -9.93),
    inside the y guard). Frozen per row: CLIP-HU (H-HALFUP-CLIP, floor(256 y + 1/2)), CLIP-HA
    (H-HAZ-CLIP), CLIP-RNE, CLIP-TR, H-EXACT. The three rows part the four rules (HU up, up, up;
    HA up, up, down; RNE down, up, down; TR down, down, up); 1 to 4 decisive pixels a row, each
    2.5e-4 px or more from both rivals' edges.
  - The 4096 x 16 rows (H-VP's box [-1024, 5120] x [-4, 20]): clipr-w4-d, a vertex at (5000,
    4.5 + 9/512), and clipr-w4-e, at (-1000, -3/512) (--tri-unit 9), both inside H-VP's guard and
    outside H-MIN4's, their y on a 1/512 tie; the near edges run along a centre row, so the tie's
    rounding moves the crossing by 280 (d) and 16 (e) pixels. Frozen: IN-E607 (half up at x >= 0,
    E943's half away from zero below), IN-HU, IN-RNE, IN-TR, H-MIN4, H-ABS. clipr-w4-f, a far
    vertex at 2^24 px along +x (--tri-unit 5): the guard models and the x bound as a family of 17
    values from 4096 to 6144, every one its own image (5120 is H-VP's, 4100 H-MIN4's).
  - Last, the int32 ends at --tri-unit 0 on 64 x 64 (E979's near vertices rounded): clipr-i32-x
    at x = 2^31 - 1, clipr-i32-y at y = -2^31 (the other coordinate within 2^29). Frozen: the
    guard models, the family, and far.py's H-SAT, H-WRAP (a 24.8 word), H-CULL; the float32 clip
    coordinate stands for 2^31 + 32 px (a pixel the exact and float32 window vertices part is '?').
  - Controls that can fail: far-ctl first and E1024's far-x30p replicate before the int32 rows.

**Predicted outcomes.** wind: H-CULL held 3 of 3 [infer: E998 and E065's 48 pixels with bit 15
on the library's triangle]; wind-zlo H-CLAMP (E981: a negative depth from the viewport is stored
as 0; E287), wind-zhi H-RAW [infer: E287 saw a depth above 1 compare as itself], so each z model
holds on one row at most and the readings carry Q241's clause. g14: H-VP held 19 of 19 (E1023's
post hoc QUARTER), every rival FAILED; families: 128 x 128 +x contains 160, 64 x 64 -x contains 16
(a = 16). clipr: CLIP-HU held 3 of 3 (E607, E1012), IN-E607 held 2 of 2 (E607, E943), H-VP held
on w4-f and both int32 rows, H-SAT, H-WRAP and H-CULL FAILED; every job `job: ok` [infer].

## The mock's worlds (mock/world.py, kit/session.py mock)

model (every stage 0), nopix (no pixel rows: every stage stops at its first row by hook_check,
24; clipr's stop ends the session), nodepth (no `depth #1` line: wind's first control has no
reading, premise 25), rejected (`job: rejected` with a diff line, E934: wind 4), vpfault (a
poked-viewport row faults: g14 4 at g14-vp64-px), vplost (`job: lost` on the vp rows: g14 24,
clipr runs, 0), i32fault (an int32 end faults: clipr 4), i32lost (clipr 24, the session ends),
wide (a 4096-wide target prints 15 rows: clipr 24 at w4-d). The fake answers from the argv only.
Before the worlds, every row goes through the library mock built from t10's bound source (a581c06:
39 rows): none is refused.

## Replay vectors

The fold builds one `sgx545-tables` table a stage from the kept files alone (pinned:
`tools/usse-asm/closing_tables.py`, `crates/sgx-pipe/src/isp.rs`, `crates/sgx-pipe/src/zls.rs` at
dddadbd):

- wind → `wind` (per row ISP word 0, the order, the depths, drawn, the dump's out-of-range
  words): replay sgx-pipe `isp` (`decode_isp`'s bits 15 to 17 and the depth outside [0, 1], refused
  today under Q241) once the fold models what held; `refused` under Q241 otherwise.
- g14 → `g14` (per row the target, the viewport, the vertices in 1/256 px, the kept coverage, the
  family values that fit): replay `isp::guard_clip_image` extended past 64 x 64 and to a viewport
  (fold); `refused` under Q261 for what does not hold.
- clipr → `clipr`: as g14, with the clip vertex's rounding and the 4096 x 16 rows; `refused` under
  Q199 for what does not hold.

## Layout

- gen/make.py writes `tables/`, `predictions/` (`predictions/wind/`, `/g14/`, `/clipr/`) from
  gen/wind.py, gen/rows.py and gen/guard.py (new, standard library only) over the byte copies
  gen/q261_rule2.py (c6's engine) and r13-isp's gen/clip.py, gen/far.py, gen/pivot.py (tests use
  clip.py to check the engine), read at the pinned data commit (gen/pins.py; tests/test_gen.py
  checks every copy). Per row `NAME.ref.txt` (the first model's bitmap), `NAME.models.txt` and
  `NAME.family.txt` (each model or value as the pixels it differs by), `NAME.KEPT.txt` (a control's
  kept image); wind's `NAME.MODEL.txt` (drawn bitmap and the dwords).
- score/score.py, run/hooks.sh (readings job, drawn, pixels, hash, diff, depth_changed; checks job
  ok and the whole image), mock/world.py, `tests/` (`test_gen.py`, `test_twin.py`, `test_score.py`,
  `kept.py`), PREFLIGHT.md, TOOLSRC.sha256; fold/FOLD-NOTES.md (fold/ is outside the freeze).
  debug/ is scratch.

Publishable: everything (our own models and kept records' readings; no firmware-derived file).
**Nothing is marked for data-private.**

## Deviations from the plan

1. **wind: 8 jobs, not 7, and its depth rows under compare always.** Under E998's less with the
   background's 1.0 a depth above 1 never passes, clamped, clipped or raw, so the z rows write
   with compare always (0x01c00200), and a control at E977's depths in that mode (wind-ctl-always,
   E977's ramp) is their premise. Their depths are 1.25, 0.25, 1.25 and 0.25, -0.75, 0.25, the
   plane crossing 1 or 0 at x = 40: the plan's one vertex at 1.25 or -0.25 leaves the out-of-range
   part at (0,0) or outside the 80 x 40 target. H-ABS (E987's sign cleared) is added for zlo.
2. **The 4096-wide target is 4096 x 16, not 4096 x 128** (the plan's [check]): no kept job ran
   4096 x 128 (the library gives it n = 4 macrotiles across with whole 4-tile blocks, never run at
   that width), while r7-geo zf ran 4096 x 16 24 times `ok` with every pixel printed (tests).
   Every shape of the session takes whole 4-tile blocks (fx, fy 0 mod 4, where H-EVEN is R7-BLK:
   Q139) and has a kept job that ran ok (tests). 4096 x 16's H-VP box is [-1024, 5120] x [-4, 20].
3. **The vertices inside the 4096 guard are on y ties, at x = 5000 and -1000** (the plan: x =
   5000 + 1/512 and -1000 - 1/512). On a 16-high target every edge through such a vertex is within
   1.6 degrees of level inside the guard, so an x tie moves the edges inside the target by about
   1e-4 px or less (inside E943's band); a y tie moves a level edge's crossing of a centre row by 16
   to 280
   pixels. The negative one tests E943's half away from zero at x = -1000.
4. **The negative clip tie is on x = 80 (y = -2.55), not on y = -16 (an x tie).** A negative x on
   y = -16 with its edge through the target needs the far vertex past the lower x bound too,
   which E1023 left at -9 or -16 and which would put the row's tie on an unknown plane; on x = 80 a
   far vertex inside the y guard at (144, -9.93) gives it (t = 1/2, exact in float32). The three
   tie rows' parities still part the four rules (the signatures above).
5. **The far vertices of g14 aim one far edge at a pixel centre** (gen/guard.py `design`) instead
   of r13-isp's random draw: with r13's draw no 128 x 128 vertex parted 147, 160, 173 and 186
   pairwise in 300 tries. Each parting is a few band pixels; H-MAX4 and H-MIN4 part from H-VP by one
   pixel on each non-square row, H-TGT by thousands on the vp64 rows and one on vp128.
6. **The 128 x 128 +x rows also part 186** (E1023's post hoc integer bounds 147, 160, 173, 186).
7. **clipr's 4096 rows and int32 rows carry the guard models too** (w4-f is also a Q261 row, as
   the plan says; the int32 rows read the family as E1024's far rows did).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest; numpy unused here), which
  the offline tests use unless `PY` names another.
- Generator: `python3 gen/make.py` (`--check`: current or not; about 25 s, the designs).
- Offline: `bash tests/run_all.sh` (the guard, own tests, the library mock and the mock of every
  world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
