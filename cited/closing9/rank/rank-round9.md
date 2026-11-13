# Round 9 ranking: what is closable beyond round 8's seeds (Opus, 2026-11-13, read-only)

Basis: resgx545 `main` 5e58278 (records to E946; E924-E929 unused), 162 open (152 hw, 10 parked);
data 2d666bfaf; linux fork `resgx545` 2a650d74 (read with `git grep` only); laptop on module
B60AB0B4 (fork 2a650d74) until its next reboot. Not planned here: the seeds (closing9/seeds: Q141,
Q108, Q284, Q177, Q210, Q211, Q283, Q260, Q139) and K1 (closing9/k1: `tri --bg-layer`, the
layer-sampling program, Q190's rows). Model: round 8's ranking (`closing8/rank/rank-round8.md`).

Scratch in this directory (standard library plus the published sampler model, no firmware-derived
content, publishable): `index.py`/`digest.py`/`xref.py` and their `.txt` (round 8's scripts rerun
on 5e58278), `tiers9.py`/`tiers9.out` (all 162 placed once, checked), Q282 `q282_fit.py`,
`q282_fit2.py`, `q282_fit3.py`, `q282_resid.py`, `q282_resid2.py`, `q282_score.py`, the freezes
`q282_rule{,2,3}.json` + `.sha256` and the `.out`; Q280 `q280_fit.py`, `q280_rule.json` +
`.sha256`, `q280_fit.out`, `q280_score.out`; Q078 `q078_b14_look.py`, `q078_b14.py`,
`q078_b14_rule.json` + `.sha256`, `q078_b14_fit.out`, `q078_b14_score.out`, `q078_b14_post.out`.

Reproducibility note: the scripts import the sampler model through
`resgx545-data/texture/p1141/recompute/lib.py`, which loads `texmodel.py` and `specs.json` from the
retired kit path. The bytes are those published: `texmodel.py` sha256 ffa41eb9... equals
`resgx545-data/texture/p1141/support/texmodel.py` and `resgx545/tools/texture/p1132/recompute/`;
`specs.json` 2b891d92... equals `resgx545-data/texture/p1141/support/specs.json`. A record citing
these scripts first points their imports at the published copies (fold step, no new result).

## 0. Findings (read first)

1. **Q078, T3 bit 14 in smp: the read is the control's dword plus a whole number of stride rows
   per unit of u, held out offline at 64 x 16** (`q078_b14_*.out`; E566's kept dumps,
   `resgx545-data/texture/p1132/tx-t3`, named memory: dword i reads 0xD0000000 | i). Read on the
   fit job s64x32-t3b14 (W = S = 64): dword' = i + 32 + 64 c (c the control's column), 2048 of
   2048. Six rivals for the constant (W/2, S/2, 32) and the multiplier (S, W) were frozen by hash
   (`q078_b14_rule.sha256` fbd25356...) before the two held-out jobs were read: **s64x16-t3b14
   2048/2048 for all six** (W = S there: they cannot separate) and **s32x32-t3b14 0/2048 for all
   six** (W = 32, S = 64: all refuted) [HW data, held out offline]. Post hoc (`q078_b14_post.out`,
   not frozen): R-U, dword' = i + S * S * (c + 1/2) / W, i.e. the row moves by u * S [infer: a
   shear by the normalised u], is exact on 2048, 2048 and 1024 of 2048: the 1024 misses are
   exactly the pixel columns 32 to 63 of s32x32 whose u lies past the texture (the control's
   column clamped to 31), so the shear reads the unclamped u [infer]. tw32-t3b14 kept no image
   (failed in E566). Refuted by: any W != S job off R-U on the in-range pixels. Needs a held-out
   row (R9-A).
2. **Q078's "T0 bit 27 select" clause is answered by E723 and Q078 does not cite it**: E723
   holds T0 bit 27 as sRGB to half on point samples (4 of 4 held-out fills, 8192 of 8192 pixels);
   the bilinear part is Q282's. Text: Q078 adds E723 and drops the clause (no claim contradicted).
