# Phase 11.38 laptop batch: the arithmetic of coverage, depth and iteration

Scratch, untracked. Gate of phase 12.3 (plan.md section 4, "12.3 ISP and the first triangle", and
12.0 "open the new question on arithmetic"): for an arbitrary triangle, which pixels does the ISP
cover, what depth does it store, what does the iterator deliver. Landed knowledge (all [HW]): the
first triangle and 16 target sizes exact against a CPU reference (E023, E148, E174) that leaves a
one-pixel band around every edge undecided (`sgxfive_tri_expect`: "near" when the centre is within
a pixel of an edge line); the region test of the TA (E542: 14656 pairs); sample positions under bit
28 (3d.md 11.8: byte k places sample k at (bits 3:0, bits 7:4) / 16 of a pixel; top-left rule
"a sample on an edge is inside only on an edge that runs up the screen"); the depth compare to the
ulp (E072); the ZLS store layout (E465); the iterated position x + 0.375, y + 0.125 in every mode
(E502). Not covered by any record: the arithmetic for an arbitrary triangle, the fill rule on
shared edges, the snapping of vertices, depth interpolation.

The CPU reference of the tool is one hypothesis here (H-ref), not the truth: it cannot fail by
construction inside its band.

## 1. What runs

Tool: a copy under `tool/` (11.35 `sgxfive-test.c` + the 11.26 tree), deployed as
`~/sgxfive-test-1138`; the change by TDD (tests first, red, then green):
`tri` and `probe --tri` take `--tri-v X0,Y0,X1,Y1,X2,Y2` (window coordinates, integers in 1/256
pixel, exact clip coordinates for a target whose half-size is a power of two) and `probe --tri`
takes `--tri-z A,B,C`. Tests: `tests/test_render.c` (`test_fine_vertices`), `tests/test_cli.py` and
`tests/test_cli_tri_probe.py` (16 new tests; `make check` green: 69, 55, 252, 438, 38 passed).
Sources sha256: `sgxfive-test.c` fcb1aea98b62..., `render.c` 9c1c3a9a2d1e...; the binary's sha256
is printed by `deploy1138.sh` and kept in each dataset's env.toml.

Three job kinds per case (`cases.tsv`, column `jobs`):

- D: `tri --tri-v --tri-z --depth --depth-ctl 0x17100c --depth-fill 0xdeadbeef --depth-dump --poke
  blk:1=0x00400200 --pixels` (E465's recipe). The colour image gives coverage; the depth dump,
  decoded by E465's address rule, gives the stored depth of every pixel of the target (1.0 where
  nothing is drawn).
- I: `probe --tri pixpds:12 --vtx-coords 2` with E437's primary program (source 1, two components,
  `0x20400800`, U1 `0x01000004`) and `templates/vtx_attr_zx.s` (o4 = the vertex's clip z, o5 = its
  clip x); pa0 (iterated z, a plane through three independent values) and pa1 (iterated x) as the
  colour in two jobs. Coverage a second time, with a different pixel program.
- C: the plain green probe (coverage under a third pixel program) on every fourth small, medium
  and centre case.

Run script: `run/run_p1138.py` on the laptop, one process per job, per-job marker in /dev/kmsg,
the whole output of every job gzipped (D also the depth buffer), the GPU reset through debugfs after
a flagged job, a plain 64 x 64 triangle must draw exactly (3 failed recoveries abort). It writes no
register. The fixed campaign runner of 11.35 (`tools/campaign/campaign.py`) was not used: its script
tables stage binaries with `rm -rf` on the laptop (not allowed here) and its fence runs a probe that
hangs on purpose; the same elements are kept by hand (before and after health, kernel log, env.toml,
the dataset directory).

## 2. Cases (cases.tsv sha256 recorded in predictions-1138.toml; seed 1138)

Vertices are integers in 1/256 pixel, depths multiples of 1/1024 (exact in float32). Classes:

