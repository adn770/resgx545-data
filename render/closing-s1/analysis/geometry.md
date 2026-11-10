# S1 analysis, geometry stages (g-e1 to g-e5)

Run 2026-11-09 on the laptop (kernel 7.3.0-resgx545, module srcversion B21FDA82BD5E5CB5A627E3B
installed = loaded, firmware sha256 6a00268e..., tool `~/sgxfive-test-s1` sha256 d776afbc...,
regtimeline 079f6359...; every stage `files verified` against FROZEN.sha256; health ok after every
stage). Analysis read-only on the Mac, nothing committed. Helper scripts (all post hoc, numpy venv):
`analysis/scripts/geo_*.py`. Paths below are relative to `closing/s1/`.

Rule used throughout: the frozen verdict (`out/score-STAGE.txt`) is the result. Everything marked
**post hoc** was read after the run with code written after the run; it is not held out and not
confirmed, and each such item names the frozen run that would confirm it.

## g-e1 (Q273, Q210): the raise below P = 0x422

**Frozen verdict.** `METHOD BROKEN: positive control p-1350-0x3e0 reaches thr0 and does not raise;
nothing is concluded.`

**Data [HW].** Knob proof passed in 22 of 22 jobs: the job's own 0x0624 = P - 0x22 at P = 0x200,
0x300, 0x3e0, 0x400, 0x410, 0x420 (and 0x400 at 0x422). Control `c-1500-0x422` equals E704 word for
word (peaks 0x400, 0x400, 0x11c; dwords 35-39 = 0x3fe, 3, 0, 0, 6). Raises (dword 37 = 1<<16 |
thr0, dword 38 = 0x20, second abort at thr0 + 0x20) in exactly two jobs: `p-1350-0x300` (thr0
0x2de -> 0x2fe) and `p-900-0x200` (0x1de -> 0x1fe, 3 partial renders, not the ~16 the PREFLIGHT
feared). No raise in the other 20, among them every job at P >= 0x3e0 whose second run reached
thr0: `d-1500-0x3e0` x2, `-0x400`, `-0x410`, `-0x420`, `p-1350-0x3e0`, the twelve ladder jobs. Per
job table: `analysis/scripts/geo_e1_dwords.py out/g-e1`.

**Cause of the failed control: hardware (premise false), exposed by a design choice.**
- The premise "1350 vertices raise at P = 0x3e0" was every hypothesis's prediction (HC, HA, HS, R2
  all `yes` in `predictions/g-e1.tsv`, where the row's set is `heldout`, not `control`). The proposal
  made it a conditional positive control ("pos. control if 2 reaching runs", fallback 0x300;
  `exp-dpm-geometry.md` E1 table) and the scorer, as the proposal's decision text says, stops on
  any positive control that reaches thr0 without raising (`score/score_geo.py:69-72`). The scorer
  did what the frozen design said; the design used a held-out prediction as a method control.
- The method itself works: the two other positive controls raised and the raise is read the same
  way as in E625 (dwords 37/38 and the second abort at thr0 + 0x20).
- So the failed control is itself a finding [HW]: a scene with dword 36 = 2 whose second run
  reaches thr0 does not raise at thr0 = 0x3be. That refutes, as worded, HA ("dword 36 <= 2 raises
  at every P"), HC with its ceiling at status 0x400 (0x3be + 0x20 = 0x3de fits under it), HS (it
  predicted the raise for 1350) and R2 (raise in every reaching cell), all on this one job.

