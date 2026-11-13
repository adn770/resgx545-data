# r10-geo (round 10, session S10-geo: Q261, Q066, Q139)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 9849dab and resgx545-data 1324301be. Plan:
`closing10/seeds/exp-seeds-r10.md` sections 7, 9 and 12 (decision R10-3 (a) of
`closing10/DECISIONS-R10.md`; safe class only: no held reset, no planned fault, `#limit 0` in
every table). Stage far2 (Q199, it needs r10-tooling2's wider `--tri-unit` and `--tri-v`, t10) is
not in this session. Built offline; nothing here touched the laptop, cachix or a git repository.
Records E1005 (pivot), E1006 (bgw) and E1007 (q139c) are reserved for its fold (the builder folds
it; notes in fold/FOLD-NOTES.md); E1008 is far2's.

## What runs, in order: 61 jobs, about 15 minutes

Laptop: module srcversion B60AB0B475DD1E8972419B5 (fork 2a650d74, the test boot); tools t4
`~/sgxfive-test-rgn4` (sha256 e6951558..., resgx545 4623753 `userspace/libsgxfive/tools/
sgxfive-test.c` by `userspace/libsgxfive/Makefile`) and t9 `~/sgxfive-test-t9` (sha256 7a28be39...,
resgx545 97447b04, recipe resgx545-data `render/closing-r9-k1/lead/build_tool9.sh`), both bound by
source (`TOOLSRC.sha256`), so the kit's library mock replays every row (61 rows, none refused);
files under `~/scratch/r10g/`.

| # | stage | jobs | what | frozen | label |
|---|---|---|---|---|---|
| 1 | pivot | 37 | E979's far-x23p, far-x24p, far-x25n with the far vertex's y moved by d = 0, -16, -32, -48, -64, -96, -128, -160, -224, -288, -416, -544 px; E684's far21d0 | per pixel H-EXACT, H-EXACT-BAND; per row the pixel intervals of H-PIVOT | 1 control, 3 replicates (d = 0), 33 held out |
| 2 | bgw | 18 | the layered background's words 12, 14, 11 at 0.25, 0.5, 1.5, -1.0, words 9 and 13 at 2.0, -1.0 | per pixel H-INERT, H-SCALE0 | 2 controls (first, last), 16 held out |
| 3 | q139c | 6 | TA dumps of the four y-side words that drew whole, the 256 x 256 and 640 x 480 baselines | slots and wrong tiles (H-EVEN = R7-BLK, round 8 orders), H-LAST, H-FLAGSLOT | 2 controls, 2 replicates, 2 held out |

Time: pivot and bgw are 64 x 64 renders (E979's far rows and r9-k1's s3 ran under 2 s a job; with
the health fill and triangle between jobs about 6 and 3 minutes), q139c about 2 (640 x 480
`--pixels` with dumps the longest); with staging, the per-stage health and the copy back about 15
minutes.

**Stops.** No fault is planned anywhere: any fault, hang or unexplained failure stops the stage
(rc 4) and the session (the Mac driver stops on any status but 0 and 24). A control without its
reading stops the session at its stage (rc 25, premise). A tri row that read ok without `job: ok`,
a bgw row without the tool's bg-layer line, or the second q139c row without a hash (`needhash`)
stops that stage (rc 24; the driver goes on). A file the scorer reads that was not kept stops it
(rc 23). `min_free_mb` 400; `job_timeout` 120 s. q139c runs last: its words drew whole without a
fault in every kept job that ran them (below), but at most twice each.

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

- **pivot (Q261; E979, the seeds plan's finding 4).** E979's band: 26 band pixels of x23p, x24p
  and x25n drew where the exact coverage has them out, along the far edge from the near vertex N;
  a y displacement of the far vertex F of at least 43, 52, 42 px fits them (post hoc). The in-span
  band pixels lie on one lattice line through N, so as F's y moves the edge pivots on N and every
  such pixel of a triangle flips at one displacement t* = 42.625, 51.375, 41.625 px (exact,
  gen/pivot.py, tests/test_gen.py: they are exactly E979's misses).
  - Frozen per row: H-EXACT (the exact coverage at the row's vertices, no band) and H-EXACT-BAND
    (E979's claim: exact outside E684's 1e-3 band), and the frozen pixel intervals from which the
    scorer derives, per row, the set of D (F's y displacement, the hardware drawing the exact
    coverage of F + (0, d + D)) that gives the image pixel for pixel.
  - Per triangle H-PIVOT: one D gives all 12 rows (FAILED if the rows' sets do not meet). H-CONSTD:
    one D for the three triangles. H-ANGLE: D proportional to |F| (one angle).
  - Control (can fail): E684's far21d0 (E979's far-ctl), exact outside the band.
- **bgw (Q066; E973, E974).** E973: words 9 and 11 to 14 at 1.0 change nothing; at 0xffffffff
  word 12 zeroes v, 14 u, 11 u (and moves v); 9 and 13 nothing. The kernel builds 9 and 11 to 14
  as 0 (r9-k1's kept c-tex dump, tests/test_gen.py), so 0 is the control.
  - Frozen per background pixel (3034, gen/bgmask.txt, gen/bgl_model.py scoring): H-INERT
    (finite values change no texel) against H-SCALE0 (the word scales one coordinate, 0 read as
    1: word 12 v, 11 and 14 u, clamped outside [0, 1) as E974); 9 and 13 under H-INERT only.
  - Controls (can fail): the unpoked layer first and last, identity texels (>= 3000 of 3034);
    a row whose poke does not read back in its render_param dump is cannot tell.
- **q139c (Q139; E907, E950, E959).** The four y-side words (`CR_TE_MTILE2`, `ta:144`) of
  ta/mtile-fields-risky with whole images: 0x0200a008 and 0x0280a00a (fy 10, 256 x 256), 0x0200b008
  (fy 11, 256 x 256), 0x05c10018 (fy 23, n 4, 640 x 480).
  - Safe class: each drew a whole image and never faulted in every kept job that ran it
    (tests/test_gen.py reads them all): ta/mtile-fields-risky `q100-256x256-m2-B2-10`,
    `-m2-B2-11`, `-part2-10_10_10`, `q100-640x480-m2-B1-23` (2026-11-08, `job: ok`, no fault),
    and render/closing-r7-rp `q139-f-256x256-m2-B2-10` and `q139-h-256x256-part2-10_10_10` (t4,
    2026-11-12, `job: ok`, class ok, no fault, dumped). No other kept job names these words.
  - Controls (`reads:hash,dump`, can fail): the unpoked baselines, exact image and one header with
    a stream for every target tile (the header base of their size).
  - Frozen: every slot and wrong tile under H-EVEN, blkrow (R7-BLK), raster, blkdown, mtblk (fx is
    4 and 8 here: H-EVEN = R7-BLK); H-LAST (E959's post hoc reading, held out: exactly one header
    with flag bit 7, a target tile drawn iff its header lies at or before it); H-FLAGSLOT (that
    header sits at H-EVEN's slot of the last target tile in block order, and H-EVEN + H-LAST's
    wrong tiles); the dataset's wrong tiles (a replicate).

**Predicted outcomes.** pivot: H-EXACT FAILED on the rows where d + D > t* (at least the three d =
0 rows, E979), H-EXACT-BAND held everywhere [infer: the band holds every changing pixel], H-PIVOT
held with D bracketed to 16 to 128 px per triangle if D < t* + 544, else only bounded below;
H-CONSTD and H-ANGLE as the brackets fall. bgw: H-INERT held on 9 and 13 (NaN changed nothing
there); on 11, 12, 14 H-INERT or H-SCALE0 [no prior: E973 has only 0, 1.0 and NaN]. q139c: R7-BLK
held on all four rows (the datasets' images already match it), H-LAST and H-FLAGSLOT held.

## The mock's worlds (mock/world.py, kit/session.py mock)

model (every stage 0), nopix (pivot premise, 25), farfault (a vertex past 2^23 px faults: pivot
and the driver 4), rejected (`job: rejected` with a diff line, E934: 4 at pivot), nolayer (a poked
bgw row without the bg-layer line: bgw 24, q139c runs), nohash (q139c 24), fault (a poked q139c row
faults: 4), nodump (q139c's first control keeps no dump: 23). The fake answers from the argv (and
t9's two knobs) only. Before the worlds, every row goes through the library mock built from its
tool's bound source (t4 4623753: 43 rows; t9 97447b04: 18 rows): none is refused.

## Replay vectors

The fold builds one `sgx545-tables` table a stage from the kept files alone (pinned:
`tools/usse-asm/closing_tables.py`, `crates/sgx-pipe/src/isp.rs`, `crates/sgx-pipe/src/bglayer.rs`,
`crates/sgx-pipe/tests/bg_layer_table.rs` at 9849dab):

- pivot → `isp-far-pivot` (per row the vertices in 1/256 px, the kept coverage, the D interval):
  closing_tables.py has no kind for it, so the fold writes it as E979's rows were, an inline table
  replayed by `crates/sgx-pipe/src/isp.rs` (`far_coverage_image`, the test beside E979_ROWS): the
  band pixels stay `None` unless H-PIVOT holds with a pinned D, then the fold adds the pivot rule
  with a test; `refused` past what ran (Q199).
- bgw → `closing_tables.py texture --session . --out fold/vectors bgw` →
  `fold/vectors/pixels/bgw.table.json`; replay `crates/sgx-pipe/tests/bg_layer_table.rs` (as
  r9-k1's s3): the values the fold admits in `bglayer::check` with their rule, the rest refused.
- q139c → `closing_tables.py taslots --session . --out fold/vectors q139c` →
  `fold/vectors/ta-slots/q139c.table.json`; replay `refused` (the TA's region header placement at
  poked macrotile words is not modelled by sgx-sim or sgx-pipe, as q139b).

## Layout

- gen/make.py writes `tables/`, `predictions/` (and `predictions/pivot/`, `predictions/q139c/`)
  from gen/pivot.py, gen/bgw.py and gen/q139c.py (new, standard library only) over the byte copies
  gen/far.py (r9-x), gen/q139even.py, gen/q139model.py, gen/q139_fit.py (r9-lgeo), gen/bgl_model.py
  and gen/bgmask.txt (r9-k1), and ta/mtile-fields-risky/output.txt read at the pinned data commit
  (gen/pins.py). score/lib_dump.py, score/pbdump_dump.py, score/region_tiles_dump.py are r9-lgeo's,
  byte for byte (tests/test_gen.py checks every copy against its pin).
- score/score.py, run/hooks.sh (readings job, pixels, hash, diff, dump, inplace, layer; checks
  job ok, the bg-layer line, needhash), mock/world.py, `tests/` (`test_gen.py`, `test_twin.py`,
  `test_score.py`, `kept.py`), PREFLIGHT.md, TOOLSRC.sha256; fold/FOLD-NOTES.md (the fold's notes;
  fold/ is outside the freeze). debug/ is scratch (debug/q139_check.py: the models against the
  datasets' wrong tiles; debug/pivot_thr.py: the thresholds).

Publishable: everything (our own models and the kept records' readings; no firmware-derived file).
**Nothing is marked for data-private.**

## Commands

Every command is run through its interpreter, never by its mode bits (r7-geo's stage script
had mode 644: "permission denied", nothing staged, the first stage exited 127):

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (it has pytest and numpy), which
  the offline tests use unless `PY` names another; never a scratch venv of an older session.
- Generator: `python3 gen/make.py` (`--check`: current or not).
- Offline: `bash tests/run_all.sh` (the guard, own tests, the library mock and the mock of every
  world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`.

## Deviations from the plan (the lead may object before staging)

1. **pivot's d runs 0 to -544, not -128 to +640.** Under H-PIVOT a row draws the in-span band
   pixels iff d + D > t*, and E979 (d = 0) already drew them, so D > t*: every d >= 0 draws them
   whatever D is and decides nothing. The in-span band pixels of a triangle all flip at one t*
   (they lie on a lattice line through the near vertex), so a row is one binary reading of D, not
   a pixel-by-pixel staircase: twelve rows bracket D in steps of 16 px up to t* + 64, 32 up to t* +
   160, 64 up to t* + 288 and 128 up to t* + 544; past that only a lower bound.
2. **bgw: 0 replaced, 2.0 replaced for words 11, 12, 14.** The kernel builds words 9 and 11 to 14
   as 0, so the plan's 0 rows would repeat the control, and the plan's H-SCALE (the texel at w times
   the coordinate) is refuted by the control itself (w = 0 gives the identity texels): frozen is
   H-SCALE0, the same with 0 read as 1. At 2.0 every pixel centre lands on a texel edge under it
   (2 (x + 0.5) is an integer): 0.25 and 1.5 in place of 0 and 2.0. Words 9 and 13 at 2.0 and -1.0
   (the plan's 0 is their default too).
3. **q139c: two of the four words were dumped before.** 0x0200a008 (E907's fit row) and 0x0280a00a
   (E907's held-out row, R7-BLK 128 of 128 slots) were dumped by r7-rp, so those rows are
   replicates; m2-B2-11 and 640 x 480 m2-B1-23 are held out. H-LAST was never read on r7-rp's
   dumps (E959 read r8-lgeo's 20 and r9-lgeo's 4), so it is held out on all four.
4. **q139c: no H-EVENY.** fx is 4 or 8 on every row (H-EVEN = R7-BLK), every rival but blkdown and
   mtblk already gives the four datasets' wrong tiles, and the slot rule has no y term a "y analogue
   of H-EVEN" could change without contradicting E907's fy-10 slots (128 of 128). The rows test
   R7-BLK's slots at fy 11 and 23 (held out) instead.
5. **Order: q139c last** (the plan: pivot, q139c, bgw). Its words are the only ones with a faulting
   history around them (the risky dataset); a fault there now stops nothing after it.
