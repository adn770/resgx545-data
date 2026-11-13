# Round 10 ranking: what closes beyond round 9's follow-ups (Opus, 2026-11-13, read-only)

Basis: resgx545 `main` 58c4763 with the r9-k1 fold (`r9-fold-k1` cf0a9dd, E970-E974, Q190
retired) staged in the main worktree while this plan was written; records to E981; **158 open**
(148 hw, 10 parked). Data repo as checked out (r9 sessions published). Laptop: module B60AB0B4
(fork 2a650d74) until its next reboot; tools t4 (`~/sgxfive-test-rgn4`, resgx545 4623753) and t9
(`~/sgxfive-test-t9`, 97447b04); `r10-tooling` (5 commits, 9933208) adds `tri --isp2`, probe
`--kpoke` in the kit, bool knob readback and `hook_fault` (a t10 build is needed for `--isp2`).
Not planned here: the seeds (closing10/seeds: Q284, Q177, Q078, Q282, Q120, Q121, Q199, Q261,
Q101, Q139, Q210, Q211, Q108, Q076, Q066, Q260; Q190 is retired by the k1 fold).

Scratch in this directory (standard library, publishable: no firmware-derived content):
`index.py`/`digest.py`/`xref.py` and their `.txt` (round 9's scripts rerun on the tree above);
`tiers10.py`/`tiers10.out` (all 158 placed once, checked); Q030 `q030_slots.py`,
`q030_slots_rule.json` + `.sha256` (0dd46dec...), `q030_slots.out`; Q242 `q242_edge.py`,
`q242_edge_rule.json` + `.sha256` (ae732269...), `q242_edge.out`, `q242_e411_pages.py` + `.out`;
Q288 `q288_split.py` + `.out` (design aid, no data); stage dcmp's table `dcmp_table.py` + `.out`;
`t4-sgxfive-test.c` (the t4 source, `git show 4623753:...`, read for option checks); `q202/`
(a helper agent's offline check of Q202's perspective clause, section 0 item 3).

## 0. Findings (offline, read first)

1. **Q030: E281's sample slots hold in the tiles past the first, in every window r9-geo ran; four
   rival slot sets are refuted** (`q030_slots.out`). Data: r9-geo's kept `--pixels` images of
   stages seam1 and seam4 (E953, E954; `resgx545-data/render/closing-r9-geo/out/20261113-081038`),
   48 jobs (24 a stage, the 2 controls included): tri-full renders 64 x 96 to 128 x 96 and six
   single triangles of new slopes, modes 0 to 2, TE 0x6/0xa/0xe windows. Model: the landed region
   model (`texture/p1141/recompute/msaa_model.py`, sha 1c0e8205..., frozen before the run as the
   O8 table), scored only on the pixels of tiles other than (0, 0). Rivals declared and hashed
   before the images were read: S-CENTRE (8, 8), S-MIRX, S-MIRY, S-TRANS (x, y swapped), S-SWAP
   (slot pairs swapped). Result: **S-E281 exact past the first tile on 48 of 48 jobs (0 pixels
   off)**; the rivals each differ from it on 30 to 42 jobs and are off the kept image by 264 to
   948 pixels past the first tile (S-CENTRE 504, S-MIRX 484, S-MIRY 948, S-TRANS 264, S-SWAP 910);
   the two tri-full m2-a twins part nothing. Held out: the model was frozen before the run and
   E953/E954 already reported it exact on the whole sets; what is new is that those images
   discriminate the slot sets past the first tile (the rivals are post hoc but declared before
   this read). Refuted by: a kept or new multisampled image past the first tile off E281's slots.
   Not shown: mode 0's window with TE bits 31/30 as an identity map (sgx-pipe `msaa_source`
   refuses it under Q030: the m0 rows here are tri-full, holes only) and mode 3 (never run).
   **Q030 narrows to those two** (a record, O10-1); stage win0 (R10-B) reads mode 0's windows.
