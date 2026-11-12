# Round 6 plan, area dpm: Q210 (steps, margins, E802, the pending page), Q211 (the count), A2b

Planner output, 2026-11-12. Offline and read-only; nothing ran on the laptop, no repo was
written, no guard was run. Everything marked [infer] is an inference. Scripts and outputs are
beside this file (`/Users/jtorra/src/scratch/resgx545/closing6/dpm/`): they read only
`resgx545-data/render/closing-*` (public), the session-published `closing5/r5-dpm/gen/hu1.py`
and the repo's `tools/usse-asm/{dpm_words,pbdump}.py`. R-5 was read from our own note
(`resgx545-data-private/cited/closing4/p7/reading-r5.md`); no script imports `guard.py`, no
firmware image, listing or closed binary was opened. So every file here is publishable to
resgx545-data `cited/closing6/dpm/`.

## 0. Short version

- The planner's quick offline passes (all post hoc, FIT or reading, none a verdict) say the
  three seeds are one mechanism, the TA's page take, and most of it is decidable offline:
  1. **A2b**: 4096x2048's S2 is `0x97` in 13 of 13 kept jobs once a step is read as the bracket
     it is; the calibration's bracket was [`0x97`, `0x98`] and the frozen point rule took the
     upper end. No row needed (O1).
  2. **Steps**: the global list holds the object blocks (67 dwords each in the kept dump, so
     15.28 a page); the page take of a 1500-vertex scene is a **burst** of about one scene's
     worth of stream pages after every global step, then a few slow pages ("creep") up to the
     next step. Step spacing = burst + creep; that is why the steps are evenly spaced and sit
     3 to 4 pages under the one-triangle need (O2, O4).
  3. **Margin**: the first partial render leaves 2 global pages when the refused request falls
     in the step-and-burst phase and 1 when it falls in the creep phase: the flips `0x96/0x97`,
     `0xe2/0xe3`, `0x12d/0x12e` at 2048x2048 are the three burst ends, and the "margins 6, 5,
     4" are the creep page counts plus one (O3, O5). E774's C is a burst end.
  4. **Q211**: a page-by-page replay of the TA with **no fitted number** (HU1's regions walked
     in rows, 32 streams a page, a page per macrotile, the one raise) gives the partial-render
     count of 54 of 56 kept cells over all four scenes (U 287, 275, 198, 119), where no single
     spacing d fits; it gives the last run's peak exactly in 30 of 56 and within 3 pages in
     the rest (O6). The walk order is the open detail.
- Proposed: an **offline stage first** (one builder, half a day, no laptop) that turns 2 to 4
  into frozen models with fit and held-out labels on kept data, then **one laptop session
  `r6-dpm`**, about 90 jobs and 30 to 35 minutes, all rows class "safe", rgn4 boot as it
  stands, **no kernel change, no reboot**, every laptop file under `~/scratch/r6d/`.
- The hardware is for what kept data cannot give: held-out tests of the frozen models on
  targets, bands and scenes never run, one discriminating scene for the cause of the bursts,
  and a direct read of the page counts at the firmware's own passes.

## 1. What the planner ran (preliminary; the offline stage redoes it under freeze)

All in this directory; `r6lib.py` is the shared reader (every `closing-*/out` timeline).

**O1 `steps_iv.py` -> `steps_iv.out` [data].** A step of `0x072c`'s high half between two
samples with page counts a and b only says the count before the step is in [a, b - 1].
Intersecting the brackets of all kept first runs per (target, scene, step): one value at 28 of
31 (target, scene, step) keys, a 2-page range at 3 (one or two jobs each), an empty
intersection at none. 4096x2048 S2: 7 jobs bracket [`0x97`, `0x97`], 6 jobs [`0x97`, `0x98`],
among them a2b-cal-4x2. So S2 = `0x97` there and r5's FAILED row is the point rule
max(a, b - 1) on a two-page bracket, the same thing E861 notes for 2048x4096. Rests on: E852,
E861 and the 13 timelines. Would refute: one job whose bracket excludes `0x97`. Needs no
held-out check (it is a reading rule, not a law). New fact on the side: S6 and S7 at
2048x2048 are `0x181` and `0x1ca` (6 kept complete jobs of r2-geo and r3-geo).

