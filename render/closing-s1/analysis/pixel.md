# S1 pixel stages: analysis of the frozen verdicts (p-b1, p-c, p-g, p-b2, p-d, p-f)

Run 2026-11-09 on the laptop (cedar), stages in `out/STAGE/`, frozen scores in
`out/score-STAGE.txt`.  This file is an analysis written after the run.  Everything marked
**post hoc** was read after the verdicts and is not held out; it confirms nothing.  The frozen
verdicts stand as printed.  Helper scripts (numpy, scratch, not frozen):
`analysis/scripts/pixel_*.py`, run with `../pixel-faults/.venv/bin/python -I`.

Summary table

| stage | frozen verdict | cause of the failed control / cannot tell |
|---|---|---|
| p-b1 | cannot tell (g-ctl, g-dyadic EMPTY) | scorer bug (clear depth counted as covered), then design (one line per row is false beyond one tile) |
| p-c | cannot tell (c-u 0.990) | hardware: the order premise fails in 5 of 497 sources; criterion exact 1.0 |
| p-g | cannot tell (no transition) | design: u, v constant, the output does not resolve a 1/64 LOD step over a 0.03-step ladder |
| p-b2 | control ok; d-shift neither set | scorer bug (clear depth counted as covered); post hoc d-shift has no deviation at all |
| p-d | cannot tell (mixed) | generator bug: the 64-page jobs were scored against the 16-page A4 hash (all 0xDEADBEEF) |
| p-f | control ok; pairs exact 2/2; dc0 "split"; 1f fault | scorer label bug (dc0); design (mask 0x1f contains buffer 0) |

## p-b1 (B1, Q288: the effective depth gradient)

**Frozen verdict** (`out/score-p-b1.txt`): "SUMMARY: cannot tell: controls failed or unusable (g-ctl:
EMPTY, T16 inside and f32 outside required; g-dyadic: EMPTY, f32 inside required)".  All 11 jobs
read "0/32 (row 0 empties)".

