# Round 35 plan: safe-class sessions on questions rounds 31-34 did not run

Planner (2026-11-17, offline, read only; this file is the only output). Class: SAFE only (no
planned fault, no hang, no `kreg`, no register write, no new kernel); tools t10 (a581c06) and t30
(sha256 b5ea288d, source 42c4de7), regtimeline, the kit's words incl. `pre:miscinfo`, `noreset`,
`idle:S`, T1's `reg:@snap0` / `@snap0:ROW` controls and `@cal:STAGE` intervals with the
`session.py` lint at freeze (main c6d17ec); module 7CE8E38E as installed.

Basis: resgx545 main eea6d2a (`doc/state_digest.md`: 132 open, 122 hw), round 34's plan
(`closing29/plan/rank-round34.md`, its section 1 discipline L1-L5), the closing log's rounds 31-34
(`plans/resgx545-question-closing.md`, last line 2026-11-17 01:16), the question files named
below, E417, E484, E593, E1135, E1136, E1139 and r34-sa0b's fold (`closing29/r34-sa0b/fold/
q136-rule.out`; E1140 not yet on main). Skipped as asked: Q010, Q024, Q036, Q044 (retired),
Q082, Q111, Q136, Q002. Next free record: E1143 (E1140 is r34-sa0b's, E1141-E1142 r34-ev2's).

## 0. Summary

- **One medium question is retire-capable in one short safe session: Q073** (isp: what o0 holds
  at the start of an opaque pass). E417 narrowed it to "the previous job's colour on part of the
  pixels, the background on the rest"; the open part is *what it is left from* (the previous
  job's output at the same pixel, another slot, another tile) and *a previous job of another
  size*. A previous triangle whose colour is unique per pixel (E385's `pds_iter_xy` form) decides
  it. ~26 jobs, ~10 min, no tool change.
- **One low question is retire-capable, with a lead call on its "why": Q129** (usse: the 12 odd
  pixels of an sa1/sa5/sa7 writer, and how long an sa lasts). r34-sa0b (E1140) answered the
  lifetime for sa0 (one job); E1139's post hoc pairs show reads aliasing earlier instances' o0
  [infer]. A session with `--pixels` on single-sa writers and a gap job that writes another sa
  decides both clauses' measurable parts. ~42 jobs, ~12 min.
- **Decisive narrowing:** Q302 (pbe, low: channel rounding of modes 3-6, 9-13 and the 40
  ARGB8888-like modes; RGB565's rounding clause decides; mode 14's fault is not safe) and Q193
  (usse, low: which earlier job's value an unwritten temporary reads, per instance; the power
  cycle and module reload clauses are outside the safe class).
- None of the four is a timeline session, so L1/L2 (idle values, sample spacing) do not arise;
  the void risks are the two round-34 lessons: **D1** every reader and decoder form runs first on
  a known value, and **D2** a scorer test shows every frozen hypothesis name is produced.

## 1. Discipline (round 34's L1-L5 stand; two additions from round 34's voids)

- **D1. Every reader/decoder form has a known-value control in the same stage** (r34-sa0, E1139:
  the reader decode `pixel = read ^ key` was never run on a known value and voided 18 of 20
  readers). Each new program form (reader, position decode, per-mode unpack) gets one row whose
  expected output is fixed by construction or by a kept image, and the scorer refuses to decide
  any row of that form if its control fails ("cannot tell: form control").
- **D2. A scorer test produces every frozen hypothesis name.** (r34-ev2: a frozen name the scorer
  never emitted voided two clauses.) `tests/test_score.py` builds one synthetic table per frozen
  hypothesis (from the mock's outputs edited to that hypothesis's pattern) and asserts the
  scorer prints that name as held, and one table where it is FAILED. Freeze refuses if a name in
  `predictions/*.tsv` appears in no test. The lead checks the test exists before the run.
- **D3. Readers do not feed back.** E1139's post hoc reading: a program that reads a register and
  writes o0 in the same job sees what earlier instances wrote. Readers output exactly the value
  read (E1140's form, no key), and a reading is taken as the per-pixel value plus the
  most-frequent value, never through a transform.
- **D4. The stage-begin health pair (t10 `fill`, t10 `tri`) writes o0 and clears the csc set
  (E1134).** Every stage below starts with a row that overwrites the state it reads (an A' or W
  row), never with a reader.

## 2. Ranking

Value: high 3, medium 2, low 1; x1 retire-capable, x0.5 decisive narrow, x0.2 narrow.

| # | Q | value | session | retire? | jobs / wall | tool change | score |
|---|---|---|---|---|---|---|---|
| 1 | Q073 | medium | r35-o0 (t10 probe --tri, pass-through after a per-pixel colour) | yes | ~26 / 10 min | none | 2.0 |
| 2 | Q129 | low | r35-sa stage a, b (t30 probe fills, `--pixels`) | yes, R35-3 | ~42 / 12 min | none | 1.0 |
| 3 | Q302 | low | r35-pk (t10 probe --tri, channel ramps, pack modes) | no (14 faults) | ~110 / 22 min | none | 0.5 |
| 4 | Q193 | low | r35-sa stage t (unwritten r20, `--pixels`) | no (power cycle, reload) | ~20 / 7 min | none | 0.5 |
| - | Q008 | low | luma high cut, `copy --ramp` | only if an offline fit freezes a form | ~40 | offline fit | 0.2-1.0 |
| - | Q013 | low | pixev:2 bits 16-19 x10 with `--pixels`, 64x32 vs 128x128 | no ("what the word is") | ~60 | none | 0.2 |
| - | Q058 | medium | if0/if1 in a transfer's PDS | no: `--pds` is the secondary only | ~10 | primary/pixev slot for fill and copy | 0.2 |
| - | Q012 | medium | modes 22/34 after a known previous colour | no (format "what") | ~20 | none | 0.2, after r35-o0 |
| - | Q039 | medium | user clip plane state | no (power cycle, reload) | - | - | 0 safe |
| - | Q177 | low | modes 4-7 dword at new sizes | no ("what the half is") | ~20 | none | 0.2 |

Q073 first by score and by length. Q129 and Q193 share the probe-fill reader machinery and run as
one session of two stages (they read different register files, so neither stage's state feeds the
other: the stage boundary's health pair and a W/writer row start each). Q302 is the longest and
runs last. Q008 (round 34's Q082 precedent: three forms fit the fit half and failed the held-out
half) waits for an offline fit on E426's kept copies; Q012 may become reachable once r35-o0 shows
whether a pixel's leftover follows the previous job's pixel (E1135: mode 22's varying dwords
"change with the job before") [infer].

## 3. The top four

### 3.1 Q073 (isp, medium): what o0 holds at the start of an opaque pass (RETIRE-capable)

**Line:** "what does o0 hold at the start of an opaque pass's pixel shader?" Measured (E417, 33
jobs, 64/96/128): a pass-through shader (o0 stored unchanged) gives the previous job's constant
colour on 390-450 of 1062 pixels at 64x64 (426 four times), fewer at larger sizes, the background
0xff203040 elsewhere; pass-through after pass-through keeps it at 64x64. Open per its body and
E417's "does not show": which pixels (not mapped), *what it is left from* (the previous job's
output at that pixel, another instance slot, another tile), and a previous job of another size.

**Session r35-o0 (t10 `probe --temps 32 --pixels --tri pixel`, safe, one stage `o`, every row
after a debugfs reset unless `noreset` is named).** Programs: P = E417's pass-through (o0 = o0);
K = E417's job A (o0 = 0xff00ff00); A' = a colour unique per pixel, E385's `pds_iter_xy.bin:12`
+ `vtx_coords.bin` + `--vtx-coords 2` with a pixel program that packs x and y into o0
(o0 = 0xa5000000 | y << 8 | x, assembled from our own sources; at 128x128 x and y need 7 bits,
still unique).

| group | rows (in order) | purpose | replicates |
|---|---|---|---|
| c0 | A' (64) ; A' (128) | D1: A' stores f(x,y) on every triangle pixel (known by construction) | 1 each |
| c1 | K ; P (noreset) | D1 on P: P's non-background pixels all K (E417's form, can fail) | 2 |
| h1 | A' (64) ; P (64, noreset) | which pixel's value: the held-out reading | 3 (2nd, 3rd reversed group order) |
| h2 | A' (128) ; P (64, noreset) | previous job of another size (the body's clause) | 2 |
| h3 | A' (64) ; P (128, noreset) | the other direction | 2 |
| h4 | A' (64) ; reset ; P (64) | does a debugfs reset keep it (E1140 kept sa0 and pa0) | 2 |
| h5 | A' (64) ; t10 fill ; P (noreset) | does a non-triangle job between replace it | 1 |

First row of the stage: A' (D4). ~26 jobs plus the health pairs.

**Frozen hypotheses (P's non-background pixels, decoded as (x', y') = low 16 bits of the value).**
- H-SAMEPIX: every non-background pixel (x, y) reads A'(x, y) (the previous job's output at the
  same pixel, the tile buffer or the PBE's input left as it was [infer]).
- H-SLOTMAP: every non-background pixel reads A' of another pixel by a map that repeats between
  replicates (an instance slot reused across jobs); the scorer fits the map on h1's first
  replicate and holds it on h1's others and on h2/h3 (held out).
- H-OTHER: anything else (values not of the form f(x,y), or a map that does not repeat).
- Size clause: H-SAMEPIX predicts h2's P reads f(x, y) at x, y < 64 (A' at 128 drew them) and
  h3's reads f only inside the 64x64 corner A' drew; H-TILESLOT (the slot of the same tile
  index in drawing order: tiles of 32x16, 2 per row at 64 against 4 at 128 [infer]) predicts the
  coordinates of the tile with the same index. Both frozen; the scorer computes both maps.
- h4: H-RESETKEEP vs H-RESETCLEAR; h5: H-FILLREPLACE (P's non-background = the fill's 0xff336699)
  vs H-TRIONLY (A' values survive a fill).
- The count of non-background pixels is a reading, compared to E417 (390-450 at 64x64); not a
  verdict (the line asks what, not how many).

**Retire rule (against the line).** Controls c0, c1 pass; one of H-SAMEPIX / H-SLOTMAP holds on
every decided held-out pixel of h1-h3 (both replicates), and the size rows pick one of H-SAMEPIX /
H-TILESLOT: then "what o0 holds" is answered (the previous job's output at the pixel or slot the
held hypothesis names, else the background), with h4/h5 giving its lifetime. Which pixels keep
it (the count, E417's 426) goes to the body as not the line, or a new low question (R35-2).
Any split narrows.

**Void risks and their guards.**
- A decoder untested on a known value (r34-sa0): c0 runs the A' decoder on its own stored image,
  where the answer is f(x, y) by construction; a c0 failure makes every h row "cannot tell".
- E1139's feedback: P reads o0 and writes the same o0, so instances that read what earlier P
  instances wrote still read A' values; H-SLOTMAP absorbs a within-job reuse, and H-OTHER is the
  outcome if values stop being of A's form. No key, no transform (D3).
- The stage-begin health triangle writes 0xff00ff00/0xff203040 into the same output state: the
  stage starts with A' and every P row follows its own A' with `noreset` (D4, L5).
- A frozen name never produced (r34-ev2): D2's test covers H-SAMEPIX, H-SLOTMAP, H-TILESLOT,
  H-OTHER, H-RESETKEEP/CLEAR, H-FILLREPLACE/TRIONLY on synthetic tables.
- T1: no register value is frozen (no `reg:` control, so `@snap0` is not needed); the freeze's
  `session.py` lint still runs, and no `gate` depends on an interval (`@cal` not used).
- Safety: E385's and E417's programs ran on t10 without a fault; A' at 128x128 uses the same
  programs at a size E417 ran.

**Time:** ~26 jobs at ~5 s each (r34-q044: 198 jobs in 17 min) plus health: ~10 min.

### 3.2 Q129 (usse, low): the 12 odd pixels of an sa writer, and an sa's lifetime (RETIRE-capable)

**Line:** (a) why do 12 pixels (4 each of three values) of every fill that writes sa1, sa5 and
sa7 show those sa values as their output; (b) how long does an sa written by one job stay
readable (one job, or until the next job that writes it). Measured: E484 (18 writers, 12 pixels,
4 per sa; an sa read by the next job 9 of 9; after a job writing no sa the reader read that job's
output 3 of 3); E1139 (an sa0 writer: o0 K1 x2044 and M x4, the same 4 odd pixels for one sa);
E1140 (sa0 lasts one job, any job between replaces it with that job's colour, 16 of 16 held out).
Open per the body: the positions (never kept), sa written by fewer instances, and "a gap job that
writes an sa other than the probed one" (clause b's rival).

**Session r35-sa stage `a` (t30 `probe --temps 32 --pixels`, 64 x 32 fills, 2048 instances).**
Programs: W_n = E1139's writer on sa_n (`iaddu32.testtaz.chan0 sa_n, p0, r1, r2` making M_n,
dword 0 = M_n, o0 = K1 0xc0de0a01); W_157 = E484's form (sa1, sa5, sa7 together); R_n = E1140's
reader on sa_n (o0 = dword 0 = the value read); K = colour fill (K3 0xc0de0a03); X_1 = a writer of
sa1 only whose o0 is K2 0xc0de0a02 (the gap job of the body).

| group | rows | purpose | replicates |
|---|---|---|---|
| c0 | K | D1: position decode, every pixel K3 | 1 |
| c1 | `probe --coords` copy with o0 = pa0 | D1: position decode on known per-pixel values (y << 16 \| x) | 1 |
| c2 | W_5 ; R_5 (noreset) | D1: reader form on sa5 reads M_5 (E1140's form on a new register) | 2 |
| f | W_0, W_1 | fit: the 4 odd positions of sa0 and sa1 | 2 each |
| h | W_2, W_3, W_5, W_7, W_15, W_157 | held out: positions per n and the union | 2 each, 2nd reversed |
| p | W_5 ; X_1 ; R_5 (noreset) | clause (b): a gap job writing another sa | 2 |
| q | W_5 ; K ; R_5 (noreset) | clause (b), E484's gap form (a job writing no sa) | 1 |

First row: W_0 after c0/c1 (D4: the reader rows always follow their own W). ~42 jobs.

**Frozen hypotheses.**
- Clause (a), positions (pixel index i = y * 64 + x and the instance order the probe prints):
  H-FIXED4 (the same 4 positions for every n, both replicates); H-SHIFT (positions for n = those
  of sa0 shifted by n d, d fitted from sa1); H-VAR (positions differ between replicates of one
  n: "which instances" is not a fixed set); H-UNION (W_157's 12 = the union of W_1, W_5, W_7's).
- Clause (a), count: H-FOUR (exactly 4 odd pixels per sa written, every row) against H-OTHERN.
- Clause (b): H-ONEJOB (R_5 after X_1 reads K2, X's colour: E1140's rule for sa0) against
  H-UNTILWRITE (R_5 reads M_5: only a write to sa5 replaces it). q is E484's form (fit).

**Retire rule (against the line).** Controls pass; clause (b) decided (H-ONEJOB or H-UNTILWRITE
on 2 of 2 p rows with q agreeing); clause (a)'s "which" decided (H-FIXED4 or H-SHIFT on every
held-out n, H-UNION, H-FOUR). The "why" is then the statement the data allow: [infer] the sa write
and o0 of those 4 instances name one storage, the mirror of E1139's reader pairs. Whether that
inference retires a "why" clause is the lead's call (R35-3); otherwise retire the measurable part
and move "why" to the body of Q098 (which already holds "pa_n naming sa_n" as its open why).
H-VAR held: narrow (positions not fixed).

**Void risks and guards.** Position decode untested: c0/c1 (c1 gives every pixel a distinct
known value). Reader form on a new register: c2 runs before any R_5 is read. Frozen names: D2
test over H-FIXED4, H-SHIFT, H-VAR, H-UNION, H-FOUR, H-OTHERN, H-ONEJOB, H-UNTILWRITE. The health
pair writes o0 (and, by E1140, sa0's value): f starts with W_0. No register value frozen, no
timeline: T1's forms are not needed; lint at freeze. Safety: every program form ran in E484,
E1139, E1140 without a fault.

**Time:** ~42 jobs, ~12 min.

### 3.3 Q302 (pbe, low): channel rounding over the pack modes (decisive narrow)

**Line clauses:** (a) what modes 4-6, 9-14 and the 40 ARGB8888-like modes other than 0 store for
colours other than E031's two; (b) what 9-13 write past the target; (c) why 14 faults (a fault:
not safe); (d) how RGB565 (mode 3) rounds where truncation and rounding differ; (e) CR_REG_0400
words no record ran (bit 25 with another low byte, another sideband field).

**Session r35-pk (t10 `probe --temps 32 --pixels --tri pixel --width 64 --height 64` with E385's
`pds_iter_xy.bin:12`, `vtx_coords.bin`, `--vtx-coords 2`, `eot_plain.bin`, `--cmd 11=WORD`,
`--sideband 0x200|MODE`: E1135's argv form).** One ramp program: per pixel a byte b = x + 64 (y &
3) (every value 0-255 four times per 64 x 16 band), o0 = A b' R b G (255 - b) B (37 b mod 256)
with A b' = b xor 0x5a, so every channel takes every byte. Stages:

- s0 (D1 controls, gate): mode 0 at 0x80 stores o0 exactly (the decoder's known value); E031's
  kept colour image repeated in modes 3, 4, 7 (H-E031, as r34-q044's s0); mode 4 at 0x80 the
  alpha split of E1136 (at or above 0x80).
- r1: modes 3, 4, 5, 6, 9, 10, 11 at 0x80, 2 replicates (14 jobs); modes 12, 13 at 0x80 with
  r34-q044's pw form (writes past the target into the tool's 64 KiB scratch, E031), 2 replicates.
- r2: the 40 ARGB8888-like modes at 0x80, 1 replicate (40 jobs; they stored mode 0's image for
  E031's colour and ignore bit 25, E1135).
- r3 (clause e): modes 4, 5, 6 at 0x02000040 and 0x020000c0 (bit 25 with another low byte), and
  mode 0, 4 at sideband bits 8:6 = 0 only (E383: other values move the alpha channel; not in the
  line's safe reach without a frozen form, so r3 runs low bytes only), 2 replicates (~20 jobs).

**Frozen hypotheses (per narrowed channel of width w).** H-RZ (truncate: v >> (8 - w)), H-RN
(round half up: (v + 2^(7-w)) >> (8-w) saturated), H-RNE (ties to even), H-SCALE (round(v (2^w -
1) / 255)), each a frozen per-mode unpacker in the scorer, tested on mode 0's identity and on
E031's two kept colours first (D1). ARGB8888-like modes: H-AS0 (byte-exact as mode 0 on all 256
values per channel) against H-AS0-PART. r3: H-1136 (bit 25 inverts the alpha field and the low
byte thresholds mode 4's alpha as E1136, whatever the low byte) against H-LOWDEP.
Modes 9-13: per E031's class, readings of the target and the scratch past it (no frozen
verdict on what "past the target" means).

**Narrow rule.** Clause (d) decides if one of H-RZ / H-RN / H-RNE / H-SCALE fits every mode-3
pixel of both replicates (retire that clause into the body). (a) decides per mode the same way
(modes with no hypothesis holding stay named). (e) decides for the words run. Q302 stays open on
(c) mode 14's fault and on (b) unless the scratch dump shows a frozen form, so this narrows. If
(a), (b), (d), (e) all decide, R35-4 b (split (c) to the flagged list and retire) becomes
possible.

**Void risks and guards.** A per-mode unpacker never run on a known value: the scorer's unpackers
are tested offline on r34-q044's kept images and E031's raw.txt before freeze (D1), and s0 runs
mode 0 and the E031 repeats on the laptop first with `gate = true`. Frozen names: D2 test over
H-RZ, H-RN, H-RNE, H-SCALE, H-AS0, H-AS0-PART, H-1136, H-LOWDEP. Modes 22, 26, 34 excluded (not
repeatable, Q012); 14 never run; sideband bit 11 never set (faults, E383). r34-q044 ran every mode
but 14 at 0x80 and bit 25 safely on this module (E1135). No register value frozen, no timeline.

**Time:** ~110 jobs at ~5 s plus health: ~22 min.

### 3.4 Q193 (usse, low): which earlier job's value an unwritten temporary reads (narrow)

**Line clauses:** (a) which earlier job's value does a temporary a task did not write read, per
instance; (b) what clears it: a power cycle, a module reload (both outside the safe class and the
round's rules: narrow at best), a job of another context. Measured: E593 (the i0-i3 job, a reset
in front: 2048 of 2048 the job just before in one order; in the other 1536 and 512 from two jobs
9 and 7 earlier); E484 reach (r40, r47).

**Session r35-sa stage `t` (t30 `probe --temps 32 --pixels`).** Programs: T_j = writes marker
0x7e000000 | j << 8 | 20 to r20 in every instance, o0 = K1; U = reads r20 without writing it,
o0 = dword 0 = r20 (D3); K = colour fill (writes r0-r3 only [check at build: the probe's colour
fill's temporaries]).

| group | rows | purpose | replicates |
|---|---|---|---|
| c0 | T_1 ; U (noreset) | D1: reader reads M_1 in all 2048 (the job just before, E593's first order) | 2 |
| t1 | T_2 ; K ; U (noreset) | a job not writing r20 between | 2 |
| t2 | T_3 ; t10 tri ; U (noreset) | a triangle between (its 1536/512 instance split, E496/E1140) | 2 |
| t3 | T_4 ; reset ; U | reset between (E593: kept) | 2 |
| t4 | T_5 ; T_6 with 8 temporaries ; U | a writer of a smaller allocation between | 1 |

~20 jobs. Each row is its own process and so its own render context [check at build: t30 opens
one context per process], so clause (b)'s "another context" is in every row by construction.

**Frozen hypotheses.** H-LASTWRITER (every pixel reads the last job that wrote r20) against
H-LASTJOB (the last job, whatever it wrote: K's or the triangle's register contents) and
H-SPLIT (pixels split by instance slots between jobs, E593's 1536/512; the scorer names the
counts); t2: H-TRI1536 (the triangle overwrites the slots of its 1536 + 512 instances, the
E496 mixture) as a named rival.

**Narrow rule.** (a) decides per group; (b)'s context sub-clause decides by construction; the
power cycle and module reload stay open (R35-5). Narrow.

**Void risks and guards.** Reader untested: c0 first, where the value is fixed by construction
(E593's first order). Frozen names: D2 over H-LASTWRITER, H-LASTJOB, H-SPLIT, H-TRI1536. The
stage boundary's health pair: t starts with T_1. No register value, no timeline.

**Time:** ~20 jobs, ~7 min (r35-sa total ~62 jobs, ~19 min).

## 4. Tool changes

None needed for the four. One cheap unlock noted for later: a t-tool slot for a transfer's
primary and pixel-event PDS programs (`probe --slot pixpds/pixev` for fill and copy, as `--tri`
has) would let Q058's transfer clause run (narrow only: its first clause "what sets if0/if1"
stays). Not recommended this round.

## 5. Order

1. Build r35-o0 (Q073, E1143), r35-sa (Q129 E1144, Q193 E1145) and r35-pk (Q302, E1146-E1147) in
   parallel (own dirs, own CARGO_TARGET_DIR); each builder writes the D2 scorer test first and
   the lead checks it before freeze.
2. Run r35-o0 (10 min), then r35-sa (19 min), then r35-pk (22 min). Total ~51 min of laptop.
3. Offline: Q008's high-cut fit on E426's kept copies (numpy in scratch only); a session only if
   a form fits held-out halves.

## 6. R35 decisions

1. **R35-1 Which sessions.**
   - a) All three (r35-o0, r35-sa, r35-pk) in that order (recommended: all safe, no tool
     change, one medium retirement, one low retirement, two decisive narrows, ~51 min).
   - b) r35-o0 and r35-sa only (the two retire-capable; Q302 is narrow only).
   - c) r35-o0 only.
2. **R35-2 Q073's "which pixels keep it" (the count, E417's 426 of 1062).**
   - a) Not the line: if the retire rule holds, retire Q073 and record the count in its body
     (recommended: the line asks what o0 holds, not where).
   - b) New low question for the partition, then retire Q073.
   - c) Narrow only; keep Q073 open until the partition is ruled.
3. **R35-3 Q129's "why".**
   - a) If (a)'s positions and (b) decide, retire Q129 with the measured answer plus the [infer]
     storage statement, and move the mechanism to Q098's open "pa_n naming sa_n" (recommended:
     Q098 already owns that why, and the positions are what Q129 can measure).
   - b) Retire only if a frozen form predicts the positions from n (H-SHIFT or H-FIXED4) and the
     why stays in the inference.
   - c) Narrow only.
4. **R35-4 Q302's mode 14.**
   - a) Narrow this round; mode 14 stays on the flagged list (recommended: it faults, E031).
   - b) If every safe clause decides, split (c) into a new low flagged question and retire Q302.
   - c) Add a flagged stage for mode 14 later (one planned fault a row).
5. **R35-5 Q193's power cycle and module reload clauses.**
   - a) Leave them open; Q193 narrows (recommended: both are outside the safe class and the
     overnight rules).
   - b) Plan a module reload row for the next user-present round (kernel batch, user's OK).