2. **Q242: past the target, the integer formats store the same floor rule; E411's faults fit its
   buffer's extent** (`q242_edge.out`, `q242_e411_pages.out`). E977 scored only the 3200
   in-target pixels of r9-x's z242-c (80 x 40, G 2, tile area 96 x 48). Frozen by hash before the
   past-target dwords were read: H-EXT (format 1 = min(floor(z0 * 2^24), 0xffffff), format 2 =
   floor(z0 * 2^16) halves in E490's layout, z0 the format-0 float of the same pixel, E831's band
   stored there) vs H-FILL (the fill left) vs H-ROUND. **H-EXT 1408/1408 (format 1) and 704/704
   (format 2); H-FILL 0 and 0; H-ROUND 832 and 683** [HW data read offline after a freeze; same
   session as E977's fit rows, so held out in dwords, not in jobs]. E411's faults: E465's address
   rule recomputed for E411's 64 x 64 target (depth at scratch page 12, stencil at page 4, a
   16-page buffer) gives exactly the stored pages of E411's table for G 0, 1, 3, 5, 9, 17 up to
   each row's fault (G 5: depth 12 and 15, stencil 4; G 9: depth 12, stencil 4 at 256), and E977
   ran G 7 and 9 with a buffer sized to the extent without a fault; so the pitch field does not
   fault the job, the extent past the buffer does [infer]. One misfit kept in the note: at G 3
   the rule puts tile rows 2 and 3 at pages 16 and 18 (past the buffer) and E411 saw no fault
   there, while G 9's first page past the buffer (17) faulted: what lies past page 15 is not
   known. **Q242 narrows to the overlapping tiles** (record O10-2); stage zov (R10-C) reads them.