| class | what | 64x64 fit | heldout |
|-------|------|-----------|---------|
| sweepV+/-, sweepH+/-, sweepD+/- | an edge (vertical, horizontal, 45 degrees) moved in 1/256 steps (4 or 8 apart) across a pixel centre, the third vertex on either side | 262 | 100 at 128 x 128 |
| small | a triangle inside a 1 to 4 pixel box, random 1/256 vertices | 150 | 100 at 128, 100 at 64 (seed 2) |
| medium | inside an 8 to 40 pixel box | 80 | 60, 40 |
| large | vertices over the whole target (30% from -10% to 110%, off screen) | 30 | 30, 20 at 128; 20 at 256 x 128; 20 at 64 |
| centre | all vertices at pixel centres (x + 0.5, y + 0.5): edges through centres | 60 | 60, 20 at 256x128, 30 at 64 |
| pairA/B | a quad cut along a diagonal into two triangles with the shared edge; half with centre corners | 40 pairs | 40 + 10 + 20 pairs |
| degenerate, sliver, needle | collinear (zero area); the middle vertex 1 or 2 units off the line; 1/16 pixel wide and 20 to 40 long | 30 | 30, 10, 20 |
| repeat | 30 of the fit cases run a second time | 30 | |

1536 cases, 3112 jobs. **Sets, declared before any run.** fit: every 64 x 64 case of batch 1 (the
only set on which a hypothesis may be fitted). heldout: all 128 x 128 and 256 x 128 cases and the
64 x 64 cases of batch 2 (new seeds, never used to choose anything). repeat: the 30 reruns. Held-out
cases are compared with the hypothesis chosen on fit; a refit on held-out is printed as information
and never counts as a test. Targets 96 wide are not used (a half-size of 48 is not a power of two,
the clip coordinate would not be exact).

## 3. Hypotheses (named in `recompute/p1138lib.py`, all fitted by exhaustion on the fit set)

Coverage of pixel (x, y): inside the triangle at the sample point S, after snapping the vertices.
- Snap: none; round to 1/32, 1/16, 1/8, 1/4 pixel; floor to 1/16.
- Sample point S: every multiple of 1/16 pixel from the pixel's top-left corner (256 points; the
  centre is (8, 8)/16, the iterated position of E502 is (6, 2)/16).
- Fill rule (a sample exactly on an edge, after the vertices are ordered to one winding): R1 to R8 the
  eight top-left / bottom-right / left-right variants (an edge owns its samples if dy > 0 or dy = 0 and
  dx > 0, and so on, `RULES`), ALL (every edge owns its samples, shared edges double), NONE (none, gaps).
- Edge function: exact integers (the fit), and float32 from pixel-unit coordinates (compared on the
  held-out set).
- H-ref: the landed reference (snap round 1/16, centre, an undecided band of one pixel): by
  construction not falsifiable; its tighter form, no band, is the cell (r16, centre, R1) below.
- H-ind: coverage does not depend on the pixel program or the depth state (D, I0, I1 and C agree).
Depth: the plane through the (snapped) vertices' screen depths, evaluated at S in float64, against the
stored float32, error in float32 ulps; format: float32, 1.0 where nothing is drawn. Iteration: the
plane through the vertices' clip z (pa0) and clip x (pa1), error against the float32 pixel value.

## 4. Predictions (frozen by hash before any run: predictions-1138.toml and this file)

My expectation (an [infer] from E214, E215, 3d.md 11.8, E502): the ISP samples at the pixel centre
with vertices snapped to 1/16 pixel, a top-left rule with R1's ownership (or another one of the eight:
only the family is predicted, R1 is the frozen cell, so a different member fails P1 and is then
named by the fit), depth and iteration interpolated in float32 with an error of about 1 ulp, the
iteration at (0.375, 0.125). The criteria P1 to P11, each failing on one number, are in
`recompute_p1138.py` section 6 and `predictions-1138.toml`.

