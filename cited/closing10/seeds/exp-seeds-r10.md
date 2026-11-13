# Round 10 seeds plan: the follow-ups of round 9's folds

Planner: round 10 seeds. Offline and read-only; nothing here touched the laptop, cachix or a git
repository (resgx545 read at main 58c4763 with r9-fold-k1 cf0a9dd being merged in the working
tree, r10-tooling 9933208; data 1324301be). Scope: Q284, Q177, Q078, Q282, Q120/Q121, Q199/Q261,
Q101, Q139, Q210/Q211, Q108/Q076, Q190/Q066, Q260. Constraints (BRIEF-COMMON.md): safe class,
no kernel change, module B60AB0B4 as loaded, one sitting.

Everything run here is in this directory, standard library unless marked numpy (repo `.venv`),
read only over resgx545-data and resgx545, nothing firmware-derived (publishable as
`cited-scratch:closing10/seeds/`):

| dir | scripts | outputs | what it decides |
|---|---|---|---|
| `q282/` | `q282_r10_fit*.py`, `q282_r10_frozen.py`, `q282_r10_heldout.py`, `q282_r10_ablate.py` (numpy) | `q282_r10_rule.json` + `.sha256`, `*.out` | the bilinear sRGB stage rule, held out on 3 kept jobs |
| `q177/` | `ns_read.py`, `u5_past.py`, `u5_rows.py` | `ns_read.out`, `u5_rows.out` | 8 N + 52 with N the width, on E565's kept 32 x 8 jobs; mode 5 past the texture |
| `q284/` | `collect.py`, `search_a.py`, `search_fmad.py`, `freeze_score.py`, `rampkind.py`, `edge_cands.py`, `rows_a.py` (numpy) | `frozen_rule.json` + `.sha256`, `*.out`, `rows_a.json` | no tie rule; the misses are ramp x ramp ties; the edge tap |
| `q261/` | `band_far.py`, `pivot.py` | `band_far.out`, `pivot.out` | E979's band pixels: 26 of 46 off, the line pivots at the near vertex |
| `q120/` | see section 5 | see section 5 | formats 3 to 7 from E978's kept dumps; the stencil order |
| `q260/` | see section 11 | see section 11 | floating-point edge set-up on E683 |
| `q210/` | `s_spread.py` | `s_spread.out` | S_k's spread over the runs of one target (r9-ldpm) |
| `libmock/` | `dryrun.sh` (builds three mocks: t4 4623753, t9 97447b04, r10-tooling 9933208) | `dryrun.out` | every proposed row form on its tool's library mock |

## 0. Findings that change the round 9 follow-ups

1. **Q282 has an exact stage rule, held out offline on three kept jobs** (`q282/`, numpy). Fitted
   on r9-x's single-stage rows a1, a2, b1 and b2 only (E976's own fit set, FOLD-NOTES "srgb"),
   about 235k rules in eight families. The only exact rule (16384 of 16384 halves, R10-BF11):
   per stage on two halves A (weight 64 - k) and B (weight k), floor both to the grid 2^(e - 11),
   with e the larger exponent (an 11-bit shared mantissa); lerp exactly; round to half to nearest
   with ties up; at k = 0 return A unchanged. Frozen by hash (`q282_r10_rule.json`, sha256
   e9623e35...; the file's mtime precedes the held-out output's) with both stage orders declared.
   Held out, x stage then y stage: c1, c2 and E723's g-bl-st-b each 4096 of 4096 halves and
   2048 of 2048 pixels; y then x 536 to 773 pixels, so x comes first. Ablation (fit): M 10 6932,
   M 12 13504, input rounding 13256, RNE out 15817. One caveat for the record: an early smoke
   test of the table builder printed a few c1 rows (nothing fitted or scored on them).
   Proposed record E982 [HW, held out offline]. Q282 can retire offline (R10-1). Untested corners
   are listed in section 1.
2. **Q177: the offset is set by the width** (`q177/ns_read.out`). E565's kept 32 x 8 twiddled jobs
   (bd-hb-ns-uv4, 6, 7; texture/p1132/tx-border, 2026-11-09), never read for the offset, read
   H-MASK-V's index + 308 dwords on 2048 of 2048 pixels each, = 8 W + 52 with W = 32. The height
   rule (116) and the size rule (180) are refuted. These rows were run before E957's fit, but
   the rivals were named in E957 and not hash-frozen here: call it SEMI. Proposed record E983.
   Mode 5 past the texture (bd-hb-ns-uv5, `u5_rows.out`, post hoc): left of the texture it reads
   5 W + 52 + t, right of it 6 W + 52 + t (t the row inside the texture). The same form gives
   E932's 16 x 16 reads at t = 8 (140 and 156) [fitted, two sizes]. With v also outside, it reads
   dwords 20 and 21 (above) or 22 and 23 (below), whatever u is.
