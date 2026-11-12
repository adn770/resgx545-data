# Round 7 ranking: what is closable now beyond the seeds (Opus, 2026-11-12, read-only)

Basis: resgx545 `main` 418467e (22/22), 166 open (156 hw, 9 fw, 1 kernel), records to E892; data
7533ddc0; linux fork `resgx545` 3f0b3e74 (read with `git show`/`git grep`). Laptop: module
41E2F5C7 (render_tail_room, peek of 0x0694, bif_flush) loaded on the one-shot boot of 15:37; its
next reboot is the distro kernel, which has no sgxfive render node, so **every hardware row below
needs either the current boot (no reboot before it) or a one-shot boot of the installed test kernel
(`boot-test-kernel.sh`, user's OK), not a kernel change** unless it says so. Tool on the laptop: t6
(sha256 97df5c0e..., from d9b2969: odd heights, `--depth-dump`, `--tri-v`, `--pixels-rle`).
Model: `closing6/rank/rank-round6.md`, updated. Excluded (planners a, b, c): Q287 odd widths, Q291,
Q276, Q293, Q139, Q086; Q210, Q211, oomring2; Q003, 0x0694/Q111, Q294.

Scratch in this directory (read-only analyses, publishable: no firmware-derived content, only
public data paths): `index.py`/`index.txt`, `digest.py`/`digest.txt`, `xref.py`/`xref.txt` (round
6's scripts, rerun on 418467e), `tiers7.py`/`tiers7.out` (all 166 placed once, checked),
`q142_diff.py`/`.out` and `q142_rgn.py`/`.out` (Q142), `q178_type5.py`/`.out` (Q178),
`q260_tilerel.py`/`.out` (Q260). Note: the repo `.venv` has no numpy today; the Q260 script ran
under another local venv's interpreter with `-I` (read-only); a landed check would need numpy
added to the scratch venv first.

## 0. What changed since round 6 (E870-E892) and findings that change the plan

1. **Retired:** Q289 (E884, OR held 20/20), Q292 (E889). **Folded:** Q274 into Q183, Q244 into
   Q071 (round 6 text package, done). 170 -> 166 open.
2. **Records touching non-seed questions:** E876/E884 moved Q289's both-fields clause into Q206
   (sgx-pipe refuses a U1 that moves both axes); E880 added a note to Q023 (tag-5 word = OR of o0
   and o3); E872/E879 narrowed Q230's 1/w clause (H-FRAC held 117/117, H-MANT 72/72, the 106
   RZ+1 mantissas above half an ulp have no rule); E874's block-level replay (steps, bursts)
   bears on Q103 [infer]; E891/E892 (replay through the list current at the next TA run) touch
   Q076's requestor-directory text. `xref.txt`: the only newer records a question's evidence does
   not list are E877 for Q100 and E831 for Q291 (plus the E6xx vector records, as in round 6).
3. **Q142 is decodable offline, and the "why the same count" clause is already visible in the
   kept dumps** (`q142_rgn.out`, E504's `isp/msaa-te-dumps`, [data] for the counts, [infer] for
   the reading). From TA-data dword 4096 the TA writes 3-dword entries (a word with a 2-unit
   x/y position and flags, a pointer, 0): 72 non-zero dwords at CR_TE_AA 0x20000000, 144 at
   0x60000000 and 0xa0000000, 288 at 0xe0000000 (64 x 64, mode 2; mode 0 and mode 2 identical,
   0 of 1150976 + 6144 dwords differ at 0x60). With bit 30 the position field that steps 0, 2,
   4, 6 in the 0x20 job steps 0 to 7 (twice the entries along one axis: E504's "0x00000002 ->
   0x00000001" at 4108 is that field); with bit 31 the other field does (0x00020000 ->
   0x00010000 at 4099, and new entries point to new blocks 0x2400, 0x2480, ...); with both, both.
   The 76 parameter-buffer dwords are the 32-dword control-stream blocks the added entries open
   (an object word 0x4688000f/0x46880007/0x4690ffff/0x4688000e, 0x0c000407, a mask word, then
   0xc0000000 fill) and the reshuffled object words of existing blocks (`q142_diff.out`). So
   0x60000000 and 0xa0000000 change the same number of dwords by different values because on a
   square target they double the region grid along different axes [infer, one size]. Seen: the
   0x60/0xa0/0xe0 jobs at 64 x 64 (all of their TA data, the first rows of their parameter
   diffs) and the first 6 lines of the 128 x 128 0xe0 parameter diff; **not seen: the 128 x 128
   0xe0 TA data (367 changed dwords) and the rest of its parameter diff: a held-out set exists.**
4. **Q260's tile-relative reading is refuted offline (post hoc).** H-TILEREL (each coordinate
   rounded half away from zero relative to the origin of the tile being drawn, i.e. half up in
   tiles at or before it and half down in tiles after it) on E683's 240 S3 cases: 73 to 76
   inexact, 112 to 117 wrong pixels for tiles 16 x 8 to 64 x 64, worse than global HA (67, 101);
   and it breaks E681's positive ties (S2: 6 to 14 of 588 cases inexact, 58 to 201 pixels, where
   HU and HA are exact) (`q260_tilerel.out`). Control that could fail and did not: the script
   reproduces E683's HU 288, HA 101 and HD 142 pixels exactly. The offline routes Q260's text and
   E683's post hoc scripts name are now spent; Q260 needs its sweeps.
