# Round 12 ranking: old questions, unreplayed rules, stale lines (offline only; Opus, 2026-11-13)

Basis: resgx545 `main` de11aa3 (records to E1017, **154 open**: 144 hw, 10 parked), resgx545-data
ffd076572 as checked out, read only. Nothing staged, nothing run on the laptop, nothing built.

Scratch in this directory (all derived from published data and our own scripts, no firmware-derived
content, publishable; three `__pycache__` dirs in c2, c4, c6 were left by the helpers and should be
removed before a record cites the directory: my delete was refused by the permission system):
`index.txt`, `xref.txt` (round 11's scripts rerun on de11aa3), `unmodelled.py`/`.txt` (the 108
entries of `crates/SIM_UNMODELLED.toml` with claims), `HELPER-BRIEF.md` (round 11's freeze
protocol, renumbered), `survey/CANDIDATES.md` (old and parked questions: candidates, stale lines,
rejections), `simgap/SURVEY.md` (all 108 entries classed C/M/R/N, with groups and two ports),
and one directory per frozen check `c1-q036/`, `c2-q163/`, `c3-q107/`, `c4-q045/`, `c6-q201/`,
each with its rule, `.sha256`, `FREEZE.log` (UTC, hash, what was read before), scorer, `.out` and
`NOTE.md`. Helpers ran the checks on this brief; I read every NOTE and freeze log. Leaks before a
freeze are listed below where they exist.

Selection: 117 open questions have no record newer than E870 (untouched since round 5). The survey
read all of them plus the 10 parked ones against the data kept from rounds 1-7 and the 11.x
datasets; 7 had a clause with kept rows never used for its fit; 5 were frozen and scored (c5 Q164
is semi-held-out, E900 decoded those streams; c7 Q033 cannot see bit 19, `oomring2.s` masks it).

## 0. Findings (offline, read first)

1. **Q201: the position source and the coverage sample are CR_ISP_MULTISAMPLECTL byte 0's point;
   E606's "pixel centre" is byte 0 = 0x88** (`c6-q201/`, `sample0_rule.py` a1980fa5..., frozen
   before 254 of E064's 256 cases were read). On E064's sweep of cmd:16 bits 7:0 (64x64 triangle,
   `resgx545-data/isp/sample-positions/raw.txt`), SAMPLE0 (E606/E660 coverage, the sample at (low
   nibble / 16, high nibble / 16)) **held 256 of 256 pixel counts** (31 one-nibble values E064
   tabled: fit-ish; **225 two-nibble values held out**) and **the 27 predicted image classes equal
   the 27 observed hash classes**. Rivals: nibbles swapped 226/256 (2 of 27 classes), fixed
   (0.5, 0.5) 51/256, (n + 0.5)/16 197/256 (0 classes). Limits: counts and hashes only (no images
   kept), one triangle, one run; `diff:` is 0 throughout (not used). With E437 (x + 0.5 at 0x88)
   and E502/E1010 (x + 0.375, y + 0.125 at 0xeaa26e26, byte 0 = 0x26 = (6, 2)/16, E339), the
   "why do they differ" clause is answered [infer: the position source reads the same point the
   coverage does; no kept job iterates a coordinate set under byte 0 other than 0x88]. **Q201's
   question line is wrong about E437** (it reads x + 0.5, not + 0.375): a text fix. Refuted by: a
   byte 0 value whose count or class differs, or a position-source job under 0x88 off + 0.5.
   E064 needs an appended note (its "which nibble is x" is now named), no correction.
