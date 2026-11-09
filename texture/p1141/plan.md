# p1141/tex: verifying the Opus findings on texture, ISP and multisampling (draft)

Scratch, gitignored, written without laptop access. Nothing staged or committed, nothing written
outside `p1141/tex/`; `~/src/resgx545`, `tools/rewrite/`, p1140 and p1141/ta were read, never
written. Inputs: `debug/phase11/opus/{texture,isp,msaa}.md` (hypotheses, not results) and the landed
records and data. Record ids reserved: E700-E719, Q270-Q279 (none written here).

Method of p1126: declared fit and held-out sets, predictions frozen by hash before any run, raw
dumps gzipped, a recompute that shares no code with the run scripts, a marker per job, every case
able to fail, risky last, three failed recoveries stop a script. Nothing lands from this draft.

## 0. What is here

| path | what |
|------|------|
| `recompute/lib.py`, `tex2.py` | my sampler model on p1132's `texmodel` (imported unchanged) |
| `recompute/msaa_model.py` | the region model, written from msaa.md's words, integer geometry |
| `recompute/rescore_1132.py` | goal 1: every declared 11.32 hypothesis, plain Morton vs tile law |
| `recompute/claims_tex.py` | texture.md A1-A4, A6-A8 recomputed with my own options |
| `recompute/vec_bilinear.py` | the 21 landed `smp-bilinear` vectors, joint vs two-stage |
| `recompute/msaa_rescore.py`, `q140_rescore.py`, `isp_depth.py` | msaa, Q140, depth tile claims |
| `recompute/search_lodg*.py` | offline design search for the Q175 operand sets |
| `gen/` | `gen_p1141tex.py` writes everything below; `cat1141.py`, `tri1141.py` the cases |
| `*.sh` (13), `run-all-1141tex.sh`, `stage-p1141tex.sh` | the laptop scripts |
| `declared.tsv`, `predictions-declared.tsv`, `gen/cases.json` | cases, frozen predictions |
| `manifest-1141tex.sha256` | sha256 of all of the above, scripts, models, programs |
| `recompute/recompute_p1141tex.py` | the recompute of section 7 (`--selftest` passes) |
| `stage-bins/`, `probes/`, `templates/` | 74 staged programs, their tables, 2 templates |
| `tool-tests/test_options_parse.py` | 66 option sets accepted by the newest tool (mock) |
| `validate/mockrun.sh`, `out/` | flow check against `--mock`; every result file of goal 1 |

## 1. Goal 1: offline re-scores (own scripts, no number copied from a report)

Tile law = E561 (tiles of min(w,16) x min(h,16), y-then-x interleave, tiles raster). Out files in
`out/`: `rescore_1132.txt`, `claims_tex.txt`, `vec_bilinear.txt`, `msaa_rescore.txt`,
`q140_rescore.txt`, `isp_depth.txt`.

### 1.1 11.32 re-scored under the tile law (all 425 cases with data)

The tile law flips 71 (case, hypothesis) pairs from not exact to exact and none back. Cases with an
exact declared hypothesis: 270 plain, 315 with the tile law; 110 cases still have none.

| group | declared hypothesis | plain | tile law |
|-------|---------------------|-------|----------|
| twiddle (fit 3, held-out 24) | the model | 9 of 27 | 27 of 27 |
| t3vals held-out (24) | `t3off=pre` | 6 | 24 |
| t3vals held-out (24) | `t3off=post` | 1 | 1 |
| lod-auto (24) | `lodf=euc` | 18 | 23 (miss: ab-t43, T0 bit 27) |
| lod-auto (24) | `lodf=max4` | 15 | 20 |
| lod-auto (24) | `min`, `pwl_*` | 8, 15 | 13, 20 |
| t3bits held-out (15) | `pre`, rows after | 8 | 10 |
| shapes control 32x32 l0 | any chain | miss | exact |

Unchanged by the tile law: lod-grad (0 to 2 of 14 fit and 0 to 1 of 7 held out exact under any
declared hypothesis), aniso (0 of 21), border, fields and shapes (chain A 22/22, 22/22, 8/8, 49/49;
B and D still fail),
formats, types. So C1 holds for twiddle, T3, lod-auto and the 32x32 control, and for no other
group. E563's "1573 unresolved pixels" and E566's pre/post scores are tile-law artefacts.

