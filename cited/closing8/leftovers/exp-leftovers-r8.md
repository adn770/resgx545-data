# Round 8, round 7's leftovers (decision R8-8): plan

Planner output, 2026-11-13. Offline and read-only: no laptop, no SSH, no cachix, no commit, no
repo edit, the clean-room guard not run. Everything written is in
`/Users/jtorra/src/scratch/resgx545/closing8/leftovers/`. Read against the integration branch
r7-merge (`closing7/merge/wt`, d97c473, records to E921) and resgx545-data d3afd4351.

Scope (DECISIONS-R8.md R8-8): Q210, Q211, Q283, Q178, Q260, Q139, the sim items of Q293, Q086 and
Q139, and Q003's -110 rate offline only. Safe-class rows only: no held reset, no planned fault, no
`expectfault` row, `#limit 0` in every table. Two laptop sessions and one offline package.

## 0. What the planning already decided offline (run here, scripts beside this file)

Three readings were run while planning. Each names its status; none is a landed record yet.

**P1. Q139, the write order, on images never dumped [SEMI held out].** `q139_o1_predict.py`
replays R7-BLK's slot rule (E907, `render/closing-r7-rp/fold/q139_fit.py`, imported from its
published copy) under five write orders for every job of `ta/mtile-fields` and
`ta/mtile-fields-risky` that r7-rp did not re-run with a dump, reading `cases.tsv` only. Its
output was hashed (`q139_o1_pred.sha256`, 4dffdffe...) before `q139_o1_score.py` opened any image
(E877's loader). Of 290 predicted jobs 140 kept a whole image (49 of them wrong):

| write order | all 140 jobs | 49 wrong images |
|---|---|---|
| row by row (R7-BLK as frozen in E907) | 134 | 43 |
| by 4 x 4 tile block, block rows across the target | 136 | 45 |
| macrotile by macrotile | 107 | 16 |
| tile-row pairs | 134 | 43 |

Block order is exact where row order misses: 256 x 256 stride 1 (93 wrong tiles) and stride 2
(90), neither ever dumped. Four jobs miss under every order and are a new residue: 256 x 256
`m1-B2-10` (28 wrong, 32 predicted) and `m1-B2-11` (30, 32), 640 x 480 `m1-B1-23` (286, 288), 1280
x 720 `m2-B3p1` (52, 40): bounds that are not multiples of 4 in three of them [infer]. SEMI, not
held out: the block order was read from r7-rp's 21 dumps (stride 4 among them), and E877's score
output had printed these jobs' wrong-tile counts, though no tile map of them was used. Post hoc
(`q139_o3_rivals.py`, after the score was read): blocks column by column, macrotile then block,
macrotile row then block, and block rows bottom up each fail 256 x 256 strides 1, 2 and 4.
Refuted by: any kept image whose wrong set the block order misses and row order gives (none).
Safety reading of the same datasets: at 256 x 256 strides 0 to 31 drew (wrong tiles, no fault) and
33 and above failed; at 640 x 480 strides 4 to 63 drew, 0, 1 and 65 and above failed.

**P2. Q178, TEXTYPE 5 reads one bit per eight texels [post hoc fit].** `q178_o1_dw8.py` scans "the
pixel is 0x0000ffff iff bit B of texture dword floor(t / K) is set, t = (y mod h) w + (x mod w)"
over K 1 to 64 and B 0 to 31 on E911's six kept rows (8 x 8, 16 x 16, 32 x 32, 64 x 64, and 16 x
16 with the first 112 dwords stored 0 and 0xffffffff; 2048 pixels each). Exact on all six: (K 8,
bit 0) and (K 4, bit 1), which are one function of the map fill (dword i = 0xD0000000 | i). K 1
bit 3 fits the four plain rows and fails both memory rows (1472 of 2048), so the texel is not one
dword. That explains E911's row alternation at 8 x 8 and the 16-column step at 16 to 64. A fit on
rows already read: session L2 freezes it (H-DW8) against H-DW4B1 on rows that part them.

