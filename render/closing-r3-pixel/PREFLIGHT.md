# R3-pixel preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-10 from `closing3/pixel/exp-pixel-r3.md` and decisions R3-P1 to R3-P10. Nothing
ran on the laptop. Frozen: `FROZEN.sha256` (every generator, scorer, runner script, table,
prediction, staged program, template, `TOOL.sha256`, `TOOLSRC.sha256`, and the landed files the
generators import: probe.py, pbdump.py, usse-asm, vtx_zab.s, pds_iter_xy.s, vtx_coords.s,
sgxfive-test.c, the E709 programs), `PREDICTIONS.sha256`. Refreeze (`run/freeze_r3.sh freeze`) only
after regenerating, and never after the first job. The freeze hashes are in the lead's report.

## 1. Jobs and time

One session, the design's order (section 5), laptop directories `~/r3p-run`, `~/r3p-stage`,
`~/r3p-out` only.

- p-c3 (Q276): 75 jobs = 18 control, 28 CONFIRM (set `repeat`), 28 HELD OUT, 1 replicate. About 7
  min.
- q-f0 (loop controls, fills): 10 jobs, all controls. About 1 min.
- q-f1a (fill ladders, ascending): 54 jobs (12 FIT points, 42 HELD OUT). About 4 min.
- q-f1b (the same 54 in the exact reverse order): 54 jobs. About 4 min.
- q-t (occupancy, full-target triangles): 93 jobs = 90 + the three 4x4 rows (R3-P8). About 7 min.
- q-v (TA side, bit 7): 88 jobs = 5 controls + 83 HELD OUT. About 8 min.
- Total 374 jobs. Per-job times from R1/R2 (reset 3 s, regtimeline lead 0.3 s, dumps, 5 s a job
  with 4.6 MB dumps), plus per stage ssh, health and copy 30 s: about 35 min of jobs, staging 1 to
  4 min, plan 50. Bounds: 900 s a stage (the longest, q-v, is about 8 min), 300 s a copy, 150 s
  health, 120 s a job (a 100 ms job needs nothing like it).

## 2. Tool