3. **Q282 (sRGB bilinear): decode-to-half first is the better order, but no declared rule is
   exact** (`q282_*.out`; E723's kept g-bl-st-a and g-bl-st-b, `texture/p1141/out-hw`). Three
   declared families fitted on g-bl-st-a only, each best frozen by hash before g-bl-st-b was read:
   family 1 (1404 rules: decode exact/half/f32, arithmetic float/f32/lerp-in-half/fixed 8-20
   bits, orders xy/yx/joint, weights 1/64-1/256, truncated or rounded, half RNE/RZ/RU): best =
   decode to half, lerp in half x then y, **1506/2048 fit, 1189/2048 held out** (E723's frozen
   decode-then-filter: 1147 and 876). Family 2 (1728: per-stage and per-product roundings, the
   a + w(b - a) form): no gain. Family 3 (256: block float, the corners aligned to a shared
   exponent with M bits): best M = 11 per pair, **1493 fit, 1340 held out**. Residuals of the
   best on the fit job are +-1 half ulp (531 below, 62 above of 4096 channels), spread over the
   exact value's position between halves (`q282_resid2.out`): a narrower intermediate than half
   or float, not a rounding mode [infer]. Weights: P = 64, 128 and 256 score the same (the
   fractions are on the 1/64 grid). Not a closure: it designs R9-B's row (corners and weights
   chosen so a stage's arithmetic reads off directly).
4. **Q280 (LOD fraction residual): a 10-bit mantissa cut of the squared length fits E721's 8
   gradient jobs better but does not hold out** (`q280_*.out`). Declared family (exact,
   piecewise-linear log2 on the length or its square, mantissa cut to k = 3..12 bits before an
   exact log2, squares in float32): best `cutsq10` 16351/16384 on the 8 lg-* jobs (6 exact,
   residuals 16 and 17) against the landed rule's 16210 (4 exact, 46, 56, 19, 53). Frozen
   (`q280_rule.sha256` 3a0c46a8...) and scored on E721's 8 ladders lf-* (never read by the fit):
   **16236 for both** (cutsq10 exact on 4 ladders, worse on 3), so the frozen prediction ("at
   least the baseline on each ladder, more in total") fails. Q280 stays; a dated note only.
5. **Q103's fold into Q211 can be made now**: round 8's note waited for round 7's Q211 records
   on main; E899, E916, E938 and E939 are on main 5e58278. Text only (R9-8).
6. **Uncited newer records** (`xref.txt`): unchanged since round 8 apart from E723 for Q078
   (finding 2); the rest are the E6xx vector records of rounds 6/7 (no change proposed).

None of findings 1-4 contradicts a landed claim; finding 1 refutes no record (E566 tabled bit
14's offsets without a rule).

## 1. Candidates beyond the seeds, ranked

Boot: B60AB0B4 as it runs now (no row needs its new knobs except R9c-Q076's `alias_skip`, which
every module since fork commit 42 has). Tool: t4 (`~/sgxfive-test-rgn4`, as rounds 7/8); probe
bins built offline from main. Kit fit is stated per item. Value/cost order:

**R9-A. Q078 (texture, high; 5 crate cites).** Records E274, E397, E564, E566, E722, E723;
findings 1-2. Rows (probe `--pixels`, E566's tx_map form on named memory, `--scratch-pages` sized
to the read extent: E787's 64 KiB cause): bit 14 at W != S, frozen R-U with two rivals for the
pixels past the texture, H-UCLAMP (the clamped column's u) vs H-URAW (the raw u): strided 16 x 32
at S = 64, 32 x 16 at S = 128, 32 x 32 at S = 32 (W = S control of the rule), 48 x 32 at S = 64
(W not a power of two), 32 x 32 at S = 64 with u over [0, 1) only (no clamped pixel: R-U alone)
and over [0, 2) (rivals split): 6 jobs held out. Bits 11 and 12 on a strided 64 x 32 (E566 saw no
change: frozen "control image") and a twiddled 64 x 64 chain (E564: bit 11 cleared 2048 distinct
names from level 0, bit 12 set one constant): 4 jobs, a reading table per pixel (named memory
decodes every read; no rule frozen beyond E564's two counts). Control: s64x32-t3b14 rerun (2048
pixels known, can fail) and s64x32-ctl. 12 jobs, ~2 minutes. Risk: lowest (E566's strided t3
jobs completed; the twiddled bit-14 job tw32-t3b14 failed in E566 and is not rerun). Closes:
bit 14 if R-U holds on the 6; with bits 11/12 decoded, Q078 retires or narrows to bits 11/12.
Kit: fits (probe rows, bins in `[files] laptop`, `reads:hash` controls).

**R9-B. Q282 (texture, low).** Records E720, E723; finding 3. Rows (E723's g-bl-st form, strided
8 x 8, T0 bit 27, bilinear, injected bytes): (a) stage 1 alone: v on texel centres (fy = 0) and
every fx 0 to 63 across a row, corner pairs (0, 255), (43, 213), (75, 104), (201, 167), (b) the
same with fx = 0 (stage 2 alone), (c) a two-stage job with the pairs of (a) as rows, (d) equal
corners (a lerp of equal halves must return the half: a control that can fail): 7 jobs. Frozen
rivals per channel: H-HALF2 (family 1's best) and H-BF11 (family 3's best), plus the reading
table of (a) and (b) (the stage's output per weight for known inputs: its arithmetic decodes
directly). Control: E723's g-bl-st-a rerun (2048 pixels known). 8 jobs, ~2 minutes. Risk: lowest
(E723's 8 jobs). Closes: Q282 if a rule read off (a)/(b) predicts (c) exactly [the fit/held-out
split inside one session: (a)/(b) fit, (c) and E723's two jobs held out, scored after a freeze in
the fold, stated as such]. Kit: fits.

**R9-C. Q242 and Q243 (zls, low; 40 and 15 crate cites).** Records E466, E490, E663 (Q242),
E467, E628, E664 (Q243), E831. Q242 rows: `tri --tri-full --tri-z` ramps over [0, 1] with
`--depth --depth-dump` at 256 x 128, 320 x 240 and 96 x 48 (G other than 33, edge tiles), each
in format 0 then 1 then 2 on
the same geometry (9 jobs; `--depth-pages` set to the tile extent: the "Known tool weaknesses"
floor). Frozen per dword, from the format-0 float of the same geometry: H-ROUND
(round(z * 0xffffff)) vs H-FLOOR (floor(z * 2^24)) for format 1 (they differ outside 0.25 to
0.4166) and E466's two-rows-a-dword layout at the new G and at the edge for format 2 (rival:
the layout restarts per tile row). Q243 rows (`-n 2 --depth-ctl` store, `--depth-ctl-next` load
with bits 1 and 14, depth test equal): format 1 and format 2 stored then loaded (H-INT: the load
converts back and every pixel passes; H-RAW: the dword is read as a float32 and the pass set is
the one the bit patterns give), format 0 with `--depth-fill` 0x7fc00000 and 0x7f800000 loaded
under the equal and less tests (frozen from IEEE compares, rival "NaN passes"): 6 jobs. Controls:
E490's format-1 job at its size (dump hash known) and E467's load copy. 17 jobs, ~3 minutes.
Risk: lowest (E466/E467/E490/E831 ZLS jobs, no fault). Closes: Q242's 24-bit rounding clause and
its 16-bit layout clause; Q243's integer-format and NaN clauses (its moved-base clause stays).
Kit: fits (`outdir_opts` for `--depth-dump`).

**R9-D. Q121 then Q120 (zls, medium both; 8 and 10 crate cites).** Records E466, E467, E490;
E284 (ISP word 2's stencil fields), E831. Q121 rows: a
stencil pattern made by geometry, not by the fill (the fill modes give no per-pixel byte): two
triangles with slanted edges at 64 x 32 and 96 x 48, `--stencil --stencil-store`, `--isp2` with
E284's replace-by-reference operation and two references, `--depth-dump` (it writes the stencil
buffers too); frozen rivals for the byte of pixel p in a tile: H-DEPTH4 (the depth store's order,
dword p >> 2, byte p & 3), H-ROW4 (four x-neighbours a dword, rows raster in the tile), H-COL4;
4 jobs. Q120 rows: the same depth ramp and stencil stored in formats 3 to 7 at 64 x 32 and
96 x 48 (10 jobs), frozen only the per-tile counts scaled from E466 (format 3 and 4 with the
stencil, 5 and 6 data-dependent: a range) and a reading table of each format against the known
depth and stencil of every pixel. Controls: format 0 of the same job (dump known from the
geometry) and E466's 1024 x 768 stencil-store count rerun. 16 jobs, ~3 minutes. Risk: lowest.
[check] E284's ISP word 2 encoding for "replace" in `--isp2` and that the state block takes it
without a stencil test failing every pixel (a mock reading of the dry run). Closes: Q121's byte
order (and, if the replaced pixels read back, its "test against a loaded stencil" clause by a
second stage reloading with bits 1 and 13); Q120 narrows to decoded layouts (5 and 6 may be
compressed: a reading, not a closure). Kit: fits.

**R9-E. Q199 and Q261 (isp, high and medium; 12 crate cites on Q199).** Records E606, E607,
E682, E683, E684. Rows (`tri --tri-v` with `--tri-unit 0`, whole pixels, a 64 x 64 target, one
vertex far
off and two inside, as E684 at k up to 21): the far vertex at +-2^22, +-2^23, 2^24 and 2^26
pixels in x and in y (8 jobs), a far vertex on a tie at 2^20 pixels plus 1/512 (unit 9; 2 jobs),
two far vertices (2 jobs). Frozen rivals per job, images from sgx-pipe's E606 coverage rule:
H-EXACT (no limit), H-SAT (the 24.8 vertex clamped to +-(2^23 - 1/256)), H-WRAP (two's complement
wrap of 24.8 at 2^23 pixels), H-CULL (nothing drawn). Control: E684's k = 21 job (image known).
13 jobs, ~2 minutes. Risk: new range (E684 stopped at 2^21; 208 jobs, no fault): stop on the
first fault or hang [infer: a vertex the TA cannot hold is clipped or culled, not a fault]. The
float32 clip coordinates the tool builds are exact at powers of two only, so every far value is
one. Closes: Q199's saturation clause and Q261's "where the format saturates" clause; the error
band of Q261 stays. Kit: fits [check that `--tri-unit 0` with values near 2^30 passes the tool's
parse and is printed back exactly].

**R9c-F. Q101 (zls, low; conditional on a userspace change).** Round 8's R8-3 dropped: the tool
refuses `--tri-z` outside [0, 1] (`parse_tri_z`, `sgxfive-test.c:3349`). Change, test first, in
the tool build K1 already needs (t8): `--tri-z` accepts [-1, 2] (the probe form's own z as
well), a unit test for the parse, the printed depth unchanged in format. Rows: R8-3's 8 + 2
controls (frozen rivals H-ABS, H-CLAMP, H-WRAP, H-NONE per dword). ~2 minutes. Closes Q101 if one
rival holds on both integer formats; the "vertex depth outside [0, 1]" clause of Q241 rides
along (the stored float-format depth of the same rows, exploratory). Kit: fits once t8 exists.

**R9c-G. Q076 (bif, high; expect-fault rows, not safe class).** Records E021 ... E457, E592, E745,
E761 (16 crate cites).
No kernel change: `alias_skip` (debugfs mask of firmware buffer ids 0-15 left out of the client
directory's alias, fork commit 42, in B60AB0B4). Rows (E457's form, `tri -n 2 --keep-going` on a
new VM): buffers 0-5 and 12-15 one at a time (10), 6/7/8/10/11 together (1), the same set with an
overflowing scene (E625's partial-render form, 1), controls `alias_skip` 0 (hash known) and
TA3DCtl left out (E457's known fault). Frozen per row from E457's mechanism: "needed" (a fault
whose CR_BIF_FAULT page lies in the buffer) vs "not needed" (the control's hash). Up to 12 planned
faults, each declared `expect:fault`, health triangle after each, `#limit` excludes declared
faults (round 8's tooling), stop on two -110 in a row. ~14 jobs, ~5 minutes. Risk: medium
(planned faults the kernel recovers, not held resets). Closes the "buffers 0 to 5 and 12 to 15"
and "larger scene" clauses of Q076; the per-requestor and other-context clauses stay. Kit: fits
(expect-fault controls and rows are kit kinds since round 8).

Not picked, close behind: Q071 (ZLS control bits in combination: after R9-D, same rows with the
bits set), Q104 (1D and side-1 mip chains, named memory, cheap), Q201 (position source vs the
coordinate set, needs a program carrying window x, y), Q112 (`--index-width` exists: 32-bit
indices), Q296 (offline fit on the dense table's FIT half), Q012 (mode 34 reads as a packed
small-float field: an offline decode of E429's kept pixels first).

## 2. Proposed sessions and the offline package

**Offline O9 (Mac, worktrees, `git commit -- <paths>`; ~2.5 h):**
- O9-1 Q078 record: bit 14 from E566's kept dumps, the six rivals frozen and held out (s64x16
  2048/2048 tied, s32x32 0/2048 refuted), R-U post hoc (2048, 2048, 1024 of the in-range 1024);
  the T0 bit 27 clause answered by E723 (cite, clause dropped); the scripts moved to
  `resgx545-data` with imports pointed at the published model copies. R9-A's predictions
  generated from R-U and frozen with the session. 1.5 h.
- O9-2 Dated notes: Q282 (finding 3: 3 families, best fit/held-out counts, hashes; the R9-B design),
  Q280 (finding 4: cutsq10 refuted on the ladders). 30 min.
- O9-3 Text: Q103 folded into Q211 (finding 5); Q066 and Q019 notes pointing at K1's rows. 30 min.
- sgx-pipe: no change in O9 (R-U is post hoc; it lands with R9-A's record, test first).

**Session `r9-x` (B60AB0B4, t4, kit; no kernel change).** Stages in order of risk: t3 (R9-A, 12),
srgb (R9-B, 8), zls (R9-C, 17), zst (R9-D, 16), far (R9-E, 13): **66 jobs, ~12 minutes of runs,
~35 with staging, preflight and health.** Stops: the first fault or hang in `far`, any fault
elsewhere (none of these forms faulted before), two unparsed outputs in a stage, free space below
300 MB. Every stage fits the kit as it is (probe and tri rows, `outdir_opts` for
`--depth-dump`, `reads:hash` controls); no held recovery, no stepped cell, no knob. Builder
checks before the freeze, by mock and the preflight's dry run: `--isp2`'s replace encoding
(R9-D), `--tri-unit 0` at 2^30 (R9-E), each probe's scratch extent below the mapped pages
(R9-A). If one fails, that stage drops, not the session. Run after the seeds' safe sessions, in
the same sitting on B60AB0B4. Optional stages: `z2` (R9c-F, 10 jobs) only if K1's t8 is built
with the `--tri-z` change; `bif` (R9c-G, 14 jobs) last, only with the user's expect-fault OK.

| Item | Runs on | Change | Jobs | Wall | Risk |
| --- | --- | --- | --- | --- | --- |
| O9-1..3 | Mac | none | 0 | ~2.5 h | none |
| r9-x t3, srgb, zls, zst, far | B60AB0B4, t4 | none | 66 | ~35 min | lowest; far: new range |
| r9-x z2 (Q101) | B60AB0B4, t8 | `--tri-z` range (userspace) | 10 | ~5 min | lowest |
| r9-x bif (Q076) | B60AB0B4, t4 | none | ~14 | ~10 min | medium: declared faults |

Records (the lead numbers them): O9 one (O9-1); r9-x one per stage (5), plus one each for z2 and
bif if run.

## 3. Kernel-enabled questions: fork change, tests, cost

No new kernel work is recommended this round: B60AB0B4 already carries every knob the picks need
(`alias_skip` since commit 42; K1's `render_bg_layer`/`render_bg_src` for the k1 planner), and a
change costs a cachix recheck, a delivery and a one-shot boot. Costed for the record:

- **K9-1 Q109 (PDE page-size field; low).** As round 8's K3: a debugfs check file (0400, like
  `xfer_iso`) building a client PD with one PDE of size field s over a table laid out under a
  frozen layout (16 KiB: 256 entries of `addr >> 14 & 0xff`), one fill, the BIF registers
  reported; KUnit for the PD builder per s. ~half a day; ~12 rows, faults likely, the layout a
  guess. Recommend no.
- **K9-2 Q068 / Q064 / Q049 (an interrupted TA, a context-switch path, two overlapped contexts).**
  A fork path for a context switch mid-TA is an own phase (days), not a round's item. Recommend
  no.
- **K9-3 Q193 (what clears an unwritten temporary).** No fork change: a module reload between
  marker jobs. The laptop rules forbid builds/reboots, not `rmmod`/`modprobe`, but a reload under
  the running display is untested on this module [infer: gma500 owns the display]. Recommend no.

## 4. Tiers of all 162 (`tiers9.out`, every id once, checked complete)

- SEEDS (closing9/seeds, 9): Q141 Q108 Q284 Q177 Q210 Q211 Q283 Q260 Q139.
- K1 (closing9/k1, 1): Q190.
- R9, picked here (8): Q078 Q282 (offline + r9-x), Q120 Q121 Q242 Q243 Q199 Q261 (r9-x).
- R9c, conditional (2): Q101 (t8 change), Q076 (expect-fault OK).
- K9, kernel-enabled, not recommended (4): Q109 Q068 Q064 Q193.
- F9, text (5): Q103 (fold now), Q146 Q194 (keep apart), Q066 Q019 (notes to K1's rows).
- O9, offline later (20): Q280 (noted) Q296 Q100 Q053 Q288 Q200 Q163 Q075 Q012 Q008 Q125 Q107
  Q070 Q074 Q290 Q179 Q082 Q030 Q089 Q142.
- H9, safe hardware rows later (74): round 8's H8 less Q242/Q243/Q120/Q121/Q199 (picked), plus
  Q086 Q111 Q201 Q202 Q205 Q206 Q207 Q230 Q231 Q240 Q241 Q262 Q276 (round 7/8 subjects now idle).
- X, hangs, faults, held resets, new tooling (24): round 8's X plus Q003 and Q294.
- Ph, hardware but parked by the laptop rules or other hardware (5): Q048 (clock-gate writes),
  Q063 (other SGX cores), Q099 (capture harness), Q154 (deny-listed registers), Q168
  (trc_hazard).
- P, the digest's 10 parked (fw/kernel): Q004 Q029 Q034 Q049 Q084 Q088 Q095 Q118 Q119 Q277.

## 5. Retire, fold and merge candidates (with records)

- **Q078: narrow now** (O9-1: T0 bit 27 answered by E723; bit 14's rule post hoc), **retire
  after R9-A** if R-U holds on the six held-out jobs and bits 11/12 decode; else narrow to
  11/12.
- **Q103: fold into Q211 now** (round 8's proposal; its condition, round 7's Q211 records on
  main, is met: E899, E916, E938, E939). A fold, not an answer.
- **Q242: narrow after R9-C** to the overlapping-tiles and the G-past-3 fault clauses if both
  frozen readings hold; **Q243** narrows to the moved base.
- **Q101: retire after R9c-F** if one rival holds on both integer formats.
- **Q282, Q280: dated notes** (findings 3-4); no retirement.
- **Q146 / Q194: keep apart** (round 3's decision; no record since E602).
- **The 10 parked (P)**: HACKING keeps `fw` and `kernel` questions open and parked; none has a new
  record. Q088's hardware half is Q038's already (its text says so). Q095 could be retired as
  "decided in" the boot spec only if the user decides the EDM's own directory is the design and
  the comparison is not wanted (no record answers it). Q118, Q119, Q277, Q084 ask about the closed
  firmware's or driver's own routine, moot for the own-firmware route [infer]; retiring them would
  need a new RETIRED reason ("out of scope"), a tooling change. Recommend no change.
- Answered in part by E922-E946: every one of those records names a seed question (E922/E934
  Q141, E923/E930/E931 Q284, E932 Q177, E933 Q271 retired, E935-E939 Q210/Q211, E940/E941 Q283,
  E942 Q178 retired, E943 Q260, E944 Q139, E945/E946 Q108): their folds are the seeds planner's.
- No landed claim needs a correction for any item here.

## 6. User decisions

1. **R9-1 Offline package O9.** a) O9-1 (Q078 record: bit 14 held out at 64 x 16, refuted rivals
   at 32 x 32, R-U post hoc; T0 bit 27 by E723), O9-2 (Q282 and Q280 dated notes), O9-3 (Q103
   fold, Q066/Q019 notes), ~2.5 h (recommended); b) O9-2 and O9-3 only (notes, no record);
   c) none.
2. **R9-2 Session r9-x (B60AB0B4, t4, kit, no kernel change).** a) t3, srgb, zls, zst, far: 66
   jobs, ~35 min, after the seeds' safe sessions in the same sitting (recommended); b) t3 + srgb
   + zls only (37 jobs, ~20 min, no [check] items); c) none this round.
3. **R9-3 Q101's userspace change.** a) `--tri-z` accepts [-1, 2] in K1's t8 build (test first),
   stage z2 (10 jobs) appended to r9-x if t8 is built (recommended); b) defer to a round without
   K1.
4. **R9-4 Q076 by `alias_skip` (expect-fault rows).** a) Stage bif last in the sitting, ~14 jobs,
   up to 12 declared faults, stop on two -110 in a row (recommended: high value, no kernel
   change, E457's form); b) defer; c) only the "together" and the overflow rows (2 jobs, faults
   unlikely).
5. **R9-5 Kernel work.** a) None beyond K1's (recommended); b) cost K9-1 (Q109) in detail for a
   later round.
6. **R9-6 Q078.** a) Narrow now (O9-1), retire after R9-A if R-U holds and bits 11/12 decode
   (recommended); b) narrow now, leave open until bits 11/12 have a rule; c) no change before
   R9-A.
7. **R9-7 The 10 parked questions.** a) No change (HACKING's policy; no new record)
   (recommended); b) retire Q095 as decided by the kernel's design; c) add an "out of scope"
   RETIRED reason (tooling) and retire Q118, Q119, Q277, Q084 with it.