**P3. Q210, why `--vtx-coords 8` did not repeat [source reading, infer].**
`userspace/libsgxfive/include/sgxfive_tri_probe.h` says the option is "for a vtxuse program that
writes o4 on"; `src/tri_probe.c` only raises OUTSEL's vertex size, the coordsize word and the
vertex task's output rows. R6-dpm's and R7-dpm's rows ran `probe --tri pixel` with a pixel program
only, so the default vertex program never wrote o4 to o11 and the TA received whatever those
outputs held. [infer] That is why the N 8 object blocks, steps and need changed between sessions
(E917) while the scene of 4 pairs happened to repeat. Refuted by: a vertex program that writes
every extra output and still gives other blocks from run to run (L1 stage `v`, a control that can
fail). `probes/tsp/templates/vtx_coord4.s` is such a program for 4 pairs.

## 1. Offline package OL (no laptop; before or beside the builds)

Each item: what it rests on, the frozen prediction, what refutes it, whether it needs hardware.

| item | question | work | rests on | status it can reach |
|---|---|---|---|---|
| OL1 | Q139 | record P1; sgx-pipe `ta`: header slots of poked macrotile words in block order | E877, E907, P1 | SEMI record, model with refusals |
| OL2 | Q086 | sgx-pipe: H-COV, a poked 4x grid completes iff it covers both axes | E886, E908 | model, 13 held-out rows as vectors |
| OL3 | Q293 (retired) | sgx-pipe: `CR_TE_AA` 0x40000000 object layout and empty image | E829, E888, E906 | model, 4 rows as vectors |
| OL4 | Q260 | E914 refusal test; E683's 101 pixels against the long-edge band | E683, E684, E914 | refusal, one offline verdict |
| OL5 | Q003 | the -110 rate: boot table, H-DONE's page counts, power | E901, E919, E920 | FIT only, no verdict |
| OL6 | Q178 | record P2 | E894, E911, P2 | post hoc record, frozen in L2 |
| OL7 | Q210, Q211 | record P3; multi-kick replay; frozen tables for L1 | E874, E875, E899, E900 | freezes for L1 |

**OL1 (Q139).** Record P1 as it stands (scripts are standard library only and import published
copies: publishable through `tools/records/scratch_cites.py`). sgx-pipe, test first: a function in
`ta.rs` giving each target tile's header slot or none for poked `CR_TE_MTILE1`, `CR_TE_MTILE2` and
stride words, block order, with the 21 r7-rp dumps (fit, replicate, held out) as slot vectors and
the 49 wrong images of P1 as wrong-set vectors. It refuses: the four residue jobs' class (a bound
that is not a multiple of 4, until L2's dumps are read), strides outside the ranges that drew, the
faulting words of E509, sizes other than 256 x 256, 512 x 384, 640 x 480, 768 x 640 and 1280 x
720. `render.rs` keeps refusing a render with poked words (the image of a tile without a header
is not modelled beyond "not drawn"). E907 leaves `crates/SIM_UNMODELLED.toml`. Refuted by: a
vector the function misses. Hardware: L2 stage `q139` holds the order out on dumps.

**OL2 (Q086).** `ta.rs`: `poked_4x_grid_covers(target, words)`, complete iff B3 + B1 tiles per axis
reach the 1x tile grid on both axes, else the 3D-side fault (requestor 256, `BIF_FAULT`
0x10000011). Vectors: E886's 9 and E908's 4 held-out rows and the bridges. Refuses contexts not
made for 4x targets, other word sets than the rule's, U2, U2Q, FX and HS, and E886's 11 unrun
rows. E908 leaves SIM_UNMODELLED. No hardware (a fault row is not safe class). The closed driver's
words over sizes stay with the capture batch.

**OL3 (Q293).** `objects.rs` and `render.rs`: with `CR_TE_AA` 0x40000000 (bit 30 without bit 29)
the TA writes each object with a zero dword before its format word (objects at dump dwords 0, 27,
54 for three renders, E906 u1), the 3D reads the bit-29-set layout and draws nothing; the twin
layout poked in draws 4096 of 4096 (u3) and 0xffffffff at dword 11 draws nothing (u4). Vectors:
r7-rp q293's four rows and E888's t7 dump head and hash. Scope refused: other sizes than 64 x 64,
more than one triangle a render, other `CR_TE_AA` words (Q142). E906 leaves SIM_UNMODELLED.