**Data.** 11 jobs, rc 0, class ok, a depth dump each (`out/p-b1/NAME.depth.1.bin.gz`, 49152
dwords = 48 pages), echoed vertices equal to the table.  The tool's own line for g-ctl: `depth #1:
49152 dwords, 32768 changed, 450 distinct; 0x3f800000 x 20496, 0xdeadbeef x 16384, ...`: the ZLS
writes the clear depth 1.0 to every pixel of the 1024 x 32 target the triangle does not cover
(20496 of 32768).  g-r2 and g-r2-rep are byte-identical.

**Cause 1: scorer bug.**  `score/score_pix.py:49` (`row_ranges`): `cov = (z != BG) & (z != 0)`
counts the cleared 1.0 (0x3f800000) as covered.  Every row of these jobs has the triangle on its
left (about 400, 512, 700, 900 or 1024 px minus y) and 1.0 on the right, so no single line fits
any row and the scorer reports EMPTY at row 0 for all 11 jobs.  The test that validated the reader
(`tests/test_scorers.py:57-61`, E731's dp-bx-b0 on 256 x 128) has no cleared pixel in its rows
(the triangle covers the whole target), so it could not catch this.

**Correct reading (post hoc, `pixel_b1_posthoc.py`: the same code with 0x3f800000 excluded):**
- g-dyadic: 32/32 rows, joint range of width 16.06 ulps of A, f32 and every other rule inside
  (all 16 rules give the same word 0x39000000).  The frozen status rule (`score_pix.py:122`,
  width > 4 ulps is WIDE) would still mark it WIDE, so the control would still fail.
- g-ctl and 9 of 10 ramps: still EMPTY at row 0.  g-r7: feasible (963 ulps wide, uninformative).
  No rule is inside on all 8 ramps.

**Cause 2: design (the premise of the control is false at this width).**  Post hoc
(`pixel_b1_prefix.py`): in g-ctl one line fits only the first 32 pixels of row 0 (one tile), 160
of row 16, 288 of row 31; in every non-dyadic ramp the fit stops at 32 to 96 pixels.  The tile
starts drift against the exact plane by about -0.08 ulp per tile and step back at tile 11
(`pixel_b1_row0.py`); inside a tile the step is 2621 or 2622 ulps for A x 2^24 = 2621.44.  The
frozen control premise ("nine rules agree on dp-bx-b0's row fit") came from E731's 256 x 128 dump
(rows 0 to 106 fit one g).  Post hoc (`pixel_b1_vs_e731.py`), the same plane (A = 1/6400, z0 =
0.5) stored on the 1024 x 32 target differs from E731's dp-bx-b0 in 167 of 8192 shared pixels by
+-1 ulp (e.g. row 0, x = 28, 60, 92, ...: one more), and that alone empties the row fit
(`row_range` on g-ctl x < 256: 0 rows; on dp-bx-b0 rows 0 to 31: 32 rows).  So the stored depth
of one plane depends on the target (its width here); a row-wide single-gradient fit is not an
observable that transfers between targets.  E731 had already found 0 of 58 x-tiles of dp-bx-b0
fitting a single T, and Q288's "one g fits rows 0 to 106" is a property of that one target.  A
tile-segment fit (`pixel_b1_tile.py`) also empties on every non-dyadic job.

**Post hoc observation for later (not a result):** the same plane on two targets differs by +-1
ulp in 2% of pixels; B2 below shows the same kind of dependence (d-tall).  A shared candidate is
that the plane is set up from the clipped polygon (g-e3 shows the TA stores clipped polygons with
new vertices), which differs with the target size.  A frozen run must test it (S1b).

**Outcome for Q288: unchanged** (controls failed; the planned observable does not work).  The
post-hoc facts narrow the method, not the question.

## p-c (C, Q276: a guard that cannot hold)

**Frozen verdict** (`out/score-p-c.txt`): "SUMMARY: cannot tell: controls failed or void (c-e709
tag-5 pairs 17..29: 22; c-u must show tag 2 everywhere: 0.9899396378269618); void []".

**c-e709 passed** (22 tag-5 pairs, inside 17..29).  The failure is c-u alone: `score_pix.py:271`
requires `u["frac"] == 1.0` exactly.

**Cause: hardware (the control's premise is false in a small cluster), with a strict criterion.**
Post hoc (`pixel_c_posthoc.py`): c-u (both o1 writes unpredicated, tag 2' first, tag 2 second)
gives tag 2 for 492 source pixels and tag 2' for 5: sources (16,25), (16,27), (17,27), (18,27),
(19,27), landing at destinations (48,9), (48,11), (49,11), (50,11), (51,11); none of these five
sources has tag 2 elsewhere.  So in one contiguous cluster the first unpredicated write is what
lands, not the second: "the second write wins" holds for 492 of 497 sources, not all.  That is a
finding (one run, not repeated).  It is not a decode error: x and y tags agree and the other 492
sources decode to tag 2.  Also: E709's pair count is not deterministic and neither is this
layout: c-k7-x-rep differs from c-k7-x in 36 dwords (`pixel_c_rep.py`: o4 tag-5 and o1 tag-2'
landings appear or move), although the scorer never compares the replicate (`score_pix.py:241`
strips `-rep` and the replicate is not scored).

**What the frozen hypotheses would give (post hoc, controls failed, nothing confirmed):**
- c-k7: 0 tag 2, 483 tag 2': HP and HA predict 0.0 (consistent), HN 1.0 (inconsistent).
- c-k0: 0.252, tag 2 only at source parity (0,0); c-k3: 0.248, only at (1,1).  HP (0.25)
  consistent, HA (0|1) and HN inconsistent.  The lane of g25 follows the pixel's position in the
  2 x 2 quad: k = 0 is (even, even), k = 3 is (odd, odd).
- c-g23: 0.253 against HP's frozen 0.5 (`gen/s1pix.py:192`, a value the generator chose; the
  proposal said only "pixels split by the bit").  Tag 2 sources concentrate where sx mod 8 < 4 and
  sy mod 8 < 4 (25 to 28 per residue against 4 to 8), not 2 x 2 quads.
- By the proposal's own rules (HN refuted by any 2', HA by both tags in a job, HP by tag 2 at
  k = 7): HN and HA would be refuted, HP not; the g23 fraction was mispredicted.

**Outcome for Q276: unchanged in status** (no frozen verdict).  Post hoc it is strongly suggested
that the predicate gates o1 per instance with g25 = the lane in the quad; a frozen rerun is needed.
Q023 (output room) gains the c-u cluster as a post-hoc oddity only.

## p-g (G, Q280: the footprint's precision)

**Frozen verdict** (`out/score-p-g.txt`): "SUMMARY: cannot tell: ladders void or without a
transition (measured nothing): [all eight ladders]".  The control g-ctl-lf-r8 reproduced E721's
image sha256 (MATCH).

**Data.** Each ladder writes one constant dword over all 2048 pixels: g-s2 0xd00001aa, g-s13
0xd00004aa, g-s22 0xd00006aa, g-s56 0xd0000eaa; the replicates are identical.

**Cause: design.**  The ladders hold u and v constant (`mov r24, #0x3fbf0000; mov r25,
#0x3f810000`, `gen/s1pix.py` p_g) and sweep LOD*64 over only 0.031 of a 1/64 step (columns 0 to
63: 12.98438 to 13.01514 for n = 13, likewise for the others).  E721's lf ladders ramped u with
the column (its row 0 changes every few columns), so E721 never showed that a point-sampled raw
dword changes with the LOD fraction alone; PREFLIGHT 4.16 flagged this and the stage made it its
first check.  Post hoc: the output does depend on the LOD (bits 8 to 11 are 1, 4, 6, 14 for n = 2,
13, 22, 56, roughly n / 4), so its resolution is near 1/16 of a level, not 1/64: a ladder 0.03 of
a 1/64 step wide cannot show a transition unless it sits exactly on one of those coarser
boundaries.  Not the scorer (it reads row 0 correctly; there are no changes to read), not the
hardware premise of Q280.