2. **Q036: STATUS2's high halves are 0 in every kept sample, up to 18 global pages**
   (`c1-q036/`, `q036_rule.json` 7be7002f..., frozen after reading only two files' heads).
   H0 (0x0710 bits 31:16 = 0 in every timeline line, 0x071c bits 31:16 = 0 in every after-read)
   **held on 697 timeline jobs (285824 lines, closing r1-r10, s1, s1b) and 1594 after-reads**,
   including **195 jobs whose global page count passes 5** (G 6: 104, 7: 79, 11: 3, 13: 5, 18: 4),
   the case Q036 says no record reached (E358, E443, E574, E626: at most 5 pages). Rivals H-TAIL
   and H-ANY refuted. All held out (no record read these fields there). Caveat: 0x071c only in
   after-reads, none for r8/r9-ldpm and r10-dpm. **0x0748 bit 2** (fit r1-r3, held out r5-r10,
   s1, s1b: 558 jobs): clears are rare (195 of 197136 lines); by log-loss R-PR (clears in
   proportion to the partial-render count) beats R-LEN, R-0x100 and a constant in both page
   splits (G <= 5: 199.5 vs 224.9 constant; G >= 6: 67.5 vs 114.1). That is a held-out ranking,
   not a pass rule: [infer] bit 2 follows partial renders, not length or page count. E443's "0 in
   every sample" extends to G 18: an appended note, no correction.
3. **Q163: E700's counter holds out on the 11.31 sweeps for v 3 to 7; the v < 2 clauses do not**
   (`c2-q163/`, `c2_rule.py` 1e6a9e12..., frozen before outcomes; leaks: the survey's per-script
   hang totals, E545's own outcome text, the first 28 outcome lines of state2-fields' report,
   which was then not scored). On `resgx545-data/vdm/state-units/` (133 jobs in run order from
   kernel.log markers; 28 excluded for E545's word causes, all 28 hung): **v 3..7 54 of 54 under
   M1 and M3 (13 hangs, every one needing history: the stateless null gets 41, "v in {1, 6}
   hangs" 37)**; units 12/12, risky 28/28, grid 14/14; v = 2 only 31/31; threshold 8 the only one
   with 0 misses (post hoc sensitivity). v < 2 (20 jobs): M0 14, M1 14, M3 17, M2 20 but M2 misses
   one v 3..7 job (`st-b1-b119-4-r2`: the v = 0 reset refuted a third time, after E701's two).
   Block-2 v = 1 hung in all 6 risky jobs, three at c = 5, and completed in grid `sg-v1-r4..r7`
   [infer: the grid's bits 7:0 explain it as well as c]. Assumes c = 0 at each script start
   (every script ends with a GPU reset). state2-fields/-consts unscorable (no run order, no
   per-case markers). Appended notes to E700 (held out on 54 more jobs) and E701 (M2's v = 0 reset
   and M3's block-2 v = 1 clause fail here); no correction (E701 called M0-M2 exploration).
4. **Q107/Q038: E996's store overlay holds at 1024x768 without overflow and fails in every
   overflowed job** (`c3-q107/`, `q107_rule.py` 8863d621..., frozen before any G = 1 dump's bytes
   were read; one file's length seen). Predicting each G = 1 depth dump of
   `dpm/partial-model-batch/dumps/depth-safe.c1`/`.c26` from the same cell's G = 33 dump (z05 at
   P 0x23, 0x28, 0x30; ramp at 0x28, 0x30; r1 and r2): **E996's last-visited-in-header-order
   overlay 0 of 10** (32201 or 51968 of 61440 decidable dwords; 60 or 101 of 120 slots), rivals
   (first visited, raster last, zero region fixed in slot space) 0 of 10 each. Bridge control:
   **E489's non-overflowed 1024x768 G 0/1/2 ramps x and y 6 of 6, every dword** (held out for
   E996, whose fit was 64x32 to 256x64). [post hoc] every G = 1 dump starts with 15104 zero dwords
   (slots 0 to 28 + 256) and then mostly repeats one tile, not the slot's owner: the overflowed
   final store is not the plain store overlaid. E996's claim is scoped to plain renders: an
   appended note (1024x768 held out; not overflowed jobs), no correction. Q107's "tile order" stays
   open for overflowed jobs; Q038 cites E996 and the new record.
5. **Q045 (b): "state page sum = last TA run's peak - 1" is not general** (`c4-q045/`,
   `a2_rule2.py` ba89c2b0..., a re-freeze after v1 crashed before printing a score). Of 91 raised
   closing jobs (r1-r7) the frozen form held 4, failed 87; but [post hoc] 62 of the 87 read an
   all-zero page where `dpm_raise.py` locates it (2048-wide dumps: data from 0x12000), so they are
   "cannot tell" [infer], and 5 r3 c5a rows hold another layout. On the 29 located pages: 4 hold,
   25 miss, mostly by 3 (sum 570 or 571 against peak 573 or 574 on the 4096 x 4096 1500-vertex
   scenes). No record holds the statistic (it is in Q045's text from the 11.38 batch, 48/48): a
   text note scoping it to the 11.38 scenes. Weak (locator problem): **no record recommended**.
   E900 opened 183 of these pages for another field (held out of A2, not unread).
6. **Stale lines and evidence lists** (`survey/CANDIDATES.md` section 2, checked by me where noted):
   - Q201's line misquotes E437 (checked: E437's title says x and y plus 0.5); see finding 1.
   - Q107: add E996, E977, E987, E997 and the new record; Q038 adds E996.
   - Q020: E440 (a second block's primary-program douta reaches sa0 in 24 to 270 of 978 pixels)
     answers "does a primary-program douta write sa at all" (partly, varying per run); E440, E545
     cite Q020 and are not listed.
   - Q168 + E603 (r0 to r123 real storage at trc 31); Q133 + E594 (T 132 to 192 read their own
     marker); Q135 + E597 (ima32 high word, 300 of 300, already in Q127's list); Q196 + E600
     (xor.testtanz in a firmware task, on rV); Q118 (parked) + E592 (the directory word sits in the
     list register the kick wrote); Q088 (parked) context E665, E997, E989, E1014. Cites only.
   - Q114 (volume textures): E567 ran TEXTYPE 0 to 7 (checked): only type 2 follows smp3d's third
     coordinate, and type 2 is the cube (E726, E923, E930); 1, 3, 4, 5, 6, 7 are 2D layouts
     (E910, E940, E941, E958; E894, E911, E942). **No TEXTYPE names a volume [infer]**: narrow to
     "whether another word names one" (retiring on negative evidence: R12-7 b).
   - Q146/Q194: round 11 tiered them "F (text: keep apart)"; nothing new: no change.
   - Mentions that are not evidence (E620, E650, E660, E664, E617, E522, E499, E448, E661 in
     `xref.txt`): refusal or "does not show" lines; no list change.
7. **Parked (10)**: nothing new decides any. Q088 and Q118 take cites (finding 6); Q095 weakly
   E592. Q004, Q029, Q034, Q049, Q084, Q119, Q277: nothing new.

None of findings 1 to 7 contradicts a landed claim. Appended notes proposed: E064, E443, E700,
E701, E996. Records proposed: E1018 Q201, E1019 Q036, E1020 Q107, E1021 Q163.

## 1. Retire / fold candidates, clause by clause

- **Q201**: clause "why does source 0 differ from the evaluation point": answered (E1018 with
  E437, E502, E1010, E339, E278, E606). Clause "does an attribute iterated with the position's
  source read the same way": no kept job iterates a coordinate set under byte 0 != 0x88 (E606's
  setups all 0x88). **Narrow, not retire** (R12-2); retire after laptop row 1.
- **Q036**: clause "STATUS2 high halves": answered as 0 to G 18 (E1019); "0x0748 bit by bit":
  bit 2 ranked [infer], other bits open; "CR_DPM_3D_PAGE_COUNTS' high half", "owner words 0x0700 to
  0x0728 of a kept owner": untouched. Narrow.
- **Q163**: v 3..7 counter held out (E700, E1021); v < 2 and "other shapes" open. Narrow.
- **Q107**: the order for plain stores answered (E996 + bridge); the overflowed store's content
  is not the overlay (E1020); the zero prefix and repeated tile open. Narrow.
- **Q114**: TEXTYPE clause answered as "none" [infer] (E567, E726); slices, third coordinate's
  mode, mip chain moot unless another word names one. Narrow (or retire, R12-7).
- No other old question has every clause answered by records (`survey/CANDIDATES.md` section 4
  lists the 80-odd rejected with a reason each).

## 2. Sim and spec gaps (`simgap/SURVEY.md`: 108 entries = C 46 cite only, M 29 model, R 13
refusal to add, N 20 not modellable now)

- **S1 cite sweep (C)**: an existing replay or refusal already implements the rule; a cite is
  missing. vdm.rs (E702, E738, E755, E737, E756: `read_index` refuses `w[0] >> 22 != 0x203`,
  checked), zls.rs (E628, E629, E739), iter.rs (E661, E731, E740, E741, E758), bif.rs (E745, E761,
  E901, E919, E920), fwtask (E600-E604), closing_vectors.rs (E833), sgx.rs (E834), mte.rs (E619),
  tex.rs (E721), dpm.rs (E854, E775, E790, E853, E873, E882, E917, E918), ta.rs/render.rs/mte.rs
  (E736, E781, E851, E728, E825, E827, E829, E847, E865, E897, E906). E834, E736 and E781 need a
  re-read before citing (survey flags them). [check] each cite names code that already exists.
- **S2 PDS pixel outputs (R)**: E709, E742, E759, E772, E838, E850, E858, E871, E878, E880, E905
  (all 11 pds entries): one refusal under Q276 for a triangle pixel program writing o1 to o7 or
  reading o4 to o7, in `sgx-sim/src/usse.rs` (`tri_pixel`) and `sgx-pipe/src/pixel.rs`
  `colour()`. Test first: `mov o1` / `mov r2, o5` in a `tri_pixel` program return Unsupported
  naming Q276; `mov o0` still runs. [check] no kept vector writes o1+ in a triangle pixel program
  (survey grep found none).
- **S3 TA refusals (R)**: E776 (a triangle whose max x is 0.0 under a viewport offset lists no
  region on hardware) and E780 (sub-pixel boxes up to 0.98: none written, no rule) in `ta.rs`
  `write()`, under Q230; tests first.
- **S4 DPM replays (M, small)**: E705 (`one_triangle_page_need(1024,768,dx,0)` = 19, 20, 17, 12),
  E626 (first-render counts 2, 3, 5, 5, 8, 19 at six sizes), E779 (partial renders 2 at 0xa0, 1 at
  0xa3 to 0xb0), E734 (the 22 rows as a necessary condition): ports checked in `simgap/need705.py`,
  `count863.py`. E863/E883 need timeline parsing: later.
- **S5 ISP coverage envelope (M)**: E681 (S2, 588 cases, 288 held out) and E682 (S5, 160 cases)
  replayed in `tests/isp_coverage_envelope.rs` from `isp/coverage-envelope/cases-1140.tsv`;
  risk: 4096 x 4096 run time (compare the edge band or run in release).
- **S6 new records**: E1018 can be modelled (sgx-pipe isp coverage with the sample point from
  cmd:16 byte 0, single-sampled, test: E064's 256 counts and 27 classes, refusing byte 0 for
  attribute iteration under Q201); E1019 a dpm.rs constant (STATUS2 high halves 0, cited) or a
  cite in the OPEN list's doc; E1020 a zls.rs refusal (overflowed final store under Q107, E1020);
  E1021 cited at vdm.rs's VDM_STATE1 bits 11:9 refusal, whose text becomes "a function of the
  word and a job-history counter (E700, E1021)" (E700, E701 off the list with it).
- Later, not this round: E722/E743/E760/E787 (T3 address, 2-3 h), E700/E701 as a stateful model,
  E894, E769/E784, E904, the G4 held-fault table (E764-E766, E789, E826: a table of five
  observations, low value) and TA 4x arrays (E763, E788, E729, E886, E908: dumps to read).

Shrink if S1-S6 all land: about 65 entries (108 -> ~43) [check: each package reports its own].

## 3. Work packages (at most 3; each one agent, own worktree and CARGO_TARGET_DIR inside it,
`git commit --no-renames -- <paths>`; records from E1018)

**P1 DPM, ZLS and VDM (~3.5 h).** Records **E1019** Q036 (finding 2; cite `c1-q036/`), **E1020**
Q107 (finding 4; `c3-q107/`), **E1021** Q163 (finding 3; `c2-q163/`, leaks named in the claim's
method). Question text: vdm/Q036, zls/Q107, dpm/Q038 (cites E996, E1020), vdm/Q163, dpm/Q045
(finding 5's scope note, no record). Appended notes: E443, E700, E701, E996. Sim: S4 in
`sgx-pipe/src/dpm.rs` tests (E705, E626, E779, E734; test first) with dpm.rs's S1 cites and
E1019; zls.rs (E628, E629, E739 cites, E1020 refusal, test first); vdm.rs (E702, E738, E755,
E737, E756 cites; E700, E701, E1021 at the bits 11:9 refusal, its test updated first). Files:
questions vdm/Q036, vdm/Q163, zls/Q107, dpm/Q038, dpm/Q045; evidence E1019-E1021, E443, E700,
E701, E996; crates dpm.rs, zls.rs, vdm.rs (+ their tests); SIM_UNMODELLED.toml (its own lines).

**P2 ISP, texture, BIF and stale text (~3.5 h).** Record **E1018** Q201 (finding 1; `c6-q201/`).
Question text: isp/Q201 (narrowed, E437 misquote fixed), texture/Q114 (R12-7), cites only for
pds/Q020 (E440, E545), edm/Q168 (E603), usse/Q133 (E594), usse/Q135 (E597), edm/Q196 (E600),
render/Q118 (E592), zls/Q088 (E665, E997, E989, E1014). Appended note: E064. Sim: S6's E1018
model in `sgx-pipe/src/isp.rs` (test first: E064's 256 counts and 27 classes as a table test);
S5 in `tests/isp_coverage_envelope.rs` (E681, E682); S1 cites in iter.rs, bif.rs, tex.rs,
`sgx-sim` sgx.rs, fwtask.rs/fwtask vectors, closing_vectors.rs (E661, E731, E740, E741, E758,
E745, E761, E901, E919, E920, E721, E834, E600-E604, E833). Files: those questions; evidence
E1018, E064; crates isp.rs, iter.rs, bif.rs, tex.rs, sgx.rs, fwtask.rs, the two tests;
SIM_UNMODELLED.toml (its own lines).

**P3 TA/PDS refusals and the build-path fix (~3 h).** No record. Sim: S2 (usse.rs `tri_pixel`,
pixel.rs `colour()`, 11 entries), S3 (ta.rs E776/E780 refusals), S1's TA/MTE cites (E736, E781,
E851, E728, E825, E827, E829, E847, E865, E897, E906, E619; keep `Q142` first in render.rs's ids
so `command_words_no_record_reads_are_refused_by_question` still passes). **Tooling**: one
`cargo_target_dir()` in `crates/pysgx/load.py` (CARGO_TARGET_DIR if set, relative paths taken
from the repo root as cargo does; else `<repo>/target`), used for `OUT` and the built library in
load.py, and by `tools/fwcutter/asmmap.py` `sgx_asm()`, `crates/pysgx/tests/test_pysgx.py`
(usse-dis), `tools/usse-dis/r2/pds_esil_check.py` (BIN), `tools/usse-asm/test_tutorial.py` (sim),
`tools/texture/test_tx_tool_assumptions.py` (default of USSE_ASM). Test first in
`crates/pysgx/tests/test_load.py`: with CARGO_TARGET_DIR set (absolute and relative) the dir is
that one; unset, `<repo>/target`. `tools/texture/p1132/gen/check_build.py` is a frozen phase
script: leave it. Not in HACKING's weakness list (only the r11 handover names it): the log line
records the fix. Files: usse.rs, pixel.rs, ta.rs, render.rs, mte.rs and their tests, the six
Python files above; SIM_UNMODELLED.toml (its own lines).

Disjoint: no question, record or crate source in two packages (mte.rs only in P3; isp.rs only in
P2; dpm/zls/vdm only in P1). **Shared: `crates/SIM_UNMODELLED.toml`**: each package deletes only
its own lines; deletions of neighbouring lines conflict in git, so the lead resolves a conflict
there mechanically (keep every line no side deleted) and runs `tools/records/sim_coverage.py
--check`. Generated files (`doc/state_digest.md`, `doc/open_questions.md`, spec and sim coverage)
the lead regenerates at the merge. Order: parallel; merge P1, P2, P3. Each record's scratch cite
is its `c*/` directory (`tools/records/scratch_cites.py`; remove the `__pycache__` first).

| Package | Records | Questions | Sim (list) | Wall | Risk |
| --- | --- | --- | --- | --- | --- |
| P1 | E1019-E1021 | Q036, Q107, Q163 narrowed; Q038, Q045 text | dpm replays, zls/vdm cites (~22) | ~3.5 h | low |
| P2 | E1018 | Q201, Q114 narrowed; 7 cite-only | isp sample point, coverage S2/S5, cites (~20) | ~3.5 h | low-med (run time) |
| P3 | none | none | pds/ta refusals, cites (~25); build-path fix | ~3 h | low-med (tri_pixel) |

## 4. Laptop rows for a later round (no design; B60AB0B4 or stock)

1. Q201: E437's position-source program and a coordinate-set iteration under cmd:16 byte 0 =
   0x26, 0x3c, 0x0f (~6 jobs, safe; the tool sets cmd:16 by poke: kit fits [check]).
2. Q107: an overflowed 1024x768 G 1 job over a load buffer of ascending indices with a marked
   G 33 twin (~4 jobs, safe class as E628's were): where the zero prefix and the repeated tile
   come from.
3. Q036: 0x0748 bit 2 against a controlled partial-render count (0, 1, 2, 4) at one size
   (~6 jobs, safe; register timelines as now).
4. Q163: block-2 v = 1 at controlled c (0, 2, 5) with grid bits 7:0 held at a completing value
   (~8 jobs; **hangs: not safe class**, recovered by the kernel as 11.31's were).
5. Q045: raised 4096 x 4096 jobs with the state page located per width (~4 jobs; or offline once
   the locator is fixed from E627's layouts).
6. Round 11's list (`closing11/plan/rank-round11.md` section 4) stands unchanged.

## 5. Decisions (the lead takes the recommendation; every (a) is offline and self-contained)

1. **R12-1 Packages.** a) P1, P2 and P3 as in section 3, three agents in parallel, ~3.5 h wall,
   records E1018 to E1021, SIM_UNMODELLED 108 -> about 43 (recommended); b) P1 and P2 only (no
   refusal sweep, no tool fix); c) records and question text only, no sim work.
2. **R12-2 Q201.** a) Record E1018 (256/256, 225 held out, 27/27 classes), narrow Q201 to the
   iterated attribute under byte 0 != 0x88, fix the E437 misquote, note on E064, model the sample
   point in isp.rs (recommended); b) retire Q201 now [infer on the attribute clause]; c) note only.
3. **R12-3 Q036.** a) Record E1019 (high halves 0 on 697 jobs up to G 18, held out; bit 2's ranking
   as [infer]), narrow Q036, note on E443 (recommended); b) the high-half clause only, bit 2 left
   out of the record.