**Post hoc.**
- Raise in 2 of 2 jobs with thr0 <= 0x2de, in 0 of 20 with thr0 >= 0x3be, at vertex counts 900,
  1350 (both sides), 1380-1497 and 1500. Read as a limit on the raised threshold: a raise only if
  thr0 + 0x20 <= C with 0x2fe <= C < 0x3de (a lower ceiling than HC's). The vertex count does not
  separate it here (1350 is on both sides).
- E625's own rule (raise iff 2 * thr0 < U + k) also predicts a raise for `p-1350-0x3e0`: taking U
  as the summed run peaks, 0x3be + 0x3be + 0x59 = 2005 pages > 2 * 0x3be = 1916.
- Dword 36 steps between 1350 (2) and 1380 (3) at both P = 0x3e0 and 0x422. At 0x3e0 both counts
  take 2 partial renders, so the step of dword 36 is not the step of the run count there: the
  confound of E630 (dword 36 and "second reaching run" step together at 0x422) is broken at 0x3e0.
- Dword 39 reads 5 in every job at P = 0x3e0 and in `p-1350-0x420`, 6 in the 1500-vertex jobs at
  P >= 0x400, the 0x422 ladder and both raises (meaning not established).
- To confirm (frozen, S1b): 1350 and 1500 at P = 0x320, 0x340, 0x360, 0x380, 0x3a0, 0x3c0 with the
  prediction "both scenes raise below one P and not above, the same P for both" against "the step
  P differs by scene"; plus 1350/1380 at 0x3e0 repeated for the dword-36 step; no job may be a
  positive control unless an earlier run raised under those exact words (p-1350-0x300 and
  p-900-0x200 now qualify).

## g-e2a (Q211): U of six K-triangle scenes

**Frozen verdict.** `U measured for 6 of 6 scenes (void or unusable: none); residuals are against
an empirical coverage proxy ... the formula needs sgx-pipe's stream bytes.` No hypothesis was
scored, by design (PREFLIGHT 3.2: HU1 not computed before the run).

**Data [HW].** Control `u-1-0x422` U = 19 (E705). U (peak 0x0724 = free-list walk - 1, agree in all
eight 0x422 jobs): 2a 29, 3a 35, 4a 37 (37 again in -r2), 2s 19, 3s 22, 4s 22 (22 again in -r2).
Open-kick lines K - 1 in every job. `u-2f-0x38` (E627's st-two-f) overflowed as E627 did.
Extra repeats from `out/g-e2a.run1-stopped` (that run lost its dumps, timelines intact): u-1 19,
u-2f peak 22, u-2a 29, identical.

**Notes on the scorer (no verdict depends on them).** `u-2f-0x38` shows "DISAGREE" (peak 22,
walk 26): by design, an overflowing job's peak is capped at thr0 = 0x16 = 22, so the peak/walk
agreement cannot hold there. Its frozen predictions `outcome overflow` and `lists_sum 21` are not
read by the scorer at all (`score/score_geo.py:157-169` gates on u-1 only); post hoc the outcome is
overflow, matching.

**Post hoc.** The second stacked triangle (moved 16 px) added 0 pages (19 = one triangle), the
third 3, the fourth 0. Apart layouts add 10, 6, 2. Not a formula; data for HU1 when sgx-pipe's
stream bytes exist.

## g-e2b (Q211): E625's overflow rule on K-triangle scenes

**Frozen verdict.** `E625's overflow rule holds on 12 boundary/count jobs (held out)`.

**Data [HW].** All 12 boundary jobs as predicted (overflow at P = U + 0x21, completion at U + 0x22),
knob proof per job; the generator's input `out/g-e2b.generated-from.json` = the frozen U.json.

**What the verdict covers (post hoc reading of the kept output, `analysis/scripts/geo_runs.py`).**
- In 10 of 12 the outcome is that of the K-triangle scene (every kick but the last printed
  "geometry only, the scene left open"). In `b-2s-lo` kick 1 itself overflowed (thr0 0x12 = 18 <
  19, one triangle's need: U(2s) = U(1)), and in `b-4s-lo` kick 3 overflowed (thr0 0x15 = 21 <
  U(3s) = 22). The rule holds for the scene that was actually open in both; it is not a test of
  the 2s and 4s scenes. The e2b scorer does not check the open-kick lines, unlike e2a
  (`score/score_geo.py:185-192` against `:146`).
- `k-4a-P1` and `k-4a-P2` (the count jobs for k and the spacing): every frozen (k, s) pair
  predicted 1 or 2 partial renders; 3 were counted. The scorer never reads the `nparts`
  predictions (`score/score_geo.py:186`, only `outcome`; the summary's "(k, s) interval printed
  above" prints nothing). **Cause: design.** At thr0 = 5 and 6, below one triangle's need, kicks 1,
  2 and 3 each overflowed on their own ("tri 1024x768 #1: overflowed", "#2", "#3"; kick 4 alone
  completed), so no 4-triangle scene formed: the 3 stretches are three one-triangle scenes with
  one partial render each, which is E625's 1024x768 count (1). The count predictions are void,
  not refuted. An overflow ends the open scene and the tool goes on with a new one.
- Post hoc also: every overflowed kick of the k jobs shows the raise in its control block (dwords
  37/38 = 0x10005/0x20, 0x10006/0x20), as E625's rule predicts at thr0 5 and 6.

## g-e3 (Q230): what the TA writes

**Frozen verdict.** `cannot tell: controls failed or void: ['e3k-ctl']`.

**Data [HW]** (decoded objects: `analysis/scripts/geo_e3_objects.py out/g-e3`). Five of six
controls pass: `e3w-w1`, `e3z-flat099`, `e3c-w1` equal E651's object; `e3o-x1000` writes no object;
`e3f-ctl` packs the 1/256 vertices as E651. `e3k-ctl` (w = 1e-5 every vertex, WCLAMP blk:14 =
1e-3) writes an object: 4 vertices, a 0.96-pixel square centred on (32, 32) (31.52 to 32.48), every
1/w word 0x4479ffff (= 1/1e-3 rounded toward zero), depth 0.5.

**Cause of the failed control: hardware (the premise is false at the object level), carried in
by the design.** E194 saw only the image: with blk:14 = 1e-3 the w = 1e-5 case "shows background
only". The design turned that into "no object" (`gen/s1geo3.py:170,176`). The object is written;
it is shrunk under a pixel centre (no centre lies in 31.52..32.48), which gives E194's background
image. The stored 1/w = 1/clamp says the clamp replaces w by the clamp value rather than removing
the triangle (post hoc, three jobs agree: in `e3k-above`, clamp one ulp above w = 1e-3, all four
1/w words are 0x4479fffd, the reciprocal of the clamp, while `e3k-eq` and `e3k-below` keep 1/w of w
itself; all three keep the full guard-band square, as the w = 1e-3 job without a clamp).

**Scorer against the frozen design.** The proposal's decision is per group ("Cannot tell: a group
whose control fails", `exp-dpm-geometry.md` E3; the table header repeats "Every group's control ...
before the group's cells count"); the scorer makes any failed control void the whole stage
(`score/score_geo.py:280-284`). Read per group as the design says (**post hoc**; all controls of
these groups passed):
- w scan: w = 2 and 0.5 store pack(x / w) exactly (HW-exact, 3 of 3 jobs with the repeat). w =
  1e-3 and 1e-5: neither RZ32 nor RN32 holds for all words, because the objects are guard-band
  clipped (4 vertices at -16 and 80) and the clip-made vertices carry 1/w words 2 ulps apart
  (0x4479ffff/0x4479fffd; 0x47c35000/0x47c34fff). That is a design limit (the prediction assumed
  the three original vertices are stored; none of them is, all four are clip-made corners), not a
  rule failure: two of four words equal the predicted 0x4479ffff (three of four 0x47c35000).
- z clip: flat triangles at 1.01 and -1.01 write no object (HR-none 2 of 2). Cut: `e3z-cut-p` 4
  vertices (2 of 2), `e3z-cut-m` 3 vertices (2 of 2) that are not the original three ((56,20),
  (32,44), (32,14)): the scorer's vertex count (`score/score_geo.py:246`, `nvert == 3` = HC-orig)
  cannot see a clipped triangle; by the vertices both cuts are clipped polygons (HC-poly).
- w clip: second vertex at w 0.1, 0, -0.05, -0.5: clipped polygons of 4, 4, 4, 5 vertices
  (HC-poly 4 of 4).
- off target (viewport x offset): object at 8 and 64, none at 128 (2 of 2), 512 and 1000: the
  frozen HO-region reading (no object once no region lists it), HO-guard refuted at 128.
- fine grid (1/1024): HF-round (r2, r3 split it; r1 fits both).
- guard-band scale jobs `e3g-*` carry no prediction: 8x gives 5 vertices (two at (80, 80)), 64x and
  1024x the 4-vertex guard square.
- To confirm (S1b): the same groups re-run with per-group gating frozen in the scorer, the cut
  scored by vertex identity, the w = 1e-3 / 1e-5 jobs scored on original vertices only (or with
  triangles that stay inside the guard band), and a WCLAMP control predicted from the post-hoc
  rule ("w below the clamp is replaced by the clamp: 1/w = 1/clamp, x and y divided by the clamp").

## g-e4 (Q112): index header bits 25:24

**Frozen verdict.** `control ok; ix-24: HH (hang in 2 of 2); ix-25: HW signature (fault in 2 of
2); ix-2425: HW signature (fault in 2 of 2)`.

**Data [HW].** `ix-c` = E414's five-copy object (15 vertices, 67 dwords). Bit 24 alone: `job N
hung, recovering`, rc 3, "SGX stopped, 1 events seen", 2 of 2. Bit 25 alone and both: `BIF fault
0xd0008 at 0x1`, rc 3, "0 events seen", 4 of 4 (the same word and address each time). Recovery and
health fine. This is a frozen held-out result with a passing control.

**Post hoc.** The fault word 0xd0008 at 0x1 appears in no landed record (0xd0400 at 0x1 does,
E458/E462). Bits 24 and 25 do different things, so they are not one 2-bit field read as "16 vs
32": whichever is the width select, the signature (a fault) is HW's for bit 25. This justifies the
positive test the proposal scheduled for HW: `--index-width 32` (write the index buffer as 32-bit
words, set the bit), with the unflipped header over the 32-bit buffer as its negative.

## g-e8 (12.4 data; Q088, Q241): two objects over a loaded depth

**Frozen verdict.** `cannot tell: one-object controls void or not equal to the model
({'o1-less-ctl': 4224, 'o1-never-ctl': 0})`.

**Cause: design.** The control word `--depth-ctl 0x0017100e` (`tables/g-e8.txt`) has bit 1 but not
bit 14. E664 (and E665) state that the depth load needs bits 1 and 14; without them the pass starts
from the clear value 1.0. The depth buffer was filled with 0.25 but never loaded, so `less` drew
the whole triangle (green 4284 pixels; the tool's own one-triangle check passed, rc 0). The
stored depth dump agrees: 1.0 at the uncovered stored dwords, 0.25 only where the fill was not
overwritten (`analysis/scripts/geo_e8_depth.py`).

**Post hoc** (`analysis/scripts/geo_e8_union.py`). With the frozen model's code and the depth
starting at 1.0, the drawn/undrawn mask matches all 8 jobs exactly (0 pixels differ). In the
two-object jobs every drawn pixel is red and the background is render 2's (0xff000080): the tool
rewrites the context's pixel-program page for every render (`src/render.c:400-404`, memset and
`put_pixel_programs`, colour by render index `tools/sgxfive-test.c:2896`), so the object of the
geometry-only kick is shaded with the closing render's colour. So E8a cannot show list order by
colour with this tool even with a working load (design). The stopped run
(`out/g-e8.run1-stopped`) repeats both controls with identical images.

## g-e8b (Q073, Q241): translucent order

**Frozen verdict.** `controls pass; hypotheses consistent with all six jobs: HD-depth-order,
HP-pass-order` (HL-list-order refuted by t-2-far and t-1-far).

**Design note.** HD and HP predict the same winner in all six jobs (`predictions/g-e8b.tsv`), so
the table could not separate them. **Post hoc:** the four translucent images are pixel-identical
to the opaque controls (sha256 of the rows: near 47d0e49e..., far 93b00bba... for opq, 2 and 1),
so "pass type 1 has no visible effect here" (not a frozen hypothesis) fits as well as HD and HP.

## g-e5 (Q272, Q164): do the three events repeat?

**Frozen verdict.** `controls reproduce E702; r-n8-a7: HD (3 of 3); r-n8-a12: HO (0 of 3); r-n8-a8:
HI (2 of 3: not a function of the words); r-n2-a32: HD (3 of 3).`

**Data [HW].** Controls 2288 and 2821 (E702). a7: 2285 x3. a12: 2582 x3. a8: 2288, 2156, 2156.
a32 at N = 2: hang x3 (as E702).

**Scorer label for a12.** The frozen proposal defines HO for a12 as "x2288, 0 of 3" and HD as
"x2028 ... 3 of 3". The scorer only compares with 2028 and calls any 0 of 3 "HO"
(`score/score_geo.py:374-386`). The render was 2582 in 3 of 3: it is neither HD (E702's histogram)
nor HO (the base). Correct reading of the frozen definitions: the a12 change repeats 3 of 3
(deterministic) with a different histogram from E702's one job.

**Post hoc vertex fate** (q164_fate.py's functions on the S1 dumps,
`analysis/scripts/geo_e5_fate.py`): a7 r1-r3 lose ids 55, 66, 77 (unreadable, E702's three) 3 of 3;
a12 r1-r3 every vertex present, regular split 15 x 8 + 6 (E702's a12 had 15 x 7, 9, 12); a8 r1
clean, r2 and r3 lose vertex 70 with objects split 15, 15, 15, 15, 9, 15, 9, 15, 15, 3: E546's lost
vertex at 33 with 8 rows, seen again in 2 of 3 runs, the same vertex both times.

## Questions (geometry side)

| question | outcome now | basis |
|---|---|---|
| Q273 | narrowed (knob clause, frozen per-job proof); main clause unchanged | knob lands P = 0x200..0x420; raise clause void (METHOD BROKEN); post hoc: no raise at P >= 0x3e0 for 1350 and 1500, dword 36 steps 1350 -> 1380 |
| Q210 | unchanged | frozen: nothing concluded; post hoc: R2 and E625's rule fail at thr0 0x3be for 1350, a lower limit 0x2fe <= C < 0x3de fits |
| Q211 | narrowed | frozen: E625's overflow rule held out on K-triangle scenes (12 of 12, 10 as K-scenes); U measured for 6 scenes; formula and k unchanged (count jobs void by design) |
| Q230 | unchanged (frozen cannot tell) | post hoc per group: HR-none, clipped polygons, HO-region, HF-round, w exact at 2 and 0.5, WCLAMP replaces w |
| Q112 | narrowed | frozen: bit 24 hangs, bit 25 and 24+25 fault (0xd0008) 2 of 2 each, control ok; width needs `--index-width 32` |
| Q272 | narrowed: repeat clause closed for a7 (3/3) and the a32 hang (3/3) | frozen HD; a12 repeats a change 3/3 but not E702's (post hoc reading of the frozen definitions); a8 split 2/3 |
| Q164 | unchanged | post hoc: a8 loses vertex 70 in 2 of 3 with a 9, 9, 3 split |
| Q073 | unchanged | HD vs HP not separable by the table; translucent images equal opaque |
| Q088 / Q241 | unchanged | E8a's load did not happen (bit 14 absent), as E664 predicts |
