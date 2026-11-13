# Round 11 ranking: what the kept data of rounds 1-10 decides (offline only; Opus, 2026-11-13)

Basis: resgx545 `main` f3ed7d0 (records to E1010, **155 open**: 145 hw, 10 parked), resgx545-data
as checked out (round 10 sessions published), read only. Nothing staged, nothing run on the laptop.

Scratch in this directory (every file derived from published data and our own scripts, no
firmware-derived content, publishable; caches removed): `index.py`, `xref.py`, `tiers11.py` and
their `.txt`/`.out` (round 10's scripts rerun; every open id placed once, `tiers11.out` checked);
`unmodelled.txt` (the 117 entries of `crates/SIM_UNMODELLED.toml` with their claims);
`HELPER-BRIEF.md` (the freeze protocol the eight checks followed); one directory per check,
`c1-q139flag/` .. `c8-q078/`, each with its frozen rule, `.sha256`, `FREEZE.log` (UTC time, hash,
everything read before the freeze), scorer, `.out` and `NOTE.md`. The checks were run by helper
agents on this brief; I read every NOTE and freeze log. Where a split was not blind the NOTE says
so and this file repeats it.

## 0. Findings (offline, read first)

1. **Q139: E1007's bit-7 list end holds on r7-rp's 21 never-read dumps; "the highest slot
   written" is parted** (`c1-q139flag/`, rule `hflag_rule.json` 291ef61d..., frozen before any
   r7-rp `.tadata`/`.param` was opened). Set: `render/closing-r7-rp/out/20261112-205431/q139/`,
   E907's run on module 41E2...: rc 1 there is only the expectdiff line, all 24 jobs are `job: ok`
   with both dumps. H-LAST (one header with flag bit 7; a target tile drawn iff its stream header
   lies at or before it) and H-FLAGSLOT (the flag at H-EVEN's slot of the last target tile in
   block order) **held on 21 of 21 poked rows** (10 E907-fit, 10 E907-heldout, 1 replicate) and
   the poked control, every tile (128 or 600 a row); H-EVEN/R7-BLK slots exact on 24 of 24. Rival
   H-HIGHEST as "highest non-zero header slot" **fails 17 of 21** (flag 95 to 743, highest 141 to
   1183: non-target headers written past the target); restricted to target-tile headers it is never
   parted (21 of 21) [infer: no kept row has the last block-order tile below another target slot].
   On a second kernel build, never read for the flag: held out [HW, offline]. Refuted by: a
   readable dump with zero or two flagged headers, or a drawn tile whose header lies past the flag.
   E1007 needs no correction; an appended note (its "not parted" holds only for the
   target-tile form). **Q139's flag clause is answered; open: H-EVEN at fx 2 or 3 mod 4 (faults,
   not safe) and flag vs highest target slot.**
2. **Q071: E997's linear layout does not explain E989; the stencil test reads 0**
   (`c4-q071/`, `q071_rule.py` 5f705c49..., frozen before q071-b0/-l1 were opened). Three linear
   load maps (64 y + x bytes; raster in tile; 4 (64 y + x)) vs H-ZEROLOAD vs the twiddled base
   model: on E989's two rows **H-ZEROLOAD held 2 of 2** (2048 of 2048 pixels, 73728 of 73728
   store bytes); the linear maps drew 1024 extra pixels or misplaced store bytes (fail 2 of 2);
   the base model held on E988's base rows (controls). [infer] any bijective byte map passes half
   the pixels under a one-bit mask; 2048 drawn needs the loaded byte unread. No kept row clears a
   strict subset of bits 12/16/20 (every `--depth-ctl` in the data listed, `ctl_all.txt`): which
   bit does either effect is hardware-only. **Post hoc, E997's "the y of a row is not named" is
   wrong**: dword 96 y + x equals E977's control dump at (x, y) on 4608 of 4608 in all three
   cleared rows, row y +- 1 only 4441 (edge-varying values name y): an appended correction to E997.
