# Round 15 ranking: safe laptop rows, retire first (Opus, 2026-11-14, user asleep)

Basis: resgx545 `main` 158bdc5 (records to E1048, 150 open), resgx545-data cddc7b60b, fork
resgx545 2a650d74 (read only), laptop on module B60AB0B4 (one-shot boot), tools t4, t9, t10, t14.
Inputs: `doc/state_digest.md`; the round 14 handover (Next item 3) and round 13's; the 2026-11-13
and 2026-11-14 lines of `plans/resgx545-question-closing.md`; `closing14/plan/rank-round14.md`,
`closing13/plan/rank-round13.md`, section 4 of the closing11 and closing12 rank files; the round 14
records E1036 to E1048 ("What it does not show"), the FOLD-NOTES of r14-tex, r14-zls, r14-dpm,
r14-bif and r14-flag, `render/closing-r14-tex/fold/types_post.*` (data); the question lines of
Q078, Q177, Q071, Q120, Q036, Q241, Q108, Q297, Q298, Q104 and the tier list of round 11
(`closing11/plan/tiers11.out`). Nothing staged, built or run; no laptop, SSH or cachix. This file
is the only output.

Round limits applied: SAFE CLASS ONLY (no planned fault, hang, faulting word, kernel change or
boot). Every row below predicts no fault under its frozen hypothesis *and* under every rival it
scores; a row where a rival predicts a fault is listed in section 7 ("later, with the user").

Checks done for this plan (read only):
- `git log c58f9f9..158bdc5 -- userspace/` is empty: **t14 (aa550b94, from c58f9f9) is main's
  sgxfive-test**, and t10 (a581c06) differs from it only by `tri --refill` and `probe
  --scratch-pages` up to 256. No row here needs a tool change.