4. **R12-4 Q107/E996.** a) Record E1020 (overlay 6/6 held out without overflow, 0/10 with
   overflow; zero prefix post hoc), narrow Q107, cite in Q038, note on E996 (scope), zls.rs
   refusal (recommended); b) a note on E996 and Q107 only.
5. **R12-5 Q163.** a) Record E1021 (v 3..7 54/54 held out; v < 2 variants fail as listed; leaks
   named), narrow Q163, notes on E700 and E701, vdm.rs refusal text re-keyed test first
   (recommended); b) notes only.
6. **R12-6 Q045 A2.** a) A text note in Q045 scoping "peak - 1" to the 11.38 scenes, no record
   (locator not general, 4/29 on located pages) (recommended); b) a record labelled post hoc.
7. **R12-7 Q114.** a) Narrow to "does any word other than TEXTYPE name a volume" with E567, E726
   cited (recommended); b) retire on E567/E726 [infer: negative evidence; the core is built with
   volume textures, hw_spec section 2]; c) no change.
8. **R12-8 Stale cites.** a) Add the evidence named in finding 6 to Q020, Q168, Q133, Q135, Q196,
   Q118, Q088 in P2 (text untouched beyond one line each) (recommended); b) leave for the next
   text edit of each.
9. **R12-9 Build path.** a) The `cargo_target_dir()` fix in P3 with its test, six call sites
   (recommended); b) load.py and asmmap.py only; c) leave it (worktrees keep the symlink).
