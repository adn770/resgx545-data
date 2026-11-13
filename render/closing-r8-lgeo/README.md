# r8-lgeo (round 8, round 7's leftovers, session L2: Q283, Q178, Q260, Q139)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 main 91f21da and resgx545-data 1e83dc86. Plan:
`closing8/leftovers/exp-leftovers-r8.md` section 3 (session L2); decisions
`closing8/DECISIONS-R8.md`
R8-8 (safe class only: no held reset, no planned fault, `#limit 0` in every table). Built offline;
nothing here touched the laptop, cachix or a git repository. Records E940 to E944 are reserved for
its fold (the builder folds it).

## What runs, in order: 246 jobs, about 30 minutes

Laptop: module srcversion 37EC97AB0CB37213C42FCCC (the current test boot, fork 664fd0d0), before
the R8-5 one-shot boot; tool t4 only, `~/sgxfive-test-rgn4` (sha256 e6951558..., built from
resgx545 4623753, `TOOLSRC.sha256`); files under `~/scratch/r8m/`.

| # | stage | jobs | what | frozen | label |
|---|---|---|---|---|---|
| 1 | tx3 | 10 | types 3 and 1 below 8 wide | type 3 H-MIN8 vs H-2W, RASTERW; type 1 RASTERW | 3 controls, 7 held out |
| 2 | tx4 | 23 | type 4 past the first two 32 x 32 blocks; widths 24 and 40 | H-BLKROW vs H-BLKCOL, H-BLKZ; RASTERW vs RASTERP2 | 2 controls, 18 held out, 3 soft |
| 3 | tx5 | 28 | type 5: which dword, which bit | H-DW8 vs H-DW4B1 | 3 controls, 21 held out, 4 soft explore |
| 4 | zs2 | 165 | negative ties at other grid points; long edges; 256 x 512 transposed | HA's step, E914's step table, H-SHORT, H-BAND, H-YAXIS vs H-GEOM | 5 controls, 160 held out |
| 5 | q139 | 20 | the TA's write order at new strides, with dumps | block order (blkrow) vs raster, blkdown, mtblk | 3 controls, 2 fit, 11 held out, 4 residue |

Time: tx3 to tx5 about 5 minutes (the health fill and triangle after every job, `after`), zs2
about 9 (165 jobs of 512 x 256 or 256 x 512 with `--pixels`), q139 about 3 (dumps, the 1280 x 720
residue the longest); with staging, the per-stage health and the copy back about 30 minutes.

**Stops.** No fault is planned anywhere: any fault, hang or unexplained failure stops the stage
(rc 4) and the session (the Mac driver stops on any status but 0 and 24). A control without its
reading stops the session at its stage (rc 25, premise). The second soft failure in a row stops
tx4 or tx5 (rc 24; the driver goes on to the next stage); the second row of a stage without a
hash (`needhash`, zs2 and q139) or without pixel rows (`needrows`, tx stages) stops that stage
(rc 24). A file the scorer reads that was not kept stops it (rc 23). `min_free_mb` 400.

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

- **tx3 (Q283; E725, E910).** E725's map-texture fill (64 x 32 pixels, texel (x mod w, y mod h),
  dword i of the scratch 0xD0000000 | i). Held out: type 3 at 2 x 16, 4 x 8, 4 x 32, 2 x 8, 1 x 16
  and type 1 at 2 x 16, 1 x 16. Frozen: type 3 H-MIN8 (rows max(8, w) dwords apart, E910's 4 x 16
  read post hoc) against H-2W (2 w) and RASTERW; type 1 RASTERW against H-MIN8 and H-2W. H-MIN8
  and H-2W part at 2 and 1 wide (3 rows). Controls (kept images): E725's type 3 32 x 16 program,
  E910's type 3 and type 1 4 x 16 programs, byte for byte.
