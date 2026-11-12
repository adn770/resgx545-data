# Round 7 plan, area dpm: Q210 (bands 5-7, larger objects, the passes), Q211 (the count), oomring2

Planner output, 2026-11-12. Offline and read-only: nothing ran on the laptop, no repo was written,
no guard was run, no kernel was built. Everything marked [infer] is an inference. Scripts and
outputs are beside this file (`/Users/jtorra/src/scratch/resgx545/closing7/b/`, hashes in
`PLANNER.sha256`). They read only public data (`resgx545-data/render/closing-*`), the published
round 6 offline library (here imported from `closing6/dpm/offline/`; its published twin is
`resgx545-data/cited/closing6/dpm/offline/`) and the repo's `tools/usse-asm/{pbdump,dpm_words}.py`.
No firmware image, listing or closed binary was opened, so every file here is publishable to
`resgx545-data/cited/closing7/b/` once the import path is repointed to the published twin.

## 0. Short version

The planner's offline passes changed what the round needs. All three are POST HOC tallies run
once, none a verdict; the offline stage (section 3) redoes them under freeze.

1. **Q211, the count: the walk order can be READ, and with it the replay is exact.** A region
   header holds the address of the region's stream block, so a kept dump of a completed
   one-triangle job shows the order in which the TA took the blocks. In 11 kept dumps (512x384 to
   4096x4096, `q211_walk64.out`) one order places every block at its real page and slot, 16024 of
   16024: **strips of 64 pixel rows across the whole target, each strip in 64 x 64-pixel blocks
   left to right, a block's regions row by row** (H-WALK64). Row order places 7 %, column order
   0.3 %. E875's replay, unchanged (`f7_replay.replay`), with that order gives the count **and
   every run's peak** of 89 of 89 kept cells at 4096x4096 (g-qf 22 + 5 repeats + r-b's 4
   controls, s275, s198, s119, and R6's s262, s243, s220, s179: `q211_replay64.out`), where row
   order gives 83 counts and 47 peak sets; and the record cells of E625 and E779, 37 of 37
   (`q211_records64.out`). The order was read from dumps, not chosen on counts, and one order was
   tried. "No single spacing fits" is then expected: the count is the replay's.
2. **Q210, bands 5 to 7: the burst end was the wrong object.** E874 took B_k after the first
   object with index divisible by 15. Taking instead the object **b_k = floor(1024 (k - 1) / 67)
   itself, the block that straddles global pages k - 1 and k** (A_k = the replay's page count once
   b_k is tiled; H-SPAN) gives `0x97`, `0xe3`, `0x12e`, `0x178`, `0x1c3`, `0x20d` at 2048x2048:
   the six observed first one-page cells (`q210_bands.out`). b_k is 15, 30, 45 for k = 2 to 4
   (A = B there) and 61, 76, 91 after, which is why E874 held at bands 3 and 4 and failed from 5.
   On every kept first partial render of the 67-dword scene H-SPAN places 163 of 163 rows and
   E874's B 158 (`q210_phase2.out`; unscored: R6's four `--vtx-coords` cells, another scene, and
   c5b-cal at the clamp). [infer] The partial render keeps the global pages spanned by the
   objects written and not yet tiled: 2 while the straddling block is among them, else 1.
3. **Larger objects (E882).** At N 8 the blocks are 187, 187, 198, 198, 198 dwords
   (`q210_n8blocks.out`): 198 = 187 + 11, one more vertex of 8 + 1 + about 2.5 dwords [infer], so
   blocks stop holding 15 vertices and b_k must come from cumulative sizes, not from one L. The
   offline stage reads the block-open sequence from the two kept dumps instead of guessing a
   burst rule (as item 1 did for the walk).
