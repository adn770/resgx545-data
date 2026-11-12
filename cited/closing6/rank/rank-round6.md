# Round 6 ranking: what is closable now (Opus, 2026-11-12, read-only)

Basis: resgx545 `main` c3a0591 (d3de0b1 + the HACKING scratch rule), 170 open (160 hw, 9 fw,
1 kernel), records to E869; data 87857a48; linux fork branch `resgx545` tip a2788bd8 (read with
`git show`). Laptop: rgn4 boot (99CD90DA), tool `~/sgxfive-test-rgn4` e6951558 built from
4623753. Model: `closing4/rank-round4.md`. Excluded (round 5 seeds, other planners): Q292, Q293,
Q276, Q230, Q210, Q211. Kernel work is approved (BRIEF-COMMON, appended section): section 4.

Scratch in this directory (all read-only analyses, publishable, no firmware-derived content):
`index.py`/`index.txt`, `digest.py`/`digest.txt`, `xref.py`/`xref.txt` (round 4's scripts,
rerun), `tiers6.py`/`tiers6.out` (all 170 placed once, checked), `eot_sweep.py`/`.out` and
`eot_hash.py`/`.out` (Q289), `q289_predict.py`/`.out` (draft held-out table), `q139_tiles.py`/
`.out` (Q139), `q287_cells.py`/`.out` (Q287). Every offline conclusion below is [infer] unless
it names a held-out check; post hoc is said where it applies.

## 0. Findings that change the plan (read first)

1. **Q289 is decided offline on the fill, post hoc, to the hash.** The two kept sweeps of the
   fill's end-of-tile DOUTU1 x field (bits 11:3, 512 cases) and y field (bits 21:12, 1024 cases)
   (`resgx545-data/pds/end-of-tile/values-doutu1-{x,y}/raw.txt`) give four outcomes only, every
   job `ok`, `outside: 0` in all 1536 (`eot_sweep.out`): field bit 0 changes nothing, field bit
   1 leaves half the target 0xdeadbeef (x: a column, y: a row), any higher bit leaves all of it.
   Reading the fields in **half-tile units** (16 pixels in x, 8 in y), each 32 x 16 tile stored
   at ((2 t) | f) >> 1 (or + in place of |) and **nothing stored when that lies outside the
   target**, reproduces the tool's FNV-1a image hash (`sgxfive_hash_dwords`, poke.c:127) of all
   four classes in both sweeps, 8 of 8 class checks, 1536 of 1536 cases; XOR fails 4 of 8
   (`eot_hash.out`). This is the rule Q289's own text names as the first test. It is post hoc on
   both sweeps (I read both before fitting), so it needs a held-out row; on 64 x 32 OR and ADD
   cannot be told apart. A larger fill separates them (`q289_predict.out`: at 128 x 64, x^0x10
   leaves columns {0, 2} under OR and {0} under ADD). Value: sgx-pipe `xfer` refuses these 1534
   scenes today (cited to Q206, `crates/sgx-pipe/src/xfer.rs:52`, `tests/scene_vectors.rs:113`).
2. **Q139's 67 kept wrong images are wrong in whole tiles, 67 of 67** (`q139_tiles.out`: 8 in
   `ta/mtile-fields`, 59 in `ta/mtile-fields-risky`, every tile with a wrong pixel wholly wrong,
   no partial tile; 162 dumps of faulted jobs carry no image). So the "per-macrotile map" step
   of Q139 is a set test over tiles and needs no new data [data for the count; the macrotile
   assignment is not yet fitted].