**OL4 (Q260).** (a) `isp.rs` keeps refusing a negative coordinate with a sub-grid fraction; the
test names E914 and E914 leaves SIM_UNMODELLED. (b) Frozen before the run of the script: under
half away from zero, every one of E683's 101 wrong pixels lies within 6.4e-4 pixel of an edge
line at least 250 pixels long (E914's band, `fold/zs_read.py`'s distance). Fit: none. Control that
can fail: the script reproduces E683's counts (149 cases and 288 pixels half up, 67 and 101 half
away) before it measures. Refuted by one pixel outside the band; then the rounding itself is still
open and L2's stage `zs2` reads it. Numpy only from a scratch venv, as E914's note did.

**OL5 (Q003, the -110 rate; offline only by decision).** All data is already read, so this is a
FIT with no verdict. (a) One row per boot after a 0x90004 fault over the kept corpus (E901's 147)
and r7-faults (29): size, fault page, list, hold time, time from the reset to the boot, boot index
in the session, the previous boot's result, the `CR_TE_DIAG` counts and page count at the hold.
(b) The rate by size with exact binomial intervals (E919: 11 of 14 at 288 x 144, 3 of 15
elsewhere). (c) Plan step F2, never compiled: the pages a completed job allocates at each size,
H-DONE's input. (d) A null that can fail: labels permuted within sessions; a covariate "explains"
only if its log-loss beats 95 % of the permutations on the corpus AND on r7-faults scored
separately (SEMI). (e) Power: how many held resets a future session needs to separate two rates,
written as a note for the next held-class round. No row is proposed here.

**OL6 (Q178).** Record P2 as post hoc; correct nothing landed (E911's "which bits of which texels"
is what it reads). sgx-sim keeps refusing type 5 until L2's `tx5`.

**OL7 (Q210, Q211 prep).** (a) Record P3 with a dump check that can fail: in the published R6-dpm
and R7-dpm N 8 dumps the object blocks' attribute dwords differ between the two runs, and at N 4
they do not. (b) Multi-kick replay: extend E875's replay in E899's order with G4's reading (a
later kick walks again and fills the pages its macrotiles have open), fit on the kept multi-kick
dumps and cells of s1 `g-e2a`, `g-e2b` and r1-pixgeo `g-u1` (page needs and partial-render
counts), hash it. If it does not reproduce the kept cells, L1's stage `k` runs labelled explore.
(c) The frozen tables L1 needs, each hashed: A_6 and S_k per target from `g3_span.py` and
`f5lib.py`; F9's counts and run peaks; HU1's U for the shapes of stage `u`.

## 2. Session L1 `r8-ldpm` (Q210, Q211): 161 jobs, about 28 min

