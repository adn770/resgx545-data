# Round 4 proposal, area PIXEL: Q082, Q276, Q230, Q210/Q273, sim items 2 and 4, audit A1

Fable, 2026-11-11. Planning only: nothing ran on the laptop, no repo was edited, no guard was run.
Scratch scripts and outputs are in `closing4/pixel/` (`burstdump.py`, `qt_slopes.py`/`.out`,
`rule_ta.txt` + `ta_rule.py` + `ta_rule_qv.out`, `ta_other.py`/`.out`, `rule_px.txt` +
`px_rule.py`/`.out`, `fill_d6.py`/`.out`, `rhw_frac.py`/`.out`). They read the published sessions
`resgx545-data/render/closing-r3-pixel`, `closing-r3-geo` and `platform/event-*` only.

Labels: [data] computed from kept files, [source] read in a landed file, [infer] a reading.
FIT = data a rule was read from; SEMI = a rule written to a file (sha256 beside it) before the
jobs it is scored on were opened, but after other jobs of the same stage were seen: stronger than
FIT, not a frozen held-out run; HELD OUT = a row a frozen rule predicts before it runs.

Based on `closing3/pixel/exp-pixel-r3.md`, the sessions `closing3/r3-pixel` and `r3k-pixel`,
`closing3/overnight/audit-scorers`, E804 to E808, E795 to E803, E826, E829 and the plan log.

## 0. What the existing records and session outputs already decide

### 0.1 Bit 7: the vertex loop sets it when the TA's clock run passes about 130 us [data, SEMI]

In a regtimeline of a `--tri vtxuse` job, `CR_CLKGATESTATUS` (0x0008) reads 0x000ccff8 while the
TA works on the vertices (0xccfa0 before and after; [infer] for the name "TA clocks"). Rule TA-125
(`rule_ta.txt`, written after the dumps of 8 q-v jobs, before the other 66 were measured): L = the
longest run of 0xccff8; bit 7 set iff L >= 125 us, edge 120 to 131.

- All 74 run jobs of q-v (E807): every clear job has L <= 129.1 us, every set job L >= 129.8 us,
  over four bodies (4, 8, 16 instructions; 8 in two orders) and 3, 12 and 48 vertices. No job is
  on the wrong side; 8 lie in the edge band (`ta_rule_qv.out`).
- In the 39 set jobs bit 7 first shows 123.2 to 133.8 us after that run begins (median 126). My
  written tolerance (118 to 132) missed two of them by 0.3 and 1.8 us: the tolerance was one
  sample period (4.6 us) too tight, the placement is not affected.
- This is the frozen HV-TIME of round 3 measured on the right quantity. The scorer used the whole
  burst B (TA + 3D + host noise) and got 33 of 39 rows; its lines were not in the verdict or in
  E807's claim. With L the four "refuted" count hypotheses are explained: L per iteration is 0.118
  us at 3 vertices, 0.22 at 12 and 0.30 at 48 (16 times the vertices, 2.6 times the time).
- It is not the TA phase's length alone [data]: the ten 1500-vertex jobs of R3-geo g-c4 (several
  aborts, milliseconds of TA) all end with STATUS2 0x400 (`closing-r3-geo/out/g-c4`, `reg 0x0118`
  in the after-reads; 0x0008 was not sampled there). [infer] Bit 7 latches when the TA makes no
  progress for about 125 to 130 us; a vertex loop is one such stall.
- E764 to E766 measured 121.1 to 124.1 us between a fault word and bit 6 or 7. [infer] One
  timeout of about 125 us serves both bits and both causes (a fault stalls the unit).
- The older timelines (`ta_other.out`, 37 jobs of platform/event-timelines and event-trigger)
  hold no clear job with a long run (stock TA runs are 0 to 23 us). They also show the rule's
  limit: E357's held TA hang has bit 7 set with a 0xccff8 run of 8 us (its clocks read 0x78
  through the hang), so L measures a vertex loop, not every stalled TA.

Refuted by: a clear vertex-loop job with L > 136 us or a set one with L < 120. Needs a frozen
held-out run to count as a result (stage q4-v, 3.1): new bodies and one new vertex count.

