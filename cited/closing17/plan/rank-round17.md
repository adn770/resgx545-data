# Round 17 ranking: safe laptop rows, retire first (Opus, 2026-11-14, user asleep)

Basis: resgx545 `main` c2180e6 (records to E1066; E1061 and E1062 reserved by the unmerged
r16-usse fold; 147 open, 137 hw), resgx545-data af46e8077, fork resgx545 2a650d74 (read only),
laptop on module B60AB0B4 (one-shot boot), tools t4, t9, t10, t14. Inputs read: `BRIEF-COMMON.md`,
`doc/state_digest.md`, the round 16 handover (Next item 4), the 2026-11-13/14 lines of
`plans/resgx545-question-closing.md`, `closing16/plan/rank-round16.md` (sections 1a, 1b, 7), the
question files of Q078, Q177, Q071, Q069, Q299, Q120, Q241, Q046, Q139, Q107 and the open clauses
of Q284, Q260, Q296, Q086, Q042, Q066, Q240, Q202, Q002, Q096, Q019, Q109, Q123; records E1058,
E1063, E1064, E1065, E1066 (what ran, what they do not show); r16-tw's FOLD-NOTES, `gen/tw16.py`,
`fold/bilin_post.py` and `.out`. Nothing staged, built or run; no laptop, SSH or cachix.