8. **R9-8 Q103.** a) Fold into Q211 now (recommended); b) wait for the seeds' Q211 rows.

## 7. Summary (10 lines)

1. Beyond the seeds (9) and K1 (Q190), all 162 open placed once (`tiers9.out`).
2. Q078 offline: T3 bit 14 reads dword + 32 + S c; six frozen rivals held out at 64 x 16
   (2048/2048), refuted at 32 x 32 (W != S); post hoc "row += u * S" fits every in-range pixel.
3. Q078's T0 bit 27 clause is E723's (uncited): narrow now, retire after one held-out row.
4. Q282 offline: 3388 declared bilinear-sRGB rules, none exact (best 1506 fit / 1189 held out);
   the residual is +-1 half ulp: a designed stage-by-stage row (8 jobs) reads it off.
5. Q280 offline: a 10-bit mantissa cut fits E721's jobs better but ties on the ladders: refuted.
6. r9-x (B60AB0B4, t4, kit, 66 jobs, ~35 min): Q078, Q282, Q242/Q243, Q121/Q120, Q199/Q261.
7. Conditional: Q101 via a `--tri-z` range change in K1's t8; Q076 via `alias_skip` faults.
8. No new kernel work; Q103 folds into Q211 now; parked 10 unchanged; 8 decisions, (a) first.
Path: `/Users/jtorra/src/scratch/resgx545/closing9/rank/rank-round9.md`