3. **Q210: E1009's per-target bias is a fixed class, held out; the aspect reading is refuted**
   (`c5-q210/`, `s6bias_rule.py` ee0fe5e4..., frozen before any kept sample beyond E1009's own).
   Over every kept DPM run of r5 to r10 with a published replay R (520 jobs read; the standard
   1500-vertex workload): H-CLASS (S6's bracket lower end R + 1 at E1009's five targets, R at its
   eight) **37 of 37 calibrations (16 held out) and 56 of 56 partial-render cells (50 held out)**;
   the lower end is constant per target. Beyond the 13: biased (+1) 2048x3072, 2560x3072,
   3072x2560; unbiased 1024x1024, 2560x2560, 3072x2048, 3072x3072, 1024x2048, 2048x4096 (one
   cell). The frozen candidate H-RULE (biased iff w/h > 2 or w < h) fails 3072x2560, 1024x2048 and
   2048x4096: no simple w, h, area or residue rule separates the classes. Exceptions only on
   `--vtx-coords`/`--slot` 2048x2048 runs (12; another scene, which dpm.rs already refuses: scoped
   out post hoc). E1009 holds; an appended note (three more biased targets; not "wider than 2:1").
4. **Q261: no parameter-free set-up arithmetic fits; a guard-band clip fits all 48 rows with one
   integer** (`c6-q261/`, three freezes: `q261_rule.py` 4a0eaaf1..., `q261_rule2.py` 0997a099...,
   `q261_rule3.py` 5424683...). Round 1 (236 declared forms: float a, b, c of 8 to 24 bits RN/RZ in
   nine arrangements, fixed-point truncation, 2^k vertex grids, 32-bit wrap and saturation): 0
   fit; float32 is 11 of 48 rows like the exact image. Round 2 (written after round 1's misses):
   clip the far vertex to [-G, 64 + G], round the new vertex half up to 1/256, exact edges: G = 16
   fits **48 of 48 rows** (E1005's 36, E979's 10, both controls) and 318 of 318 band pixels; G 16
   to 22 all fit, G <= 15 fails far-x24p d = -416, G >= 23 fails far-x23p d = -544; the low bound
   free in 8 to 32, the y bounds untested. **[post hoc, fitted: no held-out row]**; it explains
   per-triangle "displacements" without D ~ |F| and E979's exact image outside the band [infer].
   Held-out vertices for a later row are in `q261_proposals.json` (4 +x, 3 -x, 1-2 pixel splits;
   a 128 x 128 target parts "64 + G" from an absolute 80..86). No correction yet.
5. **Q282: the subnormal flush holds out offline on a 11.32 job, thinly** (`c2-texture/` B,
   `rule_b.py` 84bd4264..., frozen before any held-out pixel). Of the kept bilinear sRGB jobs only
   p1132 tx-lod's `an-t0b27` (never in E982's or E1004's fit) reaches a subnormal stage: 12 halves
   (pixel column x = 4, rows 0 to 11, two corner quads) where the rules part. FTZ-OUT (stage
   outputs below 2^-14 to +0) **12 of 12, 2048 of 2048 pixels**; unflushed R10-BF11 2036 of 2048;
   input-only flush (x results fed to y) 2047, one half off. g-bl-st-a/b and the reruns reach no
   subnormal stage (no test). Corner bytes never decode subnormal (byte 1 is 3.0e-4), so "input
   flush" can only mean the x stage's results. Held out [HW, offline], one column: thin. A later
   row: corners 0, 1, 0, 1 at ky = 0, kx 11 to 14 parts output from input flush (`NOTE.md`).
6. **Q177: nothing kept parts max(W, H) from W; mode 5's reads off the texture are shape
   dependent** (`c2-texture/` A, `rule_a.py` 1dc23918...). 31 kept twiddled u-mode 4-7 jobs (p1132
   tx-border 16, r8-geo 4, r9-geo 11): 27 squares (no test), 4 at 32 x 8 (max = W; E983 read them).
   Only addr3's 8 x 32 and 16 x 64 part max from W, and they are E1000's fit: **8 max(W, H) + 52
   stays [fitted]**. Held out against the frozen mode-5 form: with s inside and t outside it
   **failed 384 of 896 on both uv5 jobs** (they read a per-side constant plus s; post hoc 7 M + 52
   + s above, 4 M + 52 + s below, 384/384 on both, M = W there); E983's corner dwords 20 to 23 are
   32 x 8's: 16 x 16 (bd-uv5) reads 16 to 19 (C-CONST 0 of 1152). Post hoc corner base (W + H) / 2
   or 12 + M / 4: a 16 x 64 row parts them (40 vs 28). E983/E1000 need appended notes, not
   corrections (E983 said "one size").
7. **Q120: format 6 under constant rows and format 7 under a constant stencil decode**
   (`c7-q120/`, `c7_rule.py` 4d87c5ad...; SEMI: four z2y-f6 blocks were printed before the
   freeze). F6C (a 512-dword block as four 12-dword groups when four tile rows are constant: 0x9e,
   the value, mask words 0x3f000000 at fixed places): 4 of 4 groups fitted, 4 of 4 on blocks 1 and
   2 (48 dwords; E985's raw layout 0). F7K (12 dwords a 256-dword block, a 48-byte template of
   0x3f, 0x1f and the fill byte): fitted on fill 0xa5, **held out blind on fills 0x00 and 0xff
   (48 of 48 each, no stray dword)**; the fixed-byte rival 0. Not decoded: format 5, format 7
   under the index stencil, format 6's edge tiles and its variable-length runs (116 of 212
   z2y-f6 dwords; post hoc a one-hot mask for a row's last n pixels adds 48 more). [infer] a
   row-run compression with a count mask. No correction (E986's "compressed" stands).
8. **Q078: bits 11 and 12 on the twiddled chain read level 0 and the 1 x 1 level** (`c8-q078/`,
   `q078_rule.py` f95d5bdf..., frozen after reading: **post hoc**). Only E564's an-t3b11 and
   an-t3b12 (p1132 tx-lod) exist, r9-x's three byte-identical replicates aside. With the counting
   fill every dword is named: bit 11 clear reads level 0 texel (x, y) at 2048 of 2048 pixels (the
   control reads levels 3 and 4), bit 12 set reads dword 5460, the 1 x 1 level 6, at 2048 of 2048;
   stride, offset-0 and bit-10 rivals 8, 1 and 0 of 2048. Not parted: a forced level vs mips off vs
   a LOD bias (bit 11: -3.5 or more; bit 12: +2.5 or more), the last level vs a constant dword,
   nearest vs bilinear. A note (E564 sharpened, E975's "not decoded" overtaken), no record.
9. **Retire/fold check of the round 10 narrowings** (each clause against the records):
   - Q101 (bit 19 with the integer formats): E490 (no dword changes over a positive ramp), E981
     (word 10's negative depth reaches the store as 0) and E987 (the background depth stored with
     its sign cleared) leave **no route that brings a negative depth to an integer conversion**;
     what stays is the viewport word 10's scale (E981, E987: 0.4 t, 0.6 t) and "if any route
     does". The bit-19 clause is answered as "no observable effect" [infer: on every route run];
     the word-10 clause is MTE depth, Q069's ground (E287 there). **Fold Q101 into Q069.**
   - Q242 (odd-size integer formats past the target, past page 15 of E411, overlap with edge
     tiles), Q243 (moved load base), Q241 (bits 15 to 17's meaning, 18 faults, counter, offset
     units, pass types, gate pairs), Q046 (bit 11 faults, bit 12's words), Q066, Q019, Q284,
     Q177, Q282, Q120, Q071, Q139, Q210, Q211, Q261: each keeps a clause no kept data decides
     (findings 1 to 8 narrow six of them). Not retirable offline.
   - Q202: its bit-28 and line/point clauses are Q031's and Q159-Q161's already (E992 narrowed);
     perspective planes and the divide stay. Text only; nothing new decides it (R11-9).
   - Uncited newer records (`xref.txt`): unchanged since round 10 except E1005 for Q199/Q260
     (cite at the next text edit) and E992 for Q031/Q159/Q161/Q230 (same).

None of findings 1 to 9 contradicts a landed claim, except E997's "y not named" sentence (an
appended correction, finding 2). Appended notes proposed: E1007, E1009, E983, E1004, E975, E564.

## 1. Sim and spec gaps (held rules not modelled; `crates/SIM_UNMODELLED.toml`, OPEN lists)

Every round 10 record is cited by sgx-pipe or sgx-sim (checked per id). Gaps where a held rule is
refused or a record's model is uncited:

- **G1 PBE pack modes (E383, E999).** `sgx-pipe/src/pbe.rs` models modes 0 to 3 only; E383's
  modes 7 and 8 (bits 8:6 pick the channel), 15, 18, 20, 27, 28 (the low 16 bits, two pixels a
  dword; 20 and 27 held out by E999, 16 of 16) and 24, 25 (B8) are refused under Q044. Test first:
  replay r10-x stage sb's 16 rows and E383's kept `pbe-sideband-channels` jobs as vectors; then
  the pack. [check] the half-dword order from the kept images before writing the test. Medium.
- **G2 ZLS formats 3 and 4 (E985, E986).** `zls.rs` refuses formats 3 to 7 (Q120) though E986
  held E985's layouts out byte for byte for 3 and 4 on every plane; 5 and 6 only where each pixel
  of a tile row differs; F7K (finding 7) for 7 under a constant stencil. Test first: replay
  r10-zls zst2's format-3/4 rows; keep 5, 6 (compressed rows) and 7 refused under Q120. Medium.
- **G3 Q210 bias table (finding 3).** `dpm.rs` documents E1009; with H-CLASS held out the replay
  can give S6 = R + 1 at the eight biased targets and R at the fourteen unbiased ones, refusing
  every other target under Q210. Test: the 171 scored runs' lower ends (c5's table). Small.
- **G4 sRGB flush (finding 5).** `sgx-sim/src/tex.rs` refuses E982's rule beyond E723's fills;
  with FTZ-OUT held out (thin) it can model the bilinear sRGB stage with the flush on the fills
  that ran (srgb2-sub, an-t0b27 as vectors), refusing other filters. Small. Only with R11-6 (a).
- **G5 sim-coverage cites (list shrink).** `unit_vectors.rs` already replays E489's 18 cases,
  E542, E541 and E503's 48 runs (line 89), the data of E615, E616, E617 and E618, which stay
  listed as unmodelled; E733 is the two-stage bilinear form `tex.rs` implements (cited as E720).
  Cite them where the replay is (5 entries off the list); [check] E650, E660, E664, E665 (the
  model records of vdm/ta, isp and zls) the same way. Small.
- Q101's fold (R11-7) moves `zls.rs`'s 9 Q101 refusals: bit 19 with an integer format over
  [0, 1] becomes "no change" (E490, E981, E987), bit 19 with a load refuses under Q243.

Not gaps: E1000 (max rule, fitted), E997 (linear store, which bit not separated), E1005/E1012's
clip (fitted) stay refusals, as now. The texture spec's sRGB and address sections and the zls spec
take one line each with the packages below.

## 2. Offline work packages (each one agent, its own worktree and CARGO_TARGET_DIR,
`git commit -- <paths>`, `--no-renames`; records numbered from E1011)

**P1 geometry, TA and DPM (~2.5 h).** Records: **E1011** Q139 (finding 1; data
cited-scratch closing11/plan/c1-q139flag/); **E1012** Q261 (finding 4, tier [fitted]/infer,
"post hoc, no held-out row" in the claim); **E1013** Q210 (finding 3). Question text: ta/Q139
(flag answered, open fx 2/3 mod 4 and highest target slot), isp/Q261 (the clip reading and its
vertices), dpm/Q210 (class table, H-RULE refuted). Appended notes: E1007, E1009. Sim: G3 in
`sgx-pipe/src/dpm.rs` + its test (test first); cites of E1011 in `src/ta.rs` (and
`tests/ta_slots_table.rs` if the r7-rp rows become vectors), E1012 in `src/isp.rs` (band stays
undetermined). Files: questions ta/Q139, isp/Q261, dpm/Q210; evidence E1011-E1013, E1007, E1009;
crates ta.rs, isp.rs, dpm.rs, tests.

**P2 ZLS (~3 h).** Records: **E1014** Q071 (finding 2: H-ZEROLOAD held, linear load refuted);
**E1015** Q120 (finding 7, SEMI for F6C, blind for F7K). Appended correction to E997 (y read,
4608 of 4608 by (x, y)). Question text: isp/Q071, zls/Q120; Q101 folded into mte/Q069
(R11-7: `tools/records/questions.py` RETIRED "folded into Q069", Q069 takes the word-10 clause and
Q101's evidence). Sim: G2 in `sgx-pipe/src/zls.rs` + a zst2 replay test; Q101's refusals re-keyed
(test first). Files: questions isp/Q071, zls/Q120, zls/Q101 (removed), mte/Q069; evidence
E1014, E1015, E997; crates zls.rs and a new test file; tools/records/questions.py.

**P3 texture, PBE and coverage (~3.5 h).** Records: **E1016** Q282 (finding 5, held out offline,
one column); **E1017** Q177 (finding 6: the frozen mode-5 form refuted where s is inside and t
outside, corner dwords shape dependent; the post hoc forms [fitted]). Notes: Q078 and E975, E564
(finding 8; no record unless R11-8 (b), then **E1018**), E983, E1004. Question text:
texture/Q282, Q177, Q078. Sim: G4 in `sgx-sim/src/tex.rs` (if R11-6 a), G1 in
`sgx-pipe/src/pbe.rs` + vectors test, G5 (cites in `tests/unit_vectors.rs`, `tex.rs`; entries
removed from `crates/SIM_UNMODELLED.toml`: P3 is the only package touching that file). Files:
questions texture/Q282, Q177, Q078 (pbe/Q046 unchanged); evidence E1016, E1017 (E1018), E983,
E1004, E975, E564; crates tex.rs, pbe.rs, tests, SIM_UNMODELLED.toml.

Disjoint: no question, record or crate source in two packages. Shared and generated:
`doc/state_digest.md`, `doc/open_questions.md`, spec coverage: the lead regenerates at the
merge. Order: in parallel; merge P1, then P2, then P3 (P3's list shrink last, after the new
records of P1 and P2 are cited by their own packages). Each record's scratch cite: the `c*/`
directory, checked by `tools/records/scratch_cites.py` (all publishable). Records: E1011 to
E1017 (E1018 if R11-8 b). Full check per package, then once at the merge.

| Package | Records | Questions | Sim | Wall | Risk |
| --- | --- | --- | --- | --- | --- |
| P1 | E1011-E1013 | Q139, Q261, Q210 narrowed | dpm bias table, cites | ~2.5 h | low |
| P2 | E1014, E1015 | Q071, Q120 narrowed; Q101 folded into Q069 | zls formats 3/4, Q101 re-key | ~3 h | low |
| P3 | E1016, E1017 (E1018) | Q282, Q177, Q078 narrowed | pbe packs, sRGB flush, list -5 | ~3.5 h | low |

## 3. Tiers of all 155 (`tiers11.out`, every id once, checked)

- O11, offline this round (10): Q139 Q071 Q177 Q282 Q210 Q261 Q120 Q078 Q101 Q202.
- S11, sim gaps (2): Q046 (G1 models its answered modes), Q044 (G1's refusal id).
- L, laptop rows later (11): Q243 Q242 Q241 Q199 Q284 Q211 Q066 Q019 Q260 Q108 Q076.
- K (4): Q109 Q068 Q064 Q193. F (2): Q146 Q194. O, offline later (21): round 10's O + Q288.
- H (66), X (24), Ph (5), P (10): as round 10.

## 4. Laptop rows for a later round (no design; B60AB0B4 or stock, safe class, kit)

1. Q261: c6's 7 far vertices at 64 x 64 + one at 128 x 128 (~8 jobs): parts G 16 to 22, the
   clip vs no clip; with far2 (E1008 unused, Q199 past 2^25).
2. Q071: bits 12, 16, 20 alone and in pairs, each on E977's ramp dump and under E988's stencil
   test (~12 jobs): which bit linearises, which bit stops the stencil read.
3. Q282: corners 0, 1, 0, 1 at ky = 0, kx 11 to 14 and two more subnormal rows (~3 jobs).
4. Q177: 16 x 64, 8 x 64, 64 x 8 twiddled in modes 4 to 6 (max vs W, corner base; ~6 jobs).
5. Q078: bit 11 clear at LOD 0 to 6 (smp2dreplace), bit 12 with T0's max level below 6, bits
   12:11 = 10, a 32 x 32 chain (~8 jobs).
6. Q120: a second y-ramp size and fills 0x3f/0x1f for F7K (~4 jobs).
7. Q210: two or three new targets near the class boundary (3072x2560 vs 3072x3072, 1024x2048 vs
   2048x3072), calibrations only (~6 jobs, long jobs).
8. Q243: the moved load base ([check] `--poke rd:12=` after `depth_arm`, round 10's open check).
9. Q046: bit 12 with other colours and positions (modes 0 to 6), to say what its words are.
10. Q139: a dump whose last block-order target tile is not the highest target slot (design check:
    may need fx 2/3 mod 4, which faulted: possibly not safe).

## 5. Decisions (the lead takes the recommendation; every (a) is offline and self-contained)

1. **R11-1 Packages.** a) P1, P2 and P3 as in section 2, three agents in parallel, ~3.5 h wall,
   records E1011 to E1017 (recommended); b) the records and question text only (no sim change:
   G1 to G5 wait); c) P1 only.
2. **R11-2 Q139.** a) Record E1011 (21 of 21 held out), narrow Q139 to fx 2/3 mod 4 and the
   highest target slot, a note on E1007 (recommended); b) a note only.