Files of this plan (all in `closing17/plan/`): this file and `calc/` (post hoc scripts on kept
data only, and their outputs): `q078_cols.py` (shared loader: every bilinear bit-14 pixel of E1049
and E1058), `q078_search.py`, `q078_hyp.py`, `q078_wide.py`/`.out` (the form below),
`q078_exact.py`/`.out` (exact bytes at the left wrap), `q078_ptcheck.py`/`.out` (kept point rows),
`q078_rows.py`/`.out` (the sketch of tw17's rows). They read resgx545-data's r15-tw and r16-tw
through r16-tw's pinned `gen/` (run with `PYTHONDONTWRITEBYTECODE=1`; no cache left).

## 0. Honest summary

**One retire-capable safe row remains, not two.** Round 16's leftovers and a re-check of round 16's
section 1b give:

- **Q078 (retire-capable, made so offline by this plan).** E1058 left no form that fits both
  rounds. A post hoc offline fit found one: **H-WIDE**, bit 14 samples a texture W + 4096 texels
  wide at frac(u), repeated over that width. It reproduces every bilinear bit-14 pixel kept (8 rows,
  16384 of 16384 within 1, on and off the 1/4096 grid, both edges, `calc/q078_wide.out`). At the
  left wrap its column W + 4095 is byte-exact on 124 of 128 kept pixels, where E1058's W - 1 is
  exact on 0 (`calc/q078_exact.out`). It is post hoc, so it needs a held-out row: tw17 below.
- **Q299, Q071, Q069, Q177: narrow only.** Q299's other clause is a planned fault (not safe class).
  Q071 keeps "where bit 23's bytes come from" (no frozen form) and "the ISP's use". Q069 keeps
  OUTSEL bit 13 and presence bits 16-31 (a tool change, likely faulting words) and "why 0.6".
  Q177's type 4 block form has one size past 32 (no fit to freeze), and "what the half is" has
  no observable test.
- **No older question became decidable** (section 1b): rounds 13-16 touched 14 hw questions. Each
  still has a fault clause, a "why" clause, a nondeterministic clause or too many clauses for one
  session.

Rounds 13-16 retired 1, 5, 2 and 2-3 questions. Round 17 can retire **at most one** (Q078).
**Recommendation (R17-1 a): a small round.** r17-tw (Q078, 12 jobs) plus a short r17-zls (10
jobs). Its edge-tile pass leaves Q299 with only its planned-fault clause, so one row with the user
can retire Q299 later. Then **stop laptop rounds until the user is back** (R17-7 a) and run an
offline round (section 5). About 22 jobs, 15 minutes of laptop time.

## 1. Every candidate, ranked (retire first)

"Retire" means every open clause of the question line is decided by held-out rows if the frozen
hypothesis (or exactly one rival) holds and the controls pass, as R16-6 (a). "Narrow" means a
clause stays open whatever happens.

| # | Stage (session) | Question | If it holds | Jobs | Tool | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | tw17 (r17-tw) | Q078 bilinear at both edges, on and off the 1/4096 grid | **retire** | 12 | t14 | safe; reach < 150000 (E1058 read to 224351); W 256 and 512 last, `on_stop = "end"` |
| 2 | zovp2 (r17-zls) | Q299 load pass over overlapping tiles with edge tiles | narrow (leaves only the fault clause) | 5 | t10 | safe |
| 3 | zb20 (r17-zls) | Q071 bit 20's packed records at other sizes | narrow | 5 | t10 | safe |
| 4 | zoff2 (r17-zls, R17-1 c only) | Q069 E1066's plane on another triangle | narrow | 6 | t10 | safe |
| 5 | ty3 (r17-tex, R17-1 c only) | Q177 W H + 7 W + 52 held out, mode 5, name parity | narrow | 12 | t14 | safe |

### 1a. Rows the kept data already decide (dropped or cut down)

- **Q078 point read on the 1/4096 grid** at W 16-128, H 8-64, u past 1, u16: E1049, E1058 (H-TWP-H
  8/8). It is H-WIDE's point form there: no kept point pixel parts floor((W + 4096) frac u) from
  floor(W frac u) + floor(4096 frac u) (`calc/q078_ptcheck.out`: 0 pixels in 21 rows). tw17 runs
  only off-grid point rows, where they part.
- **Q078 bilinear inside the texture and across the v edge** (rows mod H): E1058 (bl64in,
  bl16h16in, bl128vedge 2048/2048 under every column form). tw17 keeps the v edge only inside a
  corner row.
- **Q299 overlapping whole tiles, a kept NaN**: E1064. **Q071 bit 0, bit 23 against the
  reference, mask and background**: E1063. **Q069 offsets 0 to 7/16 on E987's ramp**: E1066.
  **Q177 halving, rows alike, mode 0 references**: E1055, E1065.
- **Q126, Q137**: being folded (r16-usse, unmerged). No rows, as the brief says.

### 1b. Older questions re-checked against rounds 13-16

Round 16's reasons (rank-round16.md section 1b) still hold. Rounds 13-16 touched 14 hw questions,
and none has become one safe session from retirement:

- **Q120**: five open clauses (multi-float tiles, format 7's depth dwords, format 5, format 6's
  edges and runs, the pitch, no stencil buffer).
- **Q241**: bit 18 faults (E065, E998).
- **Q046**: bit 11 faults; bit 12's low half varies by run (E1034).
- **Q139**: the faulting words fault, and its dumps need TA data kept across a recovery.
- **Q107, Q038**: need an overflowed job's stores named (a load-buffer index row). The tile order
  has no frozen form: narrow only.
- **Q036**: nondeterministic (E1057). **Q163**: hangs. **Q108**: faults.
- **Q260**: no candidate form (E984). **Q296**: needs a declared family fitted on the FIT half
  first (an offline task).
- **Q086, Q042, Q066, Q240, Q202**: several independent clauses each. **Q096**: the erratum does
  not show on this bridge (revision 3, E432). Its last clause can only narrow (a negative).
  **Q002**: the USSE's issue rate needs a timed loop. No frozen form.
- **Q024**: still needs a kit word for a debugfs `kreg` write (round 16, section 7).

## 2. Rows in detail

Every stage: `#limit 0` (any fault or hang stops it, kit rc 4). Controls are `reads:` rows of the
stage's own shape, never the default triangle. Expectdiff rows need `job: ok`. Predictions are
frozen by the kit freeze before staging. Every row carries the flags its premise needs (E934):
`--depth-pages` explicit at every odd size, formats in the control word. Each builder names its
replay table in README (HACKING "Replay vectors"). "Held out" means no kept job ran that input.

### r17-tw (t14; prefix r17w; E1067)

**tw17 (Q078, 12 probe fills).** E1058's form: r16-tw's `gen/tw16.py` extended by its builder.
E566's tx_map, scratch dword i = 0xD0000000 | i, the texture at the scratch's first dword, T0
0x07FE1400 (bilinear) or 0x07FE0000 (point), T3 0x00800800 | bit 14, 32-bit, `probe --temps 32
--coords --pixels --scratch-pages 256`. u and v are float32-exact `lin` ramps (tex.lin), v in
(0, 1].

Frozen (post hoc, `calc/q078_wide.py`, fitted on E1049's tw-bl32 and tw-bl16 and E1058's six
bilinear rows):

- **H-WIDE**: under bit 14 a bilinear sample reads a texture W' = W + 4096 texels wide at frac(u).
  fx' = W' frac(u) - 1/2; the columns are x0' = floor(fx') and x0' + 1, repeated over W' (column -1
  reads W' - 1, column W' reads 0). The weights in 64ths come from fx' and from v as before. Rows
  y0 and y0 + 1 are taken mod H. The tiles are E561's (16 x min(H, 16)) with a tile row of W'.
  On the 1/4096 grid it is E1058's post hoc "unwrapped" reading; off it, it moves the weights too.
  It fits 16384 of 16384 kept pixels within 1 (75 % byte-exact, the rest within 1, as every bit-14
  bilinear row before it).