- `probe --scratch-pages` takes 16 to 256 (sgxfive-test.c, the option's comment cites E1033);
  `--depth-pages` takes up to 0x100000 (the usage check after the options).
- Q078's reach: under E1047's form a 32-bit twiddled texture of W x H reads dword
  `TR (W + 4096) 16 + (c >> 4) 256 + inner`, TR = t >> 4, c < W + 4096. At H = 32 (two tile rows)
  the farthest dword is 135167 at W = 128 (528 KiB), under every rival (4128 a tile row, a clamp
  of u, the fraction) less: inside t14's 1 MiB. At H = 64 a full u sweep reaches 1.05 to 1.06 MB,
  past 1 MiB: **no Q078 row uses H above 32**.
- `smp1d` and `smp1dbias` are in the USSE forms (`isa/usse/forms/class-28-texture-sampling.toml`,
  `doc/specs/usse_guide.md` line 1360): Q104's 1D clause has a sampler form.
- E287: the viewport's z offset is not clipped; a window depth above 1 compares as itself and a
  negative one as 0. So Q298's integer rows outside 0 to 1 can be made by `--poke blk:10/11`
  (viewport z offset and scale, rank-round14 "Checks done") without the MTE clip that E1045 saw
  for vertex depths outside [0, 1].
- HACKING "Known tool weaknesses": `depth_min_pages` undersizes targets that are not whole tiles.
  Every r15-zls row at an odd size passes `--depth-pages` explicitly (E1041's zodd did).

## 1. Every candidate row, ranked (retire first)

"Retire" = every open clause of the question line is decided by held-out rows if the frozen
hypothesis (or exactly one rival) holds and the controls pass; void clauses are reworded [infer]
and the lead confirms (R15-6). "Narrow" = a clause stays open whatever happens.

| # | Row | Question | If it holds | Jobs | Stage (session) | Tool | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | bit 14 twiddled at W 16, 64, 128, u past 1, u16, bilinear | Q078 | **retire** | 14 | tw14 (r15-tw) | t14 | safe; never-run reach, session last |
| 2 | load pass: edge tiles, bit 19, integer formats, depths | Q297 | **retire** | 13 | zpass (r15-zls) | t10 | safe |
| 3 | overlaps in formats 1/2, integer z outside 0-1, E411 pitches sized | Q298 | **retire** | 13 | zovl (r15-zls) | t10 | safe; sized pitch rows last |
| 4 | 1D (smp1d), a side of 1, 16-bit chains, T0 fields | Q104 | **retire** | 18 | chain (r15-tex) | t10 | safe |
| 5 | types 1/3/4: halving held out, fit grid for sizes and modes 5-7 | Q177 | narrow (R15-5 b: retire-capable) | 15 | ty (r15-tex) | t10 | safe |
| 6 | 0x0748 alone, gate at 2000 ns | Q036 | narrow | 10 | pr4 (r15-dpm) | t10 | safe |
| 7 | bits 15 and 23 alone held out, 21+23, 22+23 | Q071 | narrow | 9 | zbits3 (r15-zls) | t10 | safe |
| 8 | flat format 6: low 16 bits vs flat plane | Q120 | narrow | 13 | zflat2 (r15-zls) | t10 | safe |
| 9 | the z cut's edge pixels and depths; bits 16/17 on the 48-pixel triangle | Q241 | narrow | 11 | zcut (r15-isp) | t10 | safe |
| - | EDMPROTECT on a load-only depth render | Q108 | narrow | 3 | not planned (R15-4) | t10 | fault rival live |
| - | Q139, Q163, Q046 bit 11, Q241 bit 18, Q108 WO | - | narrow | - | section 7 | - | faults / hangs |

Session totals: r15-zls 48, r15-tex 33, r15-tw 14, r15-isp 11, r15-dpm 10: **116 jobs**.

### Rows the kept data already decide (dropped, or cut down)

- **Q078 at W = 32, u in (1, 2)**: E1047 (f1-tw32 is in sample, but it ran). tw14 keeps W = 32
  only as a control and for the u16 and bilinear rows; the held-out widths are 16, 64 and 128.
  Q078's strided clauses: E1003 (point), E1027 (bilinear footprint, LOD bits 12:11).
- **Q108, CACHECONSISTENT on a depth load**: E1046 (no stale read, flag inert, both flag
  states). **EDMPROTECT and WRITEONLY on the depth store**: E965. **The stream read and a
  copy's texture read under EDMPROTECT**: E945, E964. Every Q108 clause left either needs a
  fault (WRITEONLY anywhere: E945 H-WO-ALL; the TA's and the EDM's buffers) or a tool change for
  a narrow row (a texture refilled between renders: `--refill` takes depth, stencil and fb only).
  The one row left without a tool change (EDMPROTECT on a load-only render) has a live fault
  rival: E965 faulted the same requestor (ZLS) on the same mapping when it wrote. R15-4.
- **Q071 bits 27 to 31, alone and together; bits 21 to 23 together; bits 12 and 16's pitch**:
  E1042 (nothing seen; 2048 drawn and 0xff; P-G 4 of 4). Bits 12/16/20 singles and pairs: E1030.
  Left: bits 15 and 23 alone (post hoc), 21 or 22 with 23, bit 0, bit 20, the ISP's use.
- **Q120, F7K at fills 0x3f/0x1f, the flat form at 0.25, 0.75, 1.0, 0.0**: E1031, E1043 (the
  latter post hoc for the rule "row 0's record carries the depth"). zflat2 holds that out.
- **Q241, bits 15 to 17 by winding; depth past [0, 1]**: E1045 (no winding; pixels removed).
  E287 for the clip planes. Left in the safe class: the cut's made depths and edge pixels, E065's
  pixels under bits 16 and 17. Bit 18 faults (E065, E998): section 7.
- **Q297, where the load reads and its granule**: E467, E1040. **Q298, float overlaps with edge
  tiles and four macrotiles a side, E411's G 3 pages 16 and 18**: E1041. zovl runs formats 1 and 2
  only.
- **Q036, STATUS2's high half**: E1019, E1032 (0 everywhere). Left: bit 2 (pr4), the other bits,
  owner words, settle and builder clauses (the builder fault clause needs a fault: section 7).
- **Q177, the corner base and every mode 5 region of the twiddled type**: E1039 (6 of 6). **The
  strided type**: E565 via E1026. Type 3 reads as type 1 at mode 0 (E567) and at u mode 4 (E1039),
  so modes 5 to 7 run types 1 and 4 only, type 3 once at 32 x 32.
- **Q104, non-square chains with sides 4 to 128 at 32 bits**: E562 (49 of 49 held out).
- **Q260, Q284**: no frozen form yet (E1001, E1002, E943). **Q210, Q107, Q045, Q019, Q066, Q211**:
  unchanged since round 14's R14-8 (no frozen row). **Q202** (which arithmetic forms x / w): a
  designed parting row is possible but the line keeps four other clauses; offline design first.
- Other old questions checked for a one-session retirement (tier H of round 11): Q114 and Q115
  ask for a negative over all words (no finite row set decides them), Q161's last clause is the
  closed driver's (not measurable by us), Q160 and Q159 have no frozen form, Q013, Q043 and Q044
  are "changes nothing seen" lines. **Q104 is the only one whose clauses one safe session decides.**

## 2. Rows in detail

Every stage: `#limit 0`, any fault or hang stops it (kit rc 4); controls are `reads:` rows of the
stage's own shape, not the default triangle; expectdiff rows need `job: ok`; predictions frozen by
the kit freeze before staging. "Held out" = no kept job ran that row's input; "replicate" = a kept
job rerun, a control when its kept image can fail. Every stage's replay table is named in its
builder's README (HACKING "Replay vectors").

### r15-tw (t14; the last session)

**tw14 (Q078, 14 probe fills, E1047's form: E566's tx_map, scratch dword i = 0xD0000000 | i,
the texture at the scratch's first dword, `probe --temps 32 --coords --pixels --scratch-pages
256`).** Frozen (E1047, fitted on E1033's two fault pages, one held-out row):
- H-TWP: texel (s + floor(4096 frac(u)), t), s the wrapped bit-clear column, in E561's 16 x 16
  tiles with a tile row of W + 4096 texels.
- Rivals: H-TWP4128 (a constant 4128-texel tile row), H-CLAMP1 (u past 1 clamped: the column
  s + 4096 for u >= 1), H-WRAPW (the fraction taken of u W / 4096 cycles [check: the builder
  writes the exact form]), H-TWP4096 (E1047's refuted pitch, as a negative).

Rows, in ascending predicted reach (all held out, H = 32 or less so every rival stays inside 1
MiB):
- 16 x 32 at u in (0, 1) and in (1, 2) (2): the tile row parts W + 4096 = 4112 from 4128 at rows 16
  to 31 (256 texels a tile row of difference), the second part the fraction from the clamp.
- 64 x 32 and 128 x 32, each at u in (0, 1) and in (2, 3) (4).
- Format: a 16-bit twiddled 32 x 32 at u in (0, 1) (1), the prediction in texels (2 bytes) with
  E1026's u16 reading of E561's tiles [check: tiles of 16 x 16 texels against 32 x 16 is a second
  rival for this row; the builder freezes both].
- Filtered: bilinear (E1027's form, smp2d with the filter on) at 32 x 32 u in (0, 1) and 16 x 32
  u in (1, 2) (2). Frozen H-FOOT-TW (each tap is the bit-14 address of its own wrapped bit-clear
  texel) against H-FOOT-SHIFT (the footprint's second column taken unwrapped in the wide layout)
  and H-POINT (the filter dropped). The 2 x 2 blends of named dwords decode as E1027's did.
- Controls that can fail: the bit-clear reference of each new shape (4: 16 x 32, 64 x 32, 128 x
  32 and the u16 32 x 32, E561's tile law, the image frozen), and E1047's f1-zero replicate (its
  kept image).

Stop: `#limit 0`, `on_stop = "end"` on the stage; rows in reach order, so a stray fault stops the
session at the smallest reach. Retire Q078 if one pitch form and one u form hold on all point rows,
the u16 row reads one tile form, and one footprint form holds on both filtered rows. "Other
formats" then reads "the 16-bit format" and is reworded so [infer] (R15-6). Replay: sgx-sim tex.rs
(the bit-14 geometry widened from 32 x 32), table `tw14`.

### r15-zls (t10)

**zpass (Q297, 13 jobs).** E467's load pass (load and store enables, the depth buffer filled half
0.25 and half 0.75 by tile) and E1040's identity form. Frozen predictions from sgx-pipe's
`zls::pass` extended test first by the builder (the extension is the hypothesis):
- H-EDGE: at 34 x 18 (edge tiles, E831's band) the load, test and store act per stored dword as on
  whole tiles; past the target the store follows E831's band (2 rows: depth load, stencil load).
  Rivals: H-EDGE-CLEAR (past-target dwords take the clear), H-EDGE-SKIP (the load skips edge
  tiles).
- H-19-RENEG: with bit 19 the loaded value (sign cleared, E467) is stored negated, as E411's bit 19
  stores -1.0 (2 rows: test never, test less). Rival H-19-ABS (stored as loaded, sign clear).
- H-INT-PASS: with format 1 and 2 the compare reads the loaded dword as a float (E977, E1040) and
  the store applies E991's floor rule to the passing pixel's depth (2 rows, triangle at 0.3).
  Rival H-INT-RAW (the compare on the integer word).
- H-PASS-Z: triangle depths 0.0, 0.1, 0.75 and 1.0 over the 0.25 / 0.75 halves under less (4
  rows; 0.75 parts less from less-or-equal at an equal loaded depth).
- Controls that can fail: an E467 replicate (16384 drawn), E1040's zg-c identity replicate and a
  34 x 18 store without a load (E831's band) (3).
- `--depth-pages` explicit at 34 x 18. Retire Q297 if every clause's hypothesis (or exactly one
  rival) holds. Replay: sgx-pipe `zls::pass`, table `zpass`.

**zovl (Q298, 13 jobs; its sized-pitch rows last in the session).**
- Overlaps (E996's form, G below the tiles across minus one) in format 2 at 64 x 32 G 0 and 160 x
  48 G 2, and in format 1 at 65 x 33 G 1 (edge tiles) and 640 x 480 G 2 (four macrotiles) (4).
  Frozen H-LATE/HDR (E996, E1041) with E991's floor rule; rivals H-EARLY/HDR, H-LATE/RASTER.
- Integer depth outside 0 to 1: the viewport z offset poked so the window depth is 1.25 and -0.25
  (E287: neither is clipped), in formats 1 and 2 (4). Frozen H-INT-SAT (E991's min(floor(z 2^24),
  0xffffff) above 1; a negative depth stored as 0, as E287's compare reads it) against H-INT-WRAP
  (modulo 2^24 / 2^16) and H-INT-SIGN (the float's magnitude converted).
- E411's pitches that faulted with a 16-page buffer, rerun with `--depth-pages` sized to the
  extent E991 recomputed with E465's rule (G 5, 9 and 17) (3), and E411's bit-25 row (format 2 at
  G 1) with the buffer sized (1). Frozen H-E465-EXT (the stored pages E991 lists, the values by
  E991's rule); rival H-STOP16 (the store stops at the old 16-page bound). **Last, ascending
  extent, `on_stop = "end"`**: the store reaches pages no row has written (no fault predicted: the
  buffer covers every rival's extent).
- Control: an E996 replicate (1).
- Retire Q298 if each clause's hypothesis (or one rival) holds. If the bit-25 row is read but no
  frozen form decodes it, Q298 narrows to that row. Replay: sgx-pipe zls.rs, table `zovl`.

**zbits3 (Q071, 9 jobs, E1042's st1-b0 form).** Post hoc forms of E1042 frozen:
- H15-FAIL: bit 15 alone fails the stencil test at every pixel (0 drawn, the load stored
  unchanged), held out at 96 x 32 G 2 and under the reference value flipped (2).
- H23-MOD16: bit 23 alone draws 48 of every 64 pixels in E1042's period-16 pattern in x, every row
  alike, the read byte 0x00 / 0x80 where drawn and 0x3f where not; held out at 96 x 32 G 2 and at
  64 x 32 with another loaded fill (2).
- Pairs 21 + 23 and 22 + 23 (2): H-PAIR-23 (as 23 alone) against H-PAIR-ZERO (2048 drawn, 0xff,
  as 21 to 23 together) and H-PAIR-BASE (1024).
- Controls that can fail: zb2-c-base, zb2-c-set and E1042's b23 replicates (3).
- Narrow: bit 0 under other controls, bit 20 and the ISP's use stay. Replay: sgx-pipe zls.rs
  stencil sources (bit 23's pattern refused unless H23-MOD16 holds), table `zbits3`.

**zflat2 (Q120, 13 jobs, E1043's zf-flat-f6 form, 64 x 32, control 0x0617300e).** Frozen (E1043
post hoc):
- FL-REC0: a flat plane whose float has zero low 16 bits stores E1031's 44 dwords a block, row 0's
  record carrying the depth: 0.375, 0.625, 0.9375 and 0.0625 (4).
- Rivals for the other floats: H-LOW16 (any float with low 16 bits set stores another form, as
  0.1234) against H-FLATPLANE (the form follows whether every pixel's iterated depth is one value;
  E1043's [infer]). Rows 0.1, 0.3 and 0.5 + 2^-20 (low bits set, dyadic), each with a format-0
  twin that stores the per-pixel floats (6).
- Format 5 on the flat 0.5 replicated (1, a control on E1043's kept dump).
- Controls that can fail: zl-c-flat and zl-c-y6 replicates (2).
- Narrow: format 7's depth-dependent dwords, format 5's layout, format 6's edge tiles and runs,
  the pitch, packed formats without a stencil stay. Replay refused unless a rule holds.

### r15-tex (t10)

**chain (Q104, 18 probe fills, E562's generator: the scratch as the texture, each texel naming its
dword, T0 bits 20:17, 26:21 and MIPFILTER as E441 varied them).** Frozen chain=A (E562: both sides
halve to 1, levels back to back, the last 1 x 1, a LOD above clamping there; T0's maximum, bias and
MIPFILTER read it as a square chain); rivals chain=B (stops at the short side's 1) and chain=D
(square-padded), and for 16 bits the chain in texels against in dwords.
- 1D: smp1d on a 64 x 1 twiddled 32-bit texture, LOD 0 to 6 down the rows (2 fills: whole and
  half LODs) and the maximum field at 3 (1) (3).
- A side of 1 at level 0: 1 x 32 and 32 x 1 with smp2d, LOD rows (2 each), bias 7 on 32 x 1 (1) (5).
- 16-bit: a 32 x 16 and a 16 x 64 twiddled u16 chain, LOD rows (2 each), MIPFILTER at one fraction
  (1) (5).
- Long or wide sides past E562's: 256 x 32 at two LOD row sets and 64 x 32 at one (3) [E562's
  body; not in the line].
- Controls that can fail: E562's 32 x 16 and 128 x 16 held-out rows replicated (2), their kept
  images.
- Scratch: 256 x 32's chain is 43 KiB, inside t10's 64 pages. Retire Q104 if chain=A and the field
  readings hold on the 1D, side-1 and 16-bit rows. If smp1d is refused by the kit's program forms,
  "1D" is read as W x 1 under smp2d and reworded so [infer] (R15-6). Replay: sgx-sim tex.rs chain
  (non-square already modelled; 1D and u16 added by the fold), table `chain`.

**ty (Q177, 15 probe fills, E1039's type programs, 32 pages).** Frozen at the form level (the
name map has no size form yet):
- H-HALF: every pixel is a named dword with each byte halved, rounded up ((b + 1) >> 1), and the
  rows alike (E1039 post hoc, fold/types_post.py).
- H-NAME16: at 16 x 16 in u mode 4 a held-out u range reads the names E1039's map gives for those
  u [check: the builder fits the map's u dependence from addr5's row before freezing; if no map
  fits, this row is a reading].
- Rows: 32 x 32 u mode 4 on types 1, 3 and 4 with their mode 0 references (6); 16 x 16 u modes 5,
  6 and 7 on types 1 and 4 (6); the H-NAME16 row on type 1 (1). Rivals: H-WHOLE (the named dword
  unhalved), H-MODE0 (E1039's T-MODE0, a negative).
- Controls that can fail: E1039's addr5-ty1-u4 replicate and addr5-ctl (2).
- Narrow (R15-5 a): the 32 x 32 and modes 5 to 7 names become the fit for a size form held out
  in a later round. R15-5 b runs this as a fit pass early and a held-out pass (about 10 jobs at a
  third size, frozen after an offline fit) later in the round: then retire-capable.

### r15-isp (t10)

**zcut (Q241, 11 jobs, E1045's form: E977's ramp at 80 x 40, compare always, depth written and
dumped).** Frozen:
- H-PIXCUT: the plane is drawn unchanged and a pixel is removed iff its iterated depth lies past
  [0, 1] (E1045's reading taken per pixel).
- H-POLYCLIP: the MTE clips the triangle at z = 1 (or 0) (E287), the made vertices rounded half
  away from zero to 1/256 (E1037's CLIP-HA), coverage by E606's rule, the depth plane through the
  clipped polygon. H-POLYCLIP-NR (the made vertices unrounded) as a third.
- Rows: 6 triangles, one vertex depth 1.25 or -0.25, the others chosen offline so the cut line
  passes within 1/512 pixel of 6 to 20 pixel centres and the three forms part on those pixels
  (an engine check in the builder's tests: at least 4 parting pixels a row).
- E065's triangle: bit 15 replicated (control) and bits 16, 17 alone (3). Frozen H-EQUIV (16 and
  17 leave the pixel set bit 15 leaves) against H-NONE (no pixel) [check: the builder locates the
  kept 48-pixel job the line cites; without it these three rows drop].
- Control that can fail: E1045's two depth rows replicated (2).
- Narrow: bit 18, the visibility counter, the offset's units, pass types and gate pairs stay.
  Replay: sgx-pipe mte/isp clip, table `zcut`.

### r15-dpm (t10, regtimeline)

**pr4 (Q036, 10 jobs; r14-dpm's pr3 rows and predictions, a new session directory).** pr3's rows
(PR 0 x 2 controls, 1 x 2, 4 x 3, 7 x 3, `render_pb_pages` as frozen there), 0x0748 sampled
alone. The only change: the period gate (`short`) at **2000 ns** (E1044 read 1682 ns; the floor
is near 1.3 us plus 0.4 us a register). Frozen as pr3: R-PULSE strict (pulses >= PR on all rows),
R-RARE-TOTAL (1 to 8 clears), log-loss ranking. Narrow. The pulse width is the new datum: E1032's
one clear was one 16-register sample wide (about 8.4 us); at 1.7 us a pulse of that width spans
about 5 samples [infer]. Replay refused (register timelines).

## 3. Sessions (safe class only; one sitting on B60AB0B4)

| Session | Stages (jobs) | Jobs | Wall | Prefix | Records | Tool | Order |
| --- | --- | --- | --- | --- | --- | --- | --- |
| r15-zls | zpass (13), zbits3 (9), zflat2 (13), zovl (13, sized rows last) | 48 | ~13 min | r15z | E1050, E1051, E1053, E1054 | t10 | 1 |
| r15-tex | chain (18), ty (15) | 33 | ~9 min | r15t | E1052, E1055 | t10 | 2 |
| r15-dpm | pr4 (10) | 10 | ~8 min | r15d | E1057 | t10 | 3 |
| r15-isp | zcut (11) | 11 | ~4 min | r15i | E1056 | t10 | 4 |
| r15-tw | tw14 (14) | 14 | ~5 min | r15w | E1049 | t14 (t10 health) | 5 |

Record numbers (priority 1 first): **E1049** tw14 (Q078), **E1050** zpass (Q297), **E1051** zovl
(Q298), **E1052** chain (Q104), **E1053** zbits3 (Q071), **E1054** zflat2 (Q120), **E1055** ty
(Q177), **E1056** zcut (Q241), **E1057** pr4 (Q036); E1058 conditional (R15-4 b, Q108 edmld).

Wall: about 6 s a job, 640 x 480 and the sized-pitch rows about 10 s, the dpm scene about 40 s a
job, about 3 min of staging and preflight a session: **about 39 min of jobs + 15 min staging = 55
min**, under 1.5 h. Builders run offline in parallel first (about 1 to 1.5 h); no tooling package.

Order: r15-zls (in range but zovl's sized rows, which are last with `on_stop = "end"`), r15-tex
(t10's shapes and programs run before), r15-dpm (the scene ran in r13/r14), r15-isp (the cut rows
are E1045's form), r15-tw last (bit 14 at widths never run: the one session whose reads reach
places no job has read; a stray fault there ends the round with everything else run).

Kit fit (main 158bdc5; kit unchanged since dddadbd/c58f9f9):
- r15-zls: fits (r14-zls forms; `--kpoke-render`, `--depth-pages`, `--poke blk:10/11`, formats via
  the control word). Pass `--depth-pages` at every odd size (Known tool weaknesses).
- r15-tex: fits (r13/r14-tex forms; smp1d and the type programs are own probe programs, replayed
  "not simulated" since c12542e).
- r15-dpm: fits (r14-dpm's kit session, regtimeline `wraps = true`, `dbg:render_pb_pages`); only
  the gate constant and the session name change.
- r15-isp: fits (`--tri-z`, `--depth --depth-store`, ISP word pokes as r14-isp's wind).
- r15-tw: fits (r14-flag's f1 bound t14 by `--tool-src t14=c58f9f9:...@closing14/k14/
  build_tool14.sh`; no `expectfault`, `#limit 0`; t10 health pair as r14-flag).

Per-session premise checks (builder's tests besides the library-mock replay): r15-tw: every
rival's farthest dword below 262144 (1 MiB) for every row; r15-zls: `--depth-pages` covers every
rival's extent, the blk:10/11 pokes are floats, E991's page lists recomputed for G 5, 9, 17;
r15-tex:
every chain inside the scratch, each type row has its mode 0 reference; r15-isp: at least 4
parting pixels a cut row (engine), every vertex in int32; r15-dpm: the gate constant is the only
diff from r14-dpm's frozen tables and predictions (a test diffs them).

## 4. Tool changes

None. t10 for every row but tw14 (t14, required for 256 scratch pages). t14 is main's
sgxfive-test (no userspace commit after c58f9f9); R15-7 b would bind it everywhere.

## 5. Offline parts (no laptop)

- Predictions frozen by the builders: tw14 from E1047's fold forms (H-TWP and rivals, reach
  table); zpass from sgx-pipe `zls::pass` extended test first (the hypothesis is the extension);
  zovl from E996/E1041 and E991's page lists; zbits3 from E1042's look.py; zflat2 from E1043's
  look.py; chain from E562's generator and predictions; ty from types_post.py (H-NAME16's map
  fitted on addr5's kept row first); zcut from c6's engine plus CLIP-HA; pr4 copied from r14-dpm.
- R15-5 b only: the ty fit pass is folded offline into a size form before the second pass freezes.
- Unused number if R15-4 stays (a): E1058.

## 6. Retire summary if every frozen hypothesis holds

Q078, Q297, Q298, Q104 retire (four); Q071, Q120, Q177, Q241, Q036 narrow. If R15-5 b runs and
holds, Q177 retires too.

## 7. Later, with the user (not safe class; not in any session)

- **Q108**: EDMPROTECT on a load-only depth render (3 jobs; a fault rival is live, E965), WRITEONLY
  or EDMPROTECT on a texture read (E945 H-WO-ALL predicts a fault), the TA's writes and the EDM's
  buffers (planned faults); CACHECONSISTENT on a texture read across renders needs `--refill`
  to take a texture buffer (a tool change).
- **Q139**: E509's faulting macrotile words and the stride's relation (planned faults).
- **Q163**: the counter's other shapes, v = 0, idle 120 s, a second context (recovered hangs; T13
  kit words; round 14's F3).
- **Q241 bit 18** (faults, E065, E998). **Q036's builder-fault clause** (a base-only builder fault).
- **Q046 bit 11**: faults at 0x37001000 (E1034); offline mapping of that page first.
- **Q298 at E411's original 16-page buffer**: not needed if zovl's sized rows hold.

## 8. R15 decisions (the lead takes the first option of each)

1. **R15-1 Safe sessions.** a) All five, in the order zls, tex, dpm, isp, tw: 116 jobs, about 55
   min, records E1049 to E1057 (recommended); b) only the retire-capable stages (tw14, zpass, zovl,
   chain): 58 jobs, about 30 min; c) a without r15-dpm (Q036 only narrows; saves about 11 min).
2. **R15-2 Q078 widths (r15-tw on t14).** a) Safe class, H at most 32 so every rival's reach is
   inside 1 MiB, the session last, rows in reach order, `on_stop = "end"` (recommended: E1047 read
   every bit-14 pixel inside the scratch); b) move it to section 7; c) point rows only (no u16, no
   bilinear): narrows, cannot retire.
3. **R15-3 Q036 gate.** a) Re-run pr3 as pr4 with the period gate at 2000 ns, rows and predictions
   unchanged (recommended); b) no gate, the period only reported; c) skip Q036 this round.
4. **R15-4 Q108.** a) No row this round; the EDMPROTECT load-only row goes to section 7 (live fault
   rival) (recommended); b) edmld (3 jobs, E1058) as the last stage of r15-zls with `on_stop =
   "end"`.
5. **R15-5 Q177 types.** a) One pass, narrow (15 jobs: halving held out, fit grid for sizes and
   modes 5 to 7) (recommended: the user is asleep and a second build pass adds a dependency);
   b) two passes in the round (fit early, offline size form, about 10 held-out jobs later):
   retire-capable; c) skip ty.
6. **R15-6 Retirement with void or reworded clauses.** a) As R14-6: a fold proposes retirement
   when every measurable clause is decided by held-out rows with passing controls; Q078's "other
   formats" reads "the 16-bit format", Q104's "1D" reads smp1d on W x 1 (or W x 1 under smp2d if
   smp1d is refused), each marked [infer], the lead confirms (recommended); b) these questions
   only narrow.
7. **R15-7 Tool binding.** a) t10 everywhere but tw14 (t14) (recommended: the replicate controls
   rerun kept t10 jobs); b) t14 everywhere.
8. **R15-8 Record numbers.** a) E1049 to E1057 as in section 3, E1058 only with R15-4 b
   (recommended); b) the lead renumbers after the builds.
9. **R15-9 Dropped rows.** a) As in section 1 (Q260, Q284, Q210, Q107, Q045, Q019, Q066, Q211,
   Q202 offline; Q114, Q115, Q161, Q160, Q159, Q013, Q043, Q044 no one-session retirement)
   (recommended); b) add an offline Q202 design task (divide-parting vertices) for round 16.
