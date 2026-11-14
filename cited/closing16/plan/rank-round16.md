# Round 16 ranking: safe laptop rows, retire first (Opus, 2026-11-14, user asleep)

Basis: resgx545 `main` b2b5288 (records to E1057, 149 open, 139 hw), resgx545-data 62cb03b36, fork
resgx545 2a650d74 (read only), laptop on module B60AB0B4 (one-shot boot), tools t4, t9, t10, t14.
Inputs read: `BRIEF-COMMON.md`, `doc/state_digest.md`, the round 15 handover (Next item 3), the
2026-11-11 standing rules, the 2026-11-13/14 lines of `plans/resgx545-question-closing.md`,
`closing15/plan/rank-round15.md` (sections 1, 4, 7) and `DECISIONS-R15.md`, the FOLD-NOTES of
r15-zls, r15-tw and r15-tex, records E1049 to E1055 (claims, "What it shows / does not show"),
the question files of Q078, Q297, Q299, Q177, Q071 and of every tier-H question of round 11
(`closing11/plan/tiers11.out`), E348, E396, E521/E525/E530/E597/E599 (methods), E981, E987, E995,
and `userspace/libsgxfive/tools/sgxfive-test.c` (probe and `tri --blk-add`). Nothing staged, built
or run; no laptop, SSH or cachix. The only other file: `calc/reach.py` (Q078 reach table below).

Round limits applied: SAFE CLASS ONLY. Every row below predicts no fault and no hang under its
frozen hypothesis *and* under every rival it scores; rows where a rival predicts a fault or hang
are in section 7. No tool change and no kernel change is needed by any row.

## 0. Honest summary

Round 15's leftovers give two retire-capable rows (Q078 bilinear, Q297 depth clause) and three
narrow ones (Q177, Q071, Q299; Q299 cannot retire in safe class: its first clause is a planned
fault). The wider survey of old questions found **three more retire-capable questions that no
round has touched since the rewrite**: Q116 (MTE region clip; `tri --blk-add 7=` has been in the
tool since ac5b888 and never ran), Q126 and Q137 (USSE integer forms and the class 9 test field:
finite tables with the rule already modelled in sgx-sim as the frozen hypothesis, run as client
fills by t10's `probe`, as E597 and E599 were). That is enough for a full round of 5 sessions,
119 jobs, about 40 minutes of laptop time; a smaller round (R16-1 b, 72 jobs) keeps only the
retire-capable stages.

Checks done for this plan (read only):
- `tri --blk-add BIT=V[,V]` takes presence bits 2-5 and 7 (two words); the tool's triangle block is
  0xdf43 (`src/render.c`), so `--blk-add 7=C0,C1` makes 0xdfc3, **the closed driver's own
  "triangle with clip" block** (E347's table, E348's viewport rows). `tri_probe.c` refuses a bit
  already present; `tests/test_tri_probe.c` covers it offline. No record cites `--blk-add`.
- `probe FILE` prints o0 and the scratch dwords the program changed: E597/E599's USSE tables (tool
  1135, the same subcommand) fit t10's probe and the kit's library-mock replay ("not simulated").
- sgx-sim `usse.rs` models `iaddu32` (the zero-extended value, E521; the tests, E498) and the class
  9
  test field's two parts, the `o` join and the chan fields (`a_test_field_reads_as_its_two_parts`,
  line ~8111): the sim is the frozen predictor for Q126 and Q137.
- E995 already decided a loaded NaN in the compare (H-ABS: above every finite depth); Q299's NaN
  clause is only the *store* of a kept NaN into formats 1 and 2.
