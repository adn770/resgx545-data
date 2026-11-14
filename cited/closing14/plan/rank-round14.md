# Round 14 ranking: laptop rows that hold out round 13's post hoc fits (Opus, 2026-11-14)

Basis: resgx545 `main` dddadbd (records to E1035, 153 open), resgx545-data 3309b5fd9, fork resgx545
2a650d74 (read only), laptop on module B60AB0B4 (one-shot boot; a reboot returns to stock Arch).
Inputs: round 13's records E1022-E1035 and their "What it does not show", the question lines and
last narrowings of Q261, Q199, Q177, Q282, Q243, Q071, Q120, Q036, the round 13 handover's Next
item 4, section 4 of `closing11/plan/rank-round11.md` (tier L) and `closing12/plan/rank-round12.md`,
`closing10/seeds/exp-seeds-r10.md` section 13, and `closing13/r13-zls/fold/look.out`. Nothing
staged,
built or run; no laptop, SSH or cachix. This file is the only output.

Checks done for this plan (read only):
- `git log a581c06..dddadbd -- userspace/` holds no commit: **t10 (9bedc2d6, from a581c06) is
  still main's sgxfive-test**. Every row binds t10 except the T14 rows (r14-bif, and F1 if R14-4 a).
- The viewport is state-block words 6 to 11 of `tri` (`src/render.c` `sgxfive_tri_block`: x offset,
  x scale, y offset, y scale = W/2, H/2, then z offset, z scale), and `tri --poke blk:N=V` already
  writes a block word (r13-zls zbase used `blk:1`). So a viewport other than the target needs no
  tool
  change [check: with `--isp2` the words move on by one; no row here uses both].
- `probe --scratch-pages` takes 16 to 64 pages only (sgxfive-test.c line 4078). E1033's second fault
  is at scratch + 0x40000, exactly 64 pages: **t10 cannot map the reach of E1033's held-out row**.
  That is T14 item 2.
- E944/E950 read three residue TA dumps at fx 2 or 3 mod 4 out of faulting jobs, so a faulting Q139
  row still yields its TA dump (F2 is decodable).
- E1031's flat block (zf-flat-f6) is a byte stream of 0x00, 0x3f, 0x9e, 0xc0 (`look.out`): no rule
  is
  frozen yet, so zflat's prediction is written by its builder offline before the freeze (section 5).

## 1. Every candidate row, ranked (retire first)

"Retire" = every open clause of the question line is decided by held-out rows if the frozen
hypothesis holds and the controls pass (void clauses marked [infer], R14-6). "Narrow" = a clause
stays open whatever happens.

| # | Row | Question | If it holds | Jobs | Stage (session) | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | quarter-target guard on 5 targets + viewport | Q261 | **retire** (with R14-6) | 21 | g14 (r14-isp) | safe; vp rows last |
| 2 | clip-made vertex rounding, 4096-wide, int32 ends | Q199 | **retire** (with R14-7) | 10 | clipr (r14-isp) | safe; 2^31 rows last |
| 3 | trilinear lerp held out, bytes 2 and 3 | Q282 | **retire** | 13 | srgb4 (r14-tex) | safe |
| 4 | mode 5 corner base at 6 shapes, types 1/3/4 | Q177 | **retire** (with R14-6) | 14 | addr5 (r14-tex) | safe |
| 5 | load-base granule 8/16/32, int format, stencil base | Q243 | **retire** (with R14-7) | 11 | zgran (r14-zls) | safe |
| 6 | integer formats at odd sizes, E411 past page 15 | Q242 | retire-capable | 7 | zodd (r14-zls) | safe |
| 7 | set half bit by bit, linear stencil pitch | Q071 | narrow | 20 | zbits2 (r14-zls) | safe |
| 8 | flat F6 blocks at 5 depths, F5/F7 forms | Q120 | narrow | 9 | zflat (r14-zls) | safe |
| 9 | 0x0748 alone, fast sampling, PR 0 to 8 | Q036 | narrow | 10 | pr3 (r14-dpm) | safe |
| 10 | bits 15-17 on the other winding, depth outside [0, 1] | Q241 | narrow | 7 | wind (r14-isp) | safe |
| 11 | CACHECONSISTENT on refilled data | Q108 | narrow | 6 | refill (r14-bif) | safe; needs t14 |
| 12 | bit 14 twiddled with the reach mapped | Q078 | **retire-capable** | 5 | F1 (r14-flag) | **planned faults** |
| 13 | H-EVEN at fx 2/3 mod 4 | Q139 | narrow | 5 | F2 (r14-flag) | **planned faults** |
| 14 | counter: other shapes, v 0, idle 120 s, second context | Q163 | narrow | 10 | F3 (r14-flag) | **hangs**, optional |