3. **R11-3 Q261.** a) Record E1012 as a post hoc fit (one integer G, 48 of 48, no held-out row)
   with c6's vertices named for a later row; sgx-pipe keeps the band undetermined (recommended);
   b) a Q261 note only, no record until the held-out row.
4. **R11-4 Q210.** a) Record E1013 and model S6 = R + class at the 22 measured targets, refusing
   others (G3, test first) (recommended); b) record only.
5. **R11-5 Q071 and E997.** a) Record E1014 and the appended correction to E997 (rows named in
   y) (recommended); b) the E997 correction only.
6. **R11-6 Q282.** a) Record E1016 (FTZ-OUT 12 of 12 halves held out offline, one column), narrow
   Q282 to the input/output flush split and model the flush in sgx-sim (G4); retire after laptop
   row 3 (recommended); b) retire Q282 now on E1016 (thin: one pixel column); c) a note only.
7. **R11-7 Q101.** a) Fold into Q069 (bit 19: no route brings a negative depth to an integer
   conversion, E490/E981/E987; word 10's scale moves to Q069), zls.rs refusals re-keyed test
   first (recommended); b) keep Q101 open as is.
8. **R11-8 Q078 bits 11/12.** a) Appended notes on Q078, E975 and E564 (post hoc decode on the
   only two jobs; replicates are not held out) (recommended); b) a record E1018 labelled post hoc.