R1's build `~/sgxfive-test-r1` (sha256 bf4f8be2...d4f053, `TOOL.sha256`) and `~/regtimeline`
(079f6359...de803, from R1's `stage-r1.log`), no rebuild, no tool change (R3-P1). `TOOLSRC.sha256`
(51 files) still matches the repo today; `freeze` refuses if it does not. The runner's preflight
and `stage_r3.sh` compare the laptop's binaries with the pins by hash: a mismatch STOPS AND ASKS
(rc 1 and the message), nothing is rebuilt. `tests/mock_all.py` runs all 374 commands against the
landed tool's `--mock`: 374 of 374 accepted, with the target, `--tri-full` triangle and
vertex-count echoes checked. The mock does not execute loops: acceptance only; the loops are
checked in sgx-sim (section 3).

## 3. Controls: how each passes and fails

Every Q082 row: STATUS2 read after the reset (must be 0x400, else the row is not run: rc 16) and
after the job, the job under `regtimeline 0 0.3 0x0008,0x0118,0x012c`, the loop proof, the burst B
and the time of the latch. A void row (no output, an rc that is not a result of the tool, STATUS2
pre not 0x400, a failed loop proof, a missing dump) is NODATA for every hypothesis, tested before
any match.

- Loop programs (R3-P1): relative `p0 br -#(BODY-1)` and a MARK (prologue `mov r30, #(0xC0DE0000 |
  N)`, last instruction `xor.end o0, r1, r30`), so o0 = MARK only where the counter reached zero.
  `tests/test_loops.py` runs every program in sgx-sim at the code indices a fill (0), a `--tri`
  pixel slot (0x20) and a higher page (0x1020) give: 23 checks, o0 = MARK and the step count
  prologue + BODY x N + 1 exactly. The absolute `ba` loop ends at index 0 and stops at 0x20 ("a ba
  to an index before the program in its code base"): E770's mechanism. The generator refuses `ba`
  for a `--tri` slot; the guard refuses an `abs` program in a `--tri` row.
- q-f0 (the first control is the unproven backward `br` in a PIXEL task): rel 53, 56, 53, 56 with
  the runner's `proofstop` (o0 must be MARK on 2048 of 2048; else rc 17, health, and the pixel loop
  stages end cleanly), abs 53, 56, 53, 56 (E431's `ba` loop in a fill: o0 = 0), rel 16 (clear,
  burst 204 +- 125 us), rel 136 (set, t6 120..340 us). Fails: a proof failure (gate closed), abs
  and rel on different bits (exit 41), a miss on a frozen bit (reported).
- q-f1: the two short points of each ladder are its FIT rows (the slope of the burst); every other
  point is HELD OUT. A loop proof failing voids that job only. Hypotheses: H-MA (multiply-adds of
  an instance reach M* in (318, 336]: the design's table, b16 21, 22 clear, 23 either, 24, 25 set,
  and so on), H-WD (a tile's time (B - 60.2) / 4 >= 121.8 us; N* = 4 T* / s_body from the two short
  points, ld8 from the job's own B), H-WD-busy, H-BURST (B >= 536 +- 20 us). H-ITER and H-INSTR
  (E769's refuted rows) are printed without weight (set `repeat`). Verdict rule as the design:
  refuted by ONE ladder whose two orders agree and contradict it; `holds` needs every ladder; the
  orders disagreeing at one N is an `edge`; a contradiction in one order only is `unreplicated`. If
  b2, b8n and b4 never set, H-MA and H-WD are both refuted and the verdict says E769's fit stays
  unexplained.
- q-t: stock `pix_green` full at seven sizes (o0 green on W x H of W x H), the loop at N = 1 at
  seven sizes (MARK on W x H of W x H; a size failing it is void, the others stand), the 64x32
  bridge at 53 and 56 (clear, set). Ladders HELD OUT, first set N per size against H-INST / H-TILE
  / H-JOB (the design's table, scaled by the measured 64x32 first set / 56; a failed bridge is
  reported and scales every cell).
- q-v: ctl0 (no loop), n1, n3 (the first backward branch of this run; E784 showed it in a vertex
  task), i880 (clear), i1760 (set): loop proof = the stored depth word of every decoded vertex
  0x3f200000 + N. Any of them failing makes the stage `cannot tell` (n3 alone: "the first backward
  branch did not loop"). Then the b8v narrowing ladder up and down (one bracket of 55, both orders
  within one step) and the formulas of N8* on b16v, b4v, 12 and 48 vertices.
- p-c3: controls scoped to their group (R3-P6): G-o4 (c-e709 and c-o4-u: tag-5 words 10..100 in
  each job, pairs 5..60, every pair source (even, even), tag-5' words <= 2 in the x job; passes in
  26 of 26 real runs of R1's p-c2 and S1b's p-c, fails on a world with no o4 words, a flood, odd
  sources, tag-5' words) gates the o4 rows; G-o1 (c-u, c-u-r2: tag-2 fraction >= 0.98) the o1 rows;
  c-g23r4 the register-form rows; c-o4s-u the swapped-order o4 rows; the three premise controls
  (c-rd-pa default, c-rdf-pa full 64x64, c-rdf128-pa full 128x128: o0 = pa decodes to the pixel's
  own position in >= 90%) their direct reads. A failed control voids its group only. Verdict "Q276
  ANSWERED" iff every control passes, M holds in every CONFIRM and HELD OUT row, and each
  alternative fails where it differs.

## 4. Fit vs held out

- FIT: E431 / E357 timelines (B = 60.2 + 9.02 N us, sd 36; bit 6 124..329 us after the burst
  starts; T* = 121.8 us), E769's iteration points, E784 (i880 clear, i1760 set), E772's post hoc
  readings of g23 / g25 (the CONFIRM rows, set `repeat`, run again), the two short points of every
  q-f1 ladder.
- HELD OUT: every other ladder point, every q-t size ladder, the q-v narrowing and the four
  discriminating ladders, the 28 new Q276 jobs (c-g23r1, r2, r6, m18, eq20, eq40, c-g25b0, b1,
  c-o4s-k0, k3, k7, the g24 and full-target direct reads).

## 5. Gates, stops, what the lead decides

Runner exit status (`run/run_stage.sh`): 1 preflight (also a table, program or runner file that is
not the frozen one, a laptop FROZEN.sha256 that is not the Mac's, a tool, regtimeline or kernel
module that is not the pinned one: srcversion loaded = installed = B21FDA82BD5E5CB5A627E3B, and the
debugfs files reset, hold_recovery, regs, render_param, render_tadata, render_pb_pages, alias_skip
must exist); 3 watchdog, lockup or BUG (touch nothing); 4 any unexpected hang, fault or failure
(the tool's messages are searched in the WHOLE output and kernel slice, tested with a
12000-character output); 5 failed health recovery; 6 a job did not return; 7 unknown knob; 8
missing program; 12 registers unreadable; 13 reset failed; 14 fault latched before a job; 16
STATUS2 not 0x400 after the reset; 17 a loop proof failed (q-f0). Driver (`run/r3.sh`): 20 frozen
files changed, 30 to 37 health, 38 no SUMMARY, 39 attempt exists, 41 abs and rel loops disagree.

- THE LOOP GATE (R3-P1: "its failure must end the Q082 loop stages cleanly"). A failed relative
  loop proof stops q-f0 at its first control (rc 17), the driver scores it, runs health, SKIPS
  q-f1a, q-f1b and q-t (their gates are computed from the kept q-f0), still runs q-v (the vertex
  loop, proven by E784, with its own depth proof), and ends with exit 0 and a line naming what was
  skipped. Tested end to end in the mock.
- ABS vs REL disagreeing on the bit (gate exit 3, driver exit 41): the lead decides. The design
  says "the fill ladders run with both"; no abs ladder tables are built (DEVIATION 6).
- Sweep stops (q-v): `sweep:G:0x80` rows are skipped once a row of group G has set bit 7;
  `watch:G:0x80` rows (work inside E784's intact 3 x 1760 x 8 instructions) are never skipped but
  set the group; the b8v and b16v ladders carry neither.
- Any fault, hang, STATUS2 pre mismatch or BUG stops the stage; there is no held fault, no
  `hold_recovery` write and no debugfs write but the kernel's own `reset`; no clock-gate write.
- After the session: `$PY score/score_r3.py verdict out/ATT`.

## 6. Risks

- p-c3: 81 of 81 jobs of this shape completed in R1/S1b; new on hardware: `--tri-full` and 128x128
  in this probe shape (the premise controls, last in their stage), and `--tri-full` with the PDS
  iteration program. A refusal stops the stage (rc 4); the pixel stages follow.
- q-f1: fills only; the longest (b2 at 16000, b8n at 3840) are below E357's 112 ms. No fault is
  expected by design.
- q-t: the first working loops in a triangle; jobs up to about 100 ms (pixels x N <= 2.3e7) at
  128x128 and 256x256; a hang stops the stage. The partial-triangle rows and the 4x4 rows have
  never run with a loop.
- q-v: vertex loops past E784's length only under the sweep stop; `--vertices 12 / 48` with a
  vertex loop has never run (DEVIATION 9); regtimeline on vertex jobs is new.
- The loop rows trust that the tool patches `0x5CAF0000` (the ld8 scratch address) as in E769.
- Time: 374 jobs in one session; STATUS2 pre mismatches are expected to be zero (E784: 0x400 after
  every reset).

## 7. DEVIATIONS from the design, and why

1. H-WD's N* uses the inverse-variance slope of the two short points and the band is max(8%, 2
   sigma of that slope) (design: +- 8%): the burst's residual sd of 36 us makes the slope of a 6 or
   8 iteration step uncertain by 15 to 30%, so +- 8% would count noise as a refutation. ld8 uses
   the job's own B, as the design says.
2. The design says each ladder's two short points are "clear by every hypothesis": for b2 (500,
   1000) and b8n (60, 120) they are not (H-WD predicts set from about 215 and 54). They stay the
   FIT rows, listed and excluded from the verdict.
3. The o4 class is read from words with a floor of 10 per job (design: 20): R1's own c-g23r3 had
   19, and the G-o4 control's range is 10..100.
4. The "gated o4" alternative is "class is not 5" (5' or mixed) at k3, k7 for the CONFIRM rows and
   "not 5'" for the swapped-order rows: a write gated by p1 gives a mix, not a pure 5'.
5. Exact-column Q276 rules (eq20, eq40) use an exception budget of 1 (design: max(2, 2%) = 10 of
   about 490 sources): the 2% budget cannot separate M from "g23 = x" at x = 52 (2 to 5 sources).
   An alternative that differs from M at no more sources than its budget is void, never consistent.
6. No abs ladder tables are built for the abs/rel disagreement case; the driver stops (exit 41) and
   the lead decides (the design says only "run with both").
7. The runner is R2-pixel's without its held-fault machinery (no held job, no hypothesis group, no
   fault budget): R3-pixel expects no fault, so any fault or hang stops the stage. New knobs: `s2`
   (STATUS2 pre/after, pre != 0x400 stops, rc 16), `sweep:G:MASK`, `watch:G:MASK`,
   `proofstop:HEX:COUNT` (rc 17). The sweep was R2-geo's `sweep:G` (bit 7 only), generalised.
8. HV-TIME uses the burst length B of the regtimeline (0x0008) as the TA phase's length: the TA
   phase alone is not separable in these three registers.
9. The vertex loop's imae write r4..r8 in turn (E784 used `--temps 16`; b16v needs 13 imae and a
   larger temps count could change the occupancy being measured). With V = 12 or 48 the proof reads
   the decoded object's vertices (pbdump `first_object`), which never ran on hardware for more than
   3 vertices; an undecodable dump voids the row, the stage's other rows stand.
10. The pixel loops keep the MARK in r30 (the draft used r10, which b16's imae and ld8's load use).
11. At 4x4 H-TILE and H-JOB are frozen as "clear at 56, 220, 880" (their thresholds, 1792 and 7168,
    are beyond the ladder), H-INST as "set"; the design only offered the rows.
12. For q-t `ladder-*` the allowed first-set points are the design's cells when the bridge holds
    (first ladder point >= value x ref / 56 otherwise).
13. p-c3 keeps R1's `--dump-render` (4.6 MB a job) so that the job shape is identical to the 81
    jobs that completed.

## 8. Offline test results and freeze

`bash tests/run_all.sh` (2026-11-10, before the freeze was verified): ALL TESTS PASS.

- test_loops: 24 ok (every staged loop program, 139 in `bins/`, rebuilt from the generator and run
  in sgx-sim at its slot's code indices; the abs loop stops at 0x20).
- test_gen: 79 ok (counts, ladders, orders, knobs, sweep and watch assignment, 2.3e7 bound, the
  frozen files verify).
- test_scorers_r3: 61 ok (E431's timelines, E784's kept vertex runs through a real pbdump decode,
  worlds H-MA, H-WD, H-WD-busy, never-sets, H-INST, H-TILE, H-JOB, HV-INSTR, HV-MA, HV-JOB, void
  rows, edges, one-order contradictions, the loop gate's three exits).
- test_scorers_c3: 33 ok (the G-o4 control in 26 of 26 real runs; worlds M, transpose, g23 = x, g23
  = y << 16 | x, gated o4, g24 = y, no wrap at 128; each control failing voids its group only).
- mock_all: 374 of 374 commands accepted by the landed tool's mock.
- run_mock: 101 ok (runner end to end: every stage, 7 debugfs files, srcversion twice, tool and
  regtimeline pins, STATUS2 pre stop, loop proof stop, sweep and watch, whole-output search,
  health, attempts, closed pipe, guard injections, staging, the whole driver, the loop gate closing
  the pixel stages cleanly, abs vs rel exit 41).
- guard_r3: clean.

Freeze: `FROZEN.sha256` 270 files, `PREDICTIONS.sha256` 6 files; `shasum -a 256 FROZEN.sha256` =
8a0fa9aa17bad7f1d74bc99bbe1e65f9de87144e08d8b11f2426962354ca9379 and `shasum -a 256
PREDICTIONS.sha256` = d1cdc86b773074b82f4947a91f33d8e9a030b719329bed4f96f8764c687b014f.
`run/freeze_r3.sh verify`: files verified.