- **tx4 (Q283).** The 64 x 32 window moved over larger type 4 textures by the map axis's offset
  (`texbuild.py` ORs it into the pixel coordinate): 64 x 64 (2 windows), 128 x 64 (4), 128 x 128
  (8), 256 x 32 (4). Frozen: H-BLKROW (32 x 32 blocks of 1024 dwords numbered row by row) against
  H-BLKCOL and H-BLKZ (block coordinates interleaved, x in bit 0); H-BLKCOL parts 14 rows,
  H-BLKZ 9, all three part at 128 x 64. **The tag fill**: t4 fills every dword of its scratch
  (`SCRATCH_FILL` over `SCRATCH_PAGES`, 16 pages = 16384 dwords by default, exactly a 128 x 128
  texture; tests/test_gen.py reads it in t4's source); the held-out rows take `--scratch-pages
  64` (65536 dwords, a t4 option, 16 to 64) because H-BLKZ reads 256 x 32 up to dword 22527: no
  frozen rival reads past the fill (no read past the buffer, the safe class), and the x0y0
  windows repeat E910's blocks with it. A row whose `scratch at ... (N KiB)` line is not the
  frozen size cannot tell. Controls: E910's type 4 64 x 32 and 4 x 16 programs and images. Soft,
  last: type 3 at 24 x 8 and 40 x 8 through the linear axis (RASTERW = H-MIN8 there, against
  RASTERP2, the stride rounded to a power of two), with type 3 32 x 16 through the same axis as
  their bridge: unless it gives E725's map image the two rows cannot tell.
- **tx5 (Q178; E911, the plan's P2, a post hoc fit).** Frozen: H-DW8 (the pixel is 0x0000ffff iff
  bit 0 of texture dword floor(t / 8) is set, t the raster index) against H-DW4B1 (bit 1 of dword
  floor(t / 4)). They part on 13 rows: 8 x 8 with all 64 dwords stored 0x1, 0x2, 0xfffffffe,
  0xfffffffd; one dword j = 0xffffffff among 64 zeros (j 0, 1, 3, 7); 16 x 16 j 0, 5, 31 and V 0x1,
  0x2 over 112 dwords (`texbuild.py`'s inject, E911's count). They agree on 8 rows (V 0x4, 0x8,
  0x10000, 0x80000000; plain 32 x 8, 8 x 32, 16 x 8, 64 x 64 at window y 32: the raster index),
  scored as one claim. Controls: E911's 8 x 8, 16 x 16 and 16 x 16 zeroed programs and images.
  Soft explore, last: the format word 9 and 18 and the bilinear filter word at 16 x 16 and 8 x 8
  (values printed, no verdict).
- **zs2 (Q260; E914).** Vertices in 1/4096 pixel, one vertex swept d = -2 .. +2 steps of 1/4096
  across the 1/512 tie above a grid point, its edge aimed through a pixel centre C
  (gen/zsmodel.py, E914's construction). (g) ties at -1/256, -1.25, -17.75 and -200.5 (x) /
  -100.5 (y), both axes, aimed at the nearest on-screen centre, 40 rows; (l) long edges at -64.5
  and +64.5, both axes, four aims each, 80 rows at 512 x 256; (t) the 100 and long aims again on
  256 x 512 with the scene transposed, 40 rows. Frozen: HA (half away from zero: C flips between d
  0 and +1 at a negative tie, between -1 and 0 at a positive one) against HU, on 8 (g) sweeps;
  E914's step table on the 24 (l, t) sweeps; H-SHORT (the image is exactly HA's where no edge
  reaches 250 pixels, 70 rows); H-BAND (elsewhere it differs from HA's only in pixels within
  6.4e-4 pixel of an edge of 250 pixels or more, E914's band and `fold/zs_read.py`'s distance,
  distance 0 included as E914 read it, 90 rows); H-YAXIS (on 256 x 512 the rows that miss HA's
  image are target y sweeps) against H-GEOM (they follow the transposed scene to target x),
  decided only by the rows that miss. Controls (kept hashes): E681's and E683's cases and E914's
  -0.5 x sweep at d -1, 0, +1. The predicted images are `predictions/zs2/NAME.{HA,HU}.spans`.
- **q139 (Q139; E907, the plan's P1, SEMI).** The datasets' own command (r7-rp's q139 rows) with
  `--keep-going --dump-render "$W"`, one `--kpoke-render` of the stride or a macrotile word, only
  inside the ranges that drew without a fault in the kept data (256 x 256 strides 0 to 31, 640 x
  480 4 to 63; the residue jobs drew in their datasets). Controls: the 256 x 256 and 640 x 480
  baselines (exact image, one header a tile, slots as R7-BLK) and 256 x 256 stride 4 (its kept
  wrong set). Fit: strides 1 and 2 (images kept, never dumped). Held out: 256 x 256 strides 3, 5,
  6, 7, 12, 20; 640 x 480 strides 5, 6, 7, 8, 12. Frozen: block order, the wrong-tile set and
  every header slot (`predictions/q139/NAME.ORDER.slots`); raster parts 7 of the 11, blkdown and
  mtblk all 11. Residue (scored nothing, dumps for the fold): P1's four jobs no order gives.

**Predicted outcomes.** H-MIN8 and RASTERW (tx3), H-BLKROW (tx4), H-DW8 (tx5), HA's step and the
step table (zs2), block order (q139), each held on every held-out row; H-SHORT held; H-BAND and the
y-axis question open (E914 saw misses only on long y sweeps; neither is favoured beyond the frozen
H-YAXIS line).

## The mock's worlds (mock/world.py, kit/session.py mock)

model and rival (every stage 0; rival's images fail the frozen rows or their kept-image controls),
norows (tx3 premise, 25), soft2 (tx4 stops 24, the driver goes on), ctlnohash (zs2 premise, 25),
nohash (zs2 stops 24, q139 runs), fault (a zs2 fault: stage and driver 4), nodump (q139's first row
lacks its dump, 23). The fake answers from the argv only: probes by their program's sha256
(`mock/progs.tsv`), tri jobs by their geometry and pokes.

## Replay vectors

The fold builds one `sgx545-tables` table a stage from the kept files alone (pinned:
`tools/usse-asm/closing_tables.py`, `closing_vectors.py`, `pbdump.py`, `region_tiles.py` at
91f21da). At 91f21da `closing_tables.py` has no texture and no slot kind: the round's tooling agent
adds them (test first) before the fold, or the fold reports the tables as not built.

- tx3, tx4, tx5 → `vectors/closing/r8-lgeo/tex-layout.table.json` (per row: type, size, window,
  stored dwords, the texel offset or bit each pixel read); replay: `crates/sgx-sim/tests` texture
  layout test (`tex.rs`) for the layouts that hold, `refused` for type 5 until H-DW8 holds.
- zs2 → `vectors/closing/r8-lgeo/zs-ties.table.json`; replay: `refused` (the ISP's evaluation of
  long edges is not modelled, E914) unless HA's step holds, then the rounding rows by sgx-sim's
  `isp.rs` test.
- q139 → `vectors/closing/r8-lgeo/ta-slots.table.json` (per row and tile: the header slot or none,
  wrong or drawn); replay: the `ta.rs` slot test of OL1 (block order), the residue rows refused.

## Layout

- gen/lgen.py writes `tables/`, `predictions/` (and its `zs2/`, `q139/` files), `bins/` and
  `mock/progs.tsv` from gen/texmodel.py, gen/zsmodel.py, gen/q139model.py (standard library
  only) and the published records' kept files read at the pinned data commit (`gen/pins.txt`).
  Byte copies (pinned): gen/texbuild.py, gen/texcatalog.py, `templates/tx_map.s` (r7-geo),
  gen/q139_fit.py (r7-rp fold), score/lib_dump.py, score/pbdump_dump.py,
  score/region_tiles_dump.py (r7-rp). The programs are assembled with usse-asm from `git
  archive` of 91f21da (`debug/asm`, which tests/run_all.sh builds; its sources are pinned).
- score/score.py, run/hooks.sh (readings rows, hash, dump; needhash, needrows),
  `mock/world.py`, `tests/` (`test_gen.py`, `test_models.py`, `test_twin.py`, `test_score.py`,
  `kept.py`), `PREFLIGHT.md`, `TOOLSRC.sha256`.

Publishable: everything (our own programs and models; no firmware-derived file). **Nothing is
marked for data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script had
mode 644 and staged nothing):

- Offline: `bash tests/run_all.sh` (the assembler, the guard, the session's tests, the mock of
  every world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`.

## Deviations from the plan (the lead may object before staging)

1. Laptop prefix `r8m` (the lead's), not the plan's `r8l`.
2. Tool t4 only: t7 (f2df4f99, resgx545 1c64f3a) differs from t4 only by odd target widths, which
   no row needs, so it is not declared (a declared tool is checked on the laptop at staging).
3. tx4's held-out rows take `--scratch-pages 64` (above); the controls keep E910's commands.
4. tx4's bridge is a scored premise of the two linear rows (set `bridge`, soft), not a control: a
   soft control that fails would stop the session at the premise. The linear rows' rival is
   RASTERP2 (H-MIN8 equals RASTERW past 8 wide, H-2W is not a reading there).
5. zs2 aims: (g) "aimed 1 pixel away" is read as the nearest on-screen centre (pixel 0; 0.5 to
   201 pixels from the tie); at -64.5 the aims 1 and 4 would put C off screen, so 65 and 68
   (pixels 0 and 3); the long aims are 300 (x) and 200 (y), but 190 at +64.5 y (C on the 256
   rows). H-SHORT and H-BAND are split by the frozen longest edge (250 pixels), not by the aim.
6. q139's controls read the hash and the dump size (`reads:hash,dump`; the shell hook cannot read
   slots); the scorer checks every baseline header and slot. The dump goes to `$W` (the kit makes
   no directory under it). Its rows are labelled safe (inside the drawn ranges; r7-rp said risky).
7. tx5's explore rows: formats 9 and 18 and the bilinear filter (the plan's "format and filter
   words changed").