9. **R11-9 Q202.** a) No change this round (its moved clauses already live in Q031 and Q159 to
   Q161; nothing new decides perspective planes or the divide) (recommended); b) a text
   narrowing dropping bit 28 and lines/points, with the 11 crate cites unchanged.
10. **R11-10 Q120.** a) Record E1015 (F7K held out blind on two fills; F6C SEMI) and G2 for formats
    3 and 4 only (recommended); b) a note only and no sim change.
11. **R11-11 Sim gaps G1 and G5.** a) Both in P3 (pack modes from E383/E999; five list entries
    off by citing their existing replays) (recommended); b) G5 only; c) neither.

## 6. Summary (10 lines)

1. 155 open; eight offline checks run under hash freezes (c1 to c8), every file publishable.
2. Q139: bit-7 list end held on r7-rp's 21 unread dumps (21/21); "highest slot written" fails 17.
3. Q071: E989's stencil reads 0 (held 2/2), not E997's linear layout; E997's y is named (4608).
4. Q210: E1009's bias is a per-target class, held out on 16 calibrations + 50 cells; aspect refuted.
5. Q261: a guard-band clip (G 16 to 22) fits all 48 far rows post hoc; set-up float forms 0/236.
6. Q282: subnormal flush held out offline on an-t0b27's 12 halves (thin); Q177's max stays fitted.
7. Q120: F7K held out blind on two fills, F6C SEMI; Q078 bits 11/12 decoded post hoc.
8. Q101 folds into Q069; no other retirement is decided by kept data.
9. Three packages (records E1011-E1017): P1 geo/TA/DPM, P2 ZLS, P3 texture/PBE + list shrink.
10. 11 decisions, (a) throughout; one appended correction (E997), six appended notes.