3. **Odd heights are in `main` but not on the laptop.** a6d78db (2026-11-11 19:13, "libsgxfive:
   allow odd target heights") postdates 4623753, the source of the laptop's rgn4 tool, so Q287
   needs a tool rebuild and push (`tools/bringup/push-tools.sh`, image name now the build host's),
   not a kernel change; odd widths stay refused (render.c:395, the PBE stride in 2-pixel units).
   Along y alone, heights 7, 11, 19, 23 and 35 separate rule A from FLOOR inside the tile area
   (`q287_cells.out`); ROUND equals A there and CEIL is already refuted (E831).
4. **Kernel-enabled candidates exist but few pay this round** (section 4): a one-register
   debugfs peek for 0x0694 (the rgn4 regs file lists it as `skip`, so E855's DPM_TASK_STATE row
   was "cannot tell"), and a BIF-flush step before the held-fault reset for Q003's replay. Both
   are small, test-first fork commits that can ride the render4x planner's tail-room boot (one
   test boot for the round).

## 1. Candidates beyond the seeds, ranked

Format: question; records; offline status; laptop rows and risk; sim/spec gain.

**R6-1. Q289 (transfer, medium; with Q206's refusals).** Records E620, E126, the two sweeps
above. Offline: done as a fit (finding 1), post hoc. Laptop: one held-out fill row, frozen from
`q289_predict.out`: 128 x 64 fill, x pokes ^0x8 .. ^0x40 (8) and y pokes ^0x1000 .. ^0x8000 (8),
256 x 32 x pokes ^0x10, ^0x18, ^0x30, ^0x50 (4 that separate OR from ADD), baseline at each size
(2) and a repeat of the 64 x 32 ^0x10 case (control that can fail: its hash 0x97334f75829dab25
is known). ~23 fills at ~0.3 s each, about 2 minutes with staging. Risk: lowest class (1536
fill pokes of this field ran with no hang or fault; the 12 hangs of E620 are data-word pokes,
not run here). Refutes: any hash off both models, or an `outside` above 0 (a store outside the
target). Stop: two missing or unparsed hashes. Gain: sgx-pipe `xfer` takes the U1 tile rule and
stops refusing ~1534 scenes; Q289 retires on the fill and copy if E126's exchanges also fit
(offline check after the row), else narrows to the copy.

**R6-2. Q287 + Q291 (zls, low; 21 crate cites in `zls.rs`).** Records E730, E831. Offline: the
cell table (finding 3); nothing more to read. Laptop: new tool (a6d78db) pushed under a new name
(`~/scratch/<prefix>/sgxfive-test-r6`, the rgn4 tool kept), then the g-z runner of
`render/closing-r3-geo-c` reused at W 34: fit H 19 (the question's own .75 cell); held out H 7,
11, 23, 35; confirmations H 17, 21 (.25: A = FLOOR); control 34 x 18 (E831's exact set, can
fail); two runs each, 20 depth-dump jobs, ~3 minutes. Q291 (same session): the pixel probe that
stores each instance's iterated clip x to scratch (`--pixels`, as E606) at 34 x 19 and 34 x 23
and 34 x 18, reading the pixels of the tile area past the target (rows 19 to 31): predicted the
depth band's rows [infer: a guard-band clip, E730 "what it shows"]; 6 jobs. Risk: low (tri with
depth, no fault in E730/E831's 27 jobs); the only new thing is an odd height on rgn4 (the module
has no odd-size test, `git grep` of the fork [check by a dry 34 x 17 job first]). Refutes A: a
.75 cell storing floor(1.25 H) rows. Gain: zls.rs stops refusing odd heights; Q287 narrows to odd
widths (tool cannot) or closes on y with x by symmetry [infer] (decision 3).

**R6-3. Q139 + Q100 (ta, medium; offline only).** Records E505, E506, E509, E407; data
`ta/mtile-fields{,-risky}` (images kept in `dumps/`). Offline: freeze the four-boundary reading
(B1, B2, B3 and the stride place each tile's macrotile; a wrong image is the union of the
macrotiles whose lists were dropped or misplaced) on the 8 safe images, score it on the 59 risky
images with their fit/held-out split (`cases.tsv`: 211 fit, 12 held out). Refutes: a wrong-tile
set that is no union of the frozen macrotiles. Zero jobs. Gain: `ta.rs` macrotile words (Q100
crate 5, Q139 5), and E509's PA/PB/PC misfits get a per-tile reason.

**R6-4. Q086 (ta, medium).** Records E507, E511, E824. Laptop: E511's 20 skipped 4x cases (H86i
and the poked U2, U2Q, HS, FX families at 320 x 160 to 640 x 480) plus the 1024 x 768 R job, on
contexts made for 4x targets (rgn4 tool, E824's words), all at or below 1024 x 768 where E824
completed 8 of 8; HS last, fault budget 3 (E511's HS faults read 0x1000001x, the 0x90100 class
after which the next health triangle passed 3 of 3 in E848). 21 jobs + health after each fault,
~10 minutes. Gain: the te macrotile rule at 4x for `ta.rs` (narrowing; the closed driver's rule
over sizes still needs the capture batch). Interaction: the render4x planner's kernel change
(tail room) touches only contexts above 1024 x 768 [check with that planner]; run Q086 on the
rgn4 boot before the test boot so its rows read the landed kernel.

**R6-5. Q003, the replay clause (transfer, medium; 24 crate cites).** Records E767, E826, E848.
E848's FAILED h4 was read after the run as "the replay goes through the directory list current
at the next TA run" [infer]. Offline: freeze that as H-LIST and, as its rival, H-WORD (E848's
frozen word test). Laptop, two variants: (a) no kernel change: a 288 x 144 4x job on one array
(`render_rgn_arrays` 1, E828's forced fault, 0x90004), held, reset, then a fill (list 1), then a
health triangle (predicted fault at the failed page with list 2 under H-LIST), then a second
health; 3 cells x 1 = 3 faults + 6 health jobs. (b) with the kernel change K2 (section 4): the
same with a BIF invalidate written between hold and reset, frozen H-FLUSH (no replay) against
H-PEND (the replay as without it). Risk: medium; E848 saw "SGX recovery failed: -110" after 3
of 4 held resets on this boot, and the health triangles after 0x90004 fail before one passes;
budget 3 faults, stop on two -110 in a row or a health that does not pass within 3 tries. Gain:
the recovery contract (what clears a latched fault) in `doc/specs` and the sim's fault model.

**R6-6. Q294 (edm, low) with Q111's 0x0694 row.** Records E537, E812, E814, E855-E857; R-6 and
the pysgx S0 oracle (closing5/r6, data-private). Offline first: run the S0 oracle (labelled
assumptions as in S0) with sa65 = E814's word and the word with each of bits 4, 7, 10 cleared
alone and in pairs (7 oracle runs), frozen before the run, outputs to data-private only; the
oracle predicts which words stop the tick. Laptop (only if the oracle separates): E814's writer
with the same 7 words + E812's keeping control, ~8 jobs, each stop recovered by the debugfs
reset as in E814/E855 [check that E814's writer passes the rgn4 verifier]. With kernel change K1,
one b1p stop (E855's row) read with the 0x0694 peek: R-6 predicts DPM_TASK_STATE 2 [RE]. Risk:
tick stops are the known recoverable kind (E855: 3 of 3 recovered). Gain: the EDM tick contract
for the fw compiler; Q294 is low value alone, the oracle check is the cheaper half.

Not picked, close behind: Q142 (decode E504's 76 + 132 changed dwords against the four-array
layout, offline; it shares dumps and layout work with the Q293 seed, so the render4x planner
should take it if it wants it); Q271 (arithmetic only: no natural job has R x V of 34 or 35, so
the sim refuses above 33 and the question narrows to forced R; text); Q053 (g18/g21 per tile from
E708's 32 tiles, offline fit, weak); Q082 bit 6 (E841 refuted the segment rules; no offline route
left that I can see).

## 2. Sessions and the offline package

**Offline package (no laptop, Mac, worktrees, `git commit -- <paths>`).**
- O1 Q289: freeze the held-out table (OR and ADD both, controls named), then fold E620/E126's
  exchanges as a second offline check; the fill result as a record only after session A.
- O2 Q139: four-boundary set test, frozen on the safe dataset, scored on the risky one.
- O3 Q294: S0 oracle runs (data-private; the lead's reading process, Sonnet-able).
- O4 Q003: H-LIST / H-WORD / H-FLUSH frozen text for session B.
- O5 Text (section 5): merges and narrowings, no record changes beyond dated notes.
Wall: O1 and O4 under an hour each; O2 2-3 hours; O3 up to the 2 h box S0 used; O5 an hour.

**Session A, `r6-geo` (rgn4 boot as it stands, no reboot, no kernel change).** Q289 (23 fills),
Q287 (20 depth jobs) + Q291 (6 probe jobs), Q086 (21 4x jobs, HS last). ~70 jobs, ~25 minutes of
runs, ~45 minutes with staging and health. Needs a tool build on cachix (a6d78db and later, by the
lead) and a push under a new name; HACKING's `~/scratch/<prefix>/` rule and free-space check per
job. Order: Q289, Q287/Q291, then Q086 (the only fault rows), health after every fault.

**Session B, `r6-recovery` (on the round's one test boot, shared with render4x's tail-room
kernel).** Kernel changes K1 + K2 (section 4) in the same fork series as render4x's. Q003 (a) and
(b): 6 fault jobs + ~12 health; Q294's ~8 tick-stop jobs if O3 separates; E855's b1p stop with
the 0x0694 peek (2 jobs). ~28 jobs, ~40 minutes with the boot check (srcversion vs the built
module, `boot-test-kernel.sh`, no GRUB change); fault rows after render4x's own rows or in a
separate slot the lead orders. The next reboot returns to stock Arch either way.

## 3. Ranking of all 170 (tiers; `tiers6.out` lists every id once, checked complete)

- S, round 5 seeds (other planners, 6): Q210 Q211 Q230 Q276 Q292 Q293.
- R6, picked (9): Q289 Q287 Q291 Q139 Q100 Q086 Q003 Q294 Q111 (0x0694 row only).
- F, text (13): Q274 Q183 Q244 Q071 Q046 Q054 Q136 Q098 Q178 Q283 Q271 Q146 Q194 (section 5).
- O, offline narrowing on kept data (26), best first: Q142 Q053 Q260 Q288 Q200 Q280 Q282 Q078
  Q163 Q075 Q012 Q008 Q177 Q261 Q125 Q107 Q070 Q074 Q206 Q103 Q290 Q284 Q179 Q089 Q082 Q030.
- K, need a kernel change (9): Q190 Q108 Q109 Q095 Q068 Q049 Q193 Q064 Q076 (section 4).
- H, safe hardware rows for a later session (72): isp Q066 Q199 Q202 Q205 Q240 Q241 Q262 Q201
  Q032 Q073 Q141; ta Q231 Q159 Q160 Q161 Q162 Q164; zls Q120 Q121 Q242 Q243 Q101; pbe Q044 Q040;
  pds Q023 Q207 Q019 Q020 Q027 Q057 Q058 Q060 Q062 Q013 Q024 Q026; usse Q050 Q051 Q052 Q055 Q123
  Q126 Q127 Q129 Q130 Q132 Q133 Q134 Q135 Q137 Q143 Q195 Q016 Q017 Q080; edm Q196 Q158; vdm Q112
  Q092 Q042; mte Q069 Q039 Q116; render Q043 Q065; platform Q001; texture Q104 Q114 Q115 Q010
  Q181; transfer Q011.
- X, hangs, faults or new tooling (22): Q165 Q272 Q047 Q036 Q038 Q045 Q081 Q191 Q192 Q110 Q014
  Q025 Q059 Q275 Q096 Q031 Q072 Q093 Q002 Q033 Q180 Q128.
- P, parked (13): fw Q004 Q029 Q034 Q084 Q088 Q118 Q119 Q277; other hardware Q063; capture batch
  Q099; trc_hazard Q168; clock-gate writes Q048; deny-list writes Q154.

## 4. Questions a kernel change would make closable (approved this round)

- **Q111 (E855's row), K1, this round (session B).** Change: debugfs `peek` (0600): write an
  offset, read one MMIO value, from an allow list of skip-listed firmware registers holding
  0x0694 only, refused while no firmware runs. Test: debug_test (the list refuses 0x0690 and the
  host-write registers); laptop read at an idle EDM, then at a b1p stop. Value low-medium; risk:
  a read of a register the regs file never reads (the "starts work" class, regdump.c:12)
  [infer harmless: the firmware itself reads it, R-6].
- **Q003, K2, this round (session B).** Change: debugfs `bif_flush` (0200): while a recovery is
  held, write the BIF invalidate of `CR_BIF_CTRL` (the bits the kernel already uses on a map
  change) before the reset; no clock-gate write. Test: debug_test (refused when nothing is
  held); laptop rows R6-5 (b). Value medium-high (recovery contract, 24 crate cites); faults
  and -110 boots.
- **Q190, next round.** A `bg` kpoke space reaching the object's words past 17 (the 23-dword
  layered form), or a render-object switch; poke parse test, ~20 jobs as E590; low risk.
- **Q108, next round.** A switch setting WRITEONLY / CACHECONSISTENT / EDMPROTECT on one client
  buffer's PTEs; page-table unit test, fills and copies, faults expected (Q003 class).
- **Q109, no.** One directory entry with a larger page-size field over a table laid out for it;
  low value, faults.
- **Q095, no.** The EDM on gma500's default directory (`BIF_DIR_LIST_BASE15`); low value, boot
  risk.
- **Q068, Q049, no (own phase).** A context-switch path with a two-context test mode; large.
- **Q064, Q076, no.** Two contexts overlapped (the 3D slot's bit 1; a list handed over while a
  job runs); need the Q068 path.
- **Q193, no.** No fork change, a module reload sequence on the test kernel; low value.

K1 and K2 are each one small commit with a test, both in the render4x planner's series so the
round needs one cachix build and one one-shot boot. If the render4x plan does not boot, session B
runs Q003 (a) and Q294 on the rgn4 boot without K1/K2.

## 5. Retire, fold and merge candidates (from landed records)

No open question is fully answered by a landed record that its file does not already cite
(`xref.txt`: the only newer uncited records are E831 for Q291 and E833 for Q287, both notes, and
the E6xx vector records). Folds and merges, same unknown in two files:
- **Q274 into Q183**: both ask why E572's end-of-tile store fault does not reproduce in E707
  (module, tool, address immediate) and what faults E707's two 8-temporary programs at 0x1.
- **Q244 into Q071**: the same ZLS control bits (12, 15, 16, 20 to 23, 27 to 31); Q244 adds "in
  combination" and bit 0 under another control, which fit Q071's text.
- **Q046 and Q054, sideband bits 11 and 12**: the clause is in both; keep it in Q046 (pack-mode
  sweep) and drop it from Q054 (emit flags).
- **Q136's pa0 clause into Q098**: "why is pa0 not written by ima32 or mov" is Q098's lost `mov`
  to pa_n; Q136 keeps the sa0 lifetime and the left-over colour.
- **Q178 narrowed to TEXTYPE 5** (types 1, 3, 4 by E725; type 2 the cube by E726, held out by
  E844; strides are Q283, faces Q284), or merged into Q283 as "types 4 and 5".
- **Q271 narrowed** to forced R (finding in round 4's T2 list, still unwritten).
- **Q291 reword**: the band is past the target, so the attribute is read through per-instance
  scratch stores of the tile area's pixels (the `--pixels` form), not through the colour store.
- Q146/Q194: round 3 decided not to merge (pixel and EDM loads); no new record changes that.

## 6. User decisions

1. **Q289 route.** a) Freeze the half-tile rule (OR and ADD) from the post hoc fit and run the
   23-fill held-out row in session A, then E126's copy exchanges offline (recommended); b) record
   the post hoc fit as a dated note only, no row; c) leave it.
2. **Session A (rgn4 boot, no kernel).** a) Q289 + Q287/Q291 + Q086, ~70 jobs, ~45 minutes, tool
   rebuilt from main and pushed under a new name (recommended); b) without Q086 (no fault rows,
   ~50 jobs, ~20 minutes); c) Q289 only (no tool rebuild).
3. **Q287 scope.** a) Odd heights only; on a held A, close the y side and narrow Q287 to odd widths
   (the tool refuses them) (recommended); b) close Q287 with x by symmetry [infer]; c) also add
   odd widths to libsgxfive (PBE stride change, test first) and wait.
