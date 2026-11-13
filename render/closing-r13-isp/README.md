# r13-isp (round 13, session r13-isp: Q201, Q261, Q199)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 05b7039 and resgx545-data 75d01ee20. Plan:
`closing13/plan/rank-round13.md` sections 2 and 3 (decisions R13-1 (a) and R13-2 (a) of
`closing13/DECISIONS-R13.md`; safe class only: no held reset, no planned fault, `#limit 0` in every
table). Built offline; nothing here touched the laptop, cachix or a git repository. Records E1022
(q201), E1023 (q261) and E1024 (far) are reserved for its fold (the builder folds it; notes in
fold/FOLD-NOTES.md).

## What runs, in order: 47 jobs, about 9 minutes

Laptop: module srcversion B60AB0B475DD1E8972419B5 (fork 2a650d74, the test boot); one tool, t10
`~/sgxfive-test-t10` (sha256 9bedc2d6..., built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` sha256 23e1fa76... by resgx545-data
`render/closing-r10-st1/lead/build_tool10.sh`, `TOOLSRC.sha256`), so the kit's library mock
replays every row (47 rows, none refused); files under `~/scratch/r13i/`; laptop files `bins/*.bin`.

| # | stage | jobs | what | frozen | label |
|---|---|---|---|---|---|
| 1 | q201 | 23 | byte 0 of `--cmd 16` at 0x3c, 0x0f, 0xf0, 0x5a (and 0x26, 0x88) on one 64 x 64 triangle, read by the position source and by an iterated coordinate set, x and y | per row the drawn set (E1018) and the offset per model | 5 controls (0x88 coordinate set x, y; 0x26 source 0 x, y; 0x88 x replicate last), 18 held out |
| 2 | q261 | 16 | E1012's clip on held-out far vertices: 4 along +x, 3 along -x, 4 along -y, 3 on 128 x 128 | H-EXACT, the clip family per value, H-PIVOT intervals | 2 controls (E979's far-ctl first, far-x24p last), 14 held out |
| 3 | far | 8 | one far vertex at 2^26, 2^28, 2^30 px (x and y, both signs), ascending | the clip family, H-EXACT, -BAND, H-F32, H-SAT, H-WRAP, H-CULL | 1 control (far-ctl), 1 replicate (E979's far-x25n), 6 held out |

Time: every job is a 64 x 64 (q261's three 128 x 128) render under 2 s (E979, E1010); with the
reset, health fill and triangle between jobs about 6 s a job, 5 minutes; with staging, the
per-stage health and the copy back about 9 minutes.

**Stops.** No fault is planned anywhere: any fault, hang or unexplained failure stops the stage
(rc 4) and the session (the Mac driver stops on any status but 0 and 24). A control without its
reading stops the session at its stage (rc 25, premise). A tri row that read ok without `job: ok`
or a probe row without its 64 rows of 64 pixels stops that stage (hook_check, rc 24; the driver
goes on). A file the scorer reads that was not kept stops it (rc 23). `min_free_mb` 300;
`job_timeout` 120 s. **far runs last** (R13-2 a): it is the only safe-class stage in an untested
range (E684: "they may hang the TA" [infer: the clip comes first]); its rows run in ascending
distance, after its control and E979's 2^25 replicate, and the stage stops at the first job that
is not ok (a fault or hang: rc 4, the session ends there with everything else done; a job line
other than ok: rc 24).

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

- **q201 (Q201; E1018, E606, E437, E1010).** CR_ISP_MULTISAMPLECTL byte 0 (`--cmd 16=0x000000NN`,
  bytes 1 to 3 at 0 as the library's 0x88) on the triangle (5.29, 3.70), (60.10, 17.90), (14.60,
  58.20) px (`--tri-v`, on the 1/256 grid, not the tool's default). Two programs, otherwise one
  setup (every row `--vtx-coords 2` with `vtx_coords.bin`, o4 and o5 the vertex's clip x and y):
  src0, E437's primary PDS program (DOUTI 0x20400000: the position source, pa0 = x + sx, pa1 =
  y + sy); cset, the same with DOUTI 0x20400800 (E606's: coordinate set 0, pa0 and pa1 the
  iterated clip x and y, (x + sx) / 32 - 1 on 64 x 64). The pixel shader writes pa0 (x) or pa1
  (y) as the colour. The scorer reads every drawn pixel's float32 back to its offset s.
  - Frozen per row: the drawn set at E1018's point (lo/16, hi/16) (sample0_rule.covers, the
    frozen rule of closing12/plan/c6-q201); the offset per model: H-SAMPLE0 (both programs read
    at (lo/16, hi/16)), H-CENTRE (1/2), H-SWAP (hi/16, lo/16), H-SPLIT (the position source moves,
    the coordinate set stays at the centre). Tolerance 1/64 px (the grid's points are 1/16
    apart; E606's iteration error is about 1e-5 px).
  - Controls (can fail): 0x88 cset x and y (E606: the coordinate set at the centre), 0x26 src0 x
    and y (E1010: x + 0.375, y + 0.125 = E1018's (6, 2)/16), the 0x88 cset x replicate last.
  - All 18 others are held out (no kept job iterates under these bytes), 0x26 cset (the bridge)
    included. Retire if H-SAMPLE0 holds 18 of 18 with the coverage at E1018's point.
- **q261 (Q261; E1005, E1012).** E1012's clip (post hoc on all 48 kept far rows): the far edges
  clipped to a guard, each new vertex rounded half up to 1/256, the edges then exact. The engine is
  c6's own (gen/q261_rule2.py, a byte copy, sha256 0997a099... as `q261_rule3.py` checks it);
  gen/clip.py only lets each bound be its own parameter (clip4 = clip_poly where they agree,
  tests). Frozen per row: H-EXACT, the clip family (per value of the row's own guard, the pixels
  off H-EXACT), and on the 64 x 64 rows along x the H-PIVOT pixel intervals (r10-geo's
  pivot.py). Families: G = 16..22 (x <= W + G, E1012's survivors), a = 8..32 (x >= -a), g = 8..32
  (the y guard, assumed symmetric), and on 128 x 128 also h = 80..86 (an absolute guard
  [-(h - 64), h]). H-CLIP-ONE: one value of each family fits every held-out row; H-REL against
  H-ABS on the 128 rows (with the 64 x 64 rows' G).
  - Rows: c6's 4 +x and 3 -x vertices (closing11/plan/c6-q261/q261_proposals.json; their images
    reproduce c6's q261_heldout.out, tests); 4 -y and 3 128 x 128 vertices designed here (seeded,
    gen/clip.py `design`: the far vertex on the 1/32 grid that parts the family best, every row's
    image depending on its own guard only, tests). All held out.
  - Controls (can fail): E979's far-ctl (E684's far21d0) first and far-x24p (E1005's d = 0) last,
    each against its kept image pixel for pixel.
- **far (Q199; E979, E684).** Far vertices at +2^26 x, -2^26 y, -2^28 x, +2^28 y, +2^30 x, -2^30 y
  px (the other coordinate within 2^(k-2), chosen as above), E979's near vertices rounded to whole
  pixels, `--tri-unit 0` (2^30 px in an int32). Frozen per row: the clip family at E1012's
  survivors (the q261 prediction, scored per value), H-EXACT, H-EXACT-BAND (E684's 1e-3 band),
  H-F32 (the window vertex as the nearest float32), H-SAT and H-WRAP (a 24.8 word, gen/far.py),
  H-CULL. The tool sends the clip coordinate as a float32 (render.c ndc_unit): at 2^30 px that is
  2^30 + 32 px, and a float32 viewport would give 2^30; a pixel the two disagree on is '?' for
  every model (none does on these rows). Control: far-ctl; replicate: E979's far-x25n (its kept
  image and the clip family, 2^25).

**Predicted outcomes.** q201: H-SAMPLE0 held on 18 of 18 (E1018 [infer]), the coverage at
E1018's point on every row, the three rivals FAILED. q261: H-CLIP held on 14 of 14 with G narrowed
inside 16..22, a and g narrowed inside 8..32, H-REL held and H-ABS FAILED [infer: a guard in pixels
fixed whatever the target is unusual], H-EXACT FAILED where a value's band pixel differs, H-PIVOT
held per row (one D per row is weak by design). far: every row `job: ok` [infer], H-CLIP held,
H-SAT, H-WRAP and H-CULL FAILED; a fault or a hang past 2^25 stops the stage (a reading for
Q199, recorded by the fold).

## The mock's worlds (mock/world.py, kit/session.py mock)

model (every stage 0), nopix (no pixel rows: q201 24 by hook_check, then q261's first control
without its reading, premise 25), rowsmissing (63 probe rows: q201 24, the rest runs), cmdrefused
(byte 0 other than 0x88 refused: 4 at q201's 0x26 control), rejected (`job: rejected` with a diff
line, E934: q261 4), farfault (a vertex past 2^25 px faults: far 4 at its first held-out row),
farnojob (past 2^25 px rc 0 with `job: lost`: far 24). The fake answers from the argv only.
Before the worlds, every row goes through the library mock built from t10's bound source
(a581c06: 47 rows): none is refused.

## Replay vectors

The fold builds one `sgx545-tables` table a stage from the kept files alone (pinned:
`tools/usse-asm/closing_tables.py`, `crates/sgx-pipe/src/isp.rs`, `crates/sgx-pipe/src/iter.rs`
at 05b7039):

- q201 → `q201` (per row byte 0, program, component, the kept drawn set and offset): replay
  sgx-pipe `isp::coverage_image_sampled` (the coverage, E1018) and, if H-SAMPLE0 holds, the fold
  lifts `iter::sample_point`'s refusal (Q201) with a test on the table; `refused` under Q201
  otherwise. closing_tables.py has no kind for it: an inline table, as E979's rows were.
- q261 → `q261` (per row the vertices in 1/256 px, the target, the kept coverage, the family
  values that fit): replay `crates/sgx-pipe/src/isp.rs` `far_coverage_image` once the fold models
  the clip with the read guard (its band stays `None` today); `refused` under Q261 otherwise.
- far → `far`: as q261; past 2^25 px `refused` under Q199 unless the clip holds to 2^30.

## Layout

- gen/make.py writes `tables/`, `predictions/` (`predictions/q201/`, `/q261/`, `/far/`) and
  `bins/` from gen/q201.py and gen/clip.py (new, standard library only) over the byte copies
  gen/far.py (r9-x), gen/pivot.py (r10-geo), gen/q261_rule2.py (c6-q261) and gen/sample0_rule.py
  (c6-q201), read at the pinned data commit (gen/pins.py; tests/test_gen.py checks every copy).
- bins/: pos.bin (render/closing-r10-x, E1010's E437 program), cset.bin (render/closing-r7-geo
  p1138-it-a0__0.bin, E606's), pix_pa0.bin and pix_pa1.bin (render/closing-r10-x), vtx_coords.bin
  (pds/iteration-sources iter-coords, probes/pds/templates/vtx_coords.s).
- score/score.py, run/hooks.sh (readings job, pixels, hash, diff; checks job ok on tri rows and
  the 64 x 64 image on probe rows), mock/world.py, `tests/` (`test_gen.py`, `test_twin.py`,
  `test_score.py`, `kept.py`), PREFLIGHT.md, TOOLSRC.sha256; fold/FOLD-NOTES.md (the fold's notes;
  fold/ is outside the freeze). debug/ is scratch.

Publishable: everything (our own models, our own program files already published, kept records'
readings; no firmware-derived file). **Nothing is marked for data-private.**

## Deviations from the plan

1. **q201: 23 jobs, not 12.** A pixel shader writes one register as the colour (E1010's -x/-y
   form), so each (value, program) takes an x and a y job: 4 values x 2 programs x 2 = 16 held
   out, plus the 0x26 coordinate-set bridge (2, held out), and 5 controls (0x88 cset x and y,
   0x26 src0 x and y, the end replicate). About 1 minute more.
2. **q201: every row carries `--vtx-coords 2` and `vtx_coords.bin`** (the premise check), the two
   programs differing only in the PDS file's DOUTI word, so the source-0 controls are E1010's
   readings on this setup rather than byte replicates of E1010's jobs (bytes 1 to 3 of word 16
   are 0 here, 0xeaa26e here).
3. **q261: the four -y vertices are new.** Three of c6's far-y proposals depend on the x guard
   as well as the y guard and the fourth lies along +x (tests: `independent`), so the -y rows are
   designed here (gen/clip.py `design`, seed 13199, 13 of 25 g classes). The three 128 x 128
   vertices (seed 13261, 7 of 7 G classes) are new too (c6 named the target, not the vertices).
4. **far: vertices.** The plan's far2 (seeds section 8) fixed only the distance; the other
   coordinate is chosen so the clip family parts the image (a power-of-two second coordinate drew
   the same image under every value), and the near vertices are E979's rounded to whole pixels
   (`--tri-unit 0` is the only unit with 2^30 px in an int32 and quarter pixels).
5. **H-PIVOT only on q261's 64 x 64 rows along x** (r10-geo's pixel intervals are 64 x 64 and move
   the far vertex in y); -y and 128 x 128 rows score H-CLIP, H-EXACT and H-REL/H-ABS only.

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