10. **R12-10 SIM_UNMODELLED.toml.** a) All three packages edit their own lines, the lead resolves
    adjacent-line conflicts mechanically and runs `sim_coverage.py --check` (recommended);
    b) only P3 edits the toml, after P1 and P2 merge (serial, +1 h wall).
11. **R12-11 PDS refusal (S2).** a) In P3: one refusal under Q276 for o1 to o7 in triangle pixel
    programs, 11 entries off (recommended); b) leave the pds entries listed until Q276 has a rule.

## 6. Summary (10 lines)

1. 154 open; 117 untouched since round 5 surveyed; five offline checks frozen and scored (c1-c4, c6).
2. Q201: cmd:16 byte 0 is the sample point: 256/256 counts, 27/27 classes, 225 values held out.
3. Q036: STATUS2 high halves 0 in 697 jobs up to 18 global pages; 0x0748 bit 2 follows partial renders [infer].
4. Q163: E700's counter holds out 54/54 for v 3..7 on 11.31's sweeps; v < 2 variants fail.
5. Q107: E996's overlay holds 6/6 at 1024x768 unoverflowed, 0/10 on overflowed jobs.
6. Q045's "sum = peak - 1" is not general (4/29 located pages): a text note, no record.
7. Stale: Q201 misquotes E437; seven questions miss a cite; Q114 narrows (no TEXTYPE is a volume).
8. SIM_UNMODELLED: 46 cite-only, 13 refusals, 29 models, 20 not now; ~65 come off in three packages.
9. P1 dpm/zls/vdm (E1019-E1021), P2 isp/texture/stale (E1018), P3 refusals + CARGO_TARGET_DIR fix.
10. 11 decisions, (a) throughout; notes on E064, E443, E700, E701, E996; no corrections.