- Q078 reach (`calc/reach.py`, E1049's H-TWP with the v-unwrapped and 4128-row rivals): every
  bilinear row at H 16 or 32 stays under 204031 dwords (of 262144 in t14's 1 MiB); point rows at H
  64 stay under 224000 with frac(u) <= 0.4 (the v-unwrapped rival applies to bilinear rows only).
  **No bilinear row uses H 64.** H 64 rows reach dwords no job has read (E1049's maximum 132607).

## 1. Every candidate, ranked (retire first)

"Retire" = every open clause of the question line is decided by held-out rows if the frozen
hypothesis (or exactly one rival) holds and the controls pass; void clauses reworded [infer], the
lead confirms (R16-6). "Narrow" = a clause stays open whatever happens.

| # | Stage (session) | Question | If it holds | Jobs | Tool | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | tw16 (r16-tw) | Q078 bilinear held out, heights 8/16/64 | **retire** | 17 | t14 | safe; H 64 rows never-run reach, last, `on_stop = "end"` |
| 2 | zpass2 (r16-zls) | Q297 depth clause | **retire** | 15 | t10 | safe |
| 3 | rclip (r16-mte) | Q116 region clip | **retire** | 15 | t10 | safe; first `--blk-add`, gate row first, empty-clip row last |
| 4 | uadd (r16-usse) | Q126 iaddu32 forms | **retire** (test clause void) | 9 | t10 | safe |
| 5 | utest (r16-usse) | Q137 test field | **retire** | 16 | t10 | safe; raw chan rows last |
| 6 | zbits4 (r16-zls) | Q071 bit 0, bit 20, bit 23's bytes | narrow (retire only if one H23 source rival holds, R16-6) | 14 | t10 | safe |
| 7 | zovp (r16-zls) | Q299 pass over overlaps, kept NaN | narrow (fault clause stays) | 10 | t10 | safe |
| 8 | ty2 (r16-tex) | Q177 third sizes, names | narrow (R16-7 b: retire-capable) | 14 | t10 | safe |
| 9 | zoff (r16-zls) | Q069 z offset below 0.5 | narrow (OUTSEL 13, presence 16-31 need a tool change) | 9 | t10 | safe; offline gate first |

Total: **119 jobs** in 5 sessions. Records E1058 to E1066 (section 3).

### 1a. Rows the kept data already decide (dropped or cut down)

- **Q078 point read** at W 16-128, H 32, u in (0, 3), u16: E1049 (H-TWP 6/6, U16-TX 1/1); W 32:
  E1047.
  Strided bit 14: E1003, E1027. tw16 keeps one point row (H 32) only as a control.
- **Q297 edge tiles, bit 19, integer formats, the strict-less count at 0, 0.75, 1**: E1050. The
  compare against NaN and infinity: E995, E1040. zpass2 runs only the depth clause.
- **Q299 overlapping stores alone** (owner rule, formats 1/2, edge tiles, four macrotiles): E996,
  E1041, E1051. **Integer clamp above 1 and 0 below 0**: E1051, E981. Only the pass and the NaN
  store run.
- **Q071 bits 12 and 16** (linear load and store, rows of 32 (G + 1) units): E1030, E1042; **15, 23
  alone, 21/22 + 23**: E1053; **21-23 together, 27-31 alone and together**: E1042; **bit 0 under
  formats 0-2 at G 2 and a depth load**: E997; **bit 20 cleared alone and in pairs with 12/16**:
  E1030 (nothing seen).
- **Q177 mode 4 at 16 x 16 and 32 x 32, modes 5-7 at 16 x 16, halving**: E1055 (10/10), E1039.
  The twiddled type's regions: E1039, E1026. Strided type: E565 via E1026.
- **Q126's value with chan0, register, o0 and scratch destinations**: E521; **its tests**: E498.
- **Q137 and/or/xor/rol with registers, and/xor #7 (a join, chan0)**: E499; **o join**: E529;
  **chan 1-7 on 32-bit and**: E530; lane operations through the assembler's chan names: the
  landed Test channels page (360 cases).
- **Q116's word layout** (enable bit 31, columns 30:16 and 15:0, rows from the bottom, 32 x 16
  tiles, inclusive): E348 from captures only; nothing on the hardware.
- **Q069's bit 19 clause**: answered as no observable effect (folded 2026-11-13, E981, E987).

### 1b. Older questions surveyed for a one-session safe retirement

Untouched since the rewrite (last commit 2026-11-01 to 11-12). Decidable now: **Q116, Q126, Q137**
(rows above). Not decidable now, by reason:

- **A planned fault or hang is a live outcome** (section 7): Q016, Q040 (odd counts hang), Q065,
  Q072, Q112 (bit 24 hangs, 0xd0008 faults: E756), Q132/Q133 (past-allocation, phas hangs), Q162,
  Q183, Q010 (its "after hung jobs" clause), Q039 (needs a hang/reset sequence, firmware reload).
- **Firmware task or verifier first**: Q195 (the four narrow forms are refused by the verifier;
  its client clauses alone would only narrow), Q196, Q158, Q168, Q134/Q154 (register str).
- **No frozen form exists** ("why" lines or explore-only readings): Q011, Q017, Q020, Q023, Q032,
  Q073, Q098, Q164, Q276 (the lane of the OR), Q001 (bits 8/10's kept state; 0x0810/0814 "at a
  load the tool cannot build" has no finite test), Q012 (mode 22's fields need a fit pass first,
  the constants sit on uncovered pixels), Q008 (an offline luma fit on E039/E275/E426 first).
- **Nondeterministic by run** (leftovers, load timing): Q026, Q027, Q129, Q130, Q136, Q143, Q146,
  Q193, Q194.
- **Too broad for one session** (many independent clauses): Q050, Q051, Q052, Q054, Q055, Q057,
  Q058, Q060, Q062, Q080, Q111, Q127 (immediates 9-124, dual issue, `.rsN`, u16/z16), Q135 (bit 46's
  0x2255 has no form: narrow only), Q206, Q207, Q230, Q231.
- **Negatives over all words** (round 15's reasons stand): Q013, Q043 (needs a filtered copy the
  transfer tool lacks), Q044, Q092, Q114, Q115; Q159, Q160, Q161 (no frozen form).
- **Q024** (0x0a78 timing) could retire as a frozen negative (every value's median within a
  bound of 0x2c's), but it needs all 64 values with replicates on two loads (150 to 640 timed
  jobs) and a register write the kit has no word for (E396 used debugfs `kreg`; the kit's
  `dbg:NAME=V` writes value knobs only) [check]. Later, after a kit word (section 6).
- **Q042** (bit 24, offset width, which entries get bit 15) and **Q086** (4x MTILE rule): narrow
  only; not this round.

## 2. Rows in detail

Every stage: `#limit 0` (any fault or hang stops it, kit rc 4); controls are `reads:` rows of the
stage's own shape, never the default triangle; expectdiff rows need `job: ok`; predictions frozen
by the kit freeze before staging; every row carries the flags its premise needs (E934: `--depth
--depth-store`, `--depth-pages` at odd sizes, the formats in the control word). "Held out" = no
kept job ran that input. Each builder names its replay table in README (HACKING "Replay vectors").

### r16-tw (t14; the round's last session)

**tw16 (Q078, 17 probe fills, E1049's form: E566's tx_map, scratch dword i = 0xD0000000 | i, the
texture at the scratch's first dword, `probe --temps 32 --coords --pixels --scratch-pages 256`).**

Frozen (E1049's post hoc form, fitted on tw-bl32 and tw-bl16 only):
- **F-FRAC**: under a bilinear sample (T0 | 0x1400) the taps read columns X mod W and X + 1, each
  plus floor(4096 frac(u)), X = floor(W frac(u) - 1/2), rows as the point read (t, t + 1), in
  E1049's 16 x 16 tiles with a tile row of W + 4096 texels.
- Rivals: H-FOOT-SHIFT (E1049, 1 of 2), H-FOOT-TW (each tap at its own wrapped texel's bit-14
  address, 0 of 2), F-WRAP2 (both columns wrapped mod W), and for the v edge V-WRAP (row t + 1 mod
  H) against V-NEXT (row t + 1 = H, the next tile row of the wide layout).
- Point rows at other heights: **H-TWP-H** (E1049's form with tile rows TR = t >> 4 for any H; at H
  8
  the tile is 16 x 8 [check: the builder takes E561's tile law for H < 16]) against H-TWP-STRIP
  (one strip of (W + 4096) H texels: the 4096 added per texture, not per tile row) and H-TWP4128.

Rows (all held out; ascending reach):
- Bilinear: 64 x 32, footprints inside the texture (frac(u) in (0.2, 0.6)) (1); 16 x 32 across the
  left edge (frac(u) < 1/32, X = -1) (1); 128 x 32 across the right edge (1); 32 x 32 at the v edge
  (ky = H - 1, the second row past the texture) (1); 16 x 16 inside and across the right edge (2).
  Rows chosen so F-FRAC and each rival part on at least 256 pixels a row (a builder test).
- Point: 32 x 8 and 128 x 8 (2); 32 x 16 and 128 x 16 (2); **then** 16 x 64 and 64 x 64 with u in
  (0, 0.4) and (1, 1.4) (4), reaching dwords 200000 to 224000, last.
- Controls that can fail: the bit-clear references of the new shapes at H 8, 16, 64 (2: 32 x 8 and
  16 x 64; E561's law, the image frozen), and E1049's tw-bl32 rerun (its kept image) (1) = 3.
  tw-bl32 is the one that can tell whether the bilinear read replicates at all.
- Stop: `#limit 0`, `on_stop = "end"`; rows in reach order. A fault inside the scratch means the
  mapping premise failed (r15-tw FOLD-NOTES), not bit 14.
- **Retire Q078** if F-FRAC (or exactly one rival) holds on all six bilinear rows and one height
  form on all eight point rows, with the three controls passing. "Heights other than 32" then
  reads "8, 16 and 64" [infer] (R16-6). Replay: sgx-sim tex.rs (bilinear and H != 32 added by the
  fold), table `tw16`, sgx-pipe `tests/texture_t3b14.rs`.

### r16-zls (t10)

**zpass2 (Q297, 15 jobs; E1050's zpass form: `--tri-full`, `--depth --depth-store --depth-pages
20`, load and store 0x0017500e at G 1, the load buffer `bit:9` (0.75f / 0.25f by tile half), depth
test less).** The lead declined Q297 because zp-z125's frozen store (the triangle's exact depth)
failed by 1 to 9 ulps. This stage separates the pass from the plane:
- **H-PASS-TWIN**: where the pass draws, the store holds exactly what the same triangle stores
  without a load (its no-load twin, run in the same stage, adjacent rows); elsewhere the loaded
  value. So the pass adds nothing to the plane's own error (Q200).
- **H-PASS-EXACT** (one-float planes): at depths where E1054 saw the plane one float (0.375, 0.625,
  0.5 + 2^-20), the store is the depth itself where drawn.
- Rivals: H-PASS-OWN (the pass stores the exact depth whatever the twin holds; zp-z125 refutes it
  already, so it is a negative), H-PASS-LE (E1050's refuted compare, a negative at 0.375 over 0.25).
- Rows: pass + twin at 0.125 (the replicate the handover asks for), 0.0625, 0.1, 0.3 (non-dyadic:
  E1050's deviation 3), 0.375, 0.625, 0.5 + 2^-20 (14 = 7 pairs). Drawn counts by strict less:
  2048 below 0.25, 1024 (the 0.75 half) for 0.3 to 0.625.
- Controls that can fail: zp-z125 itself (the pass row at 0.125 doubles as the replicate of E1050's
  kept dump, nine floats 0x3dfffff7 to 0x3dffffff: a second run that differs voids H-PASS-TWIN's
  determinism premise) and E1050's zp-c-467 replicate (1): 14 + 1 = 15 jobs. The 0.125 twin is new,
  so H-PASS-TWIN at 0.125 is held out even though its pass row replicates.
- **Retire Q297** if H-PASS-TWIN holds on all seven pairs and H-PASS-EXACT on the three one-float
  depths: the depth clause is decided (what the pass stores at any depth is the plane's store; the
  plane's error stays Q200's). Replay: sgx-pipe `zls::pass` fed the twin's plane, table `zpass2`.

**zbits4 (Q071, 14 jobs; E988/E1053's st1-b0 form unless named).**
- Bit 0 under controls not run (E997 covered formats 0-2 at G 2 and a depth load): with E988's
  stencil load and store (0x0017300f), format 6 (E1043's flat form), format 7 (E1031's F7K), and
  bit 16 cleared (E1030's linear store) (4). Frozen **H-B0**: the depth and stencil stores equal the
  kept twin without bit 0 byte for byte, no colour pixel written. Rival H-B0-NOSTORE (no store).
- Bit 20 cleared on routes not run: formats 6 and 7, bit 12 cleared with a depth load (E1042's
  H-DEPTH-LIN), and 640 x 480 (four macrotiles) (4). Frozen **H-INERT20**: each equals its kept or
  same-stage twin (a negative; the twin replicate is the control that can fail).
- Bit 23's bytes (0x3f, 0x80, 0 by x mod 16, E1053): the reference (ISP word 0 bits 7:0) at 0x80,
  the compare mask (ISP word 2 bits 15:8) at 0xff, and the background stencil value
  (CR_ISP_BGOBJVALS.STENCIL by `--kpoke-render` [check: the builder names the render-details dword
  from 3d.md, as E987 named dword 16]) at 0x5a (3). Frozen **H23-FIXED** (the bytes unchanged)
  against H23-REF, H23-MASK, H23-BG (the bytes follow that value).
- Controls that can fail: zb3-c-b23 and zb3-c-base replicates (kept stores) (2); plus one bit-0
  twin replicate at format 6 (1) = 3.
- Narrow. Retire only if one of H23-REF/H23-MASK/H23-BG holds (bit 23's bytes then named), H-B0 on
  4 of 4 and H-INERT20 on 4 of 4: then bits 20 and 27-31 read "no effect on every route run"
  [infer] (Q069's bit-19 precedent, 2026-11-13) and "the ISP's use" is reworded to the answered
  parts (R16-6). Replay: sgx-pipe `zls::stencil_source`, table `zbits4`.

**zovp (Q299, 10 jobs).**
- Load pass over overlapping tiles: E1050's pass at E996's 64 x 32 G 0 and 160 x 48 G 2, depth
  less, triangle 0.375 (4: each with depth and with stencil load). Frozen **H-OVL-PASS**: each tile
  loads its own slot of the load buffer by E465's address (the pitch G, shared slots read the
  fill), passes as E1050, and each shared store slot holds the tile E996 names (visited last,
  H-LATE/HDR). Rival H-OVL-FIRST (the first visited tile owns), H-OVL-SKIP (a tile whose slot is
  shared skips its load).
- A kept NaN into an integer store: the load buffer filled 0x7fc00000, 0xffc00000 (the sign
  cleared on load, E467) and 0x7f800001, depth test never, formats 1 and 2 (5; 0xffc00000 in
  format 1 only). Frozen **H-NAN-SAT** (stored 0xffffff / 0xffff: NaN above every depth, E995's
  H-ABS, then E991's clamp) against H-NAN-ZERO and H-NAN-LOW (the conversion of the word's low
  bits).
- Control: E1051's zv overlap replicate (1).
- Narrow: "a store past its buffer faults" is a planned fault (section 7). Replay: sgx-pipe
  `zls::pass` with overlaps, table `zovp`.

**zoff (Q069, 9 jobs; E987's zw form, 256 x 128 G 7, format 0, the viewport z offset by `--poke
blk:10`).** Offline gate first (section 5, OQ069): replay E981's and E987's kept stores below w =
0.5 through E1056's polygon depth clip (sgx-pipe `isp::depth_cut_image`) and through H-LIN (z =
(1.6 w + 0.2) t, E987's two-point fit). Freeze whichever forms reproduce the kept dwords;
**H-POLYCLIP** (the scale is the clip at z = 0 [infer]) and H-LIN are frozen either way, H-LIN
marked [fitted].
- Rows: w at 0, 1/16, 3/16, 5/16, 3/8, 7/16 (6), w = 0.25 with the z scale (word 11) at 0.25 and
  0.75 (2). Control: E987's zw-0125 replicate (1).
- Narrow (OUTSEL bit 13 and presence bits 16-31 need the tool to grow the block past bit 7).
  Replay refused unless one form holds; then sgx-pipe isp/mte, table `zoff`.

### r16-usse (t10; client fills as E597/E599: `probe --temps 32 FILE`, a debugfs reset between)

**uadd (Q126, 9 probes).** Each program computes eight pairs r1 in {0x8000, 0x8001, 0xabcd, 0xffff,
0x7fff (control side), ...} with r2 or the source under test and stores each result to its own
scratch dword (E599's narrow.s pattern; the builder adapts `probes/p1136/gen_client.py`). Forms:
source 2 an immediate (two immediates) (2), a constant (1), `.rpt2` and `.rpt4` over consecutive
registers (2), destinations i0 and sa0 (and g if the assembler accepts it) (2). Frozen **H-ZX**
(source 1 zero-extended, E521) against H-SX per form; predictions from sgx-sim.
- Controls that can fail: E521's register pairs replicated (1), E498's iaddu32 tests over two of the
  pairs (p always, n never, z only at (0, 0)) (1).
- **Retire Q126** if H-ZX holds on every form. The test clause ("which extension the test reads")
  is not observable: the carry-counted sum is zero for (0, 0) only under either extension and the
  sign tests read nothing (E498); reworded so [infer], as Q276's predicate clause was (R16-6).

**utest (Q137, 16 probes; one program a form, every one of the 15 field values over six input pairs
whose results cover zero, positive and negative).** Frozen: the rule of E499/E529 and the Test
channels page as sgx-sim gives it.
- Forms: `shl`, `shr`, `asr` (3); `or #7`, `rol #7` (2); `iadd32` and `iaddu32` sums with both joins
  (4); field value 0 under both joins (1); an 8-bit and a 16-bit lane operation through the
  assembler's chan names with distinct bytes, the byte under test known (2).
- **Then** (last, `on_stop = "end"`): raw words with enc[38:36] = 1 to 7 on the two lane operations
  under the `o` join (2) [the E530 raw family, which ran 252 cases without a fault].
- Controls that can fail: E499's and E529's kept tables, one form each, replicated (2).
- The clause "whether our own backend may emit the combined words from the assembler's text forms"
  is decided offline (OQ137: usse-asm's words for `.testtoz`, `.testnoz`, `.testnaz`, `.testpanz`
  equal E529/E530's raw words byte for byte, or the rows run the text forms).
- **Retire Q137** if the rule holds on every row (or one named rival, e.g. a shift testing the
  shifted-out carry). Replay: sgx-sim usse vectors, table `utest`.

Kit fit (both stages): probe rows of our own programs, replayed "not simulated" by the library
mock (c12542e); the scorer reads the probe's printed scratch dwords. This is the first USSE table on
the kit: the builder checks the kit's `outdir_opts` (none needed: probe prints) and that every
program's scratch dwords stay inside the default 16 pages.

### r16-tex (t10)

**ty2 (Q177, 14 probe fills, E1055's type programs, 32 pages).** Frozen from E1055's post hoc fit,
which two sizes give exactly: types 1 and 3 mode 4 name **N13 = 39 W + 52 + (x mod W)**, type 4
**N4 = 40 W + 20 + (x mod W)** (660 at 16, 1300 at 32); modes 6 and 7 mode 4's last column; rival
NQ (c0 + k W^2, the other two-point form: 520 / 3796 at 8 / 64 for types 1 and 3), and for W != H
the rivals in W, H and max(W, H) (E1000's lesson).
- Rows: 8 x 8 and 64 x 64 in mode 4 for types 1 and 4, each with its mode 0 reference (8); 64 x 16
  in mode 4 for type 1 (W against max) (1); modes 6 and 7 at 64 x 64 for type 1 (2); mode 5 at 8 x 8
  and 64 x 64 for type 1 (readings: the fit for mode 5's constant, 163 at 16) (2).
- Control that can fail: E1055's ty-ty1u4r rerun (1).
- Narrow (R16-7 a): mode 5's constant gets three sizes for a fit, held out next round; "what the
  half is" and "which of the two names" stay. R16-7 b would add a later held-out mode 5 pass.
  Replay: sgx-sim tex.rs types at the new sizes, table `ty2`.

### r16-mte (t10)

**rclip (Q116, 15 jobs; `tri --tri-full --pixels --blk-add 7=C0,C1`, the clip words as E348
writes them).** Frozen **H-TILECLIP** (E348's reading): the clip keeps the 32 x 16 tiles with first
<= column <= last and first <= row <= last, rows counted from the bottom; pixels of tiles outside
are not drawn by the object. Rivals: H-EXCL (last bound exclusive), H-TOP (rows from the top),
H-NOCLIP (the words read but ignored), H-PIXEL (bounds in pixels, not tiles). For the pixels
outside: **H-BG** (the background object still writes them) against H-UNTOUCHED (left at the
target's sentinel). For the enable bit: H-EN (bit 31 clear: no clip) against H-ALWAYS.
- Gate first (control that can fail): the whole-target clip of E348's clear block (0x80000000 |
  (W - 1) / 32, (H - 1) / 16) at 64 x 64, equal to the no-clip image (1), and the no-clip twin (1).
- Rows at 64 x 64, 128 x 128 and 256 x 256: column ranges of one tile (c0 = c1) and of two; row
  ranges asymmetric in y (rows 1 to 2 of 8 at 128 x 128: from the bottom y 80..111 counted from the
  top, from the top 16..47) (6); a triangle (not full) straddling the clip edge mid-tile (1); the
  enable bit clear with a partial range and set with the full range (2); 256 x 256 four-macrotile
  partial (1); the clip of E348's viewport row (0x80010001, 0x00010003 at 64 x 64) (1); 100 x 60
  (edge tiles, E348's row) (1).
- **Last, `on_stop = "end"`**: a clip that excludes every tile of the object (1): no record ran an
  object with empty region lists [infer: the TA lists none, as for an object off the target].
- "Objects and clears alike": our jobs' clear is the background object; a full-target object
  with the clip stands for the closed driver's clear block [infer] (R16-6).
- **Retire Q116** if one tile form, one row origin, one bound form, one outside form and one enable
  form hold on every row with both gate rows passing. Replay: sgx-pipe region clip (added by the
  fold, test first), table `rclip`; sgx-sim refuses presence bit 7 until then [check
  SIM_UNMODELLED].

## 3. Sessions (safe class only; one sitting on B60AB0B4)

| Order | Session | Stages (jobs) | Jobs | Wall | Prefix | Records | Tool |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | r16-zls | zpass2 (15), zbits4 (14), zovp (10), zoff (9) | 48 | ~9 min | r16z | E1059, E1063, E1064, E1066 | t10 |
| 2 | r16-usse | uadd (9), utest (16, raw rows last) | 25 | ~5 min | r16u | E1061, E1062 | t10 |
| 3 | r16-tex | ty2 (14) | 14 | ~3 min | r16t | E1065 | t10 |
| 4 | r16-mte | rclip (15, empty clip last) | 15 | ~3 min | r16m | E1060 | t10 |
| 5 | r16-tw | tw16 (17, H 64 last) | 17 | ~4 min | r16w | E1058 | t14 (t10 health) |

Record numbers (priority 1 first): **E1058** tw16 (Q078), **E1059** zpass2 (Q297), **E1060** rclip
(Q116), **E1061** uadd (Q126), **E1062** utest (Q137), **E1063** zbits4 (Q071), **E1064** zovp
(Q299), **E1065** ty2 (Q177), **E1066** zoff (Q069); **E1067** spare (OQ069 as its own offline
record, only if the lead wants it apart from E1066).

Wall: round 15 ran 6 to 9 s a job; 119 jobs is about 15 min of jobs plus about 3 min staging and
preflight a session: **about 30 to 40 minutes**, well under 1.5 h. Builders run offline in
parallel first (about 1 to 1.5 h; r16-usse is the newest kind of build).

Order: r16-zls (forms run in r10-r15), r16-usse (client fills of 11.27/11.36; raw words last),
r16-tex (r15-tex's programs), r16-mte (the first `--blk-add`: a hang would end the round with the
known forms done), r16-tw last (reads past every dword read so far).

Kit fit (main b2b5288; kit unchanged since dddadbd/c58f9f9):
- r16-zls: fits (r15-zls forms; `--poke blk:10/11`, `--kpoke-render`, `--depth-fill 0x7fc00000`
  is a value fill). `--depth-pages` explicit at every odd size (Known tool weaknesses).
- r16-usse: fits [check above]: probe rows of own programs; the scorer parses printed scratch
  dwords.
- r16-tex: fits (r15-tex's ty programs, sizes in T1).
- r16-mte: fits (`tri --blk-add` on t10; the library mock must accept `--blk-add` as strictly as
  the tool: bit 7 takes exactly two words; a builder test).
- r16-tw: fits (r15-tw's binding of t14 by `--tool-src t14=c58f9f9:...@closing14/k14/
  build_tool14.sh`; t10 health pair).

Premise tests per builder: r16-tw every rival's farthest dword < 262144 per row (`calc/reach.py`'s
form, the builder's exact tile law); r16-zls the twins adjacent to their pass rows, every NaN fill a
value fill, E465's slot map for G 0 and G 2; r16-usse every program's results inside the scratch and
the sim's prediction replayed on E521/E499/E529 kept readbacks; r16-tex each type row has its mode 0
reference at its size; r16-mte the clip words of the gate row equal E348's formula, every partial
row parts H-TILECLIP from H-TOP and H-EXCL on at least 256 pixels.

## 4. Tool changes

None. t10 for every stage but tw16 (t14). Q069's presence bits 16-31 and OUTSEL bit 13 need `tri
--blk-add` to take bits above 7 (a later tooling item, not this round).

## 5. Offline parts (no laptop)

- **OQ069** (before zoff freezes): E981/E987 kept dumps replayed through sgx-pipe
  `isp::depth_cut_image` (E1056) and H-LIN; writes the forms zoff freezes. If H-POLYCLIP reproduces
  every kept dword, Q069's scale clause is answered post hoc and zoff holds it out.
- **OQ137**: usse-asm's words for the two-condition text forms against E529/E530's raw words.
- **OQ126**: sgx-sim predictions per form; the assembler's accepted destinations for iaddu32.
- Predictions frozen by builders: tw16 from E1049's fold (`fold/bilin_forms.py`) and
  `calc/reach.py`;
  zpass2 twins relational (no number frozen for non-one-float depths: the twin's dump is the
  prediction, scored row by row); zbits4 from E1053's look; ty2 from E1055's `types_post.py`; rclip
  from E348's formula.

## 6. Retire summary if every frozen hypothesis holds

Q078, Q297, Q116, Q126, Q137 retire (five); Q071 retires only if a bit 23 source rival holds;
Q299, Q177, Q069 narrow.

## 7. Later, with the user (not safe class; in no session)

- **Q299**: E411's G 5 row at its 16-page buffer (a fault is expected: the store past a mapped
  buffer).
- **Q108**: EDMPROTECT on a load-only depth render (fault rival live, E965); WRITEONLY or
  EDMPROTECT on a texture read; the TA's and EDM's buffers; CACHECONSISTENT on a texture across
  renders (needs `--refill` for a texture buffer: tool change).
- **Q139** faulting macrotile words (E509); **Q163** counter shapes (recovered hangs, T13 words);
  **Q241 bit 18** (faults, E065, E998); **Q036**'s builder-fault clause; **Q046 bit 11** (faults at
  0x37001000, E1034).
- **Q040** odd EMIT2 counts (hang); **Q112** bit 24 over a 32-bit list (hang) and other width bits
  (0xd0008 faults); **Q195**'s firmware-task forms (verifier first).
- **Q024** (not unsafe, but a kit word for a debugfs `kreg` write and 150+ timed jobs): a kit
  tooling item first.

## 8. R16 decisions (the lead takes the first option of each)

1. **R16-1 Sessions.** a) All five in the order zls, usse, tex, mte, tw: 119 jobs, about 40 min,
   E1058 to E1066 (recommended); b) only the retire-capable stages (tw16, zpass2, rclip, uadd,
   utest): 72 jobs, about 25 min; c) a without zoff and ty2 (narrow only): 96 jobs.
2. **R16-2 Q078 heights.** a) H 8, 16 and 64 point rows, H 64 last with frac(u) <= 0.4 and
   `on_stop = "end"`, no bilinear row above H 32 (recommended); b) H 8 and 16 only (the H 64
   rows reach past every read so far; "heights other than 32" then reads "below 32" [infer]).
3. **R16-3 Q297 depth clause.** a) Twin-relational H-PASS-TWIN at seven depths plus H-PASS-EXACT at
   the one-float depths (recommended: it separates the pass from Q200's plane error, the lead's
   reason to decline); b) only one-float depths with exact predictions (the handover's literal
   row; non-dyadic depths stay unrun).
4. **R16-4 Q116 (new, never run).** a) r16-mte as planned, the gate row first, the empty-clip row
   last with `on_stop = "end"` (recommended: every partial clip is a closed-driver block form);
   b) without the empty-clip row; c) skip Q116 this round.
5. **R16-5 USSE session.** a) Q126 and Q137 in r16-usse, raw chan rows last (recommended); b) Q126
   only (9 jobs); c) skip (keep to the units of recent rounds).
6. **R16-6 Retirement with void or reworded clauses.** a) As R15-6: a fold proposes retirement
   when every measurable clause is decided by held-out rows with passing controls; Q126's test
   clause is not observable (Q276 precedent), Q116's "clears" read as a full-target object and the
   background, Q078's heights read as those run, Q071's nothing-seen bits read "no effect on every
   route run" (Q069 bit-19 precedent), each [infer], the lead confirms (recommended); b) these
   questions only narrow.
7. **R16-7 Q177.** a) One pass, narrow (recommended: the user is asleep, a second build pass adds a
   dependency inside the round); b) two passes (mode 5 fit early, about 6 held-out jobs late):
   retire-capable only if "what the half is" is also reworded; c) skip ty2.
8. **R16-8 Q069.** a) OQ069 offline first, then zoff with the forms it freezes (recommended);
   b) OQ069 offline only (a post hoc note, no laptop row); c) skip.
9. **R16-9 Record numbers.** a) E1058 to E1066 as in section 3, E1067 spare (recommended); b) the
   lead renumbers after the builds.
10. **R16-10 Dropped and later rows.** a) As sections 1a, 1b and 7 (recommended); b) also add a kit
    tooling item for a `kreg` word (Q024) to the next tooling pass.
