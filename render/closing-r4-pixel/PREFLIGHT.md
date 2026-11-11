# R4-pixel preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-11 from `closing4/pixel/exp-pixel-r4.md` (section 3) and the decisions of
`closing4/DECISIONS-R4.md`, offline. Nothing ran on the laptop. Frozen: `FROZEN.sha256` (every
generator, scorer, runner script, table, prediction, staged program, template, `TOOL.sha256`,
`TABLES.md`, and by absolute path the landed files read), `PREDICTIONS.sha256`, `FROZEN.commits`
(resgx545 commit 5a13042). Refreeze (`run/freeze_r4.sh freeze`) only after regenerating and never
after the first job. The hashes are in the lead's report.

## 1. Jobs and time

One session, the plan's order, laptop directories `~/r4p-run`, `~/r4p-stage`, `~/r4p-out` only.

| stage | jobs | sets | time |
|---|---|---|---|
| p4-o4 (Q276) | 36 | 8 control, 26 HELD OUT, 2 replicate | about 4 min |
| q4-v (bit 7) | 28 | 4 bridge + 6 FIT (control), 15 ladder + 3 stock HELD OUT | about 3 min |
| q4-f (the load) | 16 | 5 bridge control, 11 HELD OUT | about 2 min |
| q4-t (triangles) | 54 | 12 control, 42 HELD OUT (4 exploratory) | about 5 min |
| g4-rw (Q230) | 24 | 4 control, 20 table jobs (60 w, 30 FIT / 30 HELD OUT words) | about 2 min |

Total 158 jobs, about 16 minutes of jobs, plus per stage ssh, health and copy 30 s, staging 1 to 4
min: plan 30. Bounds: 900 s a stage, 300 s a copy, 150 s health, 120 s a job. The pinned resgx545
commit 5a13042 is an ancestor of the main checkout's HEAD (f5b3574 at the build); the resgx545 pins
verify on both main and the lead's worktree `closing4/lead/wt`. `RESGX545_MAIN` names the tree the
generators, scorers and tests read (default `~/src/resgx545`).

## 2. Tool