**Outcome for Q280: unchanged.**

## p-b2 (B2, Q200: the lower-binade deviation region)

**Frozen verdict** (`out/score-p-b2.txt`): "SUMMARY: control reproduces dp-ax-b2; cannot tell:
d-shift matches neither set (Jaccard above)" (Jaccard 0.000 against HT and HV).

**The control passed for real**: d-ctl's deviation map equals E731's dp-ax-b2 set (7680 pixels at
-1 ulp, 1536 at -2, per tile row 0, 0, 256, 768, 1280, 1792, 2304, 2816, line x + 2y >= 319).
That is a frozen, held-out reproduction of E731's correction on a new run.

**Cause of the d-shift result: scorer bug.**  `gen/b2model.py:45` (`deviation`, used by
`score_pix.py:181`): `cov = (z != BG) & (z != 0)` counts the cleared 1.0 as covered.  d-shift
(triangle moved by (64, 32)) leaves 14336 pixels at 1.0; their "deviation" from the extrapolated
plane is 57 to 118 million ulps, 32 or 128 pixels per value (the table's huge keys), and they fill
the observed set, so the Jaccard is 0 against both.  The same bug produces the d-tall and d-ygrad
rows (32896 cleared pixels each, x + y >= 512, counts 256 down to 1).

**Correct reading (post hoc, `pixel_b2_posthoc.py`, clear excluded):**
- d-ctl: unchanged (equal to the frozen control set).
- d-b3 (z0 = 0.0625): 4608 at -1, 3072 at -2, 1536 at -3, the same 9216 pixels and the same line
  as d-ctl (frozen qualitative prediction "more, larger": same count, larger deviations).
- d-shift: **no deviating pixel** (18432 covered, all equal to trunc32 of the exact plane).
  Jaccard 0 against HT (9216 predicted) and HV (1024 predicted): both hypotheses fail.
- d-tall (same triangle and z as d-ctl, target 256 x 512): **no deviating pixel**, also in rows 0
  to 127, which d-ctl shares.  d-ygrad (gradient in y, 256 x 512): no deviating pixel.
So the region is neither tied to target coordinates (HT: d-tall's first 128 rows would equal
d-ctl's) nor to the triangle (HV: d-shift would carry it): it appears on the 256 x 128 target with
the triangle at the origin and vanishes when the target grows or the triangle moves.  Candidate
(post hoc only): the depth plane is set up from the clipped polygon, and the clip differs between
these jobs (on 256 x 128 the vertices (512,0) and (0,512) are both far outside; on 256 x 512 the
second lies on the edge).

**Outcome for Q200: narrowed by the control only** (frozen and passing: the x + 2y >= 319 region
of dp-ax-b2 reproduces on a new run, 7680 + 1536 pixels).  The HT/HV question is unanswered by the
frozen scorer; post hoc both fail.  Not closed.

## p-d (D, Q281: the 64 KiB scratch)

**Frozen verdict** (`out/score-p-d.txt`): "SUMMARY: cannot tell: mixed outcomes {'d-L2e2-64':
('ok', False), 'd-L3e3-64': ('ok', False), 'd-st-L3e2-64': ('ok', False)}".  Controls passed:
d-ok-64 A4 exact; d-L2e2-16 faulted (dmesg: `BIF fault 0x90002 at 0x3e017001 ... recovering`).
Every scratch line matched the knob (256, 84, 80, 64 KiB).

**Outcomes (frozen data):** the three 64-page jobs completed (rc 0, no fault line), so did
d-L2e2-21 (84 KiB) and d-L2e2-20 (80 KiB; both HB and HX predicted a fault).  d-L2e2-20's kernel
slice is empty: no fault.

**Cause: generator bug (the prediction).**  `gen/s1pix.py:356` takes `cj[label]["preds"]["A4"]`
from E722's `cases.json`, which was rendered for a 16-page scratch.  For the three faulting cases
that hash (9568c92a...) is the image of all 0xDEADBEEF (`pixel_d_a4hash.py`), the out-of-buffer
sentinel of the model (`resgx545-data/texture/p1141/support/texmodel.py:20`, `OOB = 0xDEADBEEF`:
"a read outside the scratch buffer (the job would fault)").  PREFLIGHT 4.18 noticed that the three
share a hash but not why.  So "DIFF" says only that the jobs did not fault-pattern; it is no test
of A4.  Not hardware, not the scorer's logic.

**Correct reading (post hoc, `pixel_d_a4pages.py`: E722's own model, `recompute/tex2.py` with the
A4 options of `gen/cat1141.py:98`, rendered with `pages` = 64, 21, 20):**
- d-L2e2-64, d-L3e3-64, d-st-L3e2-64, d-L2e2-21: A4 equal on 2048 of 2048 pixels each; "A4 shift
  idx only" 0 of 2048 on all, "A4 stride chain" 0 of 2048 on d-st-L3e2-64.
- The reads (dword index of the fill): L2e2 bytes 81920 to 84979, L3e3 172032 to 173539,
  st-L3e2 86016 to 92275.  (The proposal's "85 KiB" and "170 KiB" extents belong to st-L3e2 and
  L3e3 respectively: swapped labels, no effect on the jobs.)
- d-L2e2-20: the model reads past 80 KiB (OOB everywhere); the hardware completed and returned
  words without the 0xD tag (0x0 to 0xb003c, 128 distinct): it read mapped memory after the
  scratch without a fault.  The fault at 16 pages is at 0x3e017001 = scratch base 0x3e003000 + 80
  KiB, i.e. where the 20-page buffer ends; so the end of the probe's scratch is not the fault
  limit; what is mapped past it is (another buffer of the job's memory).

**Outcome for Q281: unchanged by the frozen verdict.**  Post hoc the first half ("complete and fit
A4 when the buffer is larger") is answered yes on 4 of 4 completing jobs, with a fault word only at
16 pages; that needs a frozen rerun with the 64-page prediction.  "How large is the buffer the
sampler may read": not the 64 KiB as such: the fault follows the mapping.

## p-f (F, Q076: which pages each requestor needs)

**Frozen verdict** (`out/score-p-f.txt`): "SUMMARY: control reproduces E573; f-12: exact 2 of 2;
f-13: exact 2 of 2; f-23: exact 2 of 2; f-45: exact 2 of 2; f-15: exact 2 of 2; f-all15: exact 2
of 2; f-3r: exact 2 of 2; f-dpm-dc0: split ['ok', 'ok'] (third run); f-dpm-1f: fault 0x91000 2 of
2 (needed: HJ)".  Knob proof present for every job (`resgx545 s1 readback NAME alias_skip=...` in
`out/p-f/kernel.log`, and render_pb_pages=0x23 for the f-dpm jobs).

**This stage has a frozen held-out verdict with a passing control**: f-ctl0 faulted 0x91000 at
0x3000b021 twice (E573).  HI (a buffer is needed only if leaving it out alone faults) holds and HJ
(a pair is needed together) is refuted for the pairs {1,2}, {1,3}, {2,3}, {4,5}, {1,5}, for 1 to 5
together, and for three renders with 6, 7, 8, 10, 11 left out (HJ predicted a fault on the third
render): 14 of 14 runs exact.

**f-dpm-dc0 "split ['ok', 'ok']": scorer bug.**  `score_pix.py:394` labels a run "exact" only if
the tool prints `tri: \d+ renders ok`; with `--keep-overflow` the tool prints `tri: 0 of 2 renders
ok, 2 overflowed`, so both runs get "ok", and `score_pix.py:411-416` sends two identical results to
the "split" branch.  The data: both runs overflowed by design (P = 0x23), `diff: 0 of 786432
pixels` for each render, identical target hashes in both runs (0xc9e301d225fe2325,
0xed1bce7108aded25).  Correct reading (post hoc): exact 2 of 2 under partial renders, consistent
with HI.

**f-dpm-1f "(needed: HJ)": design error, and an over-reading label.**  Mask 0x1f contains bit 0,
buffer 0 (`gen/s1pix.py:403`; the proposal's table has it too), and f-ctl0 (mask 0x1) faults the
same way.  f-dpm-1f's fault, 0x91000 at 0x3000b021, is the address and word of f-ctl0's: it is
buffer 0's fault and says nothing about a pair among 1 to 4.  `score_pix.py:413-414` labels any
two faults "needed: HJ" regardless of the mask.

**Outcome for Q076: narrowed (frozen, held out, control passing):** with the TA3D control block
kept, none of the pairs {1,2}, {1,3}, {2,3}, {4,5}, {1,5}, nor 1 to 5 together, is needed by a
two-render job; 6, 7, 8, 10, 11 together are not needed over three renders.  Not closed: the
partial-render case has only the post-hoc reading (scorer label), the mid-job reassignment part
was not run, and "which list" is unchanged.  Q286 and Q003: not touched by p-f beyond reproducing
E573's fault word (0x91000) twice more; unchanged.

## Questions touched by the pixel stages

| question | outcome | basis |
|---|---|---|
| Q288 | unchanged | controls failed (scorer bug + premise false at 1024 width) |
| Q200 | narrowed (control only) | d-ctl reproduces E731's region on a new run, frozen; HT/HV unanswered |
| Q276 | unchanged | c-u control failed; post hoc per-lane gating |
| Q023 | unchanged | post hoc: c-u's 5-source cluster where the first write lands |
| Q280 | unchanged | no transition (design) |
| Q281 | unchanged (frozen); post hoc yes for 64 pages | prediction taken from the 16-page model |
| Q076 | narrowed | pairs and 1-5 not needed, three renders without 6-11 exact; frozen, held out |
| Q286, Q003 | unchanged | E573's 0x91000 reproduced 4 more times (f-ctl0 2, f-dpm-1f 2) |

## S1b for the pixel stages (smallest first)

1. **p-f rescore and one job** (no tool change): fix `score_pix.py:394` to accept `tri: 0 of N
   renders ok, N overflowed` with every `diff: 0` as exact under `--keep-overflow`; replace mask
   0x1f by 0x1e (buffers 1 to 4) for f-dpm; 2 x 2 jobs.
2. **p-d frozen rerun** (no tool change): predictions rendered with the job's own pages
   (`tex2.predict(spec | {"pages": N}, ...)`), the 64-page and 21-page A4 hashes frozen; add 17,
   18, 19 pages for L2e2 to place the fault between 64 and 80 KiB, and a dump of what lies past the
   scratch (the d-L2e2-20 words); 7 jobs.
3. **p-b2 frozen rerun** (scorer fix only): exclude 0x3f800000 in `b2model.py:45`; freeze the
   post-hoc reading as hypotheses: region present only when the clip differs (HCLIP) vs target-tied
   vs triangle-tied; jobs d-ctl, d-tall (256 x 512), a 256 x 256 and a 256 x 192 target with the
   same triangle, the d-shift job, d-ctl with the triangle shrunk inside the target (no clip), each
   with `--dump-render` of the parameter buffer so the stored (clipped) vertices are read; 8 jobs.
4. **p-c frozen rerun** (no tool change): c-u as two or three repeats with a criterion frozen at
   >= 0.98 (or the cluster named), the replicate compared (scorer bug at `score_pix.py:241`), HP's
   g23 prediction frozen from the post-hoc 8 x 8 pattern or dropped to "two tags"; 15 jobs.
5. **p-b1 redesign** (scorer fix + design): exclude 0x3f800000 (`score_pix.py:49`); replace the
   row-wide line fit by a per-pixel within-tile step reading (Q288's own plan: one tile row, B =
   0, the step per pixel inside a tile, then the tile-to-tile step), on the 256 x 128 target E731
   used, so that the control reproduces dp-bx-b0 word for word; the g-dyadic WIDE threshold
   (`score_pix.py:122`) set from the observed 16 ulps or removed for the dyadic control.
6. **p-g redesign**: ladders that span at least one full 1/16 level step (pitch 1/64 step per
   column or coarser) to find where the output changes at all, then a fine ladder around the found
   boundary; freeze "the output resolves LOD in 1/16 steps" as a hypothesis from the post-hoc
   values (1, 4, 6, 14 for n = 2, 13, 22, 56).

Tool changes needed: none for 1 to 4; for 3 a `--dump-render` on `tri` depth jobs if the tool
lacks it for `tri` (it exists for `probe`); scorer fixes as listed.  Not pixel: `--index-width 32`
and `tri --move` with `--tri-v` belong to the geometry list.

## Record material

### p-b1 (B1)
- Claim: "On a 1024 x 32 target the frozen B1 scorer read no row of any of 11 depth jobs (all
  EMPTY at row 0) because it counted the cleared depth 1.0 as covered; the controls failed and
  nothing is concluded about the gradient rule."
- Data: `closing/s1/out/p-b1/` (cases.tsv, NAME.txt.gz, NAME.depth.1.bin.gz),
  `out/score-p-b1.txt`, predictions `predictions/p-b1.tsv`.
- [HW] 11 jobs rc 0; ZLS cleared 20496 of 32768 pixels to 0x3f800000 in g-ctl; g-r2 and g-r2-rep
  byte-identical depth dumps.
- Post hoc: with the clear excluded g-dyadic fits all 32 rows (16 ulps wide, all rules inside),
  g-ctl and 8 ramps stay EMPTY; one line fits only 32 to 96 px of a row; the same plane differs
  from E731's dp-bx-b0 in 167 of 8192 shared pixels by +-1 ulp (depends on the target).

### p-c (C)
- Claim: "The order control c-u (both o1 writes unpredicated) showed the second write in 492 of 497
  source pixels and the first in 5 (one cluster); the frozen scorer required all, so C is cannot
  tell; c-e709 reproduced 22 tag-5 pairs."
- Data: `closing/s1/out/p-c/`, `out/score-p-c.txt`, `predictions/p-c.tsv`, programs `bins/s1c-*`.
- [HW] c-e709 22 pairs; c-u 492/5 with the five sources (16,25), (16,27), (17..19,27); c-k7-x-rep
  differs from c-k7-x in 36 dwords.
- Post hoc: k7 0 tag 2; k0 0.252 all at (even, even); k3 0.248 all at (odd, odd); g23 0.253
  (frozen HP said 0.5); HN and HA would be refuted, HP not.

### p-g (G)
- Claim: "Eight LOD ladders with u and v constant (each 0.031 of a 1/64 step wide) wrote one
  constant dword over all 2048 pixels, so no transition was measured; the control reproduced
  E721's lf-r8 image."
- Data: `closing/s1/out/p-g/`, `out/score-p-g.txt`, `predictions/p-g.tsv`.
- [HW] g-s2 0xd00001aa, g-s13 0xd00004aa, g-s22 0xd00006aa, g-s56 0xd0000eaa, replicates equal.
- Post hoc: the constant tracks n coarsely (bits 8 to 11 = 1, 4, 6, 14), resolution near 1/16.

### p-b2 (B2)
- Claim: "d-ctl reproduced E731's dp-ax-b2 deviation region exactly (7680 pixels at -1 ulp, 1536 at
  -2, x + 2y >= 319); the d-shift verdict is void in effect because the scorer counted the cleared
  depth 1.0 as covered."
- Data: `closing/s1/out/p-b2/`, `out/score-p-b2.txt`, `predictions/p-b2*.`
- [HW] d-ctl set equal to the frozen set; d-b3 the same 9216 pixels at -1, -2, -3.
- Post hoc: with the clear excluded, d-shift, d-tall and d-ygrad have no deviating pixel; HT and HV
  both fail; the region depends on the target or the clip.

### p-d (D)
- Claim: "With the probe's scratch at 64 pages the three T3 jobs that faulted at 16 pages
  completed, as did 21 and 20 pages; the frozen A4 hashes were those of the 16-page model (every
  pixel out of buffer), so the image test is void; d-L2e2-16 reproduced the fault 0x90002."
- Data: `closing/s1/out/p-d/`, `out/score-p-d.txt`, `predictions/p-d.tsv`.
- [HW] rc 0 for the 64-, 21- and 20-page jobs, no fault line; 16 pages: BIF fault 0x90002 at
  0x3e017001 (scratch base 0x3e003000 + 80 KiB); d-L2e2-64 and -21 identical images.
- Post hoc: A4 re-rendered with the job's pages fits 2048 of 2048 on all four completing jobs and
  separates from the two alternatives; at 20 pages the reads past the scratch return untagged words.

### p-f (F)
- Claim: "With alias_skip, leaving out any of the pairs {1,2}, {1,3}, {2,3}, {4,5}, {1,5} or all of
  1 to 5 kept two-render jobs exact (12 of 12 runs), and 6, 7, 8, 10, 11 out kept three renders
  exact (2 of 2); buffer 0 out faults 0x91000 at 0x3000b021 (2 of 2, E573)."
- Data: `closing/s1/out/p-f/` (kernel.log with readback markers), `out/score-p-f.txt`,
  `predictions/p-f.tsv`.
- [HW] the 14 exact runs; f-dpm-dc0 overflowed by design, diff 0, identical hashes in both runs;
  f-dpm-1f (mask 0x1f, includes buffer 0) faulted 0x91000 at 0x3000b021 twice.
- Post hoc: f-dpm-dc0 is exact 2 of 2 (scorer label "split" is a regex miss); f-dpm-1f is buffer
  0's fault, not HJ.