4. **Kernel changes for this round.** a) K1 (0x0694 peek) and K2 (BIF flush before a held reset)
   as two test-first commits in the render4x planner's series, one cachix build, one one-shot boot
   (recommended); b) K2 only; c) no kernel change beyond render4x's; Q003 (a) runs on rgn4.
5. **Session B (on the test boot).** a) Q003 (a)+(b) and the 0x0694 row, Q294 only if the oracle
   separates the words, ~28 jobs, fault budget 3, stop on two -110 in a row (recommended);
   b) Q003 (a)+(b) only; c) no session B.
6. **Q294 offline.** a) S0 oracle runs on 7 sa65 words, frozen, outputs data-private (recommended);
   b) skip; Q294 stays low.
7. **Q139.** a) Offline set test of the four-boundary reading, safe dataset fit, risky scored
   (recommended); b) defer.
8. **Text package.** a) Merges Q274 into Q183, Q244 into Q071, the sideband clause to Q046,
   Q136's pa0 clause to Q098; narrow Q178 and Q271; reword Q291 (recommended); b) merges only;
   c) none.
9. **Next-round kernel list.** a) Note Q190 (bg poke past word 17) and Q108 (PTE flags) as the
   next kernel items, no work now (recommended); b) add Q190's poke space to this round's series.