### 0.2 Bit 6 in fills: the tile-time rule holds in 187 of 187 fills without a load [data]

Round 3's H-WD (a tile's time tau = (B - 60.2) / 4 reaches about 122 us) was refuted only by the
load body. Scored again with one constant (T = 125 us, edge 118 to 132; `rule_px.txt`, written
after R3-pixel's fills were read and before E431's and E357's timelines were scored: FIT on the
first, SEMI on the second):

- R3-pixel q-f0, q-f1a, q-f1b: 106 fills, 92 on the predicted side, 14 in the edge band, 0 misses.
- platform/event-fine, event-steps, event-trigger (E431, E357): 81 fills, 67 and 14, 0 misses.
- The latch-time part of the same file (the fill as five segments, tile 1 split 3/16 + 13/16;
  d6 = time from the first 0xfffa7/0xfffa4 sample to the bit) fits R3-pixel (62 of 68 set jobs
  within 15 us: d6 = 121 to 128 us in all 18 jobs with tau >= 667 us, tau + T just above the
  threshold) and FAILS on the older data (30 of 48). By its own rule it is refuted as written and
  is not offered as knowledge. What stands [data]: in R3-pixel's long fills the bit shows 121 to
  128 us after the 3D's clocks come on, the same delay as bit 7's.

### 0.3 Bit 6 in triangles: the N = 56 point is the edge at every size [data, FIT]

`qt_slopes.out` fits B = a + s N per size of q-t (E806). The slope a tile is nearly the fill's
(2.26 us a pass) wherever the tile is full, and is not proportional to the pixels:

| size | tiles | slope a tile (us / N) | tile time at last clear, first set (us) |
|---|---|---|---|
| 4x4 | 1 | 0.72 | 40 (N 56), 159 (N 220) |
| 8x8 | 1 | 1.65 | 92 (56), 181 (110) |
| 16x16 | 1 | 2.50 | 140 (56), 275 (110) |
| 32x16 | 1 | 2.55 | 135 (53), 143 (56) |
| 32x32 | 2 | 2.38 | 126 (53), 133 (56) |
| 64x32 | 4 | 2.50 | 140 (56), 275 (110) |
| 128x128 | 32 | 2.29 | 121 (53), 128 (56) |
| 256x256 | 128 | 2.27 | 127 (56), 250 (110) |

- Every bracket contains a tile time of 120 to 160 us. E806's "56 or 110 by size, no order in the
  size" is what a threshold near N = 55 to 60 gives on a ladder whose next point is 110: at
  128x128 the bit showed 4026 us into the job (one late tile passed), at 64x32 no tile did.
- The frozen H-TILE of round 3 failed because it scaled by pixels (8x8 at 440 or 880); by the
  measured slope 8x8 predicts 73 to 97 and 4x4 166 to 222, inside their brackets.
- The bridge "failure" (64x32 triangle clear at 56, the fill set) is the same edge: the fill's
  own edge is 54 (2 of 3, E431).
- The default 64x64 triangle (1062 pixels, clear to 110): slope 7.2 us a pass over its tiles;
  the tile count is not known, so no prediction.
- Latch time [data]: in the 23 set jobs at N >= 440 the bit showed 245 to 257 us into the burst,
  whatever the size. At N = 110 and 220 it showed later at 8x8, 64x32, 128x128 and 256x256 (295
  to 304, then 341 to 351 us) and at 16x16 at 110 (329), and at 245 to 255 at 32x16, 32x32 and
  4x4. [infer] A first piece of work of about 0.43 us a pass (0.72 at 16x16) ends before the
  timeout at small N and restarts the timer. Post hoc, the same kind of model that failed in 0.2:
  it is a held-out row of stage q4-t, not knowledge.

So the reading to test is **H-SEG**: bit 6 latches when the pixel side makes no progress for T
of about 125 us; progress is the end of a piece of work that is at most a tile. Refuted by a
size that stays clear at a tile time above 170 us (N = 72 at 16x16 or 64x32).

### 0.4 The load body: the "busy time summed" form of H-WD-busy does not fit [infer]