3. **Q284 ties: no rule, and the misses are confined to ramp x ramp ties** (`q284/`, numpy). There
   are 1212 selectors (mantissa-truncated, quantised, normalised, comparison trees) plus 352
   fmad-noise models. Fitted on r8-geo's 277 tie pixels, the best non-trivial one was frozen
   (sha256 1235c20a...); held out on r9-geo's 322 it got 140, against 321 for the plain
   higher-axis rule: no rule. Post hoc, all 7 lower-axis reads are ties where both tied
   coordinates come from fmad ramps (7 of 34 such pixels); the 565 constant x ramp ties never
   miss. So the third coordinate may be incidental [infer]. Edge (post hoc, weak: 3 columns,
   tolerance 1): one candidate fits both edges, 96 of 96 each. It is the tap centre's direction
   (across-edge coordinate 16.5) on the neighbour face, at that face's own float (s, t), filtered
   bilinearly and clamped. The adjacent-texel rival fails +z/+x (64 of 96).
4. **Q261: E979's band pixels are not noise** (`q261/band_far.out`, `pivot.out`, post hoc). Of 46
   pixels within 1e-3 px of an edge in E979's 11 rows, 26 differ from the exact image, all exact-out
   but drawn, in contiguous runs along the far edge of x23p, x24p and x25n. The run ends at the near
   vertex: the hardware line pivots there. A perpendicular displacement of the far vertex fits
   every band pixel only when it is at least 43, 52 and 42 px in y (or -171, -206, -167 px in x)
   at 2^23, 2^24 and 2^25 px. The bound is one-sided, about the same at every distance, and far
   above float32's 0.25 to 1 px at those coordinates [infer]. That is a measurable quantity, and
   section 9's sweep pins it.
5. **Q120/Q121 offline from E978's dumps** (`q120/`, SEMI). Formats 3, 5, 4 and 6 decode exactly
   at both sizes: 3 and 5 are a 5-byte record a pixel, the float with its sign set and then the
   stencil byte; 4 is stencil only; 6 is the float with its sign set. Format 7 does not decode.
   The stencil bytes paired with each pixel follow the depth's in-tile order (H-DEPTHORD, 13 of
   13 tiles), and the raster and format-2 orders match no chunk. Section 5, record E985.