### Rows the kept data already decide (dropped, or cut to a text fix)

- **Q199, negative vertices**: E683 decided that negative vertices with a sub-grid fraction are not
  rounded half up, and E914/E943 that a negative tie rounds away from zero. Q260 carries that
  arithmetic, and Q199's own text says so ("Negative vertices with a sub-grid fraction are not
  rounded half up (E683, Q260)"). No row: a text fix drops the clause from Q199's line (R14-7).
  Rounding of the vertices the clip *makes* stays, as clipr's rows.
- **Q243, integer load, NaN/infinity, equal depths**: E977 and E995 answered these (round 13 plan,
  section 1). The line still asks them, so it needs a text fix (R14-7). Only the granule, the moved
  base with an integer format and the stencil load base are left.
- **Q177, the strided type**: E565's kept bd-st-u4 to u7 read as mode 0 (E1026, read at the fold).
  Only types 1, 3 and 4 are left.
- **Q282, negative values**: void [infer] (E1025: sRGB bytes decode non-negative, weights are
  non-negative). No row.
- **Q078, bilinear footprint on a strided texture**: E1027 (H-FOOT 1 of 1). Only the twiddled clause
  is left (F1).
- **Q260**: no form to test (its text: "the question has no rows until one is formed"). Offline.
- **Q284**: E1001/E1002 found no rule for ties or edges. A row needs a frozen form first. Offline.
- **Q210, Q107, Q045**: unchanged since round 13 (E1013; E628; E627's locator offline first).
- **Q046 bit 11**: E1034 repeats E383's fault page 0x37001000 three times. What maps there is an
  offline question (the tool's `--print-addrs` and the fork's heap map). No row until a mapping is
  named. Bit 12's low half has no frozen source either (E1028, E1034: post hoc only). Offline.
- **Q019, Q066, Q211**: no row with a frozen hypothesis in any list (Q019's 32/64 attribute
  experiment needs a layered-object form nobody has written; Q066's words 9, 11-14 inert, E1006;
  Q211's long dpm jobs only narrow). Not planned.

## 2. Rows in detail

Every stage: `#limit 0` unless flagged. Any unexpected fault or hang stops it (kit rc 4). Controls
are `reads:` rows of the stage's own shape, not the default triangle, and expectdiff rows need `job:
ok`. Predictions are frozen before staging (kit freeze). "Held out" = no kept job ran that row's
input; "replicate" = a kept job rerun; a replicate is a control when its kept image can fail.

### r14-isp

**g14 (Q261, 21 jobs, `tri --tri-unit 5` or 0, t10).** Frozen point hypothesis, fitted post hoc in
E1023:
- H-QUARTER-VP: the far edges are clipped to the box a quarter of the *viewport* past each edge,
  [-W/4, 5W/4] x [-H/4, 5H/4] in the viewport's window pixels (= clip |x|, |y| <= 1.5 w). The new
  vertex is rounded half up to 1/256, then the edges are exact (E1012).

Rivals:
- H-QUARTER-TGT: the same box, but of the render target, not the viewport. It parts from VP only on
  the poked-viewport rows.
- H-MAX4 and H-MIN4: a quarter of max(W, H) or of min(W, H) on both axes. They part on non-square
  targets.
- H-PLUSG: target + G with one G per target, read as a family (E1023's 147 on 128 x 128).
- H-ABS: a guard fixed in pixels (80 to 86; refuted on x by E1023, kept for y and the lower bound).

Each bound is also read as a family per row, as E1023 did (c6's `q261_rule2.py`, extended by the
builder to a per-axis box and a viewport map; the extension is tested equal to c6's on E1023's 24
rows). Rows (all held out; vertices chosen offline so that each row's band pixels part the
rivals):
- 64 x 64: two rows along -x whose band parts a = 9 from a = 16 (E1023 left both).
- 128 x 128: two rows along +x (147 vs 160 vs 173), two along -x (-32 vs -16, -9, -19), one along
  -y and one along +y (-32 / 160 vs the 64 x 64 values).
- 256 x 256: one row each along +x, -x, +y and -y (quarter: [-64, 320]).
- 128 x 64 and 64 x 128: one row along x and one along y each (VP per axis, against MAX4 and MIN4).
- Poked viewport, last in the stage. First, a 128 x 128 target with the viewport poked to 64 x 64
  at the origin (`--poke blk:6=0x42000000` to `blk:9`, 32.0
  each), far vertex along +x, then along +y. VP cuts the triangle at window x = 80 (columns 80
  to 127 empty: thousands of pixels); TGT draws through 127. Second, a 64 x 64 target with the
  viewport poked to 128 x 128 (scale 64.0, offset 64.0 [check: whether the offset word comes first,
  from `render.c`'s order]): band-pixel parting, [-32, 160] against [-16, 80].

Controls that can fail: a replicate of E1023's t128-1 (G 19 only) and E979's far-ctl, both against
their kept images. Premise checks in the builder's tests: every row's `--tri-v` within int32, the
poked words as floats, and the TA's macrotile words of 128 x 64, 64 x 128 and 256 x 256 in the
drawn-without-fault set (E1007's baselines; Q139: fx and fy 0 or 1 mod 4 [check per shape]).

Retire Q261 if H-QUARTER-VP holds on every held-out row and both controls pass. The clause "clip
space or window pixels" is then answered as "the viewport's box": for w > 0, |x| <= 1.5 w in clip
space and [-W/4, 5W/4] in viewport pixels are the same set, so the two can part only in rounding
or at w <= 0 [infer]. The fold rewords the clause that way (R14-6). Replay: sgx-pipe
`isp::guard_clip_image` extended past 64 x 64 (fold), table `g14`.

**clipr (Q199, 10 jobs, t10; after g14, the int32 rows last).** Frozen:
- H-HALFUP-CLIP: a clip-made vertex is rounded floor(256 x + 0.5) on both axes and both signs, as
  E1012 fitted on positive coordinates.
- Rivals: H-HAZ-CLIP (half away from zero for negative coordinates, Q260's tie rule), H-RNE-CLIP,
  H-TRUNC-CLIP.

Rows (held out):
- Two far vertices whose clip vertex on x = 80 has y on an exact 1/512 tie (one with y positive,
  one negative, inside the target's band region).
- One whose clip vertex on y = -16 has x on a negative tie.

The builder picks vertices whose intersection is exact in float32 too, so the clip arithmetic's
own rounding cannot hide the tie [check by the engine: the float32 and exact intersections agree].
Then, on a 4096-wide target (4096 x 128, or the nearest drawn-without-fault shape [check]):
- a vertex inside the guard at x = 5000 + 1/512 (a tie at 1.28e6 units, H-QUARTER: guard 5120);
- one at x = -1000 - 1/512;
- one far vertex at 2^24 px along +x (VP predicts the clip at 5120; also a Q261 row).

Last, at `--tri-unit 0`: one vertex at x = 2^31 - 1 and one at y = -2^31 px on 64 x 64 (the int32
ends; E1024 stopped at 2^30). Controls that can fail: E1024's x30p and E684's far21d0 replicates.
The stage stops at its first non-ok (`#limit 0`).

Retire Q199 if H-HALFUP-CLIP (or exactly one rival) holds on the three tie rows, the 4096 rows draw
as VP's guard with the inside vertices rounded as predicted, and the int32 rows draw the clip.
After the text fix (R14-7), the line keeps only these clauses. Replay: sgx-pipe isp, table
`clipr`.

**wind (Q241, 7 jobs, t10; first stage of r14-isp, in range).** E998's ramp form (depth compare
with writes, `tri --depth --depth-store`), with ISP word 0 bits 15, 16 and 17 each set alone on the
ramp triangle with its vertex order reversed (3 rows). Frozen:
- H-CULL: each bit removes one winding, and E998 saw the other. The reversed triangle then draws
  E977's ramp and stores its depth.
- Rival: H-KILL, any triangle is removed (no pixel, as E998).

Two more rows put one vertex's depth outside [0, 1] (`--tri-z 1.25,...` and `-0.25,...`):
H-CLAMP (the stored depth is clamped to [0, 1]) against H-ZCLIP (pixels past 1 removed) and
H-RAW. Controls that can fail: the reversed triangle with bits 15-17 clear (draws), and an E998
bit-15 replicate (no pixel). Narrow: bit 18 (faults), the visibility counter, the polygon offset's
units, the pass types and the gate pairs stay open.

### r14-tex

**srgb4 (Q282, 13 probe fills, t10, srgb3's forms).** Trilinear clause, frozen post hoc in E1025:
- TRI-RNTU: the two levels' FTZ-OUT halves, the operands floored to 2^(e - 16), lerped exactly at
  f/64 and rounded to nearest, ties up.
- Rivals: TRI-RNE (ties to even, 3957 of 4096 post hoc), TRI-BF11 (3185), TRI-OUT (1137).
- LOD fraction quantization: Q-FLOOR against Q-NEAR (f = floor or nearest of 64 frac).

Rows (held out): LOD 1.125, 1.5, 1.75, 1.984 (f 8, 32, 48, 63), 0.25 (levels 0 and 1), 1.2 (f
12.8: parts Q-FLOOR from Q-NEAR), and a dark chain whose halves are subnormal before the lerp
(the flush and the third stage together).

Bytes 2 and 3: a probe program of ours (E723's, with the sample's *second* output dword moved to
the pixel; the kit replays own probe programs since c12542e) on the x stage alone, the y stage
alone and both stages. Frozen: H-ALPHA-LIN (byte 3 is not sRGB-decoded, filtered by the same
stage rule on byte / 255) against H-ALPHA-SRGB (decoded as bytes 0 and 1). Byte 2 (blue) is
FTZ-OUT in both.

Controls that can fail: a replicate of srgb3's trilinear row (its kept image, 2048 of 2048), the
new program's byte 2 on srgb3's x1 texture with the blue byte equal to x1's byte 0 (it must read
x1's
channel 0 halves), and E723's g-bl-st-a. Retire Q282 if TRI-RNTU (or exactly one rival) holds on
all 7 trilinear rows and exactly one alpha form on all 3. Replay: sgx-sim tex.rs (the third stage
added by the fold), table `srgb4`.

**addr5 (Q177, 14 probe fills, t10, addr4's forms).** Corner base, u and v in mode 5 swept past both
ends. Frozen:
- C-LOG4: c = 4 log2 max(W, H), post hoc on E1026's four shapes.
- Rivals: C-SAT24 (min(4 log2 M, 24)), C-FLOOR16 (max(16, 4 log2 M)), and E1026's three failed
  forms (as negatives).

Rows (held out): 8 x 8 (C-LOG4 12, C-FLOOR16 16), 32 x 32 (20), 128 x 32 and 32 x 128 (28 against
SAT 24), 128 x 128 (28; scratch 32 pages [check]), 256 x 32 (32 against 24) [check: T0 takes a
256-wide twiddled texture].

Types 1, 3 and 4: u mode 4 on each, with its own mode 0 reference (6 rows). Frozen: T-MODE0 (read
as mode 0, as the strided type does) against T-OFFSET (E561's index of that type plus
8 max(W, H) + 52). Read as images against the reference, since what types 1 and 4 read at mode 0
is not known (E567).

Controls that can fail: E1000's 16 x 64 mode 4 and E565's bd-uv5 replicates. Scratch: every rival's
farthest read inside it (256 x 32: 8 x 256 + 52 + 32 dwords past the texture). Retire Q177 if C-LOG4
holds on all six, and the type rows decide each type. "Why these constants" has no row: it is void
for a hardware row and is reworded to the held-out formulas [infer] (R14-6). Replay: sgx-sim tex
address (the corner base added), table `addr5`.

### r14-zls

**zgran (Q243, 11 jobs, t10, zbase's form).** `--kpoke-render 1:rd:12=0x1000 + m`, depth `index`,
test never, 20 pages. Frozen:
- G8, G16, G32, G64: the base rounded down to 8, 16, 32 or 64 bytes (E1029 post hoc).
- H-BYTE (byte exact; refuted by zb-m4) kept as a negative.

Rows (held out): m = +8, +16, +32 (the granule), +0x1008 and +0x1020 (granule with a page move),
and integer formats 1 and 2 with m = +0x1000 (H-MOVED-INT: E465's layout of the integer format from
the moved base). Stencil: E988's st1 form with the stencil load base `--kpoke-render 1:rd:14=` moved
by +0x1000 [check: rd:14 is the stencil load base, the fork's `sgxfive_kpoke` field list].

Controls that can fail: zb-c-ctl, and the +4 and +0x40 replicates (they must load unmoved and moved
by 16 dwords). Retire Q243 if exactly one granule holds on all five granule rows and the integer and
stencil rows load from their moved bases. Replay: sgx-pipe zls.rs (the granule), table `zgran`.

**zodd (Q242, 7 jobs, t10, E977/E991 forms).** Integer formats 1 and 2 at 63 x 31 and 65 x 33 (4
rows). Frozen: H-FLOOR-EXT (E977/E991's floor rule extended over the whole edge tile, as past 80 x
40) against H-ZERO-PAST and H-EDGE-CLAMP. E411's G 3 job rerun with `--depth-pages 20` (1 row:
H-NEXTTILE, pages 16 and 18 hold the tiles E465's layout puts there, against H-STRAY). E996's
overlap form at a pitch with edge tiles (1 row: E996's header-order rule). Control: an E996
replicate. Retire-capable: the "four macrotiles a side" clause holds only if the builder's overlap
row covers it [check].

**zbits2 (Q071, 20 jobs, t10, zbits' forms).**
- The set half, under E988's stencil test, bit by bit: 15, 21, 22, 23, 27, 28, 29, 30, 31 alone
  (9 rows), and 21-23 and 27-31 as groups (2). Frozen: H-ONE-k for each bit (exactly one bit reads
  0), against H-GROUP (no single bit does).
- Linear stencil pitch: bit 12 cleared and bit 16 cleared, each at 96 x 32 G 1 and at 64 x 32 G 2
  (4). Frozen P-64 (64-byte rows) against P-W (width bytes) and P-G (32 (G + 1)), post hoc in
  E1030.
- Bit 12 cleared with a depth load (z243's loaded ramp; H-DEPTH-UNCH against H-DEPTH-LIN) (1).
- Bit 16 cleared on the 16-bit depth format (1).

Controls that can fail: zbs-base (1024 drawn), zbs-set (2048, every byte 0xff), and the zbr-c16
replicate (E997's linear image). Narrow: bit 0 under other controls, bit 20's role and the ISP's use
of the control stay.

**zflat (Q120, 9 jobs, t10, zfmt's form).** The builder first fits E1031's 44-dword flat block
offline (section 5) and freezes it. If no rule fits, the rows are readings and the stage narrows by
data only. Rows: flat planes at 0.25, 0.75, 0.1234 (four distinct float bytes), 1.0 and 0.0 (5);
format 7 under the index stencil fill (1); format 5 on a plane of constant rows (1). Controls that
can fail: zf-flat-f6 and z2y-f6 replicates (their kept dumps byte for byte). Narrow.

### r14-dpm

**pr3 (Q036, 10 jobs, regtimeline over t10, pr2's scene).** Q036 was narrowed on 8 jobs with ~19
registers sampled about every 8 us. pr3 samples **0x0748 alone**, to shorten the period [check:
the period against the register count, from the kept r8-ldpm and r13-dpm timelines]. Rows: PR 0
x 2 (controls: no clear line), PR 1 x 2, PR 4 x 3, PR 8 x 3 (`render_pb_pages` below 0xe2
[check: the scene still overflows 8 times]). Frozen:
- R-PULSE: at least one clear line per partial render once the period is short.
- R-RARE: Poisson at E1032/E1019's 0.07 to 0.17 per partial render, whatever the period.
- R-CONST.

Scored strict for R-PULSE and by log-loss for the others. Narrow: CR_DMS_CTRL, the signature
registers and the builder fault stay. Replay refused (register timelines).

### r14-bif (t14)

**refill (Q108, 6 jobs, `tri -n 2 --refill 2:depth=V`).** The depth load buffer's PTE with
CACHECONSISTENT (`dbg:vm_pte_addr`, `dbg:vm_pte_flags` [check: the flag's bit, E945]). Render 1
loads the buffer, the host refills it, render 2 loads it again. Rows:
- the flag set with and without the refill (2);
- the flag clear with and without (2);
- the refill of a buffer render 1 never read (1: must read V, the control that can fail);
- the plain two-render job (1: control).

Frozen: H-CC-COHERENT (flag: render 2 reads V) against H-CC-STALE, and both readings for the
flag-clear rows. Narrow (WRITEONLY and EDMPROTECT on a texture read, the TA's writes and the EDM's
buffers need faults). Replay refused.

### r14-flag (flagged; user OK; after every safe session)

**F1 (Q078 bit 14 twiddled, 5 jobs, t14 with up to 256 scratch pages; t10 at 64 if R14-4 c).**
The builder fits address forms, post hoc, on E1033's two fault pages (+0x21000 and +0x40000) and
freezes them. Rows, with the scratch filled with its dword index:
- E566's tw32-t3b14 at the largest scratch;
- the held-out u = x / 4096 row at the largest scratch;
- u = 0 everywhere (does a twiddled read with no move fault?).

Each row predicts an image (the read lands in the scratch) or a fault page. `#limit 3` counts only
these three planned rows. Two bit-clear references are the controls: a fault there stops the stage.
Retire Q078 if one frozen form gives the image or fault page of all three.

**F2 (Q139 fx 2/3 mod 4, 5 jobs, t10).** Four TA-dump jobs at fx 2, 3, 6 and 7 mod 4 at strides
and targets never run, each chosen so that H-EVEN's map parts the flag's two rivals (the last
block-order target tile against the highest target slot), `expectfault`, `#limit 4` (planned
only). Control: E1007's 256 x 256 baseline (draws exactly, no fault). Frozen: H-EVEN against
R7-BLK slots; H-LASTBLOCK against H-HIGHSLOT. Narrow (the stride's relation and E509's words stay).

**F3 (Q163, ~10 jobs, ~5 hangs, t10 on the T13 kit words; optional, R14-5).** Each sequence is
opened by a reset row:
- v = 0, and v = 1 in block 1 (the counter's premise);
- 24- and 48-vertex streams at v = 7 twice;
- `idle:120` between a v = 7 pair;
- a `--ctx2` job between a v = 7 pair.

Frozen: E700/E1035's counter (M3) against H-SHAPE, H-DECAY, H-CTXCLR. `#limit 6`. Stop at the
first failed recovery (no reboot; the user decides). Narrow (what the counter is stays).

## 3. Sessions (safe first; one sitting on B60AB0B4)

| Session | Stages (jobs) | Jobs | Wall | Prefix | Records | Tool | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| r14-tex | srgb4 (13), addr5 (14) | 27 | ~8 min | r14t | E1038, E1039 | t10 | safe |
| r14-zls | zgran (11), zodd (7), zbits2 (20), zflat (9) | 47 | ~11 min | r14z | E1040-E1043 | t10 | safe |
| r14-dpm | pr3 (10) | 10 | ~7 min | r14d | E1044 | t10 | safe |
| r14-isp | wind (7), g14 (21), clipr (10, int32 last) | 38 | ~10 min | r14i | E1045, E1036, E1037 | t10 | safe; vp and int32 rows last |
| r14-bif | refill (6) | 6 | ~4 min | r14b | E1046 | **t14** | safe |
| r14-flag | F1 (5), F2 (5), F3 (~10, optional) | 10-20 | ~8 (+10) min | r14f | E1047, E1048 (E1049) | t14/t10 | **flagged** |

Record numbers: E1036 g14 (Q261), E1037 clipr (Q199), E1038 srgb4 (Q282), E1039 addr5 (Q177), E1040
zgran (Q243), E1041 zodd (Q242), E1042 zbits2 (Q071), E1043 zflat (Q120), E1044 pr3 (Q036), E1045
wind (Q241), E1046 refill (Q108, if R14-4 a/b), E1047 F1 (Q078), E1048 F2 (Q139), E1049 F3 (Q163, if
R14-5 b). Priority-1 rows take the low numbers.

Wall: about 6 s a job (round 13: 168 jobs in about 45 min with staging), larger targets (256 x 256,
4096 x 128) about 10 s, faults and hangs about 40 s each, about 3 min of staging and preflight a
session. **Total about 48 min safe + 8 min flagged (+10 with F3), under 1.25 h.** Builders run
offline in parallel first (about 1 to 1.5 h); T14 and the cachix build of t14 run alongside them.

Order: r14-tex, r14-zls, r14-dpm (all in range), r14-isp (its viewport and int32 rows are the only
safe rows in untested ground, last in their stages; `#limit 0` stops at the first non-ok), r14-bif
(the new binary), then r14-flag: F1, F2, and F3 last (a failed recovery there ends the round with
everything else run).

Kit fit (main dddadbd):
- r14-tex: fits (r13-tex forms; the second-dword probe program replays as "not simulated" in the
  library mock since c12542e; no t10p).
- r14-zls: fits (zbase/zbits/zfmt forms; `rd:14` in `--kpoke-render` [check the mock accepts it]).
- r14-dpm: fits (regtimeline `wraps = true`, `dbg:render_pb_pages`, one register).
- r14-isp: fits (`--tri-unit`, int32 `--tri-v`, `--poke blk:N`, `--tri-z`). The 4096-wide pixel
  dumps are 0.5 M lines a job: `min_free_mb` to be raised [check the size gzipped].
- r14-bif: needs t14 (T14 item 1); the kit is unchanged (the library-mock replay builds the tool
  from its source commit).
- r14-flag: fits (`expectfault`, `#limit` counting planned rows only, `noreset`, `idle:S` up to
  120).
  F1 at 256 pages needs t14 (T14 item 2).

Per-session premise checks (builder's tests, besides the library-mock replay):
- r14-isp: every far row has `--tri-unit` and int32 values; the vp rows poke four words as floats;
  every target's macrotile words are in the drawn-without-fault set.
- r14-zls: zgran's kpoke follows depth_arm's pokes and `--depth-pages` covers the largest move;
  `--isp2` only with `--depth --stencil --stencil-store`.
- r14-tex: scratch covers every rival's farthest read; every type row has its mode 0 reference.
- r14-flag: `#limit` counts only planned rows; `hook_fault` reads the keys the scorer needs; a
  reference row's fault stops the stage (E946's lesson).

## 4. Tooling package T14 (one agent, test first, then a t14 build on cachix by the lead)

Changes only in `userspace/libsgxfive/tools/sgxfive-test.c` (and its tests). The kit is unchanged.
1. `tri -n N --refill K:BUF=V` (BUF one of `depth`, `stencil`, `fb`; 2 <= K <= N). The host writes V
   to every dword of BUF's CPU mapping after render K - 1 has completed and been read back, and
   before render K's kick. It uses the same write path as the first fill, and prints `refill:
   render K buf BUF value V`. Refused (usage, rc 2) without `-n` >= K, or when BUF is not mapped.
   Tests: the argv refusals, and in mock mode the fill lands between the two submits (the order of
   the mock's log).
2. `probe --scratch-pages`: upper bound 64 -> 256 (1 MiB). Before changing it, the agent checks that
   the scratch heap has the room (E1033: the 1 MiB past the default scratch is unmapped, so the heap
   reaches past it [check against the fork's heap sizes]). Tests: 256 accepted, 257 refused, and the
   `--low`/`--late` bounds follow.

Build: the lead builds t14 from the T14 commit on cachix with round 10's recipe
(`closing10/k10/build_tool10.sh` with the new commit), and binds it as `--tool-src
t14=<commit>:userspace/libsgxfive/tools/sgxfive-test.c@<recipe>`. About 45 min on the Mac plus the
build. Without T14: r14-bif drops, and F1 runs at 64 pages with t10, which still reads the next
fault
page past +0x21000 (narrow only).

## 5. Offline parts (no laptop)

- Predictions, all frozen offline by the builders:
  - g14 and clipr from c6's engine, extended per axis and through the viewport;
  - srgb4 from E1025's post hoc third stage (`fold/srgb3_tri_post.out`) and c2's `rule_b.py`;
  - addr5 from E1026's forms;
  - zgran from E1029's `look.py`;
  - zbits2 from E1030's `look.py` forms;
  - pr3 from E1032's scorer.
- zflat: fit E1031's 44-dword block (the byte stream of 0x00, 0x3f, 0x9e, 0xc0; 0x3f is the top byte
  of 0.5's float [infer]) before freezing, and freeze the fit or "readings only".
- F1: fit address forms on E1033's two fault pages, frozen as post hoc forms.
- Text fixes in the folds (R14-7): Q199's line drops the negative-vertex clause (E683, Q260); Q243's
  drops the integer, NaN and equal-depth clauses (E977, E995).
- Q046 (no row): name what maps at 0x37001000 from the tool's `--print-addrs` and the fork's heap
  map; compare bit 12's low halves of E383, E1028 and E1034 against the previous job's target.
- Unused numbers if decisions cut rows: E1046 (refill), E1049 (F3).

## 6. User decisions

1. **R14-1 Safe sessions.** a) r14-tex, r14-zls, r14-dpm, r14-isp in that order: 122 jobs, about
   36 min, records E1036 to E1045 (recommended); b) only the priority-1 stages (srgb4, addr5,
   zgran, zbits2, zflat, pr3, g14, clipr): 108 jobs, about 32 min; c) only the retire-capable
   stages (srgb4, addr5, zgran, zodd, g14, clipr): 76 jobs, about 24 min.
2. **R14-2 Poked-viewport rows (Q261, 3 jobs).** a) Safe class, last in g14 after every in-range
   row, stop at the first non-ok (recommended: a viewport word is a float the tool already writes,
   only its value changes [infer]); b) move them to r14-flag; c) skip them (Q261's viewport clause
   stays, so Q261 cannot retire).
3. **R14-3 Q199's int32-end rows (2 jobs at +-2^31 px).** a) Safe class, the last two rows of
   r14-isp
   (E1024 ran 2^30 without a fault) (recommended); b) in r14-flag; c) skip (Q199 keeps "past 2^30").
4. **R14-4 Tooling T14 and a t14 build.** a) Both items (`--refill` for Q108, `--scratch-pages` up
   to 256 for F1); r14-bif runs and F1 uses t14 (recommended: Q108's row has waited since round 10,
   and the round has wall time to spare); b) `--refill` only (F1 at 64 pages with t10, narrow);
   c) none: r14-bif dropped, F1 at 64 pages with t10.
5. **R14-5 Flagged session r14-flag.** a) F1 (3 planned faults) and F2 (4 planned faults), after
   every safe session, with the user present (recommended); b) F1, F2 and F3 (~5 recovered hangs,
   stop at the first failed recovery, last); c) F1 only; d) none.
6. **R14-6 Retirement with void clauses.** a) A fold may propose retiring a question when every
   measurable clause is decided by held-out rows with passing controls, and rewords a clause no row
   can decide: Q177's "why these constants" becomes the held-out formulas, and Q261's "clip space
   or window pixels" becomes the viewport's box, the two being one set for w > 0. Each such
   reword is marked [infer] and confirmed by the lead (recommended); b) such questions only narrow,
   and their reword waits for an offline round.
7. **R14-7 Text fixes.** a) In the folds: Q199's line drops the negative-vertex clause (E683; Q260
   carries it), Q243's drops the integer, NaN and equal-depth clauses (E977, E995) (recommended);
   b) leave both lines as they are (then Q199 and Q243 cannot retire on this round's rows).
8. **R14-8 Dropped rows.** a) No rows for Q260, Q284 (no frozen form), Q210, Q107, Q045 (as in round
   13), Q046 (offline mapping first), Q019, Q066 or Q211 (recommended); b) add Q046's bit 12
   low-half rows to r14-tex as readings (about 6 jobs, no frozen source, narrow).
9. **R14-9 Tool.** a) t10 for every row except r14-bif and F1 at 256 pages (t14). t10 is still
   main's sgxfive-test (no userspace commit after a581c06) (recommended); b) t14 for every row
   (one binding, but every replicate control then also tests the new binary).
10. **R14-10 Record numbers.** a) As in section 3: E1036 to E1048, with E1046 and E1049 conditional
    (recommended); b) the lead renumbers after the builds.