ld8 (a load, a wait, 4 multiply-adds, counter, branch) stayed clear to N = 320 with bursts of
13.4 ms. The four ALU bodies set at about 440 to 476 instructions of an instance (N* 25.9, 31.0,
54.6, 119.1 for 16, 12, 8 and 4 instructions), so a sum of the non-waiting time would set ld8
near N = 75; it was clear at 4 times that. The frozen H-WD-busy only said "later than N*" and
cannot fail upward. Two readings remain: **H-YIELD** (a wait ends the piece of work: the timer
restarts at every load) and **H-LOADOFF** (a program that waits on a load never latches). Stage
q4-f separates them with an ALU loop after one load.

### 0.5 Q276, the o4 clause: both order rules are refuted, and the design could not tell more

E808: with the 5' write first and 5 last (4 configurations) and with 5 first and 5' last (4
configurations), every o4 word read was tag 5 (25 to 51 words a job, tag 5' in none). So "the
last write wins" and "the first write wins" are each contradicted by four configurations [data].
What decides is the value: the generator's tags are 5 and 13 (`gen/r3_c.py` line 18, "o4 tags: 5
(p1 true), 13 = 0xd (5')"), which differ in bit 3 only [source]. Readings that fit all 16 jobs
[infer]: V1 the path drops bit 3 of the word (13 lands as 5); V2 a word with bit 3 set does not
land; V3 the two writes combine (AND gives 5; the smaller wins). OR is refuted (it gives 13).
Tag 8 (o7) never appears in the pairs of E570 and E709 (tags 5 to 7 only), which V1 and V2 also
predict [infer]. The predicate clause cannot be read until this is known: with k = 7 the p1
write never runs, the !p1 write carries 13, and 5 was read all the same.

No offline check separates V1 to V3. Stage p4-o4 does, with tags that differ in one other bit.

### 0.6 Q210 and Q273: the landed firmware dataflow already answers "why 0x20" [source]

`doc/specs/edm_dataflow.md` (generated, E013) lists for the routine 0xb50-0xc22:
`CR_DPM_ZLS_PAGE_THRESHOLD` (0x0624, the register that reads P - 0x22) written as itself + 0x20
(line 1297); `ta3d_ctl.zls_threshold_step` (TA3D_CTL+0x098 = dword 38) written from 0x20 (line
847); `CR_DPM_TA_GLOBAL_LIST` written as (itself & 0xffff) + 0x10 | 0x10000 and its old value
saved in dword 37 (lines 844, 1301); `ta3d_ctl.abort_page_count0` and `abort_page_count1` (dwords
35 and 36) written there and tested against the high halves of `CR_DPM_PAGE_STATUS` and
`CR_DPM_GLOBAL_PAGE_STATUS` (lines 838 to 843); `CR_DPM_REQUESTING` bit 0 branches (line 1392).

- So the raise is the firmware's own write, in its out-of-memory routine: 0x20 is a constant of
  that routine, and E625's dwords 37 and 38 are the saved global-list threshold and the step.
  The clause "why is the raise 0x20" of Q210 is answered at the tier of E013 (static reading)
  plus E625 (the dwords). The limit C is then a branch of that routine, not a hardware compare.
- The analysis left that routine with "branch on a predicate of unknown origin 7" and "base of
  unknown structure 2" (section 6 of the spec), and dwords 35 and 36 "written from ?". The guard
  of the + 0x20 write is therefore not in the spec yet.
- Dword 36 is written in that routine at every abort [source], which is what H-last (the count
  before the LAST abort, 58 of 58, E803) needs; what value it is written from is the open part.

Next offline step (reading R-5, the route of R3-E8: landed tools, facts only, lead reviews): the
conditions of routine 0xb50-0xc22 on the path to the + 0x20 write and the source of the two
abort counts. Then a test that is held out by construction: the condition, read from the firmware,
must place the five exact flips (0x351/0x352 at 4096x4096, 0xe2/0xe3 at 2048x2048, 0x1b2, 0x1b6,
0x1e8; E774, E799, E801) and E802's scene from the registers the kept timelines of g-c4 and g-c5
hold (0x0624, 0x0628, 0x0724, 0x0728, 0x072c are sampled). Refuted by one flip on the wrong
side. No hardware unless the registers it needs were not sampled.

### 0.7 Q230, the 1/w word: no threshold in the reciprocal's fraction [data]

`rhw_frac.out`: over the 23 w with a recorded word (E754, E795, E796, E798) the fraction of the
exact 1/w in the last place does not separate "RZ" from "one ulp above": 1.0625 is RZ at 0.94,
1.59375 is above at 0.63; nor does the mantissa of w (1.375 RZ, 1.40625 above, 1.4375 RZ). So
the word is not a directed or nearest rounding of the exact quotient at any threshold; [infer] it
is an iterative or table reciprocal with an error of 0 or +1 ulp. Five "above" words carry too
few bits to fit an algorithm (E783's lesson: 4 of 257 models fit six words by chance). A table of
about 60 w is the smallest run that can fit and hold out (stage g4-rw). The depth formula stays
parked behind it: it very likely uses the same reciprocal [infer].

### 0.8 Specs that lag the records [source]

- `doc/specs/hw_spec.md` lines 326 to 334 (EVENT_STATUS2) stop at E784; E804 to E807 are not
  cited in any spec.
- `doc/specs/usse_guide.md` line 163 and `usse_isa.md` line 270 give g23 to g25 "in a fill"
  only; E808 (held out at three triangles) is in the simulator and in no spec; Q053 does not
  cite E808.
- `doc/specs/3d.md` line 1885 still files dword 36 under Q036 with E438's reading.
- E826 (BIF_CTRL bit 4 holds the fault registers clear while set; a write of the set bits to
  BIF_INT_STAT changes nothing) is cited in no spec.

### 0.9 Tool state

The laptop runs the rgn4 module (srcversion 99CD90DA) and has `~/sgxfive-test-rgn4` (sha256
e6951558..., R4's sessions) and `~/sgxfive-test-r1`. R3-pixel ran the r1 tool on module B21FDA82.
Every stage below starts with bridge controls that must reproduce R3-pixel's values.

## 1. Knowledge to write with no hardware (K items, the fold's work, tests first where code)

| item | where | what | tier |
|---|---|---|---|
| K1 | hw_spec.md EVENT_STATUS2 | E804 to E807 as measured; 0.1 to 0.4 as dated readings | HW + infer |
| K2 | Q082, notes on E805, E806, E807 | 0.1 (74 of 74), 0.2 (187 of 187), 0.3, 0.4 | data, SEMI/FIT |
| K3 | usse_guide.md, usse_isa.md, Q053 | g23, g24, g25 in a triangle's pixel task (E808) | HW |
| K4 | Q276 | order rules refuted; tags differ in bit 3; line reworded | data + source |
| K5 | Q210, 3d.md DPM section | the raise is routine 0xb50-0xc22's write; 0x20 its constant | source (E013) |
| K6 | Q273, 3d.md line 1885 | dword 36 = abort_page_count1, written at each abort; H-last | source + HW |
| K7 | Q230 | 0.7 as a dated note | data |
| K8 | hw_spec.md BIF text | E826 | HW |
| K9 | Q082 "to settle it" text | replaced by section 3 of this file once decided | - |

None contradicts a landed claim. E806's paragraph "Read after the run [infer]" says the burst
does not place the bit and there is no order in the size; K2 adds a dated note under it (a
second reading of the same data), no correction of the claim. K5 rewords Q210's question line
(the clause "why is the raise 0x20" leaves; "what the firmware's routine compares" stays).

## 2. Sim items 2 and 4 of R3-P11, and audit A1

**State.** Items 1 and 3 landed with the L2 fold (`sgx-sim/src/usse.rs` lines 4000 and 4825 on,
`sgx-pipe/src/pixel.rs` line 623, the scene tests a059cb9). Item 2: `sgx-pipe/src/events.rs`
refuses, Q082 in its OPEN list. Item 4: no closing session has vectors (`datasets/` holds none).

**Item 2, the STATUS2 latch.** sgx-pipe has no clock, so it cannot derive a duration from a
scene. What can land is a rule over measured timings, `events::status2_latch(timing)`:
- bit 6, a fill without a load: clear for a tile time below 118 us, set above 132, refused
  between; this rule was frozen in round 3 and held on five ALU ladders and on E431 (0.2), so it
  meets "only for rows that held";
- a pixel program with a load, any triangle, and bit 7: refused today. Bit 7 (0.1) and
  triangles (0.3) are post hoc: they land only after q4-v and q4-t hold.
It would change: `events.rs` (the function, Q082 stays in OPEN for the refused regions), tests
from the 187 fills. It needs: item 4d's timing vectors; a timeline reader in `tools/closing/`
(Python, standard library: burst, tile time, the 0xccff8 run; tests on kept data first) since
the scorers' copies are per session; the edge band agreed (decision 5).

**Item 4, vectors from R3-pixel.** Four parts, all offline:
- 4a direct reads (9 jobs: g23, g24, g25 at the default, full 64x64 and full 128x128 triangle)
  as scene vectors for sgx-pipe; needs the scene of each job (`--emit-scene` of the mock) and a
  mask for the pixels the premise control did not decode (0.995 and 0.996 of the pixels).
- 4b loop proofs (6 fills, 90 triangles): fills convert with `tools/usse-asm/convert_extra.py`
  as they are; the `--tri pixel` slot needs a new `init` key (the slot at code index 0x20) in
  the converter and in `sgx-sim/tests/vectors.rs`.
- 4c depth words of the 74 vertex-loop jobs (0x3f200000 + N at every vertex) as vertex vectors,
  after `vectors-usse-globals-vertex`; needs the dump decode (`pbdump first_object`) in the
  converter.
- 4d timings (B, tile time, L, t6, t7, the bit) as a data file per job, not a sim prediction;
  the input of item 2.
It would change: resgx545-data `vectors/closing/...` (about 180 files) and three or four
`datasets/vectors-closing-r3-pixel-*.toml`, `doc/specs/vectors.md`, converter and test code. It
needs: converter changes test-first, a guard pass by the lead on the new files, no hardware.

**Audit A1, `score_v.consistent`.** The record side is done (E807's claim line corrected
2026-11-11). Left alone: the scorer. A strict-overlap fix (the rule of `tools/closing/scorekit.py`:
open end = None, no slack) changes one token of the kept output, `b4v HV-INSTR consistent` to
REFUTED, in `score-q-v.txt` and `verdict.txt`; the other nine rows are unchanged
(`audit-scorers/qv_strict.out`). Unlike the three fixes of POSTRUN-FIX.md it changes a verdict
line, so `score-q-v.fixed.txt` and `verdict.fixed.txt` would differ from the as-run files. It
needs: the test first (the audit's repro as a case of `tests/test_scorers_r3.py`),
`score/score_v.as-run.py`, a new section of POSTRUN-FIX.md that says the line changes and names
E807's correction, the FROZEN.sha256 lines, the dataset manifest and FROZEN.commits recomputed
by the lead. No record changes again. With 0.1 the b4v row has a measured reason: L was 137.8
us at 1760, already past the timeout.

## 3. The smallest hardware rows (one session, R4-pixel, 158 jobs)

Common to every row, as R3-pixel: a debugfs reset, STATUS2 read before (not 0x400 stops the
stage) and after, the job under `regtimeline 0 0.3 0x0008,0x0118,0x012c` (reads only), loop proof
by MARK or depth word, a failed proof voids the job. Scorers copy `scorekit.py`. Timings come
from one reader (section 2). Stop: a hang or fault line, a job that does not return, a failed
bridge control.

### 3.1 Stage q4-v: bit 7 held out (28 jobs)

| rows | set | frozen |
|---|---|---|
| v-ctl0, v-n1; v-i880; v-i1760 | control (bridge to E807) | 0x400; clear, L 95 to 112; set |
| b12v (10 imae), 2 FIT points + 5 | HELD OUT | per job: set iff L >= 129.5, edge 122 to 136 |
| b2v (counter and branch only), 2 + 5 | HELD OUT | same |
| b8v with 24 vertices, 2 + 5 | HELD OUT | same |
| stock program, 1500 vertices at 2048x2048 (2) and 4096x4096 (1) | HELD OUT | clear |

The five points of a ladder sit at 0.80, 0.92, 1.08, 1.20 and 1.60 times N* = 127 us over the
slope of its two FIT points (run first, formula frozen). Latch time: 118 to 138 us after the
0xccff8 run begins in every set job. The last row separates H-STALL (no progress: clear, as
g-c4's ten jobs) from H-PHASE (the phase's length: set); its L is recorded, and if L is below
125 us the row is void for that. Refuted: a ladder point on the wrong side outside the edge.
Will not close: what "progress" is inside the TA.

### 3.2 Stage q4-f: the load (16 jobs)

| rows | set | frozen |
|---|---|---|
| rel b8 at 16, 53, 56, 136; ld8 at 70 | control (bridge to E804, E805) | c, c, S, S; c |
| ld0-K: one load and wait, then the b8 loop K times; K = 28, 53, 70, 110 | HELD OUT | below |
| ldo-K-M: M times (load, wait, b8 loop K times); (28,4) (28,16) (40,8) (70,1) (70,4) (110,2) (220,1) | HELD OUT | below |

| hypothesis | ld0 28, 53, 70, 110 | ldo (28,4) (28,16) (40,8) | ldo (70,1) (70,4) (110,2) (220,1) |
|---|---|---|---|
| H-YIELD (a wait restarts the timer) | c, either, S, S | c, c, c | S, S, S, S |
| H-LOADOFF (a waiting program never latches) | c, c, c, c | c, c, c | c, c, c, c |
| H-SUM (busy time of the tile summed) | c, either, S, S | S, S, S | S, S, S, S |

Two-level counters; every program checked in sgx-sim at code index 0 (MARK only when both
counters end). H-SUM is already unlikely (0.4); its rows cost three jobs. d6 is recorded with no
prediction (0.2's timing model failed).

### 3.3 Stage q4-t: triangles (54 jobs, 59 with 2x2)

`probe --tri pixel --temps 32 --tri-full`, rel b8 loop, as E806. Frozen from 0.3 (FIT).

| rows | set | frozen |
|---|---|---|
| green and N = 1 at 4x4, 8x8, 16x16, 32x16, 64x32; fill 53, 56 | control (12) | MARK; c, S |
| 8x8 at 60, 66, 72, 80, 88, 96, 104 | HELD OUT | H-SEG: 60, 66 clear; 104 set; first set 72 to 104 |
| 4x4 at 80, 110, 140, 170, 200 | HELD OUT | H-SEG: 80, 110, 140 clear; H-N: set from 80 |
| 16x16, 32x16, 64x32 at 46, 60, 66, 72 and 56 twice | HELD OUT (18) | H-SEG: 46 clear, 66 and 72 set at all three; 56 and 60 either |
| 64x32 and 8x8 at 150, 180, 250, 330 | HELD OUT (8) | set; t6 = 250 + 0.43 N to N = 290, then 250, +- 15 us |
| default 64x64 triangle at 150, 200, 280, 400 | exploratory (4) | none |
| optional 2x2: 56 and 440 FIT, 3 points by the slope | HELD OUT (5) | set iff its slope x N >= 125, edge 118 to 160 |

H-N (the threshold is a pass count near 57 to 62 at every size) differs from H-SEG at 8x8 and
4x4; E806's reading (a size-specific first set anywhere in (56, 110]) is refuted for a size that
sets at 66 and survives otherwise. H-SEG is refuted by 16x16 or 64x32 clear at 72, by 8x8 set at
60 or clear at 104, or by 4x4 set at 110. The t6 row is the only test of the "first piece"
reading; if it fails, the bit rule can still hold.

### 3.4 Stage p4-o4: which o4 word lands (36 jobs)

R3's p-c3 shape and decode. Tags 6, 7 and 8 belong to o5 to o7, so the second marker moves to
bit 4 of the word (the job marker's low bit, reserved): A = tag 5, A4 = tag 5 with bit 4, A3 =
tag 13 (bit 3, E808's 5'), A5 = tag 5 with bit 5. Each configuration an x and a y job.

| rows | set | frozen |
|---|---|---|
| c-e709, c-o4-u, c-o4s-u, c-u | control (8) | G-o4, tag 5, tag 5 (E808's reading, 2 of 2), G-o1 |
| single write A3; single write A4 | HELD OUT | V1: 5; V2: no o4 word; V3: 13. A4 lands with bit 4 |
| A then A4; A4 then A | HELD OUT | last wins / first wins / AND (no bit 4) / OR (bit 4) |
| A then A5; A5 then A | HELD OUT | the same four, on bit 5 |
| A3 then A4 | HELD OUT | V1: bit 3 gone, bit 4 by the order rule; V2: A4 |
| p1 A, !p1 A4 and the swapped order, k = 0, 3, 7 | HELD OUT (12) | gated: A at k = 0, A4 at 3 and 7; ignored: by the order rule |
| c-o4-u again | replicate (2) | same class |

14 held-out value jobs gate the 12 predicate jobs: if the bit-4 pairs read one class in both
orders the predicate rows are cannot tell. Verdict: Q276 answered iff G-o4 passes, one combining
rule holds in all value rows, and the predicate rows fit "gated" or "ignored" in 6 of 6
configurations. Will not close: why the pair count wanders; why bit 3 (if V1 or V2).

### 3.5 Stage g4-rw: a table of 1/w words (24 jobs, Q230)

R2's t3-nocut shape (z = 0, w = C x + D: three w a job, one run before, E782), 20 jobs for 60 w:
1 + k/32 for k = 1 to 31 and 29 other mantissas, in (1, 2) and scaled by 4 and 1/4 for a third.
Controls (4 jobs): w = 1 (0x3f800000), 3 and 7 (RZ), 9 and 0.7 (RZ + 1), 1.40625 (RZ + 1), the
window rule 32 + 32 x / w. The 60 w are split into 30 FIT and 30 HELD OUT by the sha256 of the
w's bits, frozen with the table. After the run: algorithms are declared as families before the
fit (as E783's note), fitted on the FIT half, frozen, scored on the other half. Frozen now: every
word is RZ or RZ + 1 (23 of 23 known words of kept vertices; made vertices are outside this). Stop
condition for the analysis: more than one family fits 30 of 30 held out, or none: the words are
recorded and no rule adopted. Will not close: the depth formula (next, once the reciprocal has
a rule), the made vertex's 1/w.

### 3.6 Not proposed

Q210 and Q273 (0.6: the firmware reading first; a hardware row only if the registers the guard
names were not sampled). Q003 (needs held faults; its rows are the kernel area's). Depth at w
other than 1 (behind g4-rw). The 121 us after a fault word (0.1 reads it as the same timeout;
q4-v and q4-f test the timeout without faults).

## 4. What is reused, what is new

| piece | from | change |
|---|---|---|
| runner, driver, staging, freeze, mock harness | `closing3/r3-pixel/run`, `tests` | prefix `~/r4p-`, FROZEN.commits, scorekit copied |
| loop generator, MARK proof, sim check | `r3-pixel/gen/r3loops.py`, `debug-src/simcheck` | nested loop, load prologue, bodies b12v, b2v |
| vertex loop | `r3-pixel/templates/vtx_loop.s` | 24 vertices; stock 1500-vertex rows from r3-geo's g-c4 command |
| Q276 generator and decode | `r3-pixel/gen/r3_c.py`, `score/score_c3.py` | marker bit 4 and 5 variants, classes by bit |
| w table | `r2-geo` g-t3 (t3-nocut), `templates/vtx_zw.s` | the w list, the frozen split |
| timeline reader | `closing4/pixel/ta_rule.py`, `px_rule.py`, `qt_slopes.py` | becomes `tools/closing/` reader with tests on R3's kept jobs |
| tool | `~/sgxfive-test-rgn4` | none planned; hash checked at staging |

Laptop: userspace only, no rebuild, no kernel change, no register written but the kernel's own
reset; 0x0008 is read. Offline before the freeze: every program through `usse-asm` and sgx-sim,
every command against `--mock`, scorers on synthetic worlds for each hypothesis column and on
R3's kept data (the TA rule must give 74 of 74, the fill rule 106 of 106).

## 5. Job counts, time, risk, order

| stage | jobs | time | risk |
|---|---|---|---|
| p4-o4 | 36 | 4 min | low: 75 jobs of this shape completed in R3 |
| q4-v | 28 | 3 min | low: loops inside E807's lengths; the 1500-vertex rows are g-c4's |
| q4-f | 16 | 2 min | low-medium: first load followed by a long loop; fills |
| q4-t | 54 (59) | 5 min | low: every size and length inside E806's |
| g4-rw | 24 | 2 min | low: one job of the shape ran (E782) |
| total | 158 (163) | about 16 min + staging; plan 30 | no row faults by design |

Order: bridge controls of each stage first; p4-o4, q4-v, q4-f, q4-t, g4-rw. Offline work order:
K1 to K9 and A1 (no dependency), reading R-5 (Q210), item 4 then item 2, then the session build.

## 6. Records to touch

Before the run (decision 1): notes on Q082, E805, E806, E807 (0.1 to 0.4), Q276 (0.5), Q210 and
Q273 (0.6), Q230 (0.7), Q053 (E808). After the run: Q082, Q276, Q230 and new records. No
correction of a landed claim is needed by anything here; A1's scorer fix refers to E807's
existing correction.

## 7. User decisions

1. **Offline readings into the records now.** (a) recommended: K1 to K9 as dated notes and spec
   text, each with its tier (SEMI and FIT said as such), before any run. (b) only the [source]
   and [HW] ones (K3, K5, K6, K8); the timing readings wait for the run. (c) nothing until the
   run.
2. **Q210 route.** (a) recommended: reading R-5 of routine 0xb50-0xc22 with the landed tools
   (Sonnet subagent, facts only, lead reviews), then the offline test on the five flips; no
   hardware. (b) also reword Q210 now as a firmware question (kind and line). (c) keep Q210 as a
   hardware question and plan another target ladder.
3. **Audit A1.** (a) recommended: fix `score_v.consistent` in the published copy as a disclosed
   post-run fix whose fixed output differs in one token, test first. (b) leave the scorer, add a
   line to POSTRUN-FIX.md that it is known and where E807 corrects it. (c) leave as is.
4. **Sim item 4 (vectors).** (a) recommended: all four parts, 4b and 4d first (they need the
   least converter work). (b) 4b and 4c only (sim-checkable words; no timings, no scenes). (c)
   hold until the run adds its jobs.
5. **Sim item 2 (latch).** (a) recommended: land the no-load fill rule now (edge 118 to 132 us
   refused), everything else refused until q4-v and q4-t hold. (b) nothing until the run. (c)
   also bit 7 now, marked post hoc (against "only for rows that held").
6. **Hardware session.** (a) recommended: one session R4-pixel with all five stages (158 jobs).
   (b) Q082 only (q4-v, q4-f, q4-t: 98 jobs). (c) Q276 and the w table only (60 jobs). (d) no
   pixel hardware this round.
7. **Bit 7 scope.** (a) recommended: q4-v as written, the 1500-vertex rows included. (b) without
   them (25 jobs; H-PHASE then rests on g-c4's after-reads alone). (c) add a vertex loop with a
   load (unknown on hardware, exploratory, last).
8. **Triangles.** (a) recommended: q4-t with the t6 row, without 2x2. (b) with 2x2 (+5, a new
   shape on hardware). (c) bit rows only, no t6 row (-8).
9. **Q276 design.** (a) recommended: the bit-4 and bit-5 marker variants (36 jobs). (b) value
   rows only (22 jobs), the predicate rows in a later round once the combining rule is read. (c)
   retag o5 to o7 instead, to free tags 6 and 7 (changes the shader of every earlier run).
10. **Q230 table.** (a) recommended: g4-rw with the frozen FIT / HELD OUT split (24 jobs). (b) an
    offline algorithm search on the 23 known words first, the run only if a family survives. (c)
    hold Q230 this round.
11. **Tool.** (a) recommended: `~/sgxfive-test-rgn4` with the bridge controls of each stage as
    the gate. (b) `~/sgxfive-test-r1` (R3's binary; not run on the rgn4 module by R3-pixel's
    shapes). (c) both for the bridge rows.