3. **Q202: three of its six clauses are answered by records it does not cite.** Targets whose
   half-size is not a power of two: E680 (6 of its 10 targets, 0 of 1.09e9 pixels off) and E913
   (128 x 96, 128 x 144, 64 x 33, 96 x 47: 240 of 240). Vertices well outside the target: E979 (one
   or two vertices at 2^22 to 2^25 pixels, H-EXACT 10 of 10, clamp and wrap refuted). 4x sample
   points: E953/E954 with finding 1 (E281's slots, top-left ties on the sixteenth grid, every tile
   and window run). Open after them: perspective (w other than 1), ISP word 0 bit 28 widening
   (Q031 holds the multisampled hang), lines and points (Q159 to Q161 hold their rules).
   Perspective (`q202/`, a helper agent's check): on r6-pixel's 114 kept w != 1 jobs (g6-rwa 8,
   g6-rw 106, E859/E879, w 2.5e-4 to 8027; E606 frozen 2026-11-09, jobs run 2026-11-12) E606's
   rule on window x/w drew every pixel (0 of 466944 off, 114 of 114 jobs) under all four declared
   rivals (exact x/w, float32 divide, float32 reciprocal, the TA's stored X/Y, which equal the
   exact snapped x/w at all 342 vertices), and **no pixel parts the rivals**: the w ramp across a
   triangle is mild (max/min w up to 1.1 in 105 jobs, 3.0 at most). The agent looked at one job's
   background rows and parameter header to learn the formats before hashing its rule. So E606
   holds with perspective on these jobs [HW data, held out]; the divide's arithmetic is not
   split. A splitting row needs a large w ramp with a pixel centre within ~1e-5 px of an edge
   (close-behind candidate, section 1).
4. **Q205's coverage clause is E606's (held out) and its plane clauses are Q200's, Q288's and
   Q262's**: E606 (0 of 14368768 pixels, held out on 814 triangles), E607 (the 1/256 snap, ties
   up), E680 and E913 answer "the precision of the edge functions ... and the rule when a centre
   lies on an edge" and "very thin, very small or off-target-partly triangles"; none of E606,
   E607, E680 is in Q205's evidence. What stays is the depth and iterator plane arithmetic, which
   Q200 (dyadic), Q288 (non-dyadic gradient) and Q262/Q240 (error bounds) ask in sharper form.
   Proposal: fold Q205 into Q200 (Q200 takes the iterators' plane clause). Cost: sgx-pipe's 13
   refusal cites of Q205 (`tests/transfer_refusals.rs`, `tests/scene_vectors.rs`, the transfer
   model) move to Q200 in the same commit, test first (R10-6).
5. **Q019: E973 is the first record in which the secondary attribute size changes a result**: in
   r9-k1's layered background, bgobj_words[1] at 0 rows (0x30000) gave each pixel a texel of the
   source but its own at only 74 of 3034 (offsets up to 47 columns), at 1 and 4 rows its own texel
   at every pixel (E973; H-NOTEX refuted). Q019 does not cite it. A dated note (no claim settled):
   the field limits what reaches the background layer's task at 0 rows [infer], unlike E125/E391's
   fill, where 0 rows passed all 32 attributes.
6. **Q046's "What is open" paragraph is stale**: it says modes 15, 18, 24, 25, 28 were not run with
   bits 8:6 and asks whether 3 is blue and 4 to 7 read as 3, but its own 11.14 paragraph (E383)
   answers all of that (modes 15, 18, 24, 25, 28 ignore the field; 3 to 7 are blue). Open after
   E383: pack modes 20 and 27 with the field, what bit 12's words are, bit 11 (faults: not safe).
   A text correction (O10-5); stage sb (R10-E, optional) runs modes 20 and 27.
7. **Q288's nine gradient rules cannot be split at E731's depths within one tile**
   (`q288_split.out`): over A = 1/D, D 64 to 19999, only 14 values give nine distinct words, and
   their closest pair differs by 0.1 ulp over a 32-pixel row at depth 0.5; near depth 2^-4 the
   gap is about 2 ulps and near 2^-8 about 32. So a split row needs a plane in the low binades
   with a dyadic control on the same depths (Q200's below-binade-0 deviation is the risk). Q288
   stays; its row is conditional (R10c-G).
8. **Uncited newer records** (`xref.txt`): unchanged since round 9 except E978 for Q121 (a seed).

None of findings 1-7 contradicts a landed claim. Finding 2's G 3 misfit is E411's own data, not a
correction: E411 already reads the faults as [infer].

## 1. Candidates beyond the seeds, ranked (value/cost)

All rows: B60AB0B4 as loaded, t4 unless named, kit as on main (f32dfac + r10-tooling once merged),
safe class (no planned fault, no expect-fault row, no held reset). Time at r9-x's measured ~6.4 s a
job (66 jobs in 7 minutes, `render/closing-r9-x/run.log`).

**R10-A. Q241 + Q243: the depth compare truth table and loaded NaN, infinity, negatives (stage
dcmp; Q241 medium-low, Q243 low; 21 and 15 crate cites).** Records E282, E467, E977, E287; 3d.md
section 9.1 (the compare is exact to the ulp at 0.5). Form: E977's z243 rows token for token
(`tri --tri-full --tri-z t,t,t --depth --depth-ctl 0x0017500e --depth-fill L --depth-store
--depth-dump "$W" --poke blk:1=(m << 22 | 0x200) --pixels`, 64 x 32), the reading the drawn count.
Rows (`dcmp_table.out`): modes 0 to 7 at L = t = 0.5 (8), modes 2, 3, 5, 6 at one ulp above and
below (8): the eight modes' truth table over <, =, > read directly against E282's GL-order
[infer]; NaN under 2, 3, 5, 6 (4); the ten rows where the value rivals part (-0.25 and -0.75
loaded under less and greater, a triangle at 0 against -0.25 and -0.0 under less, equal and
greater). Frozen per row: H-GL (E282's order) for the mode rows; H-UBITS (unsigned bit patterns,
E977's [infer]) vs H-ABS (sign cleared, E664's refusal note) vs H-IEEE vs H-CLAMP0 (a negative
loaded depth read as 0, E287's triangle side) for the value rows. Controls that can fail: E977's
z243-ctl rerun (0.75 under less, 2048) and mode 7 (2048) / mode 0 (0). 31 jobs, ~3.5 min. Risk:
lowest (E977's 7 rows, no fault). Closes: Q241's "compares 2, 3, 5 and 6 against equal depths"
clause; Q243's "other compare modes against NaN and equal depths" clause; Q243 then narrows to the
moved load base alone. [check] the builder's mock: `--tri-z 0,0,0` prints and runs (t = 0x0).
Kit: fits (E977's rows, `outdir_opts` for `--depth-dump`, `reads:drawn` controls).

**R10-B. Q030: mode 0's windows as identity maps (stage win0; medium; 7 crate cites).** Records
E502 (identity maps: mode 0 ran only with TE 0x20000000), E503, E953, E954, finding 1. Form:
E502's x and y jobs (`probe --tri pixpds:12 --tri-full`, E437's PDS program iterating source 0,
the shader writing pa0 or pa1 as the colour, cmd:13 mode, cmd:10/16 0xeaa26e26, cmd:1 TE) in mode
0 with TE 0x60000000, 0xa0000000, 0xe0000000 at 64 x 64 and 128 x 96: 12 jobs. A 4x context is
needed for TE bits 31/30 (round 8's E934 slip): probe has no `--aa4`, so each row carries
`dbg:render_rgn_arrays=1`, which makes the context multisampled (`ctx->aa_ms = aa4 || setting`,
r9-geo `gen/seam.py`) and puts E502's one array back. Frozen per pixel: H-IDENT (source = the
stored pixel, x + 0.375 and y + 0.125, E502) vs H-WIN (the window offsets 16 b31 and 8 b30 of
modes 1 and 2) vs, on the hole pixels, the region model's background (E953). Controls: E502's
64 x 64 mode 1 TE 0xe0000000 x job (its decode known) and mode 0 TE 0x20000000. 14 jobs, ~2 min.
Risk: lowest (E953 ran mode 0 with these TE values, no fault). Closes Q030's mode-0 clause; with
O10-1, Q030 is left with mode 3 only, which no question needs [infer] (R10-5 retires it with mode 3
moved to sgx-pipe's own refusal note). [check] the dry run shows the probe's render takes the
knob (the context init is the render's, not tri's), and the bins of E502 are in
`resgx545-data` (dataset of probes/isp/msaa-ident.toml). Kit: fits (probe rows, a `dbg:` knob in
the row, bins in `[files] laptop`).

**R10-C. Q242: overlapping tiles (stage zov; low; 32 crate cites).** Records E465, E466, E490,
E977, finding 2. Form: E977's z242 rows with a plane rising in x and y (z 0, 1, 0.5 at (0,0),
(2W,0), (0,2H): every pixel of the tile area its own float) and the pitch G below the tiles across
minus one: 64 x 32 G 0, 128 x 32 G 1, 96 x 48 G 1, 160 x 48 G 2, 256 x 64 G 3, format 0 (5) and the
64 x 32 G 0 job in format 1 (1); controls: the same plane at full G (the reference floats, can
fail: every dword of the tiles, E831) at the five sizes. Frozen per shared slot: H-LATE (the tile
the 3D visits later owns the slot; the visit order from sgx-pipe's region order) vs H-EARLY, a
per-dword reading otherwise (each dword's float names its source pixel through the full-G
control). 11 jobs, ~1.5 min. Risk: lowest (E465 stored at G 0 with overlap, no fault). Closes
Q242 if one rival holds on every shared dword (with O10-2 nothing else is open). Kit: fits.

**R10-D. Q071: the inert control bits together, bit 0 under other controls (stage zbits; medium;
15 crate cites).** Records E057, E411, E465, E466, E467, E665, E977. Form: E977's z242-c geometry
(80 x 40, G 2, format 0 and 1) and its z243-ctl load row, with the control: all of bits 15, 21 to
23, 27 to 31 set and 12, 16, 20 cleared at once (formats 0, 1 and the load row: 3), each half
alone (2), bit 0 with format 1, format 2, the load control and G 2 (4). Frozen: H-INERT (dump and
image hashes equal to the control's) vs a change; bit 0: H-E665 (no colour pixel written, stores
as without bit 0). Controls: E977's z242-c-f0 and -f1 reruns (dumps known, can fail). 11 jobs,
~1.5 min. Risk: lowest (E411 flipped each bit singly, no fault). Closes Q071 but its stencil-test
clause, which rides the seeds' Q121 rows once t10's `tri --isp2` is built (2 rows: the inert
mask with a stencil test, R10-4). Kit: fits.

**R10-E. Q241's untried ISP bits (stage isp0x; explore).** ISP word 0 bits 15, 16, 17, 18,
ISP word 1 bit 3 (visibility test) and bit 23 (polygon offset) flipped one at a time on E977's
z242-c ramp with the depth dumped (6) + the unpoked control (1). Frozen: "no change" (E282's
null) per row, a reading otherwise. 7 jobs, ~1 min. [check] the state block word that `blk:2`
reaches is ISP word 1 (r9-geo's seam rows poke `blk:2^=0x8`). Kit: fits. Value: narrows Q241.

**R10-F (optional). Q046: pack modes 20 and 27 with sideband bits 8:6 (stage sb; low).** E383's
form (two colours whose bytes all differ, bits 8:6 at 0 to 3, every pixel read) for modes 20 and
27: 16 jobs + E383's mode 8 control (2). ~2 min. [check] E383 ran from a probe toml
(`probes/pbe/sideband-channels.toml`): the builder writes the rows as kit probe rows (`--sideband`,
`--pbe`) and replays one E383 job in the mock. Closes Q046 but bit 11 (faults) and bit 12's words.

**R10c-G (conditional). Q288's gradient rules (stage grad; medium).** Finding 7: rows exist only
at low depths. Condition: the builder finds A values and a depth base where every pair of the
nine rules differs by at least 2 ulps somewhere in a tile row, and a dyadic control plane on the
same depths (Q200's below-binade deviation: if the control misses, the stage tells nothing).
~8 jobs, ~1 min. Recommend only if the check passes offline; else Q288 stays for a later round.

Not picked, close behind: Q202's perspective split (a vtxuse probe with w 1 to 16 across one
triangle and edges placed within 1e-5 px of centres, E879's form), Q104 (1D and side-1 mip chains on
named memory, r9-x t3's form), Q201
(position source vs coordinate set: needs a program carrying window x, y), Q116 (scissor and
clip in whole tiles), Q243's moved load base (needs a per-render `rd:12` override: [check] whether
a row's `--poke rd:12=` lands after `depth_arm`'s), Q296 and Q012 (offline families, an agent's
afternoon each, low yield on round 9's evidence).

## 2. Proposed sessions and the offline package

**Offline O10 (Mac, worktrees, `git commit -- <paths>`; ~2.5 h; records numbered by the lead):**
- O10-1 Q030 record (finding 1; scripts and rule into `resgx545-data`, imports pointed at the
  published `msaa_model.py` and r9-geo's `gen/seam.py`); Q030 narrowed to mode 0's windows and
  mode 3; sgx-pipe: no code change (its refusals are those two). 45 min.
- O10-2 Q242 record (finding 2: past-target H-EXT and the E411 page recomputation, its G 3 misfit
  stated); Q242 narrowed to the overlapping tiles. 40 min.
- O10-3 Q202 narrowed by E680, E913, E979, E953/E954, O10-1 and a record of `q202/`'s check
  (finding 3: E606 holds on 114 w != 1 jobs; the divide's arithmetic not split). 40 min.
- O10-4 Q205 folded into Q200 (finding 4) with the sgx-pipe refusal ids moved, test first. 30 min.
- O10-5 Text: Q019 note (E973), Q046 correction (E383), Q288 note (finding 7). 20 min.

**Session `r10-x` (B60AB0B4, t4, kit; no kernel change, no boot).** Stages in order: dcmp (31),
zov (11), zbits (11), isp0x (7), win0 (14), sb (18, optional): **74 jobs with sb, 56 without;
~8 min of runs, ~25 min with staging, preflight and health.** Stops: any fault or hang (none of
these forms faulted before), two unparsed outputs in a stage, free space below 300 MB, a control
failing (gate = true on dcmp, zov, zbits, win0). Builder checks before the freeze, by the mock and
the preflight's dry run: `--tri-z 0,0,0` (dcmp), the `blk:2` word (isp0x), the probe render taking
`dbg:render_rgn_arrays` and E502's bins present (win0), E383's rows as kit probe rows (sb). A
failed check drops its stage, not the session. Order in the sitting: after the seeds' sessions
(which may need t10). Conditional: grad (R10c-G, ~8 jobs) appended only if its offline check
passes; the Q071 stencil rows (2) ride the seeds' Q121 stage on t10.

| Item | Runs on | Change | Jobs | Wall | Risk |
| --- | --- | --- | --- | --- | --- |
| O10-1..5 | Mac | none | 0 | ~2.5 h | none |
| r10-x dcmp, zov, zbits, isp0x, win0 | B60AB0B4, t4 | none | 56 | ~20 min | lowest |
| r10-x sb (Q046) | B60AB0B4, t4 | none | 18 | ~5 min | lowest |
| r10-x grad (Q288) | B60AB0B4, t4 | none | ~8 | ~3 min | lowest; only if its check passes |
| Q071 stencil rows | B60AB0B4, t10 | `tri --isp2` (r10-tooling) | 2 | ~1 min | lowest; in the seeds' Q121 stage |

Records: O10 three (O10-1, O10-2, O10-3); r10-x one per stage run (5 or 6).

Kernel: none (round 10 constraint). Costed in round 9 and unchanged: Q109 (a PDE size-field check
file, faults likely), Q068/Q064/Q049 (a context-switch path, days), Q193 (a module reload between
marker jobs, untested under the display). Recommend none.

## 3. Tiers of all 158 (`tiers10.out`, every id once, checked complete)

- SEEDS (closing10/seeds, 16): Q284 Q177 Q078 Q282 Q120 Q121 Q199 Q261 Q101 Q139 Q210 Q211 Q108
  Q076 Q066 Q260.
- O10, offline this round (6): Q030 (record, then win0), Q242 (record, then zov), Q202 (narrow),
  Q205 (fold into Q200), Q019 (note), Q046 (text, then sb).
- R10, picked for r10-x (3 more): Q241 (dcmp, isp0x), Q243 (dcmp), Q071 (zbits).
- R10c, conditional (1): Q288 (grad, offline check first).
- K10, kernel or reload, not this round (4): Q109 Q068 Q064 Q193.
- F10, text (2): Q146 Q194 (keep apart, round 3's decision).
- O, offline later (20): Q280 Q296 Q100 Q053 Q200 Q163 Q075 Q012 Q008 Q125 Q107 Q070 Q074 Q290
  Q179 Q082 Q089 Q142 Q262 Q240.
- H, safe hardware rows later (67): round 9's H9 less Q071, Q241, Q046, Q202, Q205, Q240, Q262.
- X, hangs, faults, held resets, new tooling (24): as round 9.
- Ph (5): Q048 Q063 Q099 Q154 Q168. P, the digest's 10 parked: Q004 Q029 Q034 Q049 Q084 Q088 Q095
  Q118 Q119 Q277.

## 4. Retire, fold and merge candidates (with records)

- **Q030: narrow now** (O10-1: E953, E954, the new record), **retire after win0** if H-IDENT holds
  (mode 3 then stays only as sgx-pipe's "not measured" refusal, re-keyed by R10-5).
- **Q242: narrow now** (O10-2: E977's kept dumps, E411, E465), **retire after zov** if one rival
  holds on every shared dword.
- **Q205: fold into Q200** (E606, E607, E680, E913 answer its coverage clauses; Q200, Q288, Q262
  ask its plane clauses). A fold, not an answer; the 13 crate cites move with it.
- **Q202: narrow now** (E680, E913, E979, E953/E954 + O10-1); retire only if the perspective clause
  closes and its bit-28 and line/point clauses are folded into Q031 and Q159-Q161 (R10-7).
- **Q243: narrows after dcmp** to the moved load base. **Q241: narrows after dcmp and isp0x** to
  bit 15-18 meanings if any acts, the pass types over several triangles, depth outside [0, 1].
- **Q071: retire after zbits** if H-INERT holds and the stencil rows (t10) show no change; else
  narrow to the stencil clause.
- **Q046: text correction now** (E383 answers its stale paragraph); retire after sb but bit 11/12.
- **Q146 / Q194: keep apart** (no record since E602). The 10 parked: no change (HACKING policy).
- No landed claim needs a correction for any item here.

## 5. Decisions (the lead takes the recommendation: every (a) is safe class and self-contained)

1. **R10-1 Offline package O10.** a) O10-1..5 (Q030 and Q242 records, Q202 narrowed, Q205 folded
   into Q200, Q019/Q046/Q288 text), ~2.5 h, one agent (recommended); b) O10-1, O10-2 and O10-5
   only (no fold, no crate change); c) none.
2. **R10-2 Session r10-x (B60AB0B4, t4, kit, no kernel change).** a) dcmp, zov, zbits, isp0x,
   win0: 56 jobs, ~20 min, after the seeds' sessions in the same sitting (recommended); b) dcmp,
   zov, zbits only (53 min of build saved, 53 jobs fewer checks: no win0 knob check); c) none.
3. **R10-3 Optional stage sb (Q046).** a) Append it to r10-x if the builder's E383 replay passes
   (18 jobs, ~5 min) (recommended); b) leave Q046 to a later round.
4. **R10-4 Q071's stencil clause.** a) Two rows in the seeds' Q121 stage on t10 (the inert mask
   with a stencil test and a loaded stencil, H-INERT frozen) (recommended); b) wait.
5. **R10-5 Q030 after win0.** a) Retire Q030 if H-IDENT holds, moving sgx-pipe's mode 3 refusal to
   a "not measured, no question" note (test first, as Q141's isp stubs were dropped in 0c75fac)
   (recommended); b) keep Q030 open for mode 3.
6. **R10-6 Q205.** a) Fold into Q200 now with the 13 sgx-pipe refusal cites moved (recommended);
   b) narrow Q205 by E606/E607/E680/E913 and keep it open; c) no change.