**O2 `glob_pages.py`, `page_peek.py` [data; structure infer].** In a0-cal-2048's dump the global
list's head is PB page 1 (pbdump's "TA object") and its pages hold object blocks: the first
block's two head dwords recur every 67 dwords, 16 times in page 1, and page `0x52` (= S2 + 1)
starts in the middle of a block. So a 1500-vertex scene writes about 100 blocks of 268 bytes
[infer: 5 triangles a block, 10 bytes a vertex after a 29-dword head], blocks straddle pages,
and global page k is asked for at block floor(1024 (k - 1) / 67): 15, 30, 45, 61, 76, 91. The
state lists of a completed job read empty, so only overflowed jobs' dumps show the lists.

**O4 `ps_time.py` [data].** Page count against time in the two complete 2048x2048 scenes
(c3-2048-cal, c6-cal): 0 to `0x4f` in 0.2 ms, 1.2 ms with no page, `0x50`, `0x51`, global page
2, about 272 us, then `0x53` to `0x97` in 0.25 ms, then single pages 0.1 to 0.65 ms apart up
to `0x9d`, global page 3, 281 us, burst to `0xe3`, creep to `0xe8`, global page 4, 272 us,
burst to `0x12e`, creep to `0x132`, and so on to U = `0x213`. The wait between a global step
and its burst is 272 to 281 us at five of six steps (25 us at S6).

**O3 `left_table.py` -> `left_table.out`, O5 `gap_rule.py` -> `gap_rule.out` [data, post hoc].**
149 kept jobs with thr0, global pages at the abort and left, grow, raise. At 2048x2048 the
pages left read 2 for thr0 from S_k + 1 to the burst's last page less one and 1 from there to
S_k+1 (grow cells as E860), in bands 2, 3, 4 and 5; the same shape at the four other targets.
A plain waiting-time threshold does not separate the two (creep pages sometimes come in
pairs), so the rule is a phase, not a time.

**O6 `cnt_sim.py` -> `cnt_sim.out` [FIT of structure, post hoc].** The replay described in 0.4,
six walk orders listed in the script, none tuned per scene. Counts: rows of the whole target 54
of 56 (misses qf-0x27 and qf-0x6e, one render too many, by 2 to 3 pages); columns 53; macrotile by
macrotile 49. Row order, exact last-run peak: s119 10 of 11, s198 4 of 11, s275 2 of 7, g-qf
14 of 27. For comparison E854's d = 7/4 misses 4 of the 20 r5 cells and d = 1 misses 5 of
g-qf's 22. [infer] What a partial render "loses" is the part-filled page of every macrotile
the walk has open at the abort, which is why d moved with the scene (E863).
The 56 are 48 distinct overflow cells, r5's 5 repeats of g-qf cells and 3 calibrations.

## 2. Hypotheses (frozen at the offline stage's end, before any row)

- **H-IV** (reading rule): a step is its bracket; a frozen S matches when it lies in it.
- **H-OBJPAGE** [infer]: global page k is requested when object block b_k = floor(1024 (k - 1)
  / L) is written, L the block's dwords read from the scene's own dump (67 for the tool's
  1500-vertex scene). Independent of target and of what the triangles cover.
- **H-BURST-PAGE** against **H-BURST-CAP** [infer, both]: the burst after a global step is
  caused by the step (every region's stream takes a new 128-byte block when the objects move
  to a new page), or by a stream block filling after a fixed number of objects that happens
  to be near 15.28. They part when the object size changes and the regions do not
  (`--vtx-coords N`): PAGE keeps one burst per global step (steps closer in objects, spacing
  in pages unchanged), CAP keeps the bursts where they were and moves the steps between them.
- **H-PHASE** [infer]: the first partial render leaves 2 global pages iff the refused page
  request falls between a global step and the end of its burst, else 1 (1 before S2). With
  R-5's guard this gives every raise flip: C = burst end. [infer] reading: the render keeps
  the pages that hold the object under way, and the burst is the tiling of the block that
  straddles two pages.
- **H-STEPMODEL**: S_k and the burst ends E_k from geometry: a block-level replay (regions of
  the 500 shifted copies, streams by generation, pages per macrotile, plus H-OBJPAGE). Its
  constants are read from dumps, not fitted to S.
- **H-PENDREQ** [infer]: at an S cell the refused request is the global page itself, so it is
  not in the list while the partial render runs and is served when the TA restarts; that is
  the whole of "pending only after a grow" (H-GREQ and H-PEND are one fact).