`~/sgxfive-test-rgn4` (sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a, the
pin of `closing3/r4-reruns/a-q285/TOOL.sha256`, built from the fork a2788bd8's tree; its source is
at resgx545 4623753, and `userspace/libsgxfive/tools/sgxfive-test.c` at 5a13042 differs from it in
one line, the odd-height check of `probe_tri_check`, which no row of this session uses: every size
is even) and `~/regtimeline` (sha256 079f6359...de803, S1's, read-only; the pin R3-pixel used). The
runner's preflight and `stage_r4.sh` compare both with the pins by hash and the loaded and installed
module srcversion with 99CD90DA26E3AFF9C450517 (the handover's 99CD90DA; the full string is the
`SRCV_EXPECT` of `a-q285`'s README): a mismatch STOPS AND ASKS (rc 1), nothing is rebuilt.
**The lead must check before staging**: the handover names only the first 8 hex digits of the
srcversion and of the tool hash; the full values are from `closing3/r4-reruns/a-q285`
(`TOOL.sha256`, README), and `~/regtimeline` must still be on the laptop (the rgn4 boot kept the
home directory). `tests/mock_all.py` runs all 158 commands against the landed tool's `--mock`: 158
of 158 accepted, with the target, `--tri-full` triangle and vertex-count echoes checked. The mock
does not execute loops: the loops are checked in sgx-sim (section 8).

## 3. Controls and frozen predictions

Every Q082 row (q4-v, q4-f, q4-t): STATUS2 read after the reset (must be 0x400, else rc 16) and
after the job, the job under `regtimeline 0 0.3 0x0008,0x0118,0x012c`, the loop proof. A void job
(no output, an rc that is not a result of the tool, STATUS2 pre not 0x400, a failed loop proof, a
missing dump) is `cannot tell`, tested before any match. The stage scorers use `score/scorekit.py`
(a bridge control that is not a pass shuts the gate of every dependent row; a headline only with
every control passed and a row decided; the verdict is held / FAILED / cannot tell).

**The timing rules (offline readings K1 to K9, landed as spec text and corrections on E805 to
E807; `score/r4tl.py`, tested on the kept records in `tests/test_tl.py`).**
- Bit 7 (TA): with L the longest run of regtimeline samples with CLKGATESTATUS (0x0008) ==
  0x000ccff8, bit 7 is set after the job iff L >= 129.5 us; L below 122 us is clear, above 136 us
  is set, the edge between is not scored; a set job shows bit 7 118 to 138 us after the run began
  (the plan's window; the SEMI reading gave 123.2 to 133.8 us). On E807's 74 kept
  vertex-loop jobs: 69 on the predicted side, 5 in the edge, 0 wrong, the latch window in 39 of 39
  set jobs. [infer] Bit 7 latches when the TA makes no progress for about 125 to 130 us. Held out
  by q4-v.
- Bit 6 in a fill without a load: a tile's time tau = (B - 60.2) / 4 against 118 / 132 us (clear
  below, set above, edge between). On the 106 load-free fills of R3-pixel: 92 on the predicted
  side, 14 in the edge, 0 wrong. **sgx-pipe's `events::status2_bit6` (crates/sgx-pipe/src/events.rs
  at 5a13042) has the same constants and the same scope (a 64 x 32 fill without a load): the test
  reads them from the source (`BIT6_EDGE_US`, `tile_time_us`) and q4-f freezes a `pipe_rule` row
  from the same rule: it speaks (clear) at 16 iterations, (set) at 136 and refuses 53 and 56, whose
  tile times 119.5 and 126.5 us lie inside its edge. Those two predictions (clear, set) are E804's
  measured bracket, not the rule's, and the table says so. Every load row is a fill with a load,
  which the rule refuses (E805 ld8); the triangle rows it refuses too (E806, post hoc).**

**p4-o4 (Q276, o4 clause).** Word layout: low 16 bits = marker << 6 | variant bits << 4 | tag; tags
as round 3 (o4 tags A = 5, A3 = 13 (E808's 5'), A4 = 5 plus bit 4, A5 = 5 plus bit 5); E709's own
programs unchanged in c-e709. Controls (8): c-e709 and c-o4-u (G-o4: structural, as r3), c-o4s-u
(reads tag 5, E808's reading), c-u (G-o1 tag-2 fraction >= 0.98). Model family (score/o4model.py):
single-write path V1 (bit 3 dropped), V2 (a word with bit 3 does not land), V3 (as written) x
combine rule last, first, and, or, min, restricted to the 12 models that fit E808's 16 jobs (V1 x 5,
V2 x 5, V3 x {and, min}). Value rows frozen per model (single A3: V1 gives A, V2 none, V3 A3;
single A4: A4 in all; A then A4 / A4 then A: last A4/A, first A/A4, and and min A/A, or A4/A4;
the same on bit 5; A3 then A4: V2 A4, V3/and A, V3/min A3, V1 by its rule). Predicate rows (6
configurations): gated reads A at k = 0 (p1 true for the lane-0 instance that lands) and A4 at k =
3 and 7; ignored follows the model's rule. V1/and = V1/min and V2/and = V2/min are not
separable by these rows (one class each). Predicate rows are `cannot tell` if the two bit-4 pairs
read one class in both orders. Answered iff every control passes, one (gating, prediction class)
survives and the c-o4-u replicate reads the same class.

**q4-v (bit 7).** Controls (bridge to E807, `want2` stop on the runner): v-ctl0 (0x400), v-n1
(clear), v-i880 (clear, L 95 to 112 us), v-i1760 (set, L 160 to 260). Ladders (3 vertices unless
noted): b12v (10 multiply-adds, 13 instructions an iteration), b2v (counter and branch only, 2
instructions, proof by the counter reaching 0), b8v on 24 vertices; each two FIT points at 0.45 and
0.70 N* (clear by the model; `control` set, tallied apart, not gating) and five HELD OUT points at
0.80, 0.92, 1.08, 1.20, 1.60 x N* with N* from the frozen offline model of L (`r4const.py`: a
linear fit per body and vertex count of E807's 74 jobs, b12v and b2v from the line through b8v
and b16v, 24 vertices between 12 and 48: N* = 754, 2137, 500). **The rule scored is on each job's
own measured L, not on N*; the plan's "the slope of its two FIT points (run first, formula frozen)"
became a frozen model (deviation 1).** Stock rows (1500 vertices, 2048x2048 twice, 4096x4096, the
default pages, `p1139-green`): H-STALL (clear, as g-c4's ten jobs) against H-PHASE (set); a job
whose L is below 125 us is void for that.

**q4-f (the load).** Bridge (`want2` and `proofstop`): relative b8 at 16 (clear), 53 (clear),
56 (set), 136 (set, t6 120 to 340 us), ld8 at 70 (clear). Held out: ld0-K (K = 28, 53, 70, 110) and
ldo-K-M ((28,4) (28,16) (40,8) (70,1) (70,4) (110,2) (220,1)). Frozen (c clear, S set, e either):
H-YIELD ld0 c e S S, ldo c c c S S S S; H-LOADOFF all clear; H-SUM ld0 c e S S, ldo all set. d6
recorded without a prediction.

**q4-t (triangles).** Controls: green and N = 1 at 4x4, 8x8, 16x16, 32x16, 64x32 (MARK on W x H of
W x H, green; bit 6 clear), the fill at 53 (clear) and 56 (set). H-SEG: 8x8 at 60, 66 clear, 104
set, 72 to 96 either; 4x4 at 80, 110, 140 clear; 16x16, 32x16 and 64x32 at 46 clear, 66 and 72 set,
56 (twice) and 60 either. H-N (the threshold is a pass count near 57 to 62): the same at the mid
sizes, set from 66 at 8x8, from 80 at 4x4. E806-DISC (first set 56 or 110, 220 at 4x4, as E806
read it): 8x8 and 4x4 clear throughout, 32x16 set from 56, 16x16 and 64x32 clear to 72. 64x32 and
8x8 at 150, 180, 250, 330: set, and t6 = 250 + 0.43 N us after the burst starts to N = 290, 250
beyond, +- 15 us (the first-piece reading, tallied apart: if it fails the bit rule can still hold).
The default 64x64 triangle at 150, 200, 280, 400: exploratory, no prediction.

**g4-rw (Q230).** Controls (first): w = 1 (0x3f800000 at all three), (3, 9, 4.5), (7, 10, 7.75),
(1.40625, 1.78125, 1.5): the known words (RZ at 3, 7 and 1.5, RZ + 1 at 9 and 1.40625) exact. Table:
60 w in 20 jobs (w1, w2 designed, w3 = 0.75 w1 + 0.25 w2 derived), every w computed exactly in
float32, 31 grid mantissas 1 + k/32 and 29 others, a third at scale 1, a third at 4, a third at 1/4;
frozen: object present, 3 vertices in input order, window 32 + 32 x / w, depth 0x3f000000, every
1/w word RZ or RZ + 1. The 60 w are split 30 FIT / 30 HELD OUT by sha256 of the word's bytes
(`@split` in the predictions). After the run `score_rw.py` fits the 225 declared reciprocal models
(`rwfam.py`, five families) on FIT, scores the survivors on HELD OUT; more than one family at 30 of
30 held out, or none: the words are recorded, no rule adopted. It prints the chance counts on
shuffled FIT words (E783's lesson: 4 of 257 fitted six words by chance).

## 4. Fit vs held out

- FIT: the 74 E807 vertex-loop jobs and 106 load-free fills (the rules' own data), E806's tile
  slopes (the q4-t tables, `r4const.T_SLOPE`), E804 / E805 / E807 controls (bridge rows), the 23
  recorded 1/w words (the control words), the two FIT points of each q4-v ladder (control set).
- HELD OUT: every ladder point, stock row, ld0 / ldo row, triangle size ladder, o4 value and
  predicate job, table job of g4-rw (the 30 HELD OUT words only count for the family fit).

## 5. Gates, stops, what the lead decides

Runner exit status (`run/run_stage.sh`): 1 preflight (a table, program or runner file that is not
the frozen one, a laptop FROZEN.sha256 that is not the Mac's, a tool, regtimeline or kernel module
that is not the pinned one, or one of the debugfs files reset, hold_recovery, regs, render_param,
render_tadata, render_pb_pages, alias_skip missing); 3 watchdog, lockup or BUG (touch nothing); 4
any unexpected hang, fault or failure; 5 failed health recovery; 6 a job did not return; 7 unknown
knob; 8 missing program; 12 registers unreadable; 13 reset failed; 14 fault latched before a job;
16 STATUS2 not 0x400 after the reset; **17 a loop proof failed (knob proofstop: the stage ends after
its health check, is scored, the session goes on: a nested or load loop that does not prove itself
costs that stage only); 18 a bridge control read otherwise (knob want2: STATUS2 & MASK != VALUE
after the job; the stage ends after its health check, is scored, the session STOPS)**. Driver
(`run/r4.sh`): 20 frozen files changed, 30 to 37 health, 38 no SUMMARY, 39 the attempt exists, **42
a bridge control failed or cannot tell (runner rc 18, or `score_r4.py gate STAGE KEPT`: exit 0
every bridge control passed, 1 one FAILED, 2 one cannot tell), before the next stage: the lead
decides**. No fault budget: any fault or hang stops the stage (rc 4); no tick-stop budget (the
runner reads and writes no EDM state). No held fault, no `hold_recovery` write, no debugfs write
but the kernel's own `reset`, no clock-gate write, no register write at all.

## 6. Risks

- p4-o4: 75 jobs of this shape completed in R3 (`--tri-full` and 128x128 were new there and
  are not used here); the new thing is the word layout (markers at bits 15:6): the programs run
  in sgx-sim (which does not model the hardware's o4 landing).
- q4-v: b12v, b2v and 24 vertices never ran; the stock rows (1500 vertices at 2048x2048 and
  4096x4096 at the default pages 0x422) run g-c4's command without its P knobs: the TA phase is
  expected to be short of aborts; `--dump-render` at 4096x4096 keeps the dumps of R1's controls
  (4.6 MB). A hang stops the stage.
- q4-f: the nested load loop (two counters, a load per outer iteration) is new on hardware; its
  first row has the proof stop. ld8 and fills ran to 13.4 ms in R3.
- q4-t: every size and length is inside E806's (the longest, 64x32 at 330, is 7e5 pixel-iterations).
- g4-rw: at scale 1/4 the window coordinates reach about +-121 pixels: the triangle may be
  partly off the target and, if culled, the job reads as a failed shape (the scorer says so).
- The bridge rows at 53 and 56 iterations (q4-f and q4-t's fills) lie inside the edge of the fill
  rule (tile time 119.5 and 126.5 us): E804 read them 2 of 2 (53 clear, 56 set) and E431 in every run,
  and they are runner stops (want2), so a flip there stops the session with exit 42 and the lead
  decides (a rerun of the stage is a new attempt); it would also be a finding about the edge.
- Ladder placement: the N* of b2v and 24 vertices is extrapolated from E807's other bodies; if the
  model is 30% off, a ladder keeps two or three informative points (the scorer prints
  `NOT INFORMATIVE` when no point lies on one side of the edge).

## 7. DEVIATIONS from the plan, and why

1. q4-v ladders: the plan places the five points "over the slope of its two FIT points (run
   first, formula frozen)". The tables are static and carry no gate state, so the N values come from
   a frozen offline model of L (a linear fit of E807's kept timelines), and the two FIT points are
   rows run first whose own L is tallied apart. The prediction scored (set iff L >= 129.5 us, per
   job's own L) does not depend on N*.
2. b12v is the plan's "10 imae" body; the vertex bodies carry the depth accumulator, so it is 13
   instructions an iteration (b8v 8, b16v 16). b2v is the plan's "counter and branch only", a true
   2-instruction body with a counter-based proof (`templates/vtx_loop2.s`).
3. The bridge controls are runner stops (knob `want2`, rc 18) and a scorer gate (exit 42), both
   new; the plan only says "each stage's bridge controls as the gate".
4. The stock rows run at the default page count (no knob), where g-c4 set P by debugfs: the runner
   writes nothing but `reset`.
5. FIT rows of q4-v are `control` in the tables (as R3's FIT points) but do not gate; the four
   bridge rows do.
6. q4-t has no 2x2 row and no "64x32 bridge" triangle rows of R3 (the plan's list is followed).
7. p4-o4: V1/and = V1/min and V2/and = V2/min are not separable by the plan's rows, so the scorer
   treats each pair as one class (said by the scorer).
8. The loop programs of R3 not staged here (b16, b12 pixel, b4, b2, b8n, abs) are not rebuilt;
   `r4loops.py` keeps their generators and adds `pixel_load_source` (ld0 / ldo) and the b12v / b2v
   vertex bodies.

## 8. Offline test results and freeze

`RESGX545_MAIN=<tree at 5a13042> bash tests/run_all.sh` (2026-11-11): ALL TESTS PASS.

- test_tl 18 ok (the two timing rules on the kept records: 0 wrong of 74 TA jobs, 0 wrong of 106
  fills; sgx-pipe's constants read from its source), test_loops 11 ok (59 staged programs in
  sgx-sim at every code index of their slot), test_gen 56 ok, test_q082 43 ok (worlds for each
  hypothesis, failing and missing controls, void jobs, gate exits), test_o4 38 ok, test_rw 31 ok,
  mock_all 158 of 158 commands accepted by the landed tool's mock, run_mock 100 ok (runner end to
  end, stop rules 16, 17, 18, bridge gate exit 42, guard injections, staging, driver), guard clean.

Freeze: `FROZEN.sha256` 187 files, `PREDICTIONS.sha256` 5 files; `shasum -a 256 FROZEN.sha256` =
f9b0fa039e1345c2b5f109e3e5989951a1874bfd9b24ac9eed13cd903e789ab8, `shasum -a 256
PREDICTIONS.sha256` = c939d0f5f57504808fbbfd320f41ba3462c116b4a10cfab8f49c88b2b8375b75.
`run/freeze_r4.sh verify`: files verified (with `RESGX545_MAIN` the lead worktree and with the
main checkout f5b3574).