4. **oomring2** needs one table change: `ldr` of `0x0724` and `0x072c` in the own-task register
   list (`tools/fwtask/regs.toml`, generated into the fork's `sgx_own_regs.h`), one fork commit,
   tests on both sides (section 5). The closed out-of-memory routine reads both registers itself
   (`doc/specs/edm_dataflow.md` lines 1374 and 1383 [source]).
5. **R6's slip** is designed out by a build-time test that every gating control gives a reading
   and can fail, and by a gate that treats "no reading" as a stop at the premise stage, never as
   a silent gate (section 6).

Proposed: an **offline stage** (one builder, half a day), then **one session `r7-dpm`**, about 100
jobs, 30 to 40 minutes, every row class "safe"; its last stage (10 jobs) needs the new module.

## 1. What the planner ran

| script | output | what | label |
|---|---|---|---|
| `q210_bands.py` | `q210_bands.out` | E874's replay per object around each burst | post hoc |
| `q210_phase2.py` | `q210_phase2.out` | H-SPAN and E874's B on all kept rows | post hoc |
| `q210_targets.py` | `q210_targets.out` | model S, B, A at 11 targets (cells) | model |
| `q210_n8blocks.py` | `q210_n8blocks.out` | head-pair offsets, N 4 and N 8 dumps | reading |
| `q211_walk.py` | (printed) | regions of a page in address order | reading |
| `q211_walk64.py` | `q211_walk64.out` | H-WALK64 against 11 dumps, block by block | post hoc |
| `q211_replay64.py` | `q211_replay64.out` | counts and peaks, 89 cells, 3 orders | post hoc |
| `q211_records64.py` | `q211_records64.out` | E625, E779 record cells | post hoc |

How post hoc: `q211_walk.py` printed u-2048's pages; the order was written from that print and
`q211_walk64.py` then scored it on all 11 dumps in one run (u-2048 is the fit dump, the ten
others SEMI: the first run printed six pages of three of them). `q211_replay64.py` ran once
after; no order was added or changed after its output. H-SPAN was written after E881's table
was read (its 15 r-m rows are the fit), then scored once.

Rests on: E773 (HU1's regions), E832, E854, E863, E875, E883 (the cells), E874 and E881 (the
replay and the r-m rows), E882 (the N dumps), E310 and E625 (record cells), the dumps of
`closing-r1-pixgeo/out/g-u1`. Would refute: H-WALK64 by one block off its slot in a completed
one-triangle dump, or one count or run peak off at a new scene; H-SPAN by one cell with
B_k <= thr0 < A_k that leaves 1 page (11 targets have such cells, none ever run outside
2048x2048), or a cell at or above A_k that leaves 2.

Unexplained and kept open: the lag of 3 objects; the 2048x4096 S3 miss (model `0x129`, read
`0x12c`); the N 4 misses of CAP at S4, S9, S10; u-4096-2 (two kicks) places 4697 of 13804 with a
one-pass sort, as expected of two walks (offline step G4 replays it kick by kick).

## 2. Hypotheses (frozen at the offline stage's end, before any row)

- **H-WALK64** [HW reading, then held out]: the walk order of section 0.1, for any target.
- **H-REPLAY64** (Q211): count and every run's peak of a one-object, one-kick scene are E875's
  replay in H-WALK64 order. Rivals for the tally only: row order, column order, d = 7/4, d = 1.
- **H-SPAN** (Q210): left = 2 iff S_k < thr0 < A_k, else 1 (thr0 = S_k is the grow cell, not
  scored). Rival: E874's B_k (H-PHASE as landed), the timeline rule E-TL.
- **H-STEPMODEL** (E874, unchanged): S_k and U at targets never run.
- **H-CUM** [infer, only if G5 supports it]: for any object size global page k is requested when
  the cumulative dwords of the blocks written cross 1024 (k - 1); the stream blocks open where
  the dumps show them. Frozen only if it places the kept N 4 and N 8 calibrations.
- **H-PASS** (needs oomring2): the counts the firmware's own passes read are the timeline's at
  the abort and after the render (dword 36 + 2 and the pages left), and at a grow cell the
  resume pass reads 1 where the next host sample reads 2 (H-PENDREQ, E874).
- **H-ISUB** (E864's [infer], post hoc in E881): the creep cell (dword 36 = 2, 1 page left) is
  silent with `sa8 & 0x380` = 0. Frozen verdict wanted; no kernel change needed.

## 3. Offline stage (no laptop; one builder; outputs under `closing7/b/offline/`)

Each step freezes its script's sha256 before its held-out set is opened; a script fails on a
missing file (no NODATA as "cannot tell").

| step | what | fit side | held out on kept data | refuted by |
|---|---|---|---|---|
| G1 | H-WALK64 on every kept completed one-kick dump (all targets, tri and `--tri-full`, 64x64 to 4096x4096; several hundred dumps) | u-2048 | all others (10 SEMI, the rest never opened) | one block off |
| G2 | H-REPLAY64 on the 89 cells and the 37 record cells, script frozen first | none (no number fitted) | all 126 (SEMI: the planner's tally) | one count or peak off |
| G3 | H-SPAN on all kept rows; A_k from the frozen `f5lib` | 2048x2048 r-m (15) | the other 148 rows (SEMI) | one row off |
| G4 | multi-kick and multi-object dumps (u-4096-2, u-2-*, u-3-stk, u-4-corners, E735's six U, s438's 27 decisions): replay kick by kick; does a later object take a block where one has room | E735's U | s438, E773's 15 | exploratory, no verdict |
| G5 | r-v dumps (v-cal-c4, v-cal-c8, 4 cells): block sizes by `pbdump.objects`, cumulative b_k, the stream blocks' open sequence read per region; then the steps | N 4 | N 8 (SEMI) | steps off: H-CUM not frozen |
| G6 | 2048x4096 S3 miss: the same reading on the 11 kept dumps there | - | - | exploratory |
| G7 | the lag: in overflowed dumps, objects in the global list against the last object any stream names | - | - | exploratory |
| G8 | the new gate (section 6) rescoring R6-dpm's kept `out/a2`: must print E881 to E883's ungated tables as verdicts and stop at a0-cal-2048f's grow row at build | - | - | a test, not a result |

What the stage can decide without hardware, labelled as it is: the walk order [HW, reading of
dumps, held out on dumps never opened]; Q211's count for one-object scenes [HW, SEMI]; Q210's
margin rule at the 67-dword scene [HW, post hoc + SEMI]. Each still needs a frozen held-out
check on the laptop before a question clause is called answered (section 4). If G2 or G3 fails
on its kept set, the matching stage shrinks to its controls (decision 3).

## 4. Laptop session `r7-dpm` (prefix `r7d`)

Reuse: R6-dpm whole (runner with freeze 2's staged-tree checks, `r6read.py`, `score_r6.py`'s
readers, mock world, tool `~/sgxfive-test-rgn4` e6951558 as R6-held ran it on 41E2F5C7,
`p1139-green`, 16-register timeline, a debugfs reset per job). New: tables from the frozen
models, the gate of section 6, per-job scene checks from the job's own calibration, `oomring2`.
Laptop files only under `~/scratch/r7d/{run,stage,out,work}`, work directories `mktemp -d
~/scratch/tmp/r7d.XXXXXX`, 600 MB free at preflight and 200 MB before every job (rc 13), whole
capture checked before any reading, dumps up to 2048x2048 only, nothing in `/tmp`. Data read by
tests through the session's data view (branch session-abspath), never by absolute path.

| stage | jobs | rows | frozen expectation | label |
|---|---|---|---|---|
| s-a0 premise | 6 | a0-cal-2048 (P `0x162`), a0-cal-2048f (complete), c4-b5, c4-b6, t-s3m6, qf `0xa2` | S2 to S7, need `0x213`; R, N; left 2, 1; count 2 and E832's run peaks | controls |
| s-m margin | 50 | 3072x3072: calibration, bands 5 and 6, thr0 B - 1 .. A (12); 3072x2048, 2048x3072, 2560x2560, 1024x1024 (never run): calibration + B3 - 1, B3 and the parting band's B - 1 .. A (32); 2048x2048 A - 1, A at bands 5 to 7 (6, replicates) | steps and U by H-STEPMODEL; left 2 below A_k, 1 from it (19 cells where E874's B says 1) | HELD OUT, discriminating; replicates |
| s-b count | 29 | 4096x4096: two new moves where H-REPLAY64 and row order differ most, calibration + 6 cells each (14); 4096x2048, one move, calibration + 4 (5); 2048x2048 with dumps, one move, calibration + 4 (5); 1024x768, 5 cells at a move never run | U by HU1; count and every run's peak by H-REPLAY64; at 2048x2048 every block's page and slot in the calibration's dump | HELD OUT |
| s-v objects | 6 | 2048x2048 `--vtx-coords 2` and `6`: calibration with dump + 2 cells each | only if G5 froze H-CUM: steps, L sequence; else calibrations only, "explore" | HELD OUT or explore |
| s-k passes (last) | 10 | own task armed: k-b5, k-b6 (controls), c4-b3, S3, S4 + 1, t-s3m6, band 5 A - 1 and A (`0x177`, `0x178`), the 2048x4096 creep cell twice | `sa8 & 0x380` as R-5; with oomring2 the counts at each pass (H-PASS); creep: 0, silent | HELD OUT; controls |

About 100 jobs. 2048-class 9 s, 3072-class 12 s, 4096-class 15 to 25 s, five stage starts: 30
to 40 minutes, plan 55. Order: health, s-a0, s-m, s-b, s-v, then task load, health, s-k.

Details:
- **Cells come from the frozen model; a calibration only checks it.** A calibration off its
  frozen steps refutes H-STEPMODEL at that target; its cells are then re-picked from the
  calibration's own steps by the frozen rule "A_k = S_k + (model A_k - model S_k)" and scored
  for H-SPAN only, labelled so. Model cells: `q210_targets.out` (3072x3072 band 5 `0x32a` to
  `0x32e` and band 6 `0x3cd`, `0x3ce`, 3072x2048 `0x225` to `0x228`, 2048x3072 `0x22a` to `0x22c`,
  2560x2560 band 6 `0x2ae` to `0x2b0`, 1024x1024 band 5 `0x6b`, `0x6c`; all below the `0x400`
  clamp). Sizes are confirmed offline against the tool's mock and the fork's size check; a
  refused size is replaced from a frozen spare list (2560x1536, 1024x1536), never by hand.
- **The creep cell's scene check** compares with the steps of its own target's kept calibration
  (`0x9a`, `0x12c`, `0x1be`), not with the model that misses S3 there: R6's void cannot recur.
- **s-k without the kernel change** runs R5's `oomring` on the module that is loaded: the `sa8`
  rows and H-ISUB get their frozen verdict, H-PASS reads "not run" and is not a headline.
- **s-k with it**: `oomring2` (R6's generated source, 16 `ldr` + 24 `stad` more than `oomring`,
  no `str`, no sa or pa write). Its first job is a premise: the arm is accepted and k-b6's rungs
  hold non-zero counts within the bracket of the host samples around them, else stop.

Controls that can fail (each proven readable at build, section 6): s-a0's six; every
calibration's steps; scene checks from the job's own data; s-b's qf control and each scene's U
(a U off HU1 voids that scene only); s-k's k-b5 raising and k-b6 silent under the task.

Stop conditions: any s-a0 control off or without a reading, capture not whole, thr0 read back
not P - `0x22`: stop before s-m. Any BIF fault, -110, watchdog or failed health: stop the
session. s-k: one EDM stall is reset once, a second ends the stage. Free space short: rc 13.
The lead decides after any stop.

Dry runs before the freeze: the scorer replays R6-dpm's `out/a2` (G8) and R5-dpm's `out/a2`;
planted directories must FAIL (a g-qf timeline in a 1500-vertex control, a control with no
partial render under a grow row, a missing dump directory, a missing sourced file in the staged
tree); the mock runs the staged tree under `env -i`, once under load; no wall-clock margin under
1 s; one file-name function shared by runner and scorer; every directory a job writes is made
by the runner and listed in a REQUIRED-files check (rc 23).

## 5. Kernel change proposed for oomring2 (the user decides)

What changes, test first on both sides:

- resgx545 `tools/fwtask/regs.toml`: two `[[allow]]` rows, `CR_DPM_PAGE_STATUS` `0x0724` and
  `CR_DPM_GLOBAL_PAGE_STATUS` `0x072c`, `use = "ldr"` (never `str`), record E864 and the
  dataflow lines above. No deny row names either offset; the list stays closed.
- resgx545 tests written first: `test_gen_verify.py` expects `sgx_own_ldr_regs = { 7, 8, 81,
  457, 459, 517, 670 }` and the `str` list unchanged; `test_verifier.py` accepts `ldr #457` and
  `#459` as canonical words, refuses `str #457`, `str #459` and `ldr` of `0x0720`, `0x0728`,
  `0x0730`, `0x0734`; `asm/fwtask/oomring2.s` lands with its sha256 and is accepted by the
  Python verifier and by the host build of the fork's C verifier (`test_host_verifier.py`, whose
  bit-flip and random-blob agreement tests then cover it); `crates/sgx-sim/src/fwtask.rs`
  `LDR_OK` gains the two offsets and its test refuses them unseeded (sim in sync).
- linux fork, one commit on `resgx545` after 3f0b3e74 ("drm/gma500: let an own task read the
  two DPM page status registers", trailer `Assisted-by: LLM`): `sgx_own_regs.h` regenerated by
  `gen_verify.py` (one line), `sgxfive_owntask_test.c` `register_lists` gains the four
  expectations (ldr true, str false, for both) and the four refused neighbours,
  `sgxfive_owntask_blobs.h` regenerated with oomring2 among the accepted blobs.
  `sgxfive_owntask.c` is table-driven and does not change.
- Checks: `tools/fork/recheck.sh 3f0b3e74 TIP` on cachix (KUnit `sgxfive_owntask` and the series
  check), `fork-land.sh`, `forkpin.py` PIN moved in the same landing, R6-dpm's
  `tests/test_oomring.py` inverted (oomring2 accepted by both; `ldr #2` and a store through an
  unpatched base still refused), `tools/fork/deliver-module.sh TIP` (manifest with the new
  srcversion), then `tools/bringup/push-gma500.sh --ko` and a one-shot boot with the user's OK.
- Risk: low. Two read-only loads of registers the closed handler loads in the same routine; no
  clock gate, no `str`, no new debugfs. Not known: a side effect of the read from a pass other
  than the out-of-memory one (none recorded; the host reads both at every timeline sample).
- Cost: one fork commit, one module build, one boot. If areas a or c get a boot this round the
  commit rides on it; the laptop needs a one-shot boot for any session once it has rebooted.

## 6. Designing out R6-dpm's slip (a frozen control that cannot produce a reading)

1. **Readable by construction.** Each control row carries the condition under which it reads
   (`needs: partial>=1`, `needs: dump`, `needs: task`). The generator refuses a control whose
   job's frozen prediction does not meet it (a0-cal-2048f predicts 0 partial renders, so a grow
   row there is a build error).
2. **Proven twice at build** (`tests/test_controls.py`, in RUN_ALL): on the mock world's
   predicted outcome every gating control prints `held`; under a planted mutation of exactly
   that control's quantity it prints `FAILED`. A control that prints `cannot tell` in either run
   fails the build. Where a kept real job of the same row exists (all six s-a0 rows do, in
   R5-dpm and R6-dpm), the test also scores that kept job and requires `held`.
3. **No silent gate.** In the scorer a control without a reading is its own state, `NO READING`,
   and never gates a later headline; on the laptop the runner scores s-a0's controls before s-m
   and stops with rc 10 on `FAILED` or `NO READING` (no stage is spent behind a dead gate).
4. **Gate scope.** A headline is gated only by its own stage's controls and by s-a0's rows of
   the same scene class (1500-vertex rows by the 1500-vertex controls, count rows by qf).
5. **G8** shows the new gate on R6-dpm's kept files: build stops at a0-cal-2048f's grow row; with
   that row removed the verdict tables equal `postrun/ungated.out`. A test of the gate only: the
   R6 verdicts stay as landed ("cannot tell", post hoc readings).

Earlier slips kept designed out: staged file list and `env -i` mock (R6 a1), created and
REQUIRED directories (R6-misc), no control on the default triangle for a 1500-vertex claim and
one file-name function (round 4), `~/scratch` paths and no timing margin (round 5).

## 7. What a result would change in landed text

- G1, G2, s-b: new records; appended notes on E875 and E883 (row order's failure stands; the
  replay holds in the order read from dumps), on E854 and E863 (the spacing is the replay's
  average); Q211's line loses the count clause for one-object, one-kick scenes; `3d.md` gains
  the walk order [HW]; `dpm.rs` takes the replay in that order and still refuses multi-object
  scenes; vectors: the 89 cells and the 16024 block addresses.
- G3, s-m: new record; appended note on E874 (its B_k is A_k only for k up to 4; the claim was
  already corrected by E881) and on E881 ("what keeps the second page at bands 5 to 7": the
  straddling block); Q210 loses the margin clause if s-m holds.
- G5, s-v: note on E882 (two block sizes are one more vertex [infer]); Q210 keeps "what opens the
  bursts for larger objects" unless H-CUM is frozen and holds.
- s-k: E864's `isub16` order from [infer] to [HW]; with oomring2, Q210 loses "the counts at the
  passes" and the pending-page clause gets a direct read.
- Still open after a full success: the lag in closed form, the 2048x4096 S3 miss unless G6
  reads it, many-object counts (G4 is exploratory), Q211's U clause for wide scenes.

## 8. User decisions

1. **Offline stage G1 to G8 before any freeze.**
   (a) Recommended: all of it first, one builder, folded as records and notes so the session's
   predictions cite landed text (as R6-1).
   (b) G1 to G3 and G8 only (the two seeds and the gate); G4 to G7 later.
   (c) Fold with the session.
2. **Kernel change for oomring2** (section 5).
   (a) Recommended: approve the one commit (two `ldr` rows), built and booted once, shared with
   any boot areas a or c get; s-k runs last on it.
   (b) The same plus `ldr` of `0x0728` and `0x0734` (four rows; nothing planned reads them yet).
   (c) No kernel work: s-k runs R5's `oomring` (bits only, 4 jobs: controls and the creep cell).
3. **Session scope.**
   (a) Recommended: s-a0, s-m, s-b, s-v, s-k (about 100 jobs, 30 to 40 minutes); a model that
   failed its kept set offline keeps only its controls.
   (b) Seeds only: s-a0, s-m, s-b (85 jobs, about 30 minutes).
   (c) Offline only this round; the held-out rows wait for round 8.
4. **s-m width.**
   (a) Recommended: five targets (3072x3072 and four never run) plus the six replicates, 50
   jobs, 19 discriminating cells.
   (b) 3072x3072 and 3072x2048 only (21 jobs, 11 discriminating cells).
5. **Larger objects (s-v).**
   (a) Recommended: run its 6 jobs only if G5 freezes a rule that places the kept N 4 and N 8
   calibrations; otherwise two calibrations as exploration.
   (b) Skip s-v; E882's clause stays open.
6. **Boot and order.**
   (a) Recommended: if the laptop is still on 41E2F5C7, run s-a0 to s-v there without a reboot,
   then the one-shot boot of the new module and s-k with its own premise; if it has rebooted,
   one boot of the new module and the whole session on it.
   (b) Wait and run everything after the new module's boot.
7. **Gate redesign** (section 6).
   (a) Recommended: adopt all five points in `tools/closing/` so the other areas' sessions get
   them too.
   (b) In r7-dpm's own scorer and tests only.
8. **Sim and vectors.**
   (a) Recommended: in the fold, tests first: `dpm.rs` walks in H-WALK64 order and replays
   one-object counts, takes A_k for the pages left, refuses what was not measured; vectors from
   the kept cells and block addresses.
   (b) Vectors only. (c) Later.