Boot: the current test module 37EC97AB (fork 664fd0d0), before the R8-5 one-shot boot. R7-dpm's
set B ran DPM cells on it with both controls held (E918). Tool t4 (`sgxfive-test-rgn4`,
e6951558...), `regtimeline` with R5-dpm's 16 registers, laptop prefix `r8d`. No own task, no poke,
no kernel change. Every job is a plain job; R7's derived cells (the runner's re-pick) are gone:
each stage runs a fixed window of thr0 cells and the frozen scorer aligns it on the calibration's
own steps (R7's rule S_k read + (cell - S_k model)), a cell outside the window reading "cannot
tell".

| stage | jobs | what | label |
|---|---|---|---|
| `a0` (gate) | 6 | R7's s-a0 rows: two 2048 x 2048 calibrations, c4-b5, c4-b6, t-s3m6, g-qf | control |
| `sp` | 20 | steps pinned by the abort's global page count | held out |
| `m6` | 69 | band 6 margin: two mapped targets, seven held-out targets | fit, held out |
| `v` | 14 | larger objects with written outputs | control, explore |
| `f9` | 18 | many-object partial-render counts (1500 vertices) | held out |
| `k` | 25 | multi-kick scenes: need and counts | held out or explore (OL7 b) |
| `u` | 9 | the U clause on other shapes | held out |

**`a0`.** As R7's s-a0, each row with `reads:` and its kept values (29 control rows held on
41E2F5C7, E915; c4-b5 and c4-b6 on 37EC97AB, E918). A control off or without a reading stops the
session (the kit's gate and rc 25).

**`sp` (2048x3072 S6, 2048x4096 S3).** A sampled step is a bracket; a cell is exact: the host's
global page count at the first abort is 1 + the steps below thr0 (kept: thr0 0xe8 = S4 reads 3,
0xe9 reads 4, E918). Controls (2): those two cells at 2048 x 2048, `reads:gps_abort`. Held out:
2048x3072 thr0 0x232 to 0x236 and its calibration three times (8); 2048x4096 thr0 0x125 to 0x12e
(10; no calibration completes there). Frozen: S6 = 0x234 (R7's one-sample bracket) against E874's
model 0x233; S3 = 0x12c (the kept creep cells' reading) against the model 0x129. One cell flips
the count: that cell minus one is the step. Stop: a control off stops the stage.

**`m6` (band 6).** H-SPAN failed at A_6 of 3072x3072 and 2560x2560 and held at 2048x2048 (E915).
Fit (mapping, with `--dump-render`): 3072x3072 thr0 0x3ce to 0x3d8 (11) and 2560x2560 0x2b0 to
0x2b5 (6), up to S7 - 1: where one page is first left, and the last block tiled at the abort.
Controls (2): 2048x2048 0x1c2 leaves 2, 0x1c3 leaves 1 (kept twice). Held out: a calibration and
A_6 - 1 to A_6 + 3 at seven targets (42), plus calibrations of the two mapped targets (2), band 7
of 2560x2560 (4, explore) and band 4 of 3072x3072 (2, explore). Frozen at the A_6 cell (pages
left):

| target class | targets | H-SPAN | H-BIG6 | H-ANY6 |
|---|---|---|---|---|
| both sides at most 2048 | 1536x1536, 1024x1024 | 1 | 1 | 1 |
| one side above 2048 | 4096x2048, 3072x2048, 2048x3072 | 1 | 1 | 2 |
| both sides above 2048 | 2560x3072, 3072x2560 (new) | 1 | 2 | 2 |
| replicates of E915's misses | 3072x3072, 2560x2560 | 1 | 2 | 2 |

H-BIG6 and H-ANY6 are post hoc readings of two targets [infer], frozen as rivals; a fourth,
H-6LATE (2 everywhere but 2048x2048), is tallied. A_6 per target comes from OL7 c. Stop: a
calibration whose steps leave the model by more than the window voids its target ("cannot tell"),
the stage goes on; any fault or hang stops it.

**`v` (larger objects).** Control (1): R7's plain N 4 calibration, its 12 steps and need 538
(`reads:` steps, need). N 8 with a vertex program writing o4 to o11 (the builder's `vtx_coord8.s`,
after `vtx_coord4.s`), three times with dumps (3); N 4 with `vtx_coord4.s` twice (2); plain N 8
twice (2, explore). Frozen: H-DET, the three written N 8 runs give the same steps and the same
block sizes; refuted by one differing run, which also refutes P3. H-CUM (E900's replay at the
dump's own block size, computed in the frozen scorer from the same job's dump) is tallied as a
rival of no rule: explore. Six cells at written N 4 around its S4 and S5 (the margin, explore).
The verdict of this stage is the determinism; the step rule is fitted at the fold on its dumps.

**`f9` (many objects).** E874's F9 gave the partial-render count of the 1500-vertex scene at 43
and 45 cells, labelled exploratory, nearly all with one partial render. Held out with counts of 2
to 8: 1536x1536 and 1024x1024 at thr0 0x24, 0x30, 0x48, 0x60, 0x90, 3072x2048 at 0x60, 0x90,
0xc0, 0x120, 0x1a0, each target with its calibration (control: steps and need as replayed, 314,
153, 773). Frozen: F9's count and run peaks (OL7 c); rivals E625's formula and E854's d = 7/4 and
d = 1. Lesson of E916: a first run no sample fell in reads "cannot tell", not FAILED.

**`k` (several kicks).** `tri -n K --geometry 1 .. --geometry K-1 --move i:DX,DY`, K 2, 3, 4 at
2048x2048 and K 2, 4 at 4096x4096: a calibration at P 0x422 (the 2048 ones dumped) and four thr0
cells each. Frozen: U = HU1 over the scene's triangles (a region counted once), the count and run
peaks from OL7 b's replay; rival: the one-kick replay of the union. Gated by `a0`'s g-qf row (the
one-triangle count), no
row of its own.

**`u` (other shapes).** One triangle by `--tri-unit 12 --tri-v`, calibrations at P 0x422: the
full-target triangle at 1024x768 and 2048x2048, a thin diagonal sliver and a 20-pixel triangle at
2048x2048, a 40-pixel-high triangle across 4096x2048, three more at the builder's choice where the
rivals part most. Frozen: U = HU1 (`render/closing-r5-dpm/gen/hu1.py`, pinned); rival H-BBOX (a
stream for every region of the bounding box). Control: s22's calibration again. Every shape's U
under both rivals stays below 0x3f0.

Stop budget of L1: no fault planned; any fault, hang, -110 or failed health stops the session; a
gate failure at `a0` stops it before `sp`. `min_free_mb` 600 (dumps of up to 4.3 MB a job).

**Kit fit.** Plain jobs, one gate, no held recovery, no stepped cell. Two points need the round's
tooling agent before the build (builder notes 1 and 2): the DPM cells of `probe` end rc 3 with
"scene overflowed", which the kit's classifier calls a failure, and the tool runs under
`regtimeline`.

## 3. Session L2 `r8-lgeo` (Q283, Q178, Q260, Q139): 246 jobs, about 30 min

Boot: the same, 37EC97AB, before the R8-5 boot. Tool t4, prefix `r8l`. Order: `tx3`, `tx4`, `tx5`,
`zs2`, `q139` (the poked rows last).

| stage | jobs | what | label |
|---|---|---|---|
| `tx3` | 10 | types 3 and 1 below 8 wide | control, held out |
| `tx4` | 23 | type 4's 32 x 32 blocks past the first two; widths 24 and 40 | held out, soft |
| `tx5` | 28 | type 5: which dword, which bit | held out, explore |
| `zs2` | 165 | negative ties at other grid points; long edges; the transposed target | held out |
| `q139` | 20 | the write order at new strides, dumps of the residue | control, fit, held out |

**`tx3`.** E725's map fill. Controls (3, kept images, `reads:` the hash): type 3 at 32 x 16
(E725), type 3 at 4 x 16 (E910, stride 8), type 1 at 4 x 16 (E910, stride 4). Held out: type 3 at
2 x 16, 4 x 8, 4 x 32, 2 x 8, 1 x 16; type 1 at 2 x 16 and 1 x 16. Frozen: H-MIN8, type 3 reads
rows max(8, w) dwords apart; rivals H-2W (2 w: parts at 2 and 1 wide) and RASTERW; type 1
RASTERW.

**`tx4`.** The generator's map axis already takes an offset (`texbuild.py` `axis_code`, the `or`
of high bits), so the 64 x 32 window reads any part of a texture. Controls (2): type 4 at 64 x 32
and 4 x 16 (E910's images). Held out: 64 x 64 (2 windows), 128 x 64 (4), 128 x 128 (8), 256 x 32
(4). Frozen: H-BLKROW, block index (y div 32) ceil(w / 32) + (x div 32); rivals H-BLKCOL
(columns first) and H-BLKZ (the two block coordinates interleaved); 128 x 64 parts all three.
Widths that are not powers of two (3 rows, `soft`): type 3 at 24 x 8 and 40 x 8 through the
generator's linear axis, with type 3 at 32 x 16 through the same axis as their control (it must
equal the map image, or the two rows are void).

**`tx5`.** Frozen: H-DW8 (P2) against H-DW4B1 (bit 1 of dword floor(t / 4)). Controls (3, kept
images): plain 8 x 8, plain 16 x 16, 16 x 16 zeroed. Held out at 8 x 8, all 64 dwords stored V:
0x1, 0x2, 0xfffffffe, 0xfffffffd, 0x4, 0x8, 0x10000, 0x80000000 (H-DW8: lit only for 0x1 and
0xfffffffd; H-DW4B1: only for 0x2 and 0xfffffffe); one dword j set to 0xffffffff among zeros, j 0,
1, 3, 7 (H-DW8 lights texels 8 j to 8 j + 7, H-DW4B1 4 j to 4 j + 3). At 16 x 16: j 0, 5, 31 and
V 0x1, 0x2. Plain 32 x 8, 8 x 32, 16 x 8 and 64 x 64 at window offset y 32 (the raster index).
Four rows with the format and filter words changed, `soft`, explore.

**`zs2`.** 512 x 256 and 256 x 512, vertices in 1/4096 pixel, five steps (d -2 to 2) across each
1/512 tie. Controls (5, kept hashes): E681's and E683's cases and three steps of R7's -0.5 x
sweep. (b) Ties at other grid points, edge aimed 1 pixel away: -1/256, -1.25, -17.75 and -200.5
(x) or -100.5 (y), both axes, 40 rows. Frozen: half away from zero (the image changes one step
after the tie); rival half up. (c) Long edges at -64.5 and +64.5, both axes, aimed 1, 4, 100 and
200 or 300 pixels away, 80 rows at 512 x 256; the 100 and 200 aims again on 256 x 512 with the
scene transposed, 40 rows. Frozen: the step table as E914's (d = 1 negative, d = 0 positive);
H-SHORT, the image is HA's (HU's for positive) exactly at aims 1 and 4; H-BAND, at the long aims
it differs only in pixels within 6.4e-4 pixel of an edge over 250 pixels long. Rivals for which
sweeps miss: H-YAXIS (the y sweeps, on both targets) against H-GEOM (the misses follow the
transposed scene to x). No fault expected (E914: 230 jobs clean).

**`q139`.** The datasets' own command with `--keep-going --dump-render`, one `--kpoke-render` of
the stride or a macrotile word, as r7-rp. Controls (3, `reads:` slot count and base): the 256 x
256 and 640 x 480 baselines and stride 4 at 256 x 256 (its kept wrong set, 84 tiles). Fit with
dumps (2): 256 x 256 strides 1 and 2 (images kept, P1). Held out (11), every stride inside the
range that drew: 256 x 256 strides 3, 5, 6, 7 (row order parts in 40, 24, 16 and 8 tiles), 12 and
20 (column and macrotile orders part in 40 and 24); 640 x 480 strides 5, 6, 7 (48, 32, 16), 8 and
12. Frozen: block order, the wrong-tile set and every header slot (`q139_o2_candidates.out`,
`q139_o3_rivals.out`); rivals row order, blocks by column, macrotile then block. Residue (4, fit,
dumps only): the four jobs of P1 that no order gives; each drew without a fault in its dataset.
640 x 480 strides below 4 are not run (0 and 1 failed there).

Stop budget of L2: no fault planned; any fault or hang stops the stage and the session; the second
soft failure in a row stops `tx4` or `tx5`. `min_free_mb` 400 (640 x 480 and 1280 x 720 dumps).

**Kit fit.** Entirely: plain jobs, `after`, `expectdiff`, `soft`, the session's own `needhash` and
`needdump` words, `--kpoke-render` (the kit forbids `--kpoke`, not this option) with `kpoke` in
`debugfs`.

## 4. Order, time, boot

1. OL7 before L1's freeze (its tables are pins); OL1 to OL6 in parallel with the builds.
2. L2 then L1, or either alone, on 37EC97AB, after r8-geo and before the R8-5 one-shot boot. About
   30 and 28 minutes, 407 jobs.
3. If a session slips past the R8-5 boot, it is scaffolded again with that module's srcversion (a
   freeze is never rewritten); nothing in either session needs the round 8 kernel, and `a0` and
   the kept-hash controls check the module either way.