5. **TEXTYPE 5 does not read the texel tags at 16 x 16** (`q178_type5.out`, E567's kept rt5-*
   dumps, [data] 3 of 3 jobs, one pixel hash): every row stores 0 at x mod 16 = 0..7 and
   0x0000ffff at 8..15, the same under smp2d and smp3d at w 0.5 and 1.5; none of 2048 pixels
   holds a 0xD000xxxx tag, where types 1, 3, 4 and 7 return tags. E567 recorded only "2 distinct
   values". [infer] Type 5 is not a layout of the dword texels: the value is a function of u
   alone (a compare or a per-half constant), so Q178's "to settle it" (a map texture at 8 to 64)
   would read nothing; the row below adds a memory control.

## 1. Candidates beyond the seeds, ranked

Format: question(s); records; offline status; rows, risk; what it closes; sim gain.

**R7-1. Q142 (ta, medium; offline only; 2 crate cites, `sgx-pipe` render.rs:96 refuses every
CR_TE_AA other than 0x20000000).** Records E504, E503, E281, E728, E888. Offline: freeze a TA
model before opening the held-out dumps: H-GRID, "bit 30 halves the region's extent in y and bit
31 in x (one region per position unit in place of two), the TA lists each region the triangle
covers in the finer grid, the header word's position field counts in the finer unit, blocks
are opened in entry order at 0x80-dword steps of the pointer"; fit on the 64 x 64 0x60/0xa0
jobs (already seen), scored dword for dword on te-m2-e0-128x128 (TA data 367 changed dwords,
parameter buffer 805) through sgx-pipe's TA writer with the region unit a parameter. Rival frozen
beside it: H-HALF (the fields are the same regions with coordinates halved, no new regions;
refuted on 64 x 64 already by the entry count, kept as the control that the scorer can fail).
Refutes H-GRID: any changed TA-data dword at 128 x 128 off the model, or a block opened at a
pointer the model does not give. Zero jobs, 2 to 3 hours (decoder of the header word's fields,
then the writer). Closes: Q142's layout and its "why" clause on a held-out size [held out] ->
retire candidate; the window of E503 (which samples are stored) stays Q030/Q089's. Sim gain:
`sgx-pipe` admits CR_TE_AA bits 30/31 on the TA side (vectors of the 14 dumped jobs).