Pilot (3 cases outside every set, run before the freeze to test the pipeline): it found two things.
A pipeline bug: with the pitch G fixed at 1 the tiles of a 128-wide target overlap in the depth buffer
(E465's window rule), so G is now tiles across - 1 (fixed in `run_p1138.py`, tested). And its depth and
iteration values fit the plane through the *unsnapped* vertices at the pixel centre, not the position
iteration's (x + 0.375, y + 0.125): P7, written before the pilot, is kept and expected to fail; P7c and
P7d are the pilot-informed predictions, declared as such. The pilot says nothing about coverage.

## 5. Safety, order, stop

No register written (render options only), no clock-gate register, no kpoke, no reboot or module
change, no git on the laptop, no deletion of directories. Order: a pilot of ten cases that are not in
the sets (the default triangle in the same form) to check the pipeline, then fit D, I, C; then
heldout; then repeat. Stop on three failed recoveries; a freeze or watchdog reboot: stop and report.
Health before, after each set, at the end; `journalctl -k` per script.

## 6. Recompute

`python3 recompute/recompute_p1138.py DATADIR` (numpy; shares no code with the run script): section
1 the whole hypothesis grid on fit, the winner on held-out by class and size, float32 edge functions;
1b degenerate classes; 2 shared edges (gaps, doubles, ties exactly on the diagonal); 3 depth; 4
iteration; 5 repeats and pixel-program independence; 6 the criteria. `tests/test_recompute.py` builds a
synthetic dump directory from a model hardware and checks that the fit recovers it, and that another
hardware fails P1.

## 7. Changes after the freeze (stated, not hidden)
The freeze (`freeze1138.sh`: 33 files in `manifest-1138.sha256`, predictions sha256 11ecc93e...)
was made after the pilot and before the first main job. Afterwards, and before any main dump was
read: `recompute/extra_p1138.py` (a model-free reading of the edge sweeps: where the first covered
pixel changes), and one added test in `tests/test_recompute.py` (the only frozen file that no
longer matches its hash; the cases, the run script, the recompute script, the library and the
predictions do). `plan.md` itself also changed after the freeze: sections 7 to 9 were appended
(follow-ups and what they found); sections 1 to 6 are as frozen.

## 8. Follow-up "fine" (declared after the main fit set was read, before any fine job)

What the main fit said (692 cases, 413856 pixels of bounding boxes): the cell (no snap, centre,
R4) misses 0 pixels, the only one of the 15360 cells that does; vertices snapped to 1/128 pixel
already miss 21, to 1/32 pixel 78, to 1/16 pixel 256. The grid stopped at 1/256 because the
vertices are 1/256 apart, so "no snap" means "no snap down to 1/256". The follow-up
(`gen/gen_fine.py`, `cases-fine.tsv`, 874 cases, `predictions-fine-1138.toml`,
`freeze-fine1138.sh`) puts vertices finer than that: a second tool change by TDD (`tool-b/`:
`--tri-unit K`, vertices in 1/2^K pixel, K 5 to 20, deployed as `~/sgxfive-test-1138b`), edge
sweeps in steps of 1/4096 pixel across the tie at 64 x 64, random and near-tie triangles at
1/4096, and sweeps in steps of 1/65536 pixel at 256 x 128 near and far from the origin
(edge-function precision). D jobs only. The heldout main set had not been analysed when this was
frozen.

## 9. What the fine set said, and the confirmation "fine2" (declared before any fine2 job)

The frozen predictions of section 8 failed: the sweeps flip 8 units of 1/4096 pixel after the tie,
not at it (PF1: 484 of 654 cases agree with "no snapping"), random near-centre triangles are
mispredicted by the exact model (239 pixels, 52 of 60 triangles; PF2), and the far-from-origin
1/65536 sweeps (33 steps, 1/4096 pixel in all) are uninformative once the vertices are rounded
(PF3). Post hoc (`recompute/fine_extra_p1138.py`, one of 24 variants fitted on the fine set): the
vertices rounded half-up to 1/256 pixel, then the exact centre-sample test, reproduce all 874 fine
cases with 0 mismatching pixels (half-down 145, floor 1156, 1/512 577, 1/128 1157, ceil 4572, none
4576), and the depth plane through the rounded vertices is within 1 ulp for 99 to 100% of the
sweep pixels (maximum 1.6 ulp). The main set is unaffected: its vertices are on the 1/256 grid.
`gen/gen_fine2.py` (seed 11381, `cases-fine2.tsv`, 422 cases, `predictions-fine2-1138.toml`,
`freeze-fine2-1138.sh`) is held out from that fit: 150 random fine triangles at 128 x 128, 60
near-centre ones at 1/65536 on 256 x 128, 132 sweep cases at 128 x 128 and 80 tiny-edge cases (a
50 to 120 pixel edge passing a pixel centre at a cross product of +1 or -1 in units of 1/65536
pixel squared) on 256 x 256, which separate an exact integer edge function from a float32 one
(what the main set could not).

The `fine_extra_p1138.py` of the frozen fine2 manifest had a bug that this set exposed: for a
vertex unit equal to 1/256 (the tiny-edge cases) `snapped()` took a grid step of one unit and its
half-up rule added one unit to every coordinate. The first analysis of fine2 therefore said PH3
failed (51 of 80 tiny edges equal to the model); the fix (a grid step of one unit returns the
vertices unchanged, in `fine_extra_p1138.py`, so the file no longer matches
`manifest-fine2-1138.sha256`) gives 80 of 80 and PH3 passes. The fine set (units 12 and 16) never
reached that branch and its numbers are unchanged.