7. **R10-7 Q202.** a) Narrow now by E680, E913, E979, E953/E954, O10-1 and the `q202/` record
   (E606 holds with w != 1; the divide's arithmetic stays open) (recommended); b) also fold its
   bit-28 clause into Q031 and its line
   and point clauses into Q159-Q161 and retire it when perspective is settled; c) no change.
8. **R10-8 Stage grad (Q288).** a) Only if the builder's offline split check passes (every pair 2
   ulps apart in a tile row, a dyadic control on the same depths) (recommended); b) skip this
   round.

## 6. Summary (10 lines)

1. 158 open (r9-k1 fold in): 16 seeds elsewhere, the other 142 placed once (`tiers10.out`).
2. Q030 offline: E281's slots exact past the first tile on 48 of 48 kept 4x images (E953/E954);
   four rival slot sets off by 264 to 948 pixels: narrow now, mode 0's windows left (win0).
3. Q242 offline: past the target the integer formats follow floor (1408/1408, 704/704, frozen);
   E411's faults fit its buffer's extent [infer]: narrow to overlapping tiles (zov).
4. Q202: E680/E913/E979/E953 answer 3 clauses; E606 holds on 114 kept w != 1 jobs (no pixel splits
   the divide); narrow. Q205's coverage is E606's: fold it into Q200.
5. Q019 gains E973 (0 rows mis-assign the layer's texels); Q046's open text is stale (E383).
6. Q288's nine gradient rules part only at low depths (finding 7): conditional row.
7. r10-x (B60AB0B4, t4, kit): dcmp 31 (Q241/Q243), zov 11, zbits 11 (Q071), isp0x 7, win0 14.
8. ~20 min of laptop, no kernel change, no fault rows; optional sb (Q046) and grad (Q288).
9. O10 ~2.5 h: three records (Q030, Q242, Q202 perspective), one fold, three notes.
10. 8 decisions, (a) recommended throughout; no landed claim needs a correction.