### 1.2 The claims of texture.md, recomputed (`claims_tex.txt`)

| claim | in-sample (the report fixed the rule on them) | held out (not looked at first) |
|-------|-----------------------------------------------|--------------------------------|
| A1 pairing (0,2),(1,3), euclid | gr-uu/vv/uvy/all/neg/vx: 2016-2048 of 2048 | none in the data |
| A1 against E563's order | 8, 8, 52, 2024, 2024 px: pairing wins on 3 jobs, ties on 2 | none |
| A2 two-stage bilinear | an-ctl, an-r1..r5: 6 of 6 (joint 0), 45-form search | vectors: 1.3 |
| A3 T0 bit 27, sRGB to half | s64x32 and ab-t43: 2 of 2 | ind-t0b27 2 of 2 (one job) |
| A4 T3 level, scale, bit 10 | 12 of 12 | ind-t3b10/b18/b27/b28 4 of 4; r-b* 2 of 2 part seen |
| A6 `t3off=pre` + tile law | no | tv-*: 24 of 24 (post 1 of 24) |
| A7 format 27 is ETC1 | fb-27-base, ordA, ordB 3 of 3 | fb-27-lo, hi, fn-27 3 of 3 |
| A8 types 1, 3 (stride 16), 4 (32) | 4 + 2 jobs of 16x16, 6 of 6 | none, one size |