- **H-WIDE-PT** (point rows): column floor(W' frac(u)) of the same layout.
- Rivals:
  - **H-WIDE-G**: the left column wraps to W - 1. Names 65536 dwords apart differ by one in byte 2,
    so only exact bytes part it. Frozen rule: at the left-wrap pixels, the winner is byte-exact on
    at least 90 % and the loser on at most 10 %; anything else is "cannot tell" for that sub-clause.
    The kept split is 124/128 against 0/128.
  - **H-WIDE-NEXT**: column W' unwrapped, the next tile's column. It parts by names, at W 256 and
    512 only: at W 128 no whole-64th u reaches the right-wrap band.
  - **UNWRAP-G**: E1058's post hoc reading, columns floor(W frac u - 1/2) + floor(4096 frac u) and
    + 1, left column at W - 1.
  - **F-FRAC**: E1049's form, refuted by E1058, carried.
  - **H-POINT**: the filter dropped.
  - Point rows: **H-TWP** (floor(W frac u) + floor(4096 frac u), E1049/E1058's form).

Rows (sketch in `calc/q078_rows.out`; the builder recomputes and freezes). Every row has whole-64th
weights under H-WIDE (no weight rounding is assumed past the kept 64ths model). Rows run in this
order:

- Bilinear, held out:
  - **bl16left** (W 16, u = 1 + x/1024: the left edge on the grid, 32 left-wrap pixels).
  - **bl64grid** (W 64, u from 3 - 40/4096, step 1/4096: both edges on the grid).
  - **bl128off3** (W 128, step 3/8192, so pixels alternate on and off the grid, both edges).
    UNWRAP-G parts on 704 pixels.
- Controls that can fail:
  - **bl64left-rep**: E1058's bl64left program byte for byte, its kept image within 1.
  - **ref256**: the bit-clear 256 x 32 image, E561's law, a new width.
  - **ref512h16**: the bit-clear 512 x 16 image.
  - ref256 and ref512h16 gate every W 256 and 512 row (GATE as tw16's).
- Point, held out:
  - **pt128off** (step 1/8192, H 32): H-TWP parts on 512 pixels.
  - **pt256off** (H 16): 768 pixels.
  - **pt512off** (H 16): 896 pixels.
- **Last, `on_stop = "end"`** (widths never run with bit 14):
  - **bl256edge** (W 256, step 1/16384 across u = 3): UNWRAP-G parts 1040 pixels, NEXT 32,
    WIDE-G 31.
  - **bl512edge** (W 512, step 1/32768 across u = 1): 1056, 96 and 32.
  - **bl256corner** (W 256, u across the right edge and v across the v edge at once).

Total: 9 held out + 3 controls = **12 jobs**.

- [check] The builder widens the right-wrap band if it can. It is 1/W' of u, and the sketch has
  only 32 to 96 parting pixels a row, against round 16's rule of 256 or more. W 1024 or 2048 gives
  more, with W' x 32 at most 196608 dwords < 262144 in the reach proof. Otherwise it says so in
  README.
- Reach: every frozen form and rival stays under 150000 dwords (sketch: 147541 at most), inside
  E1058's 224351. No range is read for the first time. W 256 and 512 still go last after their
  gates.
- Stop: `#limit 0`, `on_stop = "end"`. A fault inside the scratch means the mapping premise failed
  (r15-tw FOLD-NOTES), not bit 14.
- **Retire Q078** if all of these hold:
  - H-WIDE (or exactly one rival) holds within 1 on all six bilinear rows.
  - The left wrap is decided by the exact-byte rule, and the right wrap by names.
  - One point form holds on all three point rows.
  - The three controls pass.

  If H-WIDE-PT wins, the point clause of the question line is restated as floor(W' frac u): an
  appended correction to E1049's and E1058's point claims is not needed. They held on the grid,
  where the two forms are one [infer]. The fold says so.
- Replay: sgx-sim tex.rs gains the bilinear bit-14 sample (it refuses it now, Q078). Table `tw17`,
  replayed by sgx-pipe `tests/texture_t3b14.rs`.
- Kit fit: fits. It uses r16-tw's binding of t14 (`--tool-src t14=c58f9f9:...@closing14/k14/
  build_tool14.sh`) and the t10 health pair. The exact-byte statistic lives in the session's own
  `score/score.py` (scorekit bracket plus a counted reading), not in a shared tool. The library
  mock replays own probes "not simulated" (c12542e).

### r17-zls (t10; prefix r17z; E1068, E1069)

**zovp2 (Q299, 5 jobs).** E1064's zovp form: E996's plane, depth less, the load buffer filled 0.2f
(0x3e4ccccd) and stored, and E988's st1 stencil load at the same pitches. It runs at shapes with
both shared slots and edge tiles: 65 x 33 G 1 (E1051's edge-tile store shape) and 161 x 49 G 2.
The builder confirms by E465/E1041 that each shape has slots shared by two tiles and edge tiles,
and names the slots.

- Rows: depth load and stencil load at each shape (4).
- Frozen **H-OVL-PASS-EDGE**: sgx-pipe `zls::pass` with overlaps (E1064) and E1041's edge-tile
  store. Each tile, edge tiles included, loads its slot and passes on its own. The tile visited
  last keeps a shared slot.
- Rivals: H-OVL-FIRST (the first visited tile owns), H-EDGE-SKIP (edge tiles do not load and store
  the plane over the fill).
- Control that can fail: E1064's 160 x 48 G 2 depth row replicated (1).
- Narrow. If it holds, Q299's line becomes its fault clause alone: E411's G 5 row in a 16-page
  buffer, one planned fault, in section 7.

**zb20 (Q071, 5 jobs).** E1063's bit-20 rows (formats 6 and 7, 0x0607300e and 0x0707300e) at two
other sizes, 128 x 64 and 96 x 32 G 2 (4), with `--depth-pages` explicit.

- Frozen from E1063's fold, post hoc: **H-PACK2048** (the per-tile records packed one after another
  from dword 2048, whatever the size). Rivals: H-PACK-AFTER (from the end of the last slot) and
  H-PACK-SCALE (from an offset that scales with the target's slots).
- Control that can fail: E1063's zf-flat-f6 bit-20 row replicated (1).
- Narrow: bit 23's source and "the ISP's use" stay.

Kit fit (both stages): fits. They use r16-zls's forms and pokes, and `--depth-fill` is a value
fill. Replay: sgx-pipe `zls::pass` with edge tiles (table `zovp2`) and `zls` bit-20 packing (table
`zb20`, or `refused` naming Q071 if no form holds).

### Only under R17-1 (c): narrow rows

- **zoff2 (Q069, 6 jobs, r17-zls, E1070).** E1066's plane (1.6 w + 0.4 s) t and its far vertex on a
  triangle not E987's (vertices away from t = 0), w at 1/8 and 5/16, s at 0.25 and 0.5, and the
  bend's pixels read, with E1066's zw2 replicate as the control. Narrow: OUTSEL bit 13, presence
  bits 16-31 and "why 0.6" stay.
- **ty3 (Q177, 12 jobs, r17-tex on t14, E1071).** E1065's type programs:
  - Type 1 at 16 x 64 (W against max(W, H)), 128 x 32 and 32 x 8 against the post hoc W H + 7 W +
    52 (rivals: max(W, H)^2 + 7 W + 52, E1055's 39 W + 52).
  - Type 3 at 8 x 8 and 64 x 64.
  - Mode 5 at 128 x 32 and 32 x 8 (7 W + 51).
  - Modes 6 and 7 at 16 x 64.
  - Type 4 at 32 x 64 and 64 x 32 as readings for a block form.
  - The control is E1065's ty-ty1u4r replicate.

  The builder chooses sizes whose two candidate names (N and N - 256) part after halving: byte 1 of
  the lower name even. Narrow: type 4's form, then "what the half is".

## 3. Sessions (safe class only; one sitting on B60AB0B4)

| Order | Session | Stages (jobs) | Jobs | Wall | Prefix | Records | Tool |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | r17-zls | zovp2 (5), zb20 (5) [+ zoff2 (6) under R17-1 c] | 10 (16) | ~4 min (~5) | r17z | E1068, E1069 [+ E1070] | t10 |
| 2 | r17-tw | tw17 (12; W 256/512 last) | 12 | ~5 min | r17w | E1067 | t14 (t10 health) |
| (3) | r17-tex | ty3 (12), R17-1 c only | 12 | ~4 min | r17t | E1071 | t14 |

R17-1 (a): **22 jobs, about 10 minutes of jobs plus staging, under 20 minutes in all**. R17-1 (c):
40 jobs, about 30 minutes. Both are well under 1.5 h. Builders run offline in parallel first,
about 1 h. tw17 is a delta on r16-tw's generator and scorer. zovp2 and zb20 are deltas on
r16-zls's.

Order: r17-zls first (forms run in rounds 10-16), then r17-tw (new widths last). A fault would then
end the round with the known forms done.

## 4. Tool changes

None for R17-1 (a), (b) or (c). Only R17-3 (c) would need one: a `probe --scratch-fill` whose
dword names part in every byte, so names 65536 apart are told apart by more than exact bytes. That
means a tooling agent with tests and a t17 build on cachix by the lead. It is not recommended
overnight.

## 5. Offline parts

- **OQ078 (done in this plan, `calc/`)**: the tw17 builder re-derives H-WIDE with its own generator
  on the kept files before freezing (R17-2). The fold cites the builder's files, not `calc/`.
  `calc/` is publishable: it uses kept data only and nothing firmware-derived.
- **Offline round after this one (R17-7 a)**, candidates for the lead's offline planner [check:
  surveyed, not verified]:
  - Q177: a type 4 block-form fit on E941's and E1065's kept dumps, so a later round can hold it
    out.
  - Q296: the declared family fitted on its FIT half (an offline task by its own text).
  - Retire, fold or park candidates whose last clause no run on this hardware can decide: Q063 (the
    rest of the SGX family), Q096 (no erratum on a revision 3 bridge, E432).
  - sgx-sim refusals that kept records already decide (SIM_UNMODELLED).
- **r16-usse** (Q137 retirement, Q126) waits on the user's guard claim (round 16 Next item 1).

## 6. Retire summary if every frozen hypothesis holds

R17-1 (a): Q078 retires (one). Q299 narrows to its planned-fault clause alone, and Q071 narrows.
R17-1 (c) adds narrowing of Q069 and Q177, and no retirement.

## 7. Later, with the user (not safe class; in no session)

- **Q299**: E411's G 5 row in its 16-page buffer (a fault is expected). After zovp2 this one row
  can retire Q299.
- **Q069**: `tri --blk-add` past bit 7 for presence bits 16-31 and OUTSEL bit 13 (a tool change;
  unknown appended words may fault).
- **Q108**: EDMPROTECT on a load-only depth render, and WRITEONLY or EDMPROTECT on a texture read.
- **Q139**: faulting macrotile words (TA data kept across a recovery: a kernel or tool change).
- **Q241** bit 18 (faults, E065, E998). **Q046** bit 11 (faults at 0x37001000, E1034). **Q036**'s
  builder-fault clause.
- **Q040** odd EMIT2 counts (hang). **Q112** bit 24 (hang) and width bits (faults). **Q163**
  counter shapes (recovered hangs).
- **Q195**'s firmware-task forms (verifier first).
- **Q024**: not unsafe, but needs a kit word for a debugfs `kreg` write and 150 or more timed jobs.
- **Q177** in two passes (fit, then hold out) and **Q078**'s hashed scratch fill (R17-3 c).

## 8. R17 decisions (the lead takes the first option of each)

1. **R17-1 Round shape.**
   - a) Small round: r17-zls (zovp2, zb20) and r17-tw (tw17). 22 jobs, under 20 min, E1067 to
     E1069. One question can retire (Q078), and Q299 is set up for a one-row retirement with the
     user (recommended).
   - b) r17-tw alone: 12 jobs, E1067.
   - c) a plus zoff2 and ty3 (narrow only): 40 jobs, about 30 min, E1067 to E1071.
   - d) No laptop round: offline only (section 5), laptop rounds paused until the user is back.
2. **R17-2 Q078's frozen form.**
   - a) Freeze H-WIDE and its rivals as section 2 names them. The builder re-derives the form from
     the kept files with its own generator (a test reproduces 16384 of 16384) before the freeze
     (recommended).
   - b) The builder runs its own independent search first and freezes what it finds.
3. **R17-3 The left wrap (names 65536 apart differ by one in byte 2).**
   - a) Decide it by the pre-declared exact-byte rule (at least 90 % against at most 10 %, kept
     124/128 against 0/128). State the parting in E1067, and retire Q078 under R16-6 (a) if every
     other part holds; the lead confirms (recommended).
   - b) Leave the wrap open whatever tw17 shows (Q078 narrows).
   - c) A `probe --scratch-fill` tool change and a t17 build first.
4. **R17-4 Widths 256 and 512.**
   - a) Include them after their bit-clear gates, last, `on_stop = "end"`. They are the only widths
     where the right wrap parts with whole-64th weights (recommended).
   - b) W 128 and below only: the right-wrap clause stays open, and Q078 narrows.
5. **R17-5 Q299 edge tiles.**
   - a) Run zovp2, leaving Q299 with its planned-fault clause alone (recommended).
   - b) Skip.
6. **R17-6 Record numbers.**
   - a) E1067 tw17, E1068 zovp2, E1069 zb20, and E1070 zoff2 and E1071 ty3 under R17-1 (c)
     (recommended).
   - b) The lead renumbers after the builds.
7. **R17-7 After this round.**
   - a) Stop laptop rounds until the user is back. The next round is offline (section 5), and the
     round 16 leftovers that need the user (r16-usse guard claim, push, cleanup) and section 7 wait
     for them (recommended).
   - b) Plan another safe laptop round. Its expected yield is zero or one retirement.