6. **Q101: no computed or loaded depth below 0 reaches the store** (E981: the ISP clamps at 0;
   E467: a load clears the sign bit; E287: the clip removes --tri-z below 0). One route never run
   is the background depth (render details dword 16, `CR_ISP_BGOBJDEPTH`, 3d.md's table;
   `--kpoke-render 1:rd:16=V`, inside the fork's kpoke range rd:0 to rd:122). It is written to
   every undrawn pixel without the ISP's arithmetic. Word 10 (the first 0.5 of the viewport
   block, `render.c sgxfive_tri_block`): the default 0.5 gives t and 0.25 gives 0.6 t, so a
   factor 1.6 w + 0.2 is the line through the two points [fitted, 2 points; the default's t
   inferred from E977's ramps], and -0.25 then gives a negative plane (stored 0, E981).
7. **Q210: S_6 moves between runs of one target** (`q210/s_spread.out`, from r9-ldpm's kept rows).
   S_2 to S_4 are one value per target in every run, but S_6 takes two values at 1536x1536,
   1792x1792, 2304x1792 and 4096x2048, and 0x1dd to 0x1e1 at 2304x2304. S_5 takes two at
   1792x1792. E962's wide-target misses (+1 or +2 at S_6, one calibration each) are within that
   spread [infer]. Whether the replay is biased or the step is noisy is decided by replicates
   (section 10), not by a new rule.
8. **Tool reach and fills** (`libmock/dryrun.out`):
   - `--tri-v` parses at most +-2^30 units, and `--tri-unit` takes 5 to 20, so the reach is
     2^25 px. Q199 past it needs a tool change (section 8).
   - t4 refuses `--isp2`; the r10-tooling tool takes it with `--depth --stencil --stencil-store`
     and the fills `index`, `bit:K` and a value.
   - No fill varies byte 1 of a stencil dword with its index, so a quarter of the stencil bytes
     cannot be told apart through a test (section 5).
   - Every other proposed form gives `job: ok` or the mock's absent debugfs (`kpoke: No such
     file`, rc 1, which `kit/session.py libmock()` does not count).

## 1. Q282: retire offline, plus a small confirmation stage

**Offline (record E982, decision R10-1).** Finding 1. Refuters: any kept or new bilinear sRGB
pixel off R10-BF11. It replaces E976's open "no rule" in the question line. sgx-pipe/sgx-sim get
the stage rule when the record lands (sim in sync).

**Optional stage srgb2** (S10-tex, 6 jobs, t4 probe of r9-x's `gen/srgb.py` form; held out
against the frozen rule; no fit). It tests what the kept jobs never reached:
- `srgb2-ctl`: E723's g-bl-st-a (the control, can fail).
- `srgb2-offgrid`: fx and fy off the 1/64 grid. The rule's k = floor(64 f) against k = round(64 f)
  and the hardware's own weight bits.
- `srgb2-k0b`: k = 0 with B the smaller corner. The bypass (A returned) against "floor only
  weighted operands".
- `srgb2-sub`: corner bytes 1 to 3, so subnormal halves.
- `srgb2-rand1`, `srgb2-rand2`: random corner bytes, random 1/64 weights.

Frozen per pixel: R10-BF11 (XY) and, on offgrid, R10-BF11 with k = round. Stop: the control off,
or the second row without pixel rows. It retires the clauses unconditionally only if the user
prefers a hardware check; recommended (R10-1 a): the record now, srgb2 in the same sitting.

## 2. Q177: a held-out stage of sizes and shapes

**Offline:** finding 2 (record E983, SEMI). Frozen now (`q177/rivals.out`):
- H-W: 8 W + 52.
- H-H: 8 H + 52.
- H-SQ: 8 sqrt(W H) + 52.
- H-WH: 4 (W + H) + 52.
- Mode 5: H-B5, left 5 W + 52 + t and right 6 W + 52 + t, with v outside 20 to 23.

**Stage addr3** (S10-tex, r9-geo's `gen/addr.py` copied and extended to W != H, t4 probe, every
row `--scratch-pages 32`, T2 0x5CAFC000, page 12, the generator test checks every rival's
farthest read < the mapping), 11 jobs:

| row | texture | parts |
|---|---|---|
| addr3-ctl-u0 | 16 x 16, u mode 0 | control (E932's, can fail) |
| addr3-u4-rep | 16 x 16, u mode 4 | replicate (+180) |
| addr3-ns32x8-u4 | 32 x 8, u and v mode 4 | replicate of E565's kept form at page 12 (H-W 308) |
| addr3-8x32-u4 | 8 x 32 | H-W 116 / H-H 308 / H-SQ 180 / H-WH 212 |
| addr3-16x64-u4, -64x16-u4 | | 180 / 564 / 308 / 372 and the transpose |
| addr3-64x64-u4, -64x64-u6 | | 564 (all agree: the size's own check) |
| addr3-4x4-u4 | 4 x 4 | 84 (all agree; E561's "whole texture when smaller") |
| addr3-16x32-u5, -32x16-u5 | | H-B5 per pixel, against E932's per-position table scaled |

Held out: every row but the control and the two replicates. Stops: as r9-geo's addr2 (any fault,
the second row without pixel rows). Answers "what sets the offset" if one rival holds on the four
non-square rows. Mode 5 narrows to H-B5 or stays a reading. Record E987.

## 3. Q284: ties by ramp kind, and a discriminating edge

**Stage cube3** (S10-tex, r9-geo's `gen/cube.py` copied; the helper's `q284/rows_a.json` are the
specs). 64 x 32 fills, 16 x 16 faces, point-sampled. 16 jobs:
- control `cube3-ctl-xn` (E726's cu-xn);
- 6 cc rows (both tied coordinates movs of +-0.75, the third a ramp 0.47 to 0.71: pairs xy, yz,
  xz, signs +- and ++);
- 6 rr rows (both tied coordinates the bit-identical ramp or its negation, the third 0.5: the same
  six), each with 2048 two-axis tie pixels;
- `cube3-a2-replay` (r8-geo's a2, 78 tie pixels including 4 of the 7 misses);
- 2 edge rows: +z/+x and -y/+x with the along-edge coordinate at 7.25 and 7.75 (off the texel
  centre), outer weights near 0.5, 16 out columns.

Frozen rivals:
- Ties, three rivals: H-HIGHAXIS everywhere (0 lower reads anywhere); H-FMADNE, the two ramps'
  values not bit-equal (the replay repeats its lower reads; cc and rr give 0 lower); H-THIRD, a
  large third coordinate (lower reads in cc and rr).
- Edges: H-SEAM-FLOAT (finding 3's candidate, tap-centre direction at 16.5, neighbour face's
  float (s, t), bilinear, clamped) against H-SEAM-ADJ.

Stops: any fault, the second row without pixel rows. Retires the tie clause if H-HIGHAXIS holds on
the 12 new rows and the replay repeats nothing, or narrows it to the replayed pixels. Retires the
edge clause if H-SEAM-FLOAT holds on both. The texel-tie clause stays a reading. Records E988
(ties), E989 (edges).

## 4. Q078: bit 14's constant held out

**Offline:** nothing kept parts R-4096 from its rivals beyond E975's six rows (all on the 1/64
u grid, 32-bit texels, strided).

**Stage t3b** (S10-tex, r9-x's `gen/t3.py` copied, t4 probe on named memory, each bit-14 row
followed by its bit-clear reference, scratch pages sized to the largest rival's read plus a page,
checked by the generator), 15 jobs:
- controls `t3b-ctl` and `t3b-b14ref` (E566's);
- replicate `t3b-u01` (E975's b14-u01);
- six held-out pairs (12 jobs):
  - S 256, W 64 (S * S = 65536);
  - S 16, W 16, H 64;
  - u off the 1/128 grid (u = x / 64 + 1/192: floor against round);
  - u from -0.5 to 1.5 (both clamps);
  - v a ramp with u fixed (H-UV: + floor(4096 v) [infer]);
  - a 16-bit format at S 64 (4096 dwords against 4096 texels).

Frozen: R-4096 (floor(4096 clamp(u, 0, 1)) dwords), R-4096TX (texels), R-ROUND, H-U01 (S * S),
H-UV.

Not safe: the twiddled texture (E566 faulted), so it stays open. Answers bit 14 on strided
textures if R-4096 holds on all six. Record E990.

## 5. Q120 and Q121: the zst dumps offline, then the stencil test stage

**Offline (done here, `q120/`; record E985, SEMI).** E978's kept dumps decode for four of the five
formats.
- Fit on 64 x 32. The rules were hashed (`frozen_rules.md`, sha256 86f0701a...) before the
  96 x 48 dumps were scored. A coverage look at 96 x 48 f3 came first, hence SEMI. About 12
  layout families were tried.
- **Tiles.** In the packed formats the tiles sit in blocks of 640 (f3, f5), 512 (f6) or 256 (f4,
  f7) dwords. Block = 2 tw (ty >> 1) + 2 tx + (ty & 1), with tw = G + 1: two tile rows form a
  macro row, x outer [fitted with the stencil slot, not independent].
- **f3 and f5** are byte-identical in all four dumps. Each pixel is a 5-byte record: the
  format-0 float with the sign bit set, then the stencil byte. A tile is 16 chunks of 160 bytes,
  one row each. The address rule within a chunk is fitted, with no mechanism known [infer].
  2560 of 2560 and 5760 of 5760 changed dwords.
- **f4** stores only stencil: in 160 of each block's 256 dwords, records of [0xf0, the stencil
  bytes of a quad x + 3 .. x], the 0xf0 the same at every depth run. 640 of 640 and 1440 of 1440.
- **f6** is one dword a pixel, x fastest: the float with the sign set, no stencil. 2048 of 2048
  and 4608 of 4608. Its row order is assumed, since an x ramp cannot test y.
- **f7 is not decoded.** It holds f4's first 160 dwords in slots >= 2, plus marks. Its layout
  depends on the stencil data [infer: a compressed form].
- **No format from 3 to 7 writes the stencil store or changes a stencil byte** (E978 replicated
  byte for byte).

**Q121's order, offline.** Rivals were hashed before scoring. The stencil bytes that f3/f5/f4
pair with each pixel follow H-DEPTHORD in 13 of 13 tiles of both sizes: byte j of the tile is the
depth in-tile index, y0 x0 y1 x1 y2 x2 y3 x3 x4, so the lane is b = y0 | x0 << 1. H-RASTER and
H-F2ORD match no chunk. Only the lane-0 pixels (x even, y even) carry the dword index under the
index fill, so this is 1/4 of the pixels, plus the high byte on lane 1 at slots >= 2.

**Stage zst2 (Q120; t4, r9-x's `gen/zls.py` form, `--stencil --stencil-fill F --stencil-store
--depth-dump "$W"`), 24 jobs:**
- controls: E978's z120-ctl-s rerun (format 0) and z120-f4-s (replicate, f4's frozen layout);
- y ramp `--tri-z 0.25,0.25,0.75` in formats 3, 4, 5, 6, 7 (5 jobs: f6's row order and what
  parts 3 from 5);
- the full depth range 0 to 1 in x in formats 3 to 7 (5 jobs: the depth coding of f4's 0xf0 and
  f7's marks);
- stencil fills 0x00000000, 0xffffffff and 0xa5a5a5a5 in formats 3, 4 and 7 (9 jobs: lanes 1 to
  3 and f7's dependence on the data);
- 40 x 20 in formats 3 and 6 (2 jobs: edge tiles), `--depth-pages` explicit. This is the known
  weakness `depth_min_pages` (HACKING): the generator sizes the buffer to the store's whole-tile
  extent, so the store cannot run past the mapping.

Frozen: E985's rules (f3, f5, f4, f6) per dword, and E985's tile blocks. f7 is a reading.
Held out: everything but the two controls. Stops: a control off, any fault (none in E978's 12
jobs; the edge-tile rows follow E977's edge rows, which stored without a fault). Retires Q120 if
the f3, f4, f5 and f6 rules hold and f7 is decoded from these dumps, else narrows it to f7.
Record E986.


**Stage st1 (Q121; tool: the r10-tooling sgxfive-test with `tri --isp2`, f42dd93, as t10 once
the lead builds it on cachix, bound by `--tool-src
t10=<commit>:userspace/libsgxfive/tools/sgxfive-test.c@<recipe>`;
t4 refuses `--isp2`, dryrun.out).** Every row:

    tri --keep-going --wait-ms 20000 --tri-full --width 64 --height 32 --max-width 64 --max-height 32
        --depth --depth-ctl 0x0017300e --depth-fill 0x3f800000 --stencil --stencil-fill F
        --stencil-store --isp2 V --depth-dump "$W" --pixels

The test compares ISP word 0's reference with the masked stencil. The block's ISP0 is 0x01d00300,
so the reference is 0 (render.c), and depth always passes. A pixel is drawn iff (S & m) == 0 under
EQUAL (V = 0x04000000 | m << 8 | SOP3 << 16 | 0xff). SOP3 = 5 (invert), so the stencil store also
shows the passing bytes, which checks load against store. 16 jobs:

| rows | fill F | m | decodes |
|---|---|---|---|
| st1-always, st1-never | index | (mode 7 / 0) | controls: all drawn / none (the test reads the job, can fail) |
| st1-f0ctl | index, ISP2 absent (`--isp2` not given) | - | control: E978's format-0 store, a copy |
| st1-lane0, st1-lane1 | 0x03020100 | 0x01, 0x02 | each pixel's byte lane b (H-DEPTHORD: b = y0 \| x0 << 1) |
| st1-idx-0, st1-idx-5 | index | 1 << k | lane-0 pixels: E985's offline order through the test path (replicates) |
| st1-bit-K (K 0..6) | bit:K | 0x41 | lane-2 and lane-3 pixels: bit K of their in-tile dword (byte 2 0x40/0x80, byte 3 0x3f/0x3e) |
| st1-e-lane0, st1-e-lane1 | 0x03020100, 40 x 20 (`--depth-pages` explicit) | 0x01, 0x02 | edge tiles |

Frozen rivals per pixel:
- H-DEPTHORD: E985's offline reading, the byte j is the depth in-tile index y0 x0 y1 x1 y2 x2 y3
  x3 x4. Held out on lanes 1 to 3 and the edge tiles; replicated on lane 0.
- H-RASTER and H-F2ORD: already 0 of 13 tiles offline, kept as refuted rivals.
- H-NOLOAD: the test reads 0, not the loaded stencil, so rows of mask m draw everything.
- H-SOP: the store shows the passing bytes inverted, the others copied.

Lane-1 pixels' in-tile dword is unseen through these fills (finding 8); H-DEPTHORD predicts it.
Stops: a control off (gate), any fault (none expected: E978 ran these buffers 12 times), the second
row without pixel rows. It answers Q121's test clause, and its order on lanes 0, 2 and 3 and the
edge tiles. Record E992.

Kit (R10-6): `--isp2` needs t10 on the laptop (a cachix build of r10-tooling plus the copy). The
lead's build and binding are the same as t9's (round 9 log, line 604). If the tooling agent can
add a fill `--stencil-fill bytes` (byte j of the buffer holds j & 0xff; test first) in the same
build, 9 more rows decode lane 1 too (8 jobs k 0..7 plus one shifted fill).
Without it Q121 cannot retire this round: lane 1 stays inferred.

## 6. Q101: the background depth route and word 10

**Stage zbg** (S10-zls, t9 `~/sgxfive-test-t9`, r9-z2's form). The triangle over (0,0) (128,0)
(0,64) of a 256 x 128 target, so most pixels are background. `--depth-fill 0xdeadbeef`,
`--poke blk:1=0x00400200` as r9-z2, no load. 12 jobs:
- **Controls (can fail):**
  - `zbg-c1`: rd:16 = 0x3f800000, the default, made explicit: background 1.0 everywhere.
  - `zbg-c25`: rd:16 = 0x3e800000, format 0: the premise that rd:16 is the background depth.
    If the background does not read 0.25, the stage stops (gate).
- **Held out, rd:16 = 0xbe800000 (-0.25)** in format 0, 0 + bit 19, 1, 1 + bit 19, 2, 2 + bit 19
  (6 jobs). Frozen: H-RAW (format 0 stores 0xbe800000, bit 19 0x3e800000, the integer formats
  floor(z 2^24) of a negative = what E977's conversion gives a negative input); H-CLAMP0 (0 in
  every format); H-ABS; H-B19-INT (bit 19 negates before the integer conversion).
- **rd:16 = 0x80000000 (-0.0)**, format 1 (1 job).
- **Word 10** at 0.75, 1.0, 0.125 (format 0, r9-z2's ramp a, 3 jobs). Frozen: H-LIN, with the
  factor 1.6 w + 0.2 (finding 6, fitted) against the readings.

Stops: zbg-c25 off (gate), any fault. Retires Q101 if one rival holds on all six -0.25 rows and
word 10 is decided; otherwise narrows. Records E993 (background), E994 (word 10).

## 7. Q066 (Q190 retired by E971/E972): what words 11 to 14 are

**Offline:** E973's readings: 1.0 changes nothing, and 0xffffffff in 11, 12 and 14 removes one
coordinate's variation. That suggests a float multiplier or a format per coordinate [infer]. No
kept value parts the readings.

**Stage bgw** (S10-geo, t9, r9-k1's s3 form: `dbg:render_bg_layer=Y dbg:render_bg_src=0x3e800000
expectdiff`, `tri --bg-layer --pixels --keep-going --dump-render $W --kpoke-render 1:bg:N=V`),
18 jobs:
- controls `bgw-ctl` (no poke) and `bgw-ctl-end`;
- words 11, 12 and 14 each at 0, 0.5, 2.0 and -1.0 (12 jobs);
- words 9 and 13 at 0 and 2.0 (4 jobs).

Frozen per pixel: H-SCALE (the word scales its coordinate's plane: the texel at w times the
coordinate, then E974's clamp) against H-INERT (no change except 0xffffffff, E973). These are
held-out rows. Stops as r9-k1's s3. It narrows Q066's "what words 11 to 14 hold". The three PDS
words and BGOBJVALS stay. Record E997. The knob words pass the mock (`--mock-knob`, dryrun.out).

## 8. Q199 and Q261 past 2^25 px: a tool change first

`--tri-v` stops at 2^30 units, and `--tri-unit` at 5 (2^25 px). E979 already ran -2^25. **Tool
change (to the round's tooling agent, R10-7):** let `--tri-unit` take 0 to 20, and `parse_tri_v`
take the int32 range, with a test each (the mock prints the vertices). Then stage far2 (S10-geo,
8 jobs): one vertex at +-2^26, 2^28 and 2^30 px in x and y, plus the control. The rivals are
E979's: H-EXACT, H-SAT and H-WRAP at a 2^31-unit word [infer], and H-F32 (the window coordinate
as float32 with 1/256 rounding). Safe as E979's rows [infer: no fault up to 2^25]. If the tool
change does not land in round 10, far2 waits.

## 9. Q261: pin the pivot (rows inside today's reach)

**Stage pivot** (S10-geo, t4, E979's form at `--tri-unit 5`, 64 x 64), 37 jobs. E979's x23p,
x24p and x25n triangles (far vertex at 2^23, 2^24 and -2^25 px), with the far vertex's y moved
by d px for 12 values of d from -128 to +640, so the row's band pixels flip where the hardware's
effective far vertex crosses each pixel. Control: E684's far21d0 (E979's far-ctl).
- Frozen: H-EXACT (d = 0 is the crossing: every row exact).
- Frozen: H-PIVOT, a displacement D of the far vertex, with D in E979's fitted interval at each
  distance (finding 4), so a row with d < -D draws as E979's misses and d > -D exact. Its value
  per distance is read as the interval the rows pin (about 16 px).
- No float edge variant is a rival: section 11 refutes them on E683.

Stops: E979's (any fault; a control off). Answers Q261's band as a function of the far vertex's
distance (D against 2^23, 2^24, 2^25) or narrows. Record E995.

## 10. Q210 and Q211: replicates, not rules

**Offline:** finding 7. No new multi-kick rule: E960's six families reached at most 7 of 20, and
nothing kept suggests a seventh. Q211's multi-kick clause has no row until a new idea (R10-8).

**Stage s6rep** (S10-dpm, r9-ldpm's `gen/plan.py` and rt wrapper, calibrations only:
`dbg:render_pb_pages=0x422 expect:rc3-overflow`, `#limit 0`), 17 jobs:
- the a0 premise pair (r9-ldpm's a0-cal-2048 and a0-cal-2048f, controls);
- 3 replicate calibrations at each of 4096x1024, 4096x1536, 3584x1024, 2048x512 and 2048x2304.

Frozen:
- H-NOISE: the replay's S_6 lies inside each target's replicate range, and the range spans at
  most 2 pages.
- H-BIAS: every replicate at the replay + 1 or + 2, as E962 read.
- E962's needs: H-REPLAY.

The steps are readings; no cell runs. Narrows Q210's "what puts E874's replay low at S_6" to noise
or bias. Record E998.

## 11. Q260: the floating-point edge family

**Offline (done here, `q260/`, numpy; reuses round 9's `ozlib.py`, hash-pinned).** 352
floating-point edge variants were declared before the fit:
- the coefficient form A x + B y + C;
- relative to a vertex;
- relative to the target or the tile origin;
- a slope form x = x0 + (y - y0) r(dx / dy);
- each with mantissas of 11 to 24 bits, RNE or truncation, on HA's vertices or on float ones.

The engine reproduces HA at p 24 on all 309 fit rows and HA's 26 band misses on E979 (the control
could fail). The fit set was E914 + E943's 395 images plus E979's 11 far rows. The best and the
family bests were frozen (`fp_rule.json`, sha256 8b05140b...) before E683 was read.

Held out on E683's 240 cases, HA scores 173. The frozen best scores 156, and the family bests
172, 173 and 172; post hoc the best of all 352 scores 174. No variant comes near the 235 gate.
Thirty-eight coarse variants (p <= 19) reproduce E979's 46 band pixels but lose 34 to 48 E683
cases: a global float edge does not explain the far band [infer]. Proposed: a note on Q260 and
Q261, no record of its own (or a paragraph of E984).

**What remains short of a new idea: nothing.** After E952 (fixed point) and this float family,
the rivals not tried are an edge re-derived for far vertices only (clipped or set up from the
clip words), and the vertex as the TA stores it. These are named in the question line, but no
candidate is formed. Q260 parks no rows (R10-9). The pivot stage (section 9) measures the far
band directly and may supply the far-edge-specific form.

## 12. Q139: bit 7 and the y side, held out on words that drew

**Offline:** the risky dataset (ta/mtile-fields-risky, output.txt) has whole images, no fault,
`job: ok`, at four y-side words never dumped:
- 256x256 m2-B2-10 (`--kpoke-render 1:ta:144=0x0200a008`, fy 10);
- m2-B2-11 (0x0200b008, fy 11);
- part2-10_10_10 (0x0280a00a);
- 640x480 m2-B1-23 (0x05c10018, fy 23).

The x side's only whole residues (fx 10, 11, 23) were E950's fit, so H-EVEN on x stays without a
safe held-out row (R9-7 unchanged).

**Stage q139c** (S10-geo, t4, r9-lgeo's q139b form: `expectdiff needhash reads:hash,dump`,
`--dump-render "$W" --keep-going`), 6 jobs:
- controls: the 256 x 256 and 640 x 480 baselines;
- the four rows.

Frozen per row:
- H-BIT7: a tile draws iff its header slot is at or before the header with flag bit 7, read from
  the row's own dump, scored against the image.
- H-EVENY: the y analogue of H-EVEN, a block column takes 8 floor(fy / 2) slots, with the
  1280 x 720 m2-B3p1 reading as its fit.
- R7-BLK.
- The dataset's wrong-tile count as a replicate.

Risk: low, not planned faults. Each word drew whole once in a run that faulted on other words. A
fault stops the stage, `#limit 0`. Narrows Q139's bit 7 clause (held out) and the y side. Record
E996.

## 13. Q108 and Q076: nothing safe that decides

Q108's open clauses are CACHECONSISTENT on data cached before a host write, WRITEONLY or
EDMPROTECT alone on a texture read, the flags on a depth load, the TA's own writes and the EDM's
buffers. Each needs either a planned fault (excluded) or a tool that writes from the host between
two renders of one context. **Tool request for round 11 (R10-7 b):** `tri -n 2 --refill N:BUF`, a
host fill of a named buffer before render N, test first. Then CACHECONSISTENT's stale-data clause
is a safe two-render row. Q076's open clauses are which list each requestor walks and a list given
to another directory mid-job. They need faults or a kernel change: no rows.

## 14. What each verdict does

| question | retires if | narrows if | records |
|---|---|---|---|
| Q282 | E982 offline (R10-1); srgb2 confirms | srgb2 misses a corner | E982, E991 |
| Q177 | addr3: one rival on the 4 non-square rows and H-B5 on mode 5 | either part | E983, E987 |
| Q284 | cube3: tie rule and edge decided (texel ties excepted: no) | otherwise | E988, E989 |
| Q078 | no (bits 11, 12 and twiddled stay) | t3b decides the constant | E990 |
| Q120 | zst2: the four rules hold and f7 decodes | f7 alone open | E985, E986 |
| Q121 | no unless the `bytes` fill lands (lane 1) | st1 | E985, E992 |
| Q101 | zbg: one rival on 6 of 6 and word 10 decided | otherwise | E993, E994 |
| Q066 | no | bgw | E997 |
| Q199 | no (far2 waits for the tool) | far2 | E999 (conditional) |
| Q261 | pivot pins D at 3 distances and a rule holds | otherwise | E984, E995 |
| Q260 | no; no rows (section 11) | note on the question | - |
| Q139 | no (H-EVEN x side, stride, E509) | q139c | E996 |
| Q210 | no | s6rep | E998 |
| Q211, Q108, Q076 | no | no rows this round | - |

E-numbers proposed (the lead assigns): offline E982 (Q282), E983 (Q177), E984 (Q261 band reading),
E985 (Q120 decode and Q121's lane-0 order); laptop E986 (zst2) and E987 to E998;
E999 conditional (far2). No landed claim is contradicted, so no correction is needed: E957's
"[fitted] 8 N + 52" gains its held-out reading in E983, and E976's "no rule" is followed by E982.

## 15. Kit sessions (one sitting on B60AB0B4, safe class)

Each session is scaffolded from main after the round's tooling merge with `new_session.py`,
`--tool-src` for every tool, `srcversion = "B60AB0B475DD1E8972419B5"`. Generators are copied from
the round 9 dirs, which stay frozen and are never edited.

| session | stages (jobs) | jobs | wall | tools | reuses | records |
|---|---|---|---|---|---|---|
| S10-tex | addr3 (11), cube3 (16), t3b (15), srgb2 (6) | 48 | ~13 min | t4 | r9-geo gen/addr.py, cube.py, texprog.py; r9-x gen/t3.py, srgb.py, tex.py | E987-E991 |
| S10-geo | pivot (37), q139c (6), bgw (18) [far2 (8) if R10-7 a] | 61 [69] | ~15 [~17] min | t4, t9 | r9-x gen/far.py; r9-lgeo q139 libs; r9-k1 s3 form | E995-E997 [E999] |
| S10-zls | zst2 (24), zbg (12), st1 (16) | 52 | ~13 min | t4, t9, t10 | r9-z2 gen; r9-x gen/zls.py | E986, E992-E994 |
| S10-dpm | s6rep (17) | 17 | ~5 min | rt (t4) | r9-ldpm gen/plan.py, rt wrapper | E998 |

Total: 178 jobs (186 with far2), about 46 minutes of jobs plus preflights, one sitting. Order:
S10-tex, S10-geo, S10-dpm, then S10-zls last, since t10 may come late. Every stage is safe class:
no planned fault, no expect-fault row, no held reset, `#limit 0`.

**Per-row premise checks** (each session's tests, besides the kit's library-mock replay):

| session | check |
|---|---|
| S10-tex | addr3 rows: `--scratch-pages 32`, T2 page 12, every rival's farthest read inside the mapping; t3b rows: scratch pages >= the largest rival's read + 1 page; every bit-14 row followed by its `-ref` |
| S10-geo | pivot rows: `--tri-unit 5` and every coordinate within +-2^30 units; bgw rows: `dbg:render_bg_layer=Y dbg:render_bg_src=0x3e800000` and tool t9; q139c: `--dump-render "$W" --keep-going`, `expectdiff` with `job: ok`, `needhash` |
| S10-zls | zst2 40 x 20 rows: `--depth-pages` explicit, at least the store's whole-tile extent; st1 rows: tool t10, `--isp2` only with `--depth --stencil --stencil-store`; ISP2's mode, mask and SOP fields as the table; zbg: `--kpoke-render 1:rd:16=` only on zbg rows, format words as listed |
| S10-dpm | every row `expect:rc3-overflow`, `dbg:render_pb_pages=0x422`, calibrations only |

**Library mock** (`libmock/dryrun.out`, three mocks built from the bound sources): the probe forms
of S10-tex (rc 3 is the mock's probe without hardware output; the kit's own replay runs the built
program binaries), tri rows of pivot, bgw, zbg and st1 (rc 1: the mock's absent kpoke debugfs,
which the kit does not count) and q139c pass; t4 refuses `--isp2` (st1 must bind t10); `--tri-v`
past 2^30 units and `--tri-unit 4` are refused (far2 waits for R10-7).

**Kit gaps:** none for S10-tex, S10-geo and S10-dpm. For S10-zls, t10 must be built and copied by
the lead, which is not a kernel change.

## User decisions (round 10 seeds; the lead takes them)

**R10-1 Offline records now (no laptop).**
- (a) **Recommended.** E982 (Q282: R10-BF11 exact on the fit set and held out offline on 3 of 3
  kept jobs: retire Q282, sgx-pipe gets the stage rule); E983 (Q177: 8 W + 52, the width, SEMI
  on E565's kept 32 x 8 jobs; mode 5's reading); E984 (Q261: E979's band pixels, the pivot at
  the near vertex, post hoc, and section 11's float family as a note); E985 (Q120's four layouts
  and Q121's lane-0 order, SEMI). Scripts publishable as `cited-scratch:closing10/seeds/`.
- (b) The same, but Q282 waits for srgb2 before it retires.
- (c) None: the findings only steer the sessions.

**R10-2 S10-tex** (Q177, Q284, Q078, Q282; t4, safe).
- (a) **Recommended.** addr3, cube3, t3b and srgb2: 48 jobs, about 13 minutes.
- (b) Without srgb2 (42 jobs), if R10-1 (a) retires Q282 offline.
- (c) addr3 and cube3 only, 27 jobs.

**R10-3 S10-geo** (Q261, Q139, Q066; t4 and t9, safe).
- (a) **Recommended.** pivot, q139c and bgw: 61 jobs, about 15 minutes; far2 joins (8 jobs) only
  if R10-7 (a) lands before staging.
- (b) Without q139c, if the lead counts words that drew once in a risky script as not safe class
  (55 jobs).
- (c) pivot only, 37 jobs.

**R10-4 S10-zls** (Q120, Q101, Q121; t4, t9, t10).
- (a) **Recommended.** zst2 and zbg (36 jobs, about 9 minutes, tools already on the laptop). st1
  (16 jobs) only once t10 is built on cachix from r10-tooling and copied (no kernel change).
- (b) zst2 and zbg only; st1 to round 11.
- (c) zbg only, 12 jobs.

**R10-5 S10-dpm** (Q210; the rt wrapper on t4).
- (a) **Recommended.** s6rep: 17 calibration replicates, about 5 minutes. They decide noise
  against bias at S_6, with no new rule.
- (b) No DPM rows this round; Q210 and Q211 keep their lines.

**R10-6 Q121's binding and fill.**
- (a) **Recommended.** Build t10 from the r10-tooling merge on cachix and bind it like t9
  (`--tool-src`, the source hash, the lead fills the binary hash). Ask the tooling agent for
  `--stencil-fill bytes` (test first) only if its branch is still open; otherwise lane 1 stays
  inferred.
- (b) Add the `bytes` fill before building t10, even if it delays S10-zls's st1.

**R10-7 Tool changes for the tooling agent (userspace only).**
- (a) **Recommended.** `--tri-unit` 0 to 20 and `--tri-v` over int32, each with a test, so that
  far2 can run (Q199 past 2^25 px).
- (b) Also queue for round 11: `tri -n 2 --refill N:BUF`, a host fill between two renders of one
  context, for Q108's CACHECONSISTENT stale-data clause (safe class once it exists).
- (c) Neither: Q199 stays at 2^25 px.

**R10-8 Q211's multi-kick count, Q108 and Q076.**
- (a) **Recommended.** No rows this round. Nothing safe decides them, and no multi-kick rule beats
  7 of 20.
- (b) Plan faulting rows for round 11 with the user present.

**R10-9 Q260.**
- (a) **Recommended.** Park the rows. E952 (fixed point) and section 11 (352 float variants: best
  156 held out, 174 post hoc, against HA's 173 and a gate of 235) leave no candidate. Add a note
  to the question. The pivot stage measures the far band directly.
- (b) Run E943's matched-length sweeps as readings anyway (about 60 jobs). They add misses, not a
  rule.

**R10-10 Order, sitting and records.**
- (a) **Recommended.** One sitting on B60AB0B4: S10-tex, S10-geo, S10-dpm, then S10-zls (st1 last,
  t10). 178 jobs, about 46 minutes plus preflights (186 and about 48 with far2). Records: offline
  E982 to E985; S10-zls E986 and E992 to E994; S10-tex E987 to E991; S10-geo E995 to E997
  (E999 far2); S10-dpm E998. The lead assigns the final numbers after the rank planner's range.
- (b) Two sittings: S10-tex and S10-geo first, the rest after review.