## 5. Builder notes

1. Kit, before L1 is built (tooling agent, test first in `tools/closing/test_kit.py`): a row word
   that makes rc 3 with "scene overflowed" in the output a reading, as R7-dpm's runner did;
   without it every partial-render cell of `probe` stops its stage (rc 4).
2. L1 runs the tool under `regtimeline` as a kit tool (`rt`, args `0 LEAD REGS -- "$HOME/
   sgxfive-test-rgn4" ...`); the mock's `answer` must emit a timeline for it. If the guard or the
   mock refuses a second binary in the args, report it: do not hand-roll a wrapper.
3. `render_pb_pages` is a declared knob (`dbg:render_pb_pages=V`), every cell's P = thr0 + 0x22
   listed in session.toml by the generator; `outdir_opts` `--dump-render`, `--words`.
4. No derived cells: windows fixed at the freeze, alignment in the scorer, "cannot tell" outside
   the window. No control without a reading (R6's slip): a calibration at P 0x422 declares only
   steps, need and knob.
5. `v` needs `vtx_coord8.s` (o4 to o11 written, the copies of `--vertices 1500` still placed):
   assemble it, pin source and binary, and check in the mock that the plain N 4 control is
   untouched.
6. `tx4`: check that the tool's tag fill covers 16384 dwords (the scratch is 64 KiB) before
   freezing 128 x 128; if it stops at 2048 dwords, drop to the sizes it covers or bind a tool
   variant by source. `tx5`: the stored words go through the generator's `inject` (E911 stored
   112 dwords); 8 x 8 needs 64.