A1 is not exact: paired euclid leaves 8 to 65 pixels a job, and gr-vx does not tell it from max4.
Of the gradient jobs only gr-vx-k4 and gr-all-k4 are 2048 of 2048. The lod-auto jobs (the quad's
own derivatives, E563's order, not the pairing) are 24 of 24 with `euc`, the tile law and sRGB.

### 1.3 Bilinear on the landed vectors (held out, `vec_bilinear.txt`)

The 21 `texture-sampler-smp-bilinear` vectors (a 16x32 strided format 12 texture, words in
r20..r25, F32 output) are 21 of 21 under the joint `(sum + 2048) >> 12` AND under two-stage
(P = 64, xy or yx): they do not separate the two forms (joint and two-stage predict the same words
on all 21). A finer fraction (1/128, 1/256) fails 8 and 15 of 21. So the held-out test confirms
that f is truncated to 1/64 and leaves the two-stage claim exactly where the 6 jobs put it: fitted
by a search, untested on any data in which the forms differ. Experiment tex-b-bilin tests it.

### 1.4 Multisampling, region model (`msaa_rescore.txt`)

| data | images | exact | status |
|------|--------|-------|--------|
| msaa-ident coverage, A (64x64) | 11 | 11 | fit (the model came from A-m1-te60 tile (1,2)) |
| msaa-ident, B (128x128) and C | 11 + 18 | 11 + 18 | held out; C has 199 of the 455 bg px |
| msaa-ident, repeats D | 8 | 8 | no bg px (bg px: A 64, B 192, C 199, D 0) |
| source pixel of 402,000 decoded pixels | 48 | 0 off | fit + held out |
| msaa-te, bit 29 set | 12 | 12 | held out; the 9 without bit 29 are empty (E281), not modelled |
| msaa-tiles (E415) | 108 | 108 | held out; the report's 105 exact has 18 tie px: top-left rule |

Nulls, 48 ident images: first region wins 30, origin = region origin 28, union of masks 40, all
slots (8,8) 40. The seam constant 1.25 W is fitted from the dumps (1.20, 1.24: 20 of 48; 1.26,
1.30: 29 of 48) and the guard band experiment (isp-a-guard) tests that same constant.

### 1.5 Q140's layout formula on E507 (`q140_rescore.txt`)

With f = region-header arrays written by the TA, `rgn + f * rgn_size <= td.size` completes, else
a BIF fault at page `td.size >> 12`: f = 1, 2: 6 of 12 sizes; f = 3: 11; f = 4 to 8: 12 of 12.
So E507 does not pin f to 4 (the factor 4 comes from E504's dumps, 64 to 256 header dwords); it
gives f >= 4. Fault behaviour alone can never tell f = 4 from 5 (no size to 1024 x 1024 does).
Predictions (f = 3 / 4 or 5): 256x160 completes / completes, 288x144 page 6 / page 6, 320x128
completes / completes (all three are the report's, none discriminates f); 256x288 completes /
page 6 and 384x384 completes / page 8 (these two do, f = 3 against f >= 4).

### 1.6 Depth tile corner (isp.md A1, `isp_depth.txt`)

My statistic (tiles with a single T consistent with truncation, interval < 0.08 ulp, T within
0.05 ulp of the float32 grid): main 60.0 % (controls 11 to 17 %), fine2, held out, 74.9 % (12 to
18 %). Honest caveat the report lacks: of 2122 tiles with 60 covered pixels in main, 1308 (62 %)
have no consistent T at all under strict truncation and 313 are too wide; the statistic is on the
usable 501 (fine2: 462 of 1671, 65 % empty). The tile-corner law is a minority effect of unknown
cause, not a model of the stored words. Experiment isp-b-depth tests it on a clean slate.

### 1.7 Not applicable or not reproduced

firh banks: not in these three reports (usse Q050; the banks' held-out set is the usse vectors),
not recomputed. texture.md A5 (T3 bits 12:11), A9 (modes 4 to 7 offsets 180, 308), T0 bit 30,
isp.md A3 (34x18 to 42x22: one size, checked by `isp-a-guard`'s control) not recomputed.

## 2. Goal 2: the frozen experiments, in order of value

Tool: `~/sgxfive-test-1138b` (has `--tri-v`, `--tri-z`, `--tri-full`, `--keep-going`,
`--dump-render`, `--depth-dump`, `--regs`; 66 of 66 `tri` option sets parse on the newest tool).
Programs: p1132's `tx_map.s` plus `tx_map_r11.s` (o0 = r11: a new template, not a tool change).
No tool, kernel or firmware change is needed; `--keep-going` already reaches `--dump-render`
after a failed image check (that is why p1126's TE 0x40/0x80/0xc0 dumps were missing: the
script did not pass it). Hence no `tool-tests` failing test and no patch.

| # | script | question | jobs | risk |
|---|--------|----------|------|------|
| 1 | tex-a-lod | Q175 footprint rule, LOD fraction | 16 | low |
| 2 | tex-c-addr, tex-d-t0b27 | Q078/Q176 T3 model; T0 bit 27 | 16 + 8 | low |
| 3 | tex-e-etc1 | Q179 format 27 | 6 | low |
| 4 | tex-f-types, -g-, tex-h-cube | Q178/Q113 TEXTYPE 1, 3, 4, 2 | 4 + 8 + 8 | 4 low, 16 risky |
| 5 | msaa-a-vis, msaa-b-te29, msaa-c-q140 | Q089/Q138, Q030, Q140 | 17 + 11 + 5 | low, low, risky |
| 6 | isp-a-guard, isp-b-depth | Q122/Q199, Q200 | 12 + 21 | low |
| 7 | tex-b-bilin | Q115 two-stage held out | 8 | low |

140 jobs, 21 risky (a fault or hang is possible). Run time not measured: my guess is under 2 h.

### 2.1 Sets, hypotheses, criteria (every case can fail)

All cases are held out (nothing in them was used to fit), except controls and repeats. Predictions
are in `predictions-declared.tsv` (380 rows); a prediction is the sha256 of the 2048 pixels (fills)
or of a canonical JSON of the predicted object (renders). Criteria:

1. tex-a-lod. 8 jobs, four operand sets on 64x64 and four on 128x32 chains (u and v scale
   differ), six footprints P (pairs (0,2),(1,3)), O (E563's), Mp, Mo, F, S; any two images differ
   in >= 1972 px on the square (Mp = Mo there) and >= 1792 on 128x32. P passes if it has the highest
   count and >= 1980 of
   2048 (the in-sample residual is <= 65) on every job; it fails on any job where another
   footprint scores higher. 8 ladders lf-r2..r24 (one operand, rho r0 to 1.0615 r0 over the 64
   columns, a column is ~0.09 of a 1/64 step): `frac=trunc` against `frac=round`, differing
   in 208 to 864 px; pass: one of them >= 1980 on 7 of 8, the other not.
2. tex-c-addr. 16 jobs: levels 1 to 3, scales 1 to 3 and both together (never read), on
   tw 64x64, 32x64, 128x32, st 128x32, 32x64, and bit 10. Hypotheses: A4, A4 with the strided
   chain by stride x h, A4 shifting only the index. A4 passes at 16 of 16; the index-only form
   differs from it on 6 of the 16 jobs, the stride chain on 1. tex-d-t0b27: 4 jobs sRGB to half on
   injected bytes (stratified over 0..255)
   and the 32x32 names, 2 jobs of the second dword (r11, exploration, no prediction), 2
   bilinear jobs: filter-then-decode against decode-then-filter. Pass: 4 of 4; the bilinear pair
   decides between the two or refutes both (an-t0b27 was 25 px off for either).
3. tex-e-etc1. Random valid blocks: 16x16 twice, 32x16, 16x32, 8x16, 8x8. Hypotheses: Morton
   y-low (the report's), raster, Morton x-low. Pass: Morton y-low at 6 of 6; on 32x16, 16x32
   the three orders differ in >= 1024 px.
4. Types: 3 at 8x8, 32x32, 32x16, 16x32 (4); 1 and 4 the same (8). H "fixed 16" (stride 16, 32
   for type 4, wrap at 16: the report's reading), H "raster w" (stride the width), H "wrap at the
   size, 16 stride". Pass: one hypothesis exact on each type's four sizes; fixed 16 expected.
   Cube: the follow-up of p1132 B3 (six directions, two w sweeps), no model: outcome faces 1, 3,
   5 for negative axes (a cube) or none (three faces).
5. msaa-a-vis. A 12x6 triangle in one region of tile (0,0), 64x64: mode 2 TE 0xe0, 0xa0, 0x60, mode
   1 TE 0xa0,
   against the same triangle at TE 0x20; `blk:2^=0x8` and `--regs 0x0494-0x04b4`. Images: the region
   model, 17 of 17 (a miss refutes the model on a held-out size). Decision (E070 counter 0x0498):
   count > 0 in an even region = W, the ISP walks every region and the last overwrites; count = 0 =
   S. The
   repeat (v-m2-tee-x0y0-r2) must agree with its twin. msaa-b-te29: TE 0x40, 0x80, 0xc0 at
   m0 and m2 64x64 and m2 128x128 with `--keep-going --dump-render`, two controls; compare the
   dwords with the landed te 0x00 and bit-29-set dumps: H gate (equal to te 0x00) against H bits
   (equal to the bit-29-set job); controls must differ in 0 dwords from the landed ones.
6. isp-a-guard. 34x18 (control, E: 924 stored), 18x18, 50x26, 66x34, 98x50, 34x50, both ramps:
   stored dwords over the tile area = {x + .5 < 1.25 W, y + .5 < 1.25 H} at 0 mismatches; the
   whole tile area and the target clip are the alternatives (differ in 100s to 1000s of px).
   isp-b-depth: 256x128, classes a (dyadic step: control), b (non-dyadic), c (T on a float32
   tie), z0 in 3 binades, a or b gradient only (18), three vertex orders (3). Candidates per
   tile: RN, truncation, a walk with step RN(32 A). Control criterion: class a must have
   every candidate inside the interval in >= 95 % of tiles or the tile structure is rejected.
   Class c separates the three (in the selftest 384, 288, 96 of 384 tiles).
7. tex-b-bilin. 8 jobs, random 8x8 texels (strided and twiddled), every fraction 0..63: joint,
   two-stage xy, yx, xy with floor. Pass: two-stage xy or yx at >= 7 of 8 and joint at 0; if
   joint wins, A2 is dead. Any two forms differ in >= 1179 px of 2048 (xy against yx 1248+).
8. msaa-c-q140. 5 sizes at 0xe0 mode 2: 256x160, 320x128 complete, 288x144 faults at page 0x20006;
   256x288 and 384x384 (f = 3 completes, f >= 4 fault at pages 6 and 8). Expect faults, a reset
   and a failed health after each (E507 saw three in a row). Do NOT run them in one script run
   if the first one already stops the script: use `ONLY=NAME`.

## 3. Items that need more than this batch

- Kernel: none to test; the Q140 fix (region headers x 4, or the closed driver's halved words)
  is a kernel change, wanted only after job 5.3 says what f is. A 4x render whose macrotile words
  differ from the kernel's (Q086 U2/HS) needs the `rtds:` kpoke index map (p1126 section 7).
- Not covered: PVRTC 23 to 26 (decode from the public paper on the existing dumps, offline);
  Q181 (load colour-space set 0, no poke); Q180/Q021; Q138's closed-driver capture (harness).
- Anisotropy (Q115 rest): no flipped word known; needs a new T0/T2 bit sweep on a passing baseline.

## 4. Why these choices (found while checking)

- Operand sets and ladders come from `search_lodg*.py`, seeded, offline; the frozen sets are in
  `cat1141.py`.
- The tie class (c) uses A*32 = 5 * 2^-(25+k): T(i) = z0 + i S is an odd multiple of half an ulp
  at every odd tile, so RN-even, truncation and a walk give three images.
- Vertex coordinates are whole pixels, z values dyadic, so the tool's decimal parse is exact.
- Faults are the only source of risk: render pokes only, no register written, no clock gate.

## 5. Run order and risk

`run-all-1141tex.sh`: tex-a-lod, tex-b-bilin, tex-c-addr, tex-d-t0b27, tex-e-etc1, tex-f-types,
msaa-a-vis, msaa-b-te29, isp-a-guard, isp-b-depth (safe), then tex-g-types-risky, tex-h-cube and
msaa-c-q140 (risky, last; health after every job). Before the first job a plain 64x64 triangle must
draw exactly; after any failed job the GPU is reset and it must draw again; three failed
recoveries stop the script. A marker goes to `/dev/kmsg` before each job. Stop the batch at the
first script that stops itself and read `dmesg`. `ONLY=NAME` runs one case.

## 6. Recompute

`recompute/recompute_p1141tex.py DIR` (`DIR` = the laptop's `~/p1141tex-dumps`): reads the kept
gzip dumps and `cases.tsv`, re-derives every prediction from `gen/cases.json` and checks it against
the frozen sha256, prints exact counts per hypothesis (fills), the model's misses and the E070
count decision (vis), dword differences against the landed dumps (te29), faulted or not and the
fault page from `journal-k.txt.gz` (q140), stored-set matches (guard) and the T intervals against
the three candidates (depth). `--selftest` builds model dumps from each case's first hypothesis
and reports on them: every section runs (`out/selftest.txt`).

## 7. Validated without the laptop

- `bash -n` on all scripts; no trailing whitespace; this plan's lines <= 100 columns.
- `gen_p1141tex.py` twice: same sha256 (below); 74 programs assemble, all <= 256 words.
- Every script ran end to end against the newest tool's `--mock` through shims (13 scripts, 140
  jobs, all kept); the mock draws no texture, so fills "fault" there: flow and formats only.
- 66 of 66 `tri` option sets accepted by the tool (`tool-tests`, `pytest`).
- recompute selftest; model reproductions of every Opus number I reproduced (section 1).
- The one denial: a first version of the generator deleted old programs with a glob; the denial
  stopped that run, the generator now deletes nothing.

Not validated: any outcome, run times, whether the 4x register read (`--regs 0x0494-0x04b4`)
returns the counter after a multisampled job, that `blk:2^=0x8` composes with the TE pokes.

## 8. Hashes

declared.tsv `5dae793900e4ed7fac82957c40e136caf5564daedea3167b4fbe65b45c1ed7fa` (140 rows)
predictions-declared.tsv `f4187d258284dfb4708f6c962b061f7d76ce6afa4776eb7704b871ed48dd1e5d`
(380 rows); manifest-1141tex.sha256
`144da32e5a7ec137cd54185013185db4eae056085ebcb7c44ada423819ffe983`.
