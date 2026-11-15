# Round 22 plan: tool changes ranked by the questions they let a later session retire

Planner (Opus, 2026-11-15, on the road, user present), offline and read only. Basis: resgx545 main
0a7849e (142 open, 132 hw; records to E1095), data 99a8cda42, fork 456404fcffe5, module
E0CC40275493F8AEAD8180B, laptop tools t10, t14, t18, t18b, t20. Read: the state digest, handovers
r19 to r21 and 2026-11-11, the closing log's 2026-11-13 to 11-15 lines, rank-round15/16/17
(section 7 and 1b), rank-round19/20/21, the round 18 survey, HACKING "Known tool weaknesses", the
build-kit brief, `userspace/libsgxfive/tools/sgxfive-test.c` and `src/render.c`, `src/poke.c`,
and the question files and last records named below. Every "retire" in this file was checked
against the question's current text, not the survey's cell. The survey was optimistic: of its 10
T items, 3 were built in round 18 and the others mostly narrow now (section 3).

No records are made by this round. E1096 to E1101 are pencilled in for the sessions of section 6.

## 0. Summary

- **New finding: the i686 `probe --poke` SIGSEGV is a dangling pointer, not a mock bug.**
  `sgxfive-test.c` line 1928 hands `sgxfive_xfer_set_hook` the address of a compound literal,
  `&(struct sgxfive_poke_set){ po->pokes, po->npokes }`, made inside `if (po->npokes) { ... }`. Its
  lifetime ends at that block's `}`, and the hook runs later, inside `sgxfive_xfer_fill` or
  `sgxfive_xfer_copy` (lines 1935 to 1937). gcc reuses the slot: the mock crashes in
  `sgxfive_poke_hook`. clang on the Mac happens to keep it, so `make check` passes there. A clang
  ASan build with use-after-scope did not flag it: clang gives compound literals no lifetime
  markers. fill, copy and tri keep their poke sets alive until their job is submitted (lines 975,
  1088, 3100) and are not affected. **The same code is in every laptop tool (t10 to t20), so `probe
  --poke` cannot be trusted on the laptop today** [infer: the mock crash is the same code path the
  hardware runs]. Since ac5b888 (2026-11-01) the poke sets went through this path in E078 and
  E292/E293 (11-01/02, firh coefficients loaded: those pokes visibly landed), and in **E125, E391
  (Q019) and E568 (Q181)**. Those three are *negatives* ("no size limits", "the poke did not load
  the set") from builds whose stack layout no one checked. Whether their pokes landed is unproven
  [infer]. Section 2.1 and R22-4.
- **Retire-capable per tool change (verified):** probe poke fix → Q181 (low) and, if a size
  limit shows, Q019 (medium); `--place` across a code step → Q123 (medium); a reload background
  in a geometry final → Q038 (high). **Q088 needs no tool.** Its last open clause (the not-raised
  load bits) is a frozen rerun of E1093's post hoc reading on t18b.
- **Narrow only, though the survey said retire:** Q191 (clause (c) has no route; a ctx2 geometry
  kick separates the kick clause), Q139 (three clauses), Q069/Q162 (presence bits 16-31 are one
  clause of several), Q096 (no erratum on a revision 3 bridge, E432), Q024 (retires only as a
  bounded negative after 640 timed jobs and a kit rule change).
- **Packages:** P1 (tool only, ~5 h): the probe poke fix with a poke echo, `--place` across
  pages and code steps, the `--depth-pages` floor, HACKING upkeep, t22 built on the laptop.
  P2 (tool only, ~8 h): `tri --bg-pds/--bg-pixel` and `--keep-target` for E442's reload in a
  geometry final, plus `tri --ctx2-geometry` with a kept copy between the second context's
  kick and its closing render. **No module package**: no kernel change unlocks a retirement
  that is worth a 40 to 50 min laptop build and a one-shot boot (section 5).

## 1. Ranking (value-weighted retirements per tool hour)

Weights as the survey: high 3, medium 2, low 1, parked 0.5. "Ret" counts the value of every
question the change makes retire-capable (conditional ones marked c). Hours are tooling-agent
hours with tests; every tool build is ~1 min on the laptop (t20's recipe), `make check` ~2 min.

| # | change (package) | adds | retire-capable | narrows | h | ret/h | risk |
|---|---|---|---|---|---|---|---|
| 0 | none: Q088 rerun | a frozen form on t18b | Q088 (0.5) | - | 0 | - | safe |
| 1 | probe poke fix + echo (P1) | correct pokes; `poked` lines | Q181 (1), Q019 (2c) | E125/E391/E568 trust | 1.5 | 2.0 | low |
| 2 | `--place` across pages/steps (P1) | long placed programs | Q123 (2) | Q062 [infer] | 2.5 | 0.8 | low |
| 3 | reload in geometry final (P2) | `--bg-pds/--bg-pixel`, `--keep-target K` | Q038 (3) | Q107 colour | 5 | 0.6 | low |
| 4 | ctx2 geometry kick (P2) | `--ctx2-geometry N`, `kept.geo.N.bin` | Q191 (3) only if R22-3 b | Q191 kick | 3 | 0 (1.0) | low |
| 5 | `--depth-pages` floor (P1) | tile-extent floor | - | weakness gone | 1 | 0 | low |
| 6 | kit `kreg:OFF=V` word | register write per row | Q024 (1) as a negative | Q001, Q110, Q076 | 3 | 0.33 | high, rule change |
| 7 | filtered copy | a non-FASTSCALE transfer | Q043 (2c) | - | 8 | 0.25 | medium |
| 8 | `tri --kick-flags` (FIRST+LAST) | one TA command, both flags | Q119 (0.5) | Q065 | 2.5 | 0.2 | low |
| 9 | `--blk-add` bits 16-31 | presence words | - | Q069, Q162 | 2 | 0 | medium (faults) |
| 10 | TA data across a recovery | `render_keep` on a failed render | - | Q139, Q100 | 3+N | 0 | flagged |
| 11 | PDS patch/offset, PB dump | `probe --pds` data words | - | Q057, Q058, Q060, Q062, Q054 | 6-10 | 0 | low |
| 12 | xfer large, `--th-delay`, scratch VA | copies > 128x64 etc. | - | Q011, Q004, Q096 | 6+ | 0 | low/flagged |
| N1 | large-page PDE knob (module) | `vm_pde_size` debugfs | Q109 (1c) | - | 4+build+boot | 0.1 | medium |
| N2 | two-context TA preemption (module) | `ctx_switch` mode | Q068 (2) | Q049, Q029 | 12+build+boot | 0.1 | high |

## 2. The changes that retire something

### 2.1 The probe poke fix and a poke echo (P1; Q181, Q019)

**Adds.** (a) The poke set in function scope:
`struct sgxfive_poke_set pk = { po->pokes, po->npokes };` declared beside `src`/`dst` and passed
as `&pk`. (b) An echo: probe's hook wraps `sgxfive_poke_hook`. For each poke it reads the word
before and after (`sgxfive_poke_find` on the views) and prints
`probe NAME: poked SPACE:N 0xOLD -> 0xNEW` once the hook has run on the built job. A row's control
can then read that the word reached the command, which E391 could not ("the bits were poked, not
read back", Q019). The mock prints the same lines from its own build.

**Unlocks (checked).**
- **Q181 (low, retire-capable).** The question is whether the fill's transfer command loads a
  colour-space set at all, and if not, which path does (E568: 8 black YUV jobs with and without
  `xfer:17^=1`, 18-22). E568's csc rows ran `probe --coords --pixels --poke xfer:17^=0x1 ...` on
  `sgxfive-test-1126` (probes/texture/templates/tx-formats.sh line 89, tables rows fy-28/29-csc),
  that is, on the dangling path, and the record says the run did not print its pokes. Row:
  fy-28-p0-csc and fy-29-p0-csc again on t22 with the echo as a premise control, plus E037's copy
  with the same words as the copy control. Either result answers the question: the set loads in a
  fill (E037's conversion, frozen), or it does not although the echo shows the words in the
  command, and then the copy is the path.
- **Q019 (medium, retire-capable only if a limit shows).** E125 and E391 poked `bg:1` through the
  same path (probes/pds/attribute-room.toml, douta.toml) and saw no size limit 0 to 8 rows. E973's
  tri path (pokes alive through the submit) saw 0 rows lose the background layer's texels. Row:
  E391's 40 jobs (attributes 0-63 at 0, 1, 2, 4, 8 rows, two runs) on t22 with the echo. Freeze
  H-E391 (every attribute 0-31 arrives at every size, as E391) against H-ROWS (fitted on 0, 1 and 4
  rows, held out at 2 and 8). If H-E391 holds with the echo, E391 stands and Q019 only narrows. If
  not, E125 and E391 need appended corrections (the poke did not land in that build [infer]).
- **Not unlocked:** Q010 (needs a planned hang and a power-off), Q013 (pixev pokes go through
  fill/copy's own sets, alive through the submit: unaffected).

**Tests.** The two failing tests (`test_probe_takes_transfer_pokes`,
`test_probe_takes_background_object_pokes`) pass in the laptop's i686 `make check` (the
regression, 0 failures, where t20's recipe accepted 2). A new `test_probe_poke_echo`:
`bg:1=0x130000`
echoes the built word and 0x00130000, and `xfer:17^=0x4` echoes old and old ^ 4, both with and
without `--coords`. A new static test fails on any `sgxfive_*_set_hook(..., &(struct` in
`tools/`. A test that an echo never appears for a poke the hook did not apply (the reject path,
`xfer:4^=0x1`).

**Cost** 1.5 h. **Risk** low: probe rows only. Fill, copy and tri output is unchanged.

### 2.2 `probe --place` across pages and code steps (P1; Q123)

**Adds.** `--place OFFSET=FILE` takes a program of up to `PLACE_MAX_WORDS` 8192 words (64 KiB,
16 pages), not one page of 256 words. It maps every page the program spans and refuses a range
that reaches the probe's own program page at the heap base or the heap's end (5 MiB). It prints
`program placed at A..B (N pages), crosses code step 0x80000 at word K` for each 0x80000-byte
step it crosses. The fill program keeps `PROBE_MAX_WORDS` 256. The scratch-immediate patch
applies to every placed word.

**Unlocks.** **Q123 (medium, retire-capable).** Open: whether the counter carries into bits 16
and 17 as an 18-bit counter would, and whether a long program is reached the same way. Every
placed program so far was one page (E475, E476, E492). Rows: a program straddling offset
0x80000 (bit 16) and one straddling 0x100000 (bit 17), each with (i) a straight run of
`nop`s across the step to a store of a marker, (ii) a `ba` and a `lapc` from the start to a
store past the step, (iii) a control program inside one step. Frozen: H-CARRY18 (an 18-bit
counter lands every marker) against H-WRAP (the low 16 bits wrap inside the step: the marker of
the run's start instead). Pad every placed word not in the program with a marker store and
`end`, so a wrong landing ends the task with a known marker, not a hang [infer: a pad of stores
is safe class; if R22-2 b, the straight-run rows go to a flagged stage].
Q062 (the fetch pc at 26-27 back to back) gains nothing certain: narrow at most [infer].

**Tests.** The mock places a 600-word program at 0x7fe00 (one crossing at word 64, two pages) and
echoes the words read back from the mapped pages. It refuses a program reaching page 0 of the heap
or the heap's end, and a fill program of 257 words (as now). The DOUTU words for `cbase` and
`exe18` are checked at 0x7fff8 and 0x100000.

**Cost** 2.5 h. **Risk** low (our own code in our own heap).

### 2.3 E442's reload in a geometry final (P2; Q038)

**Adds.** (a) `tri --bg-pds FILE:N --bg-pixel FILE`: the background object's primary PDS
program (N data dwords) and pixel shader, parsed and patched as `probe --tri`'s bgpds and bgpixel
slots already are (`probe_tri_slot`). They are accepted with `-n`, `--geometry`,
`--final-pb-pages`, `--depth` and `--refill`, and refused with `--bg-layer`. (b)
`tri --keep-target K` (2 <= K <= N): the library does not write its sentinel (or `--fb-fill`)
before render K. `render.c` line 792's fill is skipped through a new `fb_keep` parameter. Render
K's report then counts colours against render K - 1's readback, not the CPU reference:
`tri #K: target kept, X pixels changed, colours ...`.

**Unlocks.** **Q038 (high, retire-capable).** R20-3 b left its last clause, the colour of a
final that does not overflow, to "a tool change that runs E442's reload in a geometry final",
and r21's plan (section 7) named the three parts: (1) the reload object with `--geometry`, (2)
no sentinel before the final's kick, (3) a reference for kept colour. This change supplies all
three. Its depth clauses were narrowed by E1081, E1088 and E1093; the zero region and tile order
are Q107's. Row (r21's zl form, 1024x768 `-n 2 --geometry 1 --final-pb-pages 0x100`,
E442's `bg_reload_1024.s` and `pds_bg_pos.s`, `--keep-target 2`): frozen H-RELOAD (render 1's
partial colour plus the final's triangle, every pixel of T1 u T2, E442's 207456-pixel count for
T1) against H-REPAINT (E1089: the library background paints over T1 \ T2). Controls that can
fail: `--keep-target 2` without the reload (H-REPAINT predicted), and the reload at `-n 1`
without overflow (E442's exact image). Fit 0x28 (raised), held out 0x2c (raised), 0x30 and 0x34
(not raised). E1089's 18582-pixel reading at 0x30 is the not-raised prediction. It also narrows
Q107 (whether the zero rows lose colour as well as depth).

**Tests.** Mock: the slots accepted with `--geometry` and refused with `--bg-layer`;
`--keep-target 1` and `K > N` refused; the mock target unchanged between renders under
`--keep-target` (a library C test that `fb_keep` leaves `r->fb` as it was); the report line
format; `--emit-scene` still writes the background object with the slot programs.

**Cost** 5 h. **Risk** low (E442's shader ran 12 jobs safe on the laptop).

### 2.4 A kept copy between the second context's kick and its render (P2; Q191 narrow)

**Adds.** `tri --ctx2 --ctx2-geometry N`: the second context's render N is submitted geometry
only, and a closing render of the second context follows in the same iteration. `--kept-copy
DIR` adds `DIR/kept.geo.N.bin` between the two. The park-race retry of t20 applies. `--geometry`
(the first context's) stays refused with `--ctx2`, and `--final-pb-pages` is refused with
`--ctx2-geometry` (the final PB knob is taken by whichever context is created next: not needed
at 64x64).

**Unlocks.** **Q191 (high): narrow.** Its kick clause ("its TA kick or its render's end", E1092
open) becomes one row: the 64x64 owner closed early (flag 0xc), the copy after the second
context's geometry kick against the copy after its closing render. Frozen H-TAKICK (E631's four
words already in `kept.geo`) against H-RENDEREND, with the flag 0x4 control (no words in either).
"Why only after that run" and clause (c) (a load reading them back) stay. Clause (c) has only
E591's 9 of 9 junk-ramp renders unchanged. Q191 retires with this row only if the user takes that
as a bounded answer (R22-3 b); otherwise it narrows.

**Tests.** Mock: `kept.geo.N.bin` written between the two second-context renders with
`--mock-park-ms`; refusals (`--ctx2-geometry` without `--ctx2`, with `--final-pb-pages`,
N > n); the second context's geometry render leaves its scene open in the mock as the first
context's does.

**Cost** 3 h. **Risk** low.

### 2.5 Q088 without a tool change

Q088's text after E1093/E1094: open are the not-raised load clause "as a frozen form (whenever the
final loads, it draws no triangle at z 0.5 against a 0.75 load [infer]) and why", plus the zero
region (to Q107 under R21-2 a), bit 15 (to Q071) and the closed driver's purpose (fw). The frozen
form is now writable from zl-2e-ld (E1093, post hoc): **H-LOADNODRAW** (not raised, load bits:
the 0.75 load written back, T2 absent) against H-HOSTBITS. Rows on t18b, r21's zl form at not
raised P with load bits (0x2e again as fit, 0x30, 0x34 and 0x38 held out), and a no-load-bits
control (H-HOSTBITS 2 of 2 in E1093). It retires Q088 if the user takes "why" and the driver's
purpose as fw (R22-8). It belongs in the dpm session of section 6.

## 3. The survey's T and N items, re-checked

- **I1 T-dpm**: built (t18 `kept.closed`, `--kpoke-render rd:11`; module E0CC4027 with
  `--final-pb-pages`, run in r19 to r21). Q192 and Q045 retired; Q088 is 2.5 above. The HACKING
  entry for `--final-pb-pages` still says "stays listed until ... a session runs on its module".
  Sessions did (E1077, E1078), so P1 takes it off the list.
- **I2 T-kregword** (row 6): only Q024 retires, as "no value outside the bound" over 64 values x 10
  timed jobs (Q024's own "to settle it"). Q001 keeps "what bits 8 and 10 do", Q110 "whether the
  ranges exist", Q076 four clauses, Q111/Q003/Q036 several: narrow. It needs the kit's rule "no
  register write of ours" changed, and the guard refuses `--kreg` today (HACKING, guard options).
  Not proposed (R22-5).
- **I3 T-probe**: T-code128k is 2.2. T-scratchva (Q096): no erratum shows on this bridge (E432),
  only a negative. T-pdspatch/T-pdsoffset/T-pbdump (Q057, Q058, Q060, Q062, Q054): rounds 16-17's
  "too broad for one session" stands; narrow.
- **I4 T-ta-kick**: T-tadump-recover narrows Q139 only (open: what places the TA's write, the
  stride's relation, the kind at four macrotiles a side). It may need a kernel change if
  `render_keep` drops a failed context. T-blkadd16 narrows Q069 (also "why 0.6", another
  triangle, OUTSEL 13) and Q162. T-kickflags retires Q119 (parked fw, 0.5). T-thdelay does not
  retire Q004 (it also needs a CONTEXTSUSPEND and firmware reading). T-xferfilter is row 7: Q043
  retires only if its answer is "bit 0 keeps o1 off other pixels (E412)" plus a filtered copy
  that changes nothing, and the library has only FASTSCALE transfers (xfer.c line 133).
  T-xfer-large narrows Q011.
- **Q202 (high)** is not a tool item. `probe --tri` with a vertex program already sets w
  (r6-pixel's 114 jobs, w 2.5e-4 to 8027, E992). What blocks is a frozen perspective plane model:
  sgx-pipe's pixel side refuses 1/w other than 1. That is an offline modelling task.
- **N items**: N-K1 (a hold at the second kick) is replaced by 2.4 with no kernel change.
  N-ctxswitch (Q068 retire, a day or more plus a boot), the large-page PDE (Q109: three clauses,
  low), N-edm-defpd (Q095, parked kernel) and N-K3 (Q003, narrow) are each worth one low or
  parked question or less.

## 4. Known tool weaknesses (HACKING) and kit items

- `tri --depth` floor: `depth_min_pages` (line 2740) is W x H dwords, below the store's 32 x 16
  tile extent. P1: the `--depth-pages` floor uses the tile extent, ceil(W/32)*32 x ceil(H/16)*16 x
  4 bytes. The default size stays `depth_min_pages + DEPTH_MARGIN_PAGES`, so the layouts of earlier
  controls do not move (R22-7). Test: 161 x 49 (r17-zls's target) refuses 8 pages and takes 12.
  The entry leaves the list with the commit.
- `--final-pb-pages` entry: leaves the list (above).
- New entry, fixed by P1: `probe --poke` before t22, dangling poke set (2.1). It is listed with the
  fixing commit and the records whose pokes are unverified (E125, E391, E568), so a later session
  does not reuse t10 to t20 for probe pokes.
- sgx-sim refusals, the r5-events mock, texmodel.py: unchanged (frozen or documented).
- t20's laptop recipe accepted 2 known failures. t22's recipe requires 0.

## 5. Packages

### P1 (tool only, one agent, ~5 h; sonnet suffices: every item is specified here)

Branch `r22-tooling` off main 0a7849e, worktree in the lead's named place, `CARGO_TARGET_DIR`
of its own (no cargo needed: C and pytest only). Items, tests first: 2.1 (fix and echo), 2.2
(`--place`), the depth floor (section 4), the HACKING list edits, the usage header of
`sgxfive-test.c` for the new options. Recipe `closing22/k22/build_tool22_laptop.sh` from t20's
(`closing21/k21/build_tool20_laptop.sh`): bundle, source sha256 pinned, `make CC=gcc
build/sgxfive-test` (~50 s), `make check` with **0 failures** required. The lead runs it over the
cable and writes `TOOL22.built`. Nothing is installed, no module change.
**Later session: r23-pk** (section 6).

### P2 (tool only, one agent, ~8 h; after P1 merges, or in parallel on its own branch)

Branch `r22-tooling2`. Items 2.3 and 2.4, with their usage text and tests. If P1 merged first,
recipe `build_tool22b_laptop.sh` (t22b); if in parallel, one build of the merged tip.
**Later session: r23-dpm** (section 6), on module E0CC4027 as loaded.

### No module package (R22-6)

N1 and N2 are the only kernel changes that retire anything (Q109 low, Q068 medium). Each costs
more than all of P1 and P2 together: a laptop module build of 40 to 50 min, a one-shot boot with
the user's OK, KUnit first and a fork land. No tool change can replace them, but their value is
too low for this round.

## 6. The later sessions each package enables (for the next laptop round)

| session | tool | stages (jobs) | questions | records | wall | class | kit fit |
|---|---|---|---|---|---|---|---|
| r23-pk | t22 | pkg gate (4), q019 (40), q181 (8), q123 (10) | Q019, Q181, Q123 | E1096-E1098 | ~25 min | safe (q123 pad [infer]) | yes |
| r23-dpm | t22b + t18b | rl (10), og (6), zn (5) | Q038, Q191, Q088 | E1099-E1101 | ~20 min | safe | yes |

- **r23-pk** (any module; E0CC4027 as loaded). Gate: the echo shows every poke of a `bg:1` row and
  an `xfer:17` row, and the E391 row "0 rows, attributes 0-15" on t22 is a reading for R22-4 (not
  a stop). q019: E391's 40 jobs (2.1). q181: fy-28/29 csc and no-csc probe fills plus two E037
  copies (2.1). q123: 2.2's rows, the in-step control first, `on_stop = "end"` if the control
  fails. No register write, no knob. `#limit 0`. The library-mock replay runs our own probes (kit
  c12542e). The `--place` FILE over 256 words needs the mock's argv twin to accept it (P1's tests
  cover the tool; the session's world copies it).
- **r23-dpm** (E0CC4027; knobs `render_pb_pages`, `render_final_pb_pages` at default 0). rl: 2.3's
  rows under rt with r21's register list. og: 2.4's rows (t22b, knob 0). zn: 2.5's rows (t18b or
  t22b, r21's form). Stream-bounded param hashes only (kitscore.param_hash), and `expectdiff`
  rows with `job: ok`. No fault or hang is planned.
- Order: r23-pk can run as soon as t22 is built (P1 only); r23-dpm after t22b. Each is one
  sitting under the 45 min limit with one re-stage.

Offline before r23-pk's freeze: H-ROWS cannot be written before the run (no fit data). The q019
stage freezes only H-E391 and the "2/8 held out" rule, as a two-pass stage (fit rows, then a
scorer step that freezes the fitted rule by hash before the held-out rows are scored). This is the
kit's existing fit/heldout labelling, with no new kit word [check with the builder].

## 7. Retire summary if every frozen form holds

P1 + r23-pk: Q181, Q123, and Q019 if a limit shows (up to 5 value points, 3 questions). P2 +
r23-dpm: Q038 and Q088 (3.5), plus Q191 under R22-3 b (3). Up to 6 questions from about 13 tool
hours and two short safe sessions. Without the tools the r21 planner found one (Q088).

## 8. R22 decisions for the user

1. **R22-1 Which packages.**
   - a) P1 now, P2 right after on its own branch (recommended: P1 is cheap, fixes a tool that is
     wrong on every laptop build, and alone lets r23-pk run).
   - b) P1 only this round; P2 later.
   - c) P1 and P2 in parallel (two agents, two branches, `git commit -- <paths>` only).
   - d) No tool work; offline only.
2. **R22-2 Q123's straight-run rows.**
   - a) Safe class with the marker-store pad of 2.2, the in-step control first (recommended).
   - b) A flagged stage after every safe stage (a hang the kernel recovers is possible if the pad
     is not reached), with the user's OK.
3. **R22-3 Q191's clause (c), a load reading the owner's words back.**
   - a) Keep it open: 2.4's row narrows Q191 (recommended; as R20-3 b, no retirement on a
     negative nobody froze).
   - b) Take E591's 9 of 9 unchanged renders over junk lists as its bounded answer, so 2.4's row
     can retire Q191.
4. **R22-4 The earlier probe-poke records (E125, E391, E568).**
   - a) Treat their pokes as unverified until r23-pk repeats one row of each with the echo, and
     append corrections only if the result differs (recommended).
   - b) Append a caveat correction to each now ("the poke went through a dangling hook; its
     landing is not shown").
   - c) Nothing.
5. **R22-5 The kit's `kreg:OFF=V` word (Q024 as a bounded negative).**
   - a) Not now (recommended: one low question, a rule change, 640 timed jobs).
   - b) Build it as a flagged-class kit word.
6. **R22-6 A module package.**
   - a) None this round (recommended).
   - b) A large-page PDE knob for Q109 (build on the laptop ~45 min, one-shot boot).
   - c) Two-context TA preemption for Q068 (a day or more, boot).
7. **R22-7 The `--depth-pages` floor.**
   - a) Floor check by tile extent only, default size unchanged (recommended).
   - b) Also size the default depth buffer by tile extent (moves later buffers' addresses relative
     to earlier controls).
8. **R22-8 Q088.**
   - a) Add stage zn (2.5, no tool) to r23-dpm and retire Q088 if H-LOADNODRAW holds out, the
     "why" and the driver's purpose left as fw (recommended).
   - b) Keep it parked; no row.