7. `q139`: the held-out dumps are scored by the frozen scorer in the session (the order is frozen
   now), not after a fold-time fit; the four residue rows are fit rows and score nothing.
8. Pins: `render/closing-r7-rp/fold/q139_fit.py`, `cited/closing6/fold-misc/q139/q139_model.py`,
   `cited/closing7/b/offline/{g2_replay64,g3_span,olib}.py`, `cited/closing6/dpm/offline/f5lib.py`,
   `render/closing-r5-dpm/gen/hu1.py`, r7-geo's `gen/texbuild.py` and templates, and this
   directory's scripts once published.
9. Replay vectors: `q139` and OL1 feed `ta` slot tables (replay: the new `ta.rs` test); `tx3` to
   `tx5` feed sgx-sim `tex.rs` tables; `sp`, `m6`, `f9` feed `dpm.rs`; `zs2`, `k`, `u`, `v`:
   `refused` until a rule holds.
10. Scripts here use the repo `.venv` interpreter with `-I -B` and the standard library only;
    outputs are beside them (`*.out`, `q139_o1_pred.json` and its sha256).

## 6. Summary

1. Path: `/Users/jtorra/src/scratch/resgx545/closing8/leftovers/exp-leftovers-r8.md`.
2. Offline, run while planning: Q139's block write order gives 136 of 140 kept images never
   dumped (row order 134), strides 1 and 2 parting them; four residue jobs found.
3. Offline: TEXTYPE 5 is exact on E911's six rows as bit 0 of dword floor(texel / 8) (post hoc).
4. Offline: `--vtx-coords` leaves the extra vertex outputs unwritten, which explains E917.
5. Offline package OL1 to OL7: sim models for Q139, Q086, Q293, E914's refusal, Q003's rate as a
   fit, multi-kick replay and L1's frozen tables.
6. L1 `r8-ldpm`: 161 jobs, about 28 min: step pins, band 6 with three frozen rivals, written
   larger objects, many-object and multi-kick counts, the U clause.
7. L2 `r8-lgeo`: 246 jobs, about 30 min: types 3, 4 and 5, rounding ties and long edges, Q139
   strides with dumps.
8. Both on the current test module 37EC97AB, before the R8-5 boot; neither needs the round 8
   kernel.
9. Safe class throughout: no held reset, no planned fault, `#limit 0`; Q003 has no row.
10. Kit: L2 fits as is; L1 needs one kit word (rc 3 "scene overflowed") and `regtimeline` as a
    tool, both for the tooling agent before the build.