**R7-2. Q262 + Q240 (isp, medium; Q240 is refused in 6 of 9 first-triangle fixture scenes and in
`isp.rs` for every target outside E606's three and E680's ten).** Records E606, E607, E680,
E681, E682, E885 (odd heights). Offline: nothing left (E680's ten targets are coverage only; no
depth dump at those sizes). Laptop, current boot or one-shot of the installed kernel, tool t6:
(a) Q262: E606's D jobs (tri with a depth dump, vertices on the 1/256 grid) on 512 x 256, 640 x
480, 1024 x 768 and 2048 x 1024, 12 small + 12 medium each with a gradient below 0.03 (E606's 3 U
class) and 6 iterated clip-z probes each (4 U), plus 4 jobs at 4096 x 4096 dumping one window
(the 64 MB buffer is not kept whole) [check `--depth-dump` can write a window, else crop on the
laptop before gzip]; ~124 jobs. (b) Q240's family, colour and depth: 64 x 128, 128 x 64, 256 x
64, 128 x 96, 128 x 144 (the fixture sizes), 32 x 16 and 16 x 8 (below a tile; [check by one dry
job each that kernel and tool take them]), 4096 x 16, odd heights 64 x 33 and 96 x 47; 12 small +
12 medium each; ~240 jobs. Frozen predictions: coverage by E606's rule (`isp::coverage_image`,
the envelope check lifted in a scratch build: `CARGO_TARGET_DIR` in the session dir), depth
within E606's tolerances, the ZLS layout by `zls.rs` (band rule A at odd heights, E885).
Controls that can fail: two E606 cases rerun with their kept image and depth hashes (64 x 64,
256 x 128), and E680's 1024 x 768 case 1 rerun (colour hash). Stop: two unparsed outputs in a
row, any fault (none expected: 0 in E606/E680's 3700 jobs), free space below 200 MB. Risk:
lowest class (tri jobs; the depth dumps are E831/E885's form). ~364 jobs, ~30 min at E680's
pace [infer: about 5 s a job with markers and gzip]. Closes: Q262 retires if every target holds
(a held-out answer on its own sizes); Q240 narrows to odd widths (tool refuses: PBE stride,
planner a's Q287 seed) and sizes past 4096, or retires by a decision that the rule is
size-independent inside 16..4096 even widths [infer] (decision 3). Sim gain: `isp.rs` admits
depth on E680's ten and the family; the 6 refused fixture scenes become checked.

**R7-3. Q260 (isp, high; the simulator refuses a negative coordinate with a sub-grid fraction).**
Records E683, E607, E681, E684; finding 4 (offline route spent). Laptop, same session as R7-2,
tool t6 with 1/4096 vertices (`--tri-unit`/`--tri-v`, E683's form): the sweeps of the question's
own text, frozen before the run: one vertex at -0.5, -3.5 and -64.5 pixels, 17 steps of 1/4096
across the tie (-8..+8), on x and on y, edge aimed at a pixel centre one pixel and 100 pixels
away (3 x 17 x 2 = 102); the positive mirror at +0.5 and +64.5 (68); the far-side mirror at x =
W + 0.5 and y = H + 0.5 (34); 24 cases with exactly one non-tie negative coordinate. ~230 jobs,
~20 min. Frozen rivals: HU, HA, H-T7 (threshold 7/16, E683's best post hoc), "setup offset" (the
rounding acts on the coordinate plus a fixed offset of the clip-to-window step, fitted on the -0.5
sweep only, scored on -3.5/-64.5 and the y axis). Fit vs held out: x sweeps at -0.5 fit, all
others held out. Control that can fail: the positive mirror under HU (E681 says exact; a miss
there means the tool or setup moved). Refutes all: no rival exact on the held-out sweeps; the
sweep then still gives the per-step table the simulator needs (narrowing). Risk: lowest class.
Gain: a rounding rule for negative coordinates in `isp.rs` (high value: every clipped scene with
a vertex left of or above the target is refused today).

**R7-4. Q283 + Q178 (texture, low; both "Status: open" with a generator in hand).** Records E725,
E567, E726, E844; finding 5. Laptop, same session, the p1141/p1132 map-texture fills (64 x 32
fill, dword i = 0xD0000000 | i): Q283: types 1 and 3 at widths 4, 64 and 128 (frozen "raster w",
held out), type 4 at 4, 64, 128 (frozen rivals "stride 32" and "stride max(32, w)"; at 64 they
differ), and a 128 x 64 fill for type 4 at 32 to separate the type from the 64-column window
(E725's own caveat); non-power-of-two widths only if the T0 size field takes them [check the
generator]; 12 jobs. Q178: type 5 at 8 x 8, 32 x 32, 64 x 64 (frozen H-STEP: 0 where u's texel
column is in the lower half of the width, 0x0000ffff in the upper, constant in v; fitted on the
one 16 x 16 image, so held out at every other size), and two memory controls at 16 x 16: the
texture zeroed and the texture all 0xffffffff (H-STEP predicts no change: if the image follows the
memory, type 5 reads it); 5 jobs. Risk: E725's 12 and E567's 15 risky jobs ran without a fault,
health after each (as tx-types-risky). ~17 jobs, ~3 minutes. Closes: Q283 retires if the strides
hold at 4/64/128 [held out]; Q178 narrows to what the step is (a compare, a format) or retires as
"type 5 is not a layout" by decision (decision 5).

**R7-5. Q206, the both-fields U1 clause only (transfer, medium; 1 crate refusal path).** Records
E876, E884, E126. Laptop, same session: 8 fills at 128 x 64 with the end-of-tile task's U1 x and
y fields poked together (x^0x10 with y^0x1000, y^0x2000; x^0x18 with y^0x3000; four more pairs),
frozen H-INDEP (each axis placed by E884's OR rule independently; hashes from `sgx-pipe xfer`
with the both-axes refusal lifted in a scratch build), rival H-XFIRST (only the x field acts
when both move) [infer: the only other reading the single-axis data allow]; control: E884's
128 x 64 x^0x10 case (hash known, can fail). Risk: lowest class (1536 + 20 fill pokes of these
fields, no fault). ~10 jobs, 1 minute. Closes the clause (Q206 itself stays open: an umbrella);
sgx-pipe stops refusing those scenes.

**R7-6. Q190 (isp, medium; needs a kernel change and a new background program; recommended for a
later round).** Records E590, E209, E069. Change (linux fork, test first): a debugfs knob
`render_bg_layer` (0600, default 0); at 1, `sgx_render_bgobj()` builds the 23-dword one-layer
form with `sgx_xfer_bgobj_copy()` over the render rect, the layer's source a scratch texture the
tool names, and the `bg` kpoke space (`sgxfive_kpoke.c:64`) reaches 23 dwords instead of 17.
KUnit: knob 0 leaves the object byte-identical to today's 17 words; knob 1 equals the copy's 23
words for the same rect; the poke parser refuses bg:17..22 at knob 0 and accepts them at 1;
`XB_BG` (sgxfive_debug.c:67) already holds 4 x 23 bytes. Userspace: the render's background PDS
words must be a program that samples the layer (the copy's), or no coordinate word is ever read
and the rows cannot tell [check: E590's object had no layer, so its program never iterated].
Rows: E590's bg:N pokes on words 3 to 22, ten values each, coordinates first, ~40 jobs, low
risk. Delivery: `tools/fork/deliver-module.sh`, `push-gma500.sh --ko`, one-shot boot, srcversion
check. Not this round unless the user approves kernel work and planner b/c already need a boot.

Not picked, close behind: Q053 (E708's per-tile g18/g21, offline fit, weak); Q284 (cube faces'
(s, t), an E844-style fill; a good later row); Q261 (needs a tool option above 2^30 units);
Q101/Q242/Q243 (ZLS integer formats; safe rows but each needs a new depth ramp); Q271 (forced R
rows: N = 11 R = 3; vertex tooling exists, a later row); Q103 (see section 5).

## 2. Sessions and the offline package

**Offline (Mac, worktrees, `git commit -- <paths>`):**
- O1 Q142 (R7-1): decoder + H-GRID frozen by hash before te-m2-e0-128x128 is opened; then score.
  2-3 h. If held: a record (offline, held out on one size) and the sgx-pipe change test-first.
- O2 Notes, no runs: Q260 (finding 4, post hoc refutation, a dated note); Q178 (finding 5,
  [data] from E567's kept dumps, a dated note; no E567 correction needed: it says "2 distinct
  values", which stands).
- O3 Text (section 5). An hour.

**Session `r7-geo` (current 41E2F5C7 boot, or a one-shot boot of it; no kernel change):** R7-2
(~364), R7-3 (~230), R7-4 (~17), R7-5 (~10): ~620 jobs, ~55 minutes of runs, ~75 with staging
and health. All lowest-risk classes; no planned fault. Order: R7-5 and R7-4 first (short,
riskiest of the four: texture types 4/5), then R7-2, then R7-3. Run it **before** planner c's
fault rows (Q003 resets: -110 after held resets in E848 and E892), since a wedged boot ends at
the distro kernel and every later row then needs a new one-shot boot. Builder checklist (round 6
slips): every runner file staged and the staged tree mock-run under `env -i`; dump dirs created
by the runner (`mkdir -p` before `--depth-dump`); the scorer's REQUIRED-files list checked
against the keep list; controls frozen from jobs of the stage's own shape; free-space check per
job under `~/scratch/<prefix>/`; the sgx-pipe prediction builds in the session dir, never main's
`target/`.

**Kernel (only if the user approves kernel work this round):** R7-6 (Q190) as one test-first
commit in the same series as planner b's ldr-register change (oomring2) so the round needs one
cachix build and one one-shot boot. My recommendation is to defer it (decision 6).

## 3. Ranking of all 166 (tiers; `tiers7.out` lists every id once, checked complete)

- S, round 7 seeds (planners a, b, c; 11): Q003 Q086 Q111 Q139 Q210 Q211 Q276 Q287 Q291 Q293 Q294.
- R7, picked (8): Q142 (offline), Q262 Q240 Q260 Q283 Q178 Q206 (r7-geo), Q190 (kernel, later).
- F, text (7): Q230 Q100 Q103 Q146 Q194 Q030 Q141 (section 5).
- O, offline narrowing on kept data (21), best first: Q053 Q288 Q200 Q280 Q282 Q078 Q163 Q075
  Q012 Q008 Q177 Q261 Q125 Q107 Q070 Q074 Q290 Q284 Q179 Q089 Q082.
- K, need a kernel change (8 + Q190): Q108 Q109 Q095 Q068 Q049 Q193 Q064 Q076.
- H, safe hardware rows for a later session (76): round 6's H list less Q240/Q262, plus Q071
  Q046 Q054 Q098 Q136 Q183 Q271 (their text work is done; rows remain).
- X, hangs, faults or new tooling (22) and P, parked (13): unchanged from round 6.

## 4. Kernel change vs boot, per item

| Item | Runs on | Kernel change |
| --- | --- | --- |
| R7-1 Q142 | Mac only | none |
| R7-2 Q262/Q240, R7-3 Q260, R7-4 Q283/Q178, R7-5 Q206 | now, or one-shot of 41E2F5C7 | none |
| R7-6 Q190 | one-shot boot of a new module | `render_bg_layer` knob + 23-dword bg kpoke |
| Q108 (next) | new module | a switch for WRITEONLY/CACHECONSISTENT/EDMPROTECT on one PTE; faults |
| Q109, Q095, Q068/Q049/Q064/Q076, Q193 | as round 6 section 4 | no this round |

The 0x0694 peek (db7faabc) and bif_flush (3f0b3e74) are planner c's; render_tail_room is
planner a's. None of my rows uses them, so they run on any boot of 41E2F5C7.

## 5. Retire, fold and merge candidates (with the records)

- **Q142 retire** after O1 if H-GRID holds held out (answered by the new offline record; E504's
  data). If it fails: narrow to the parameter-buffer half.
- **Q262 retire / Q240 narrow** after r7-geo (answered by the session's record; E680's coverage
  stands). Q240's retirement beyond the run sizes is decision 3.
- **Q283 retire** if the held-out widths hold (E725 + the new record).
- **Q178 narrow or retire** on finding 5 + the r7-geo type-5 rows (decision 5).
- **Q100: cite fix**, add E877 to its evidence (E877 names Q100, `xref.txt`); no text change.
  (Q291's uncited E831 is planner a's.)
- **Q103 fold into Q211, later**: both ask the partial-render count (Q103 for 100 to 500
  triangles, Q211 for one triangle); E874's block-level replay (steps, bursts) is the shared
  model [infer]. Fold when planner b's count rule lands, not now.
- **Q230 split** (19 KB, "Status: open" since E776): six clauses with separate evidence and
  tools (clip order of 3 or more than 4 vertices; region limits at the edge; the 1/1024 -> 1/256
  tie; depth word at w != 1; the 1/w RZ + 1 set of 106 mantissas, E872/E879; made vertices and the
  clamp; the sub-pixel size). Split into at least "1/w RZ + 1 mantissas" (offline, numeric) and the
  geometry clauses, so the numeric one can retire when a rule is found.
- **Q141 and Q030 touch Q142**: Q141's background pixels with bits 30/31 in mode 1 may be a region
  the finer grid leaves unlisted [infer]; recheck both after O1, no change now.
- **Q146 / Q194**: no new record; round 3's "do not merge" stands.
- **Q023**: E880's note is in; the question stays (no change).

## 6. User decisions

1. **Q142 offline decode (R7-1).** a) Freeze H-GRID (and the H-HALF control) on the seen 64 x 64
   jobs, score on te-m2-e0-128x128 unseen, record + sgx-pipe change if held (recommended);
   b) a dated note of finding 3 only; c) leave it.
2. **Session r7-geo (current boot, no kernel change).** a) R7-5 + R7-4 + R7-2 + R7-3, ~620 jobs,
   ~75 minutes, run before planner c's fault rows (recommended); b) R7-2 + R7-4 + R7-5 only
   (~390 jobs, ~40 minutes; Q260 waits); c) R7-2 only.
3. **Q240 after a clean r7-geo.** a) Narrow to odd widths (the tool refuses) and sizes past 4096,
   the simulator admitting the run sizes only (recommended); b) retire by a decision that the rule
   is size-independent for even widths 16..4096 [infer], the simulator admitting all of them;
   c) keep the text as is.
4. **Q260 frozen rivals.** a) HU, HA, H-T7 and "setup offset" fitted on the -0.5 x sweep only,
   all others held out (recommended); b) HU and HA only (simpler, likely "none fits" again).
5. **Q178 after the type-5 rows.** a) If H-STEP holds and the memory controls show no read,
   retire Q178 as "type 5 is not a texel layout" and open nothing (recommended); b) reword Q178 to
   "what is type 5's step" and keep it; c) no type-5 rows, a dated note of finding 5 only.
6. **Kernel work for Q190.** a) Defer: note the `render_bg_layer` knob as the next kernel item
   with Q108 (recommended: it needs a layer-sampling background program as well); b) add it to
   planner b's series for this round's one-shot boot.
7. **Text package.** a) Q100 cite fix (E877), Q230 split, Q260 and Q178 dated notes, Q103 fold
   noted for later (recommended); b) cite fix and notes only; c) none.