- **H-REPLAY** (Q211): the count and every run's peak of a one-triangle scene are the replay's
  with the walk order W* chosen in the offline stage.
- Kept as rivals for the scorer's tally, not as hypotheses: E854's d = 7/4, d = 1.

## 3. Offline stage (no laptop; one builder; outputs under `closing6/dpm/offline/`)

Order matters: each step freezes its script's sha256 before reading its held-out set.

| step | what | fit side | held out (kept data) | refuted by |
|---|---|---|---|---|
| F1 | H-IV table of every step, all sessions | - | - | an empty intersection |
| F2 | object blocks: `pbdump.objects` on every kept overflow dump (2048 rows of r2-geo, r3-geo, r5-dpm, g-c7): L, triangles a block, list chains | a0-cal-2048 | g-c7 (`--tri-full`), d36, c4, T rows | L not constant in a scene; chain not at S_k + 1 |
| F3 | stream words: entries an object adds to a region's 128-byte block, blocks per region per generation (`pbdump.stream`) | a0-cal-2048 | g-c7, a 4096x4096 r3 dump if kept | - (feeds H-BURST) |
| F4 | H-PHASE: phase of thr0 + 1 in the target's longest first run by a frozen burst-end rule | 2048x2048 bands 2 to 4 | the 4 other targets (SEMI: seen in `left_table.out`), 4096x4096 1350 vertices | one no-grow job on the wrong side |
| F5 | H-STEPMODEL replay, constants from F2 and F3 | 2048x2048 | S_k, E_k and U of the 4 other targets and g-c7's `0x200`, `0x302` (SEMI) | a step off its bracket |
| F6 | H-PENDREQ: when the count goes 1 to 2 relative to the stretch end in the 21 kept jobs that grew, against S + 1 and S - 1 cells | - | all (a reading) | a non-grow cell with the same late page |
| F7 | H-REPLAY: enumerate a closed family of walk orders (rows, columns, macrotile rows, 16-pixel half-regions first or second, at most 16 members), pick W* on g-qf's 22 by count then last peak | g-qf | s275, s119, s198 counts (SEMI) and all their run peaks (never used in a fit: held out), E625/E779 4096 cells, 1024x768 cells | no member fits g-qf's counts; W* misses a held-out count |
| F8 | E802: is g-c7 one global page because its 15 first blocks take `0x200` pages (F2, F3, F5) | - | c7-cal | F5 misses `0x200` |
| F9 | 1500-vertex page loss (E854's "pages not conserved"): F5's replay with partial renders against the kept run peaks of g-c4, g-d36, T | g-c4 | g-d36, r5 T and A2 | exploratory, no verdict |

Decisions this stage can take without hardware: A2b (F1), "what sets S_k" and "evenly spaced"
(F2, F5), "the margin" (F4) and E802 (F8) as [HW, post hoc; SEMI held out]; the Q211 count as
FIT plus run peaks held out (F7). Each needs a true held-out check on the laptop before the
question clause is called answered: section 4. If F5 or F7 fails its kept held-out set the
matching laptop stage shrinks to its calibration rows (decision 3).

Slip guards: F4's burst-end rule and F7's family are written and hashed before their held-out
sets are opened (the planner has seen counts and flips, not run peaks per order beyond row
order: disclosed, SEMI). Every script fails on a missing file (no NODATA as "cannot tell").

## 4. Laptop session `r6-dpm` (prefix `r6d`)

Reuse: r5-dpm whole (`run/r5read.py`, runner, `score_r5.py`, mock world, `oomring`, the
16-register list, tool e6951558, rgn4 module 99CD90DA, `p1139-green`, a debugfs reset per job).
New: stage tables from the frozen models, the bracket rule in reader and scorer, per-run peak
clauses, laptop paths. Laptop files only under `~/scratch/r6d/{run,stage,out,work}`; temporary
directories `mktemp -d ~/scratch/tmp/r6d.XXXXXX`; 200 MB free checked before every job and
600 MB at preflight on that filesystem; whole-capture check before any reading; dumps on rows
up to 2048x2048 only; work directories removed at stage end, `~/scratch/r6d` moved to
`~/scratch/archive/` by the lead after the copy. Nothing in `/tmp`.

| stage | jobs | rows | frozen expectation | label |
|---|---|---|---|---|
| r-a0 premise | 7 | cal-2048 at P `0x162` and at `0x422` (complete), c4-b5, c4-b6, t-s3m7 (`0x96`), t-s3m6 (`0x97`), qf `0xa2` | steps in brackets incl. S6 `0x181`, S7 `0x1ca`; R, N; left 2, 1; count 2 | controls |
| r-m new bands | 15 | 2048x2048, 5 consecutive thr0 around F4's predicted flip in bands 5, 6 and 7 (near `0x178`, `0x1c1`, `0x20d`) | left 2 up to the frozen burst end, 1 after; all silent | HELD OUT (H-PHASE; cells never run) |
| r-n new targets | 21 | 2048x1024, 1024x2048, 1536x1536: calibration (P `0x422`) + bands 3 and 4: flip - 1, flip, S - 1 | S_k, E_k by H-STEPMODEL before the run; left 2, 1, 1; raise by R-5 | HELD OUT (targets never run) |
| r-v object size | 6 | 2048x2048 `--vtx-coords 4` and `8`: calibration with dump, then flip - 1 and flip of band 3 from that calibration | L from the dump gives S_k (H-OBJPAGE); PAGE: one burst per step; CAP: bursts every 16 objects | HELD OUT, discriminating |
| r-b count | 40 | 4 controls (qf `0x53`, `0x54`, `0xa2`, `0xa3`); 4 new one-triangle scenes at 4096x4096 (moves picked by F7 where W*, its runner-up and d = 1 differ most), calibration + 8 cells each | count and every run's peak by H-REPLAY; U by HU1 | HELD OUT |
| r-k passes (last) | 8 | task armed: c4-b5, c4-b6, c4-b3 (S4), S3 cell, S4 + 1, t-s3m6, 2048x4096 band 4 creep cell (dword 36 = 2, 1 page left), one repeat | counts at the end-of-render and decision passes: 2, 1, 1, 1, 2, 1, 1; `sa8 & 0x380` `0x180`, 0, 0, `0x180`, 0, `0x180`, 0 | HELD OUT (direct counts); controls b5, b6 |

About 97 jobs: 2048-class 9 s, 4096-class and r-b 15 to 25 s, six stage starts: 30 to 35
minutes; plan for 45. Order: health, r-a0, r-m, r-n, r-v, r-b, then firmware load, health, r-k.

Details:
- **r-n cells come from the model, the calibration only checks it.** If a calibration's steps
  are off the frozen brackets, H-STEPMODEL is refuted at that target and its cells are re-picked
  from the calibration by the frozen burst-end rule (then they test H-PHASE only; the scorer
  labels them so). Sizes: the builder confirms offline that the tool and the fork accept them
  (mock argv twin against r5's commands); a refused size is replaced from a frozen spare list
  (1536x1024, 1024x1024), never by hand.
- **r-v** needs `probe --tri pixel --vertices 1500 --vtx-coords N` to render: the builder checks
  in sgx-sim / the tool's dry path; the first job is a premise (triangle exact in the health
  sense, dump shows L above 67). If it fails the stage is skipped, nothing else depends on it.
- **r-k** `oomring2`: `oomring` plus `ldr` of `0x0724` and `0x072c` (read-only) into each rung.
  No `str`, no sa write. The builder runs the landed `tools/fwtask` verifier and the host build
  of the rgn4 fork's verifier (as `tests/test_oomring.py`); if either refuses the two `ldr`,
  r-k runs r5's `oomring` unchanged (bits only) and the count clauses are "cannot tell". No
  kernel build in any case. The band 4 creep cell (dword 36 = 2 above 1 page left, two partial
  renders) is the first cell with the saved count above the count read: `sa8 & 0x380` = 0
  pins the `isub16` operand order on the hardware (E864 left it [infer]). The builder confirms
  from the kept c5b-cal that the cell has two partial renders, else takes 3072x3072's.

Controls that can fail: r-a0's seven (new laptop paths, same module); every calibration's
brackets; scene checks from the data (1500-vertex rows show S2 and S3 of their target, r-b rows
stay at one global page); r-b's four g-qf counts and HU1's U per scene (a U off HU1 voids the
scene); r-k's b5 raising and b6 silent under the task; r-v's dump premise.

Stop conditions: any r-a0 control off, capture not whole, or thr0 read back not P - `0x22`:
stop before r-m. Any BIF fault, -110, watchdog or failed health: stop the session. r-k: one EDM
stall is reset once, a second ends the stage. Free space below 200 MB: rc 13, job not run.

Dry runs before the freeze (round 4's and 5's slips): the scorer replays r5-dpm's kept `out/a2`
as if it were r6 output and must reproduce E860 to E864's tables, with a2b-cal-4x2 now held
under H-IV; a planted directory with a g-qf timeline in a 1500-vertex control must FAIL; one
file-name function shared by runner and scorer; the mock world reproduces a full work
filesystem (rc 13) and has no wall-clock margin under 1 s anywhere (r5-events' 16 ms); the mock
is run under load once (`yes > /dev/null` x 8) before the freeze.

## 5. What a result would change in landed text

- F1: appended note on E861 (the calibration's bracket holds the frozen `0x97`; the gate
  stands as run, the three targets stay "read"). No claim contradicted.
- F2, F5, r-n, r-v: new records; Q210's line loses "what sets the page counts S_k"; 3d.md 6.4
  gains the object-page rule [HW]. E852's table unchanged.
- F4, r-m: new records; Q210 loses "the margin"; E862's "what sets the margin" answered by an
  appended note; R-5's note "why the hardware frees one page below C and two above" [open] is
  answered in the Q210 note (data-private note unchanged).
- F8: Q210 loses "why E802's scene holds one global page"; note on E802.
- F6, r-k: Q210 loses "why a page is pending only after a grow"; E864 gains an appended note
  if the operand-order cell reads 0.
- F7, r-b: Q211's count clause answered for one-triangle scenes if held out; appended notes on
  E854 (its rule is the replay's average) and E863; `dpm.rs` takes the replay and refuses
  scenes of more than one object until F9 says more (sim in sync), vectors from the kept cells.
- Still open after a full success: the cause of the creep pages in closed form, the count for
  many-object scenes (F9 is exploratory), multi-kick scenes (s438), Q211's U clause for wide
  scenes.

## 6. User decisions

1. **Offline stage F1 to F9 before any freeze.**
   (a) Recommended: run it all first, one builder, fold as records and notes before the session
   is frozen, so predictions cite landed text (as R5-1).
   (b) F1, F4, F7 only (the three seeds as written), the models F2, F3, F5 later.
   (c) Fold with the session.
2. **A2b.**
   (a) Recommended: close offline by F1 (note on E861), no rerun; the bracket rule goes into
   r6's reader and scorer.
   (b) Also rerun the six A2b rows under the bracket rule (replicates, not held out; +1.5 min).
3. **Session scope.**
   (a) Recommended: all six stages (about 97 jobs, 30 to 35 minutes); a model that failed its
   kept held-out set in the offline stage keeps only its calibration rows.
   (b) Q210 only: r-a0, r-m, r-n, r-k (51 jobs, about 15 minutes).
   (c) Seeds only: r-a0, r-m, r-b (62 jobs).
4. **The cause of the bursts (stage r-v, `--vtx-coords`).**
   (a) Recommended: run it; it is the one row set that separates H-BURST-PAGE from
   H-BURST-CAP and costs 6 jobs.
   (b) Decide from F3's stream words alone and skip the rows.
5. **Counts at the firmware's passes (stage r-k, `oomring2` with two read-only `ldr`).**
   (a) Recommended: build it, run it last; if a verifier refuses the `ldr`, fall back to r5's
   `oomring` and never to a kernel build.
   (b) r5's `oomring` unchanged (bits only). (c) Skip r-k.
6. **Q211 rows (stage r-b).**
   (a) Recommended: 4 new scenes, 8 cells each, count and run peaks frozen from the replay.
   (b) 2 scenes (22 jobs). (c) None: H-REPLAY stays FIT plus kept run peaks.
7. **Laptop.**
   (a) Recommended: run on the rgn4 boot as it stands, no reboot, before any boot another area
   needs; if the laptop is found on stock Arch, stop and ask (the pins name 99CD90DA).
   (b) Share the render4x tail-room boot: r-a0 is then the premise on the new module and the
   session runs after that area's own stages.
8. **Sim and vectors.**
   (a) Recommended: in the fold, the replay in `dpm.rs` for one-object scenes and the phase
   rule for the pages left, each refusing what was not measured; vectors from kept cells.
   (b) Vectors only. (c) Later.
