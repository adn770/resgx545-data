# Round 5 proposal, area PIXEL: Q276 (what the tag-5 word is), Q230 (the 1/w word), v-stock-4096

Planning only, 2026-11-12. Offline and read-only: nothing here touched the laptop, cachix or a
repo. Scripts and outputs are in this directory (`closing5/pixel/`); they read only the published
sessions `resgx545-data/render/closing-r3-pixel` and `render/closing-r4-pixel`, so a record may
cite them after `tools/records/scratch_cites.py --publish` (public, nothing firmware-derived).
Everything in sections 1 and 3 is a post hoc reading of kept data unless marked otherwise.

## 0. Short version

- **Q276.** Of E838's two readings, "the o4 path clears bits 5:3" is **refuted offline**: 1525 of
  1525 tag-5 words in 44 jobs of E808 keep non-zero marker bits at 5:4, and R4's own c-e709-x
  reads 0xcf5 in 39 of 39. "OR of tags" survives, with eight kin: 9 of 821 declared bitwise
  models fit every kept configuration. One stage of single-output bit rows separates all nine.
- **Q230.** The frozen analysis of g4-rw is **already decided offline**: 0 of its 225 frozen
  models fit the 19 FIT words that were read (best 16), so the 18 missing words cannot rescue it.
  What the data does support is "RZ or RZ + 1 follows the mantissa of w" (6 of 6 mantissas read at
  two exponents). The band-safe rerun is planned around that, not around the dead fit.
- **v-stock-4096** no longer matters (section 5).
- One laptop session, userspace only, no kernel change, no reboot if the laptop is still on the
  rgn4 boot: 106 jobs, about 10 minutes of jobs.

## 1. Q276 offline: what the kept images decide

Scripts: `o4_offline.py` -> `o4_offline.out` (sections A to F), `o4_family.py` ->
`o4_family.out`. Data: R3 p-c3 (`closing-r3-pixel/out/20261110-160415/p-c3`, E808, 58 marker
jobs) and R4 p4-o4 (`closing-r4-pixel/out/20261111-205726/p4-o4`, E838, 36 jobs).

### 1.1 "The path clears bits 5:3" is refuted [data]

- R3's word layout is `marker * 16 + tag`, so the marker's two low bits sit at bits 5:4 of every
  word. In the 44 jobs whose marker has a non-zero bit there, the tag-5 words keep the whole
  marker: 1525 of 1525, none with bits 5:4 cleared (`o4_offline.out` A).
- R4's bridge control c-e709-x runs E709's own program, whose o4 immediate is 0xcf5: its 39 tag-5
  words read 0xcf5, bits 5:4 set (`o4_offline.out` B; also in the fold's own
  `fold/posthoc_o4_bits.txt`, first line, low6 0x35).
- So bit 4 is kept when every output carries it (R3 markers, E709's 0xcfN) and absent when only
  o4 carries it (R4 v-a4, 92 words). No rule local to o4's word does both. What decides bits 5:4
  of the tag-5 word is what the *other* outputs wrote [infer from the two facts].
- Rests on E808 and E838's kept files. Refuted by: a tag-5 word in those 44 jobs with the marker's
  low bits cleared (none). Needs no held-out check: it is a count over frozen-run data against a
  reading stated before this count (E838, 2026-11-11).

**Correction this needs (appended, E838).** "Read at the fold": "No word of any job has bit 4 or 5
set" is wrong for c-e709-x: every word of that job has bits 5:4 set (932 tag-1 words 0xcf1 and so
on). It holds for the 34 marker-layout jobs and c-e709-y. The reading "the path that
brings o4 out clears bits 5:3" in E838's last paragraph and in Q276's 2026-11-11 note gets the
same dated note (refuted on E808's and E838's own data). Q276's question line says "with bits
5:3 clear": true of the marker jobs only; reword when the question is next narrowed.

### 1.2 What survives: nine bitwise models [infer, declared family]

Family declared in `o4_family.py` before the check: OR, AND, XOR over every subset of one
instance's o0 to o7 (765 models) and MUX(i, j) = bits 2:0 of o_i with bits 5:3 of o_j (56).
Eight kept configurations constrain them (o4 = 5, 13, 5 + bit 4, 5 + bit 5; all outputs with
bits 5:4; o1 = 12 at the source lane, E808's k3, k5, k7 rows). Survivors, 9 of 821:

| model | note |
|---|---|
| OR(o0, o3) | E838's "OR of tags": 1 or 4 |
| AND(o4, o6) | 5 and 7; 13 and 7 is 5 too |
| XOR(o0, o2, o6), XOR(o3, o5, o6) | odd count keeps the marker |
| MUX(o4; o0), (o4; o2), (o4; o3), (o4; o5), (o4; o6) | o4's low bits, another output's 5:3 |

Refuted on the way [data]: every model that reads o1 (k5 and k7 of E808 write 12 to o1 at every
instance and still read 35 to 45 tag-5 words a job, `o4_offline.out` C), o4 as written, any
even XOR (the marker would cancel).

### 1.3 Other facts read from the same files [data]

- Every tag-5 and tag-6 pair decodes to an (even x, even y) source: 1114 and 63 of 1177
  (`o4_offline.out` D); every high half is the exact coordinate of one pixel (0 exceptions), so a
  tag-5 word is not a mix of two instances' coordinates. If it is a combination, it is of one
  instance's outputs.
- An o0-only program (E808's c-rd-pa) leaves no displaced word: 1062 own, 0 other (E).
- Words whose tag no instruction wrote exist: tags 13, 14 and 15 in R3 jobs that write 1, 2 or
  12, 3 to 8 only (6, 4 and 88 words), and 5 tag-15 words in R4's c-v-a3-x, the one job whose only
  o4 word is 13 (13 OR 2 is 15; its y job has none) (F). OR-like sums of two written words do
  reach the image. This is why OR(o0, o3) is the reading I expect [infer], not a result.
- The stage's shape is the plain job, not E406's full setup: tag 2 sits on about 490 pixels and
  tag 3 on about 60 in every job, which E406's setup (ISP word 0 bit 26 or 27 and CR_REG_0148
  bit 0 as well as word 4) removes in 27 of 27. `--blk 4=0x00030001` is what the tool builds
  anyway. "E709's four-output setup" in Q276's line and E838's claim means E709's command, not
  four output dwords a pixel; worth a dated note on Q276 so nobody reads it as E406's.

No kept job changes o0, o2, o3, o5, o6 or o7, so nothing offline separates the nine.

## 2. Q276 rows: stage p5-o4 (58 jobs)

R4's p4-o4 shape, command and decode unchanged (`gen/r4_o4.py` C_BASE, marker at bits 15:6,
variant bits 5:4, x and y job a configuration, tool `~/sgxfive-test-rgn4` e6951558).

### 2.1 The walk (16 jobs, HELD OUT)

Configuration w-j, j = 0 to 7: o_j's word carries bit 4, every other output's word carries bit 5,
tags unchanged. Frozen prediction: bits 5:4 of the tag-5 words (`o4_family.out`):

| model | w-0 | w-1 | w-2 | w-3 | w-4 | w-5 | w-6 | w-7 |
|---|---|---|---|---|---|---|---|---|
| OR(o0, o3) | 3 | 2 | 2 | 3 | 2 | 2 | 2 | 2 |
| AND(o4, o6) | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 2 |
| XOR(o0, o2, o6) | 1 | 2 | 1 | 2 | 2 | 2 | 1 | 2 |
| XOR(o3, o5, o6) | 2 | 2 | 2 | 1 | 2 | 1 | 1 | 2 |

MUX(o4; o_i), i = 0, 2, 3, 5, 6, reads 1 at w-i and 2 at the seven others. Nine models, nine
different vectors. A vector that is none of them is recorded as it is: it
still says which outputs' bits reach the word, which is the next reading's input.

### 2.2 Independent rows (8 jobs, HELD OUT) and the predicate rows (24 jobs, gated)

| row | change | OR(o0,o3) | AND(o4,o6) | XOR(o0,o2,o6) | XOR(o3,o5,o6) | MUX(o4;.) |
|---|---|---|---|---|---|---|
| z-o3 | o3 = tag 0 | no tag 5, displaced tag 1 | 5 | 5 | displaced tag 1 | 5 |
| l-o4 | o4 = tag 4 | 5 | 4 | 5 | 5 | 4 |
| l-o6 | o6 = tag 3 | 5 | displaced tag 1 | displaced tag 1 | displaced tag 1 | 5 |
| n-o4 | no o4 write | 5 | none frozen | 5 | 5 | none frozen |

"Displaced tag 1": 10 to 100 tag-1 words off their own pixel, from (even, even) sources. Tag 4
is safe as a class: no tag-4 word in the 97 kept jobs of this shape.

Predicate rows, k = 0, 3, 7, both orders, x and y. Set P4 (12 jobs): `p1` writes o4 = tag 5,
`!p1` writes o4 = tag 4. Set P3 (12 jobs): `p1` writes o3 = tag 4, `!p1` writes o3 = tag 4 with
bit 4. Frozen gate: P4 is scored only if the walk's model reads o4 (AND or MUX), P3 only if it
reads o3 (OR(o0, o3), XOR(o3, o5, o6), MUX(o4; o3)); the other set is "cannot tell by design".
Gated = only the lane equal to k takes the `p1` word (the source lane is 0: the `p1` word at
k = 0, the `!p1` word at 3 and 7); ignored = the last write in both orders.

### 2.3 Controls, replicate, verdict, stop

- Controls (8 jobs, gate the stage): c-e709 (G-o4 as R4), c-u (G-o1, tag-2 fraction >= 0.98),
  **c-all4** (every output with bit 4: all nine models predict bit 4 at the tag-5 words; if it
  reads 0 the layout cannot be read and the stage is void: the control that can fail), c-v-a4
  (R4's own program again: class A, bridge to E838).
- Positive control inside the walk: in w-0 at least 95 percent of the own-pixel tag-1 words carry
  bit 4, in w-1 the tag-2 words do. Reported, not scored: where each o_j's private bit shows by
  tag (this maps tags 3, 6 and 7 for free).
- Replicate: w-3 again (2 jobs), same vector entry.
- A configuration reads a class with >= 10 words in both jobs and <= 2 of any other (R4's rule).
- Verdict: "the tag-5 word is MODEL" iff the controls pass, the 8 walk entries are decided and
  equal one frozen vector, z-o3, l-o4 and l-o6 read that model's cells, and the replicate agrees.
  Otherwise "family refuted, vector recorded" or "cannot tell" by entry.
- Stop: any fault, hang or STATUS2 not 0x400 after a reset stops the stage; a failed bridge
  control stops the session for the lead. No fault is expected (97 kept jobs of this shape, none).
- Will not close: why pair counts wander (22 to 63); where o4's own word lands if the walk says
  OR(o0, o3) (then the o4 predicate clause cannot be asked in this shape and Q276 is reworded
  to "where o4 to o7 land"; E808 already holds the predicate on o1, 29 of 29).

## 3. Q230 offline: the frozen fit is dead, the mantissa is what the words follow

Scripts: `rw_fit_alive.py`, `rw_explore.py`, `rw_band.py` and their `.out` files.

### 3.1 The frozen analysis of g4-rw cannot adopt a rule [data]

The frozen rule (`score/rwfam.py`): a model counts only after 30 of 30 FIT words. Using the 19
FIT words that were read and nothing else (the HELD OUT half is not touched by this script):
0 of the 225 frozen models reproduce all 19; best per family a 14, b 13, c 16, d 14, e 14
(`rw_fit_alive.out`). A model that misses a read FIT word cannot reach 30 of 30 whatever the 11
unread ones are. So the frozen verdict is fixed at "none: the words are recorded and no rule is
adopted", and rerunning the six jobs *to complete that test* buys nothing.
Rests on E842's kept `score-g4-rw.txt` and the frozen `rwfam.py`. Refuted by: a parsing error
only (the script imports the frozen `predict`). No held-out check needed: it is the frozen
procedure's own first step. Worth a dated note on Q230 and E842 (not a correction).

### 3.2 Exploration, post hoc, all 65 known words [infer]

- **Mantissa.** 54 distinct mantissas; 6 were read at two or three exponents (1.0625, 1.125,
  1.5, 1.59375, 1.6875, 1.75) and none shows both RZ and RZ + 1. On the grid 1 + k/32: RZ + 1 at
  k = 4, 13, 19, 22, 25, 27; RZ at 21 others; unread k = 3, 9, 17, 23 (`rw_explore.out`).
  Hypothesis **H-MANT**: word - RZ is a function of the 23-bit mantissa of w alone.
- **A wider family** (fixed-point table plus Newton steps with truncated products, 32000 models,
  declared in the script before it ran): none fits; best 49 of 54 against 42 for "always RZ".
- USSE's own `frcp` is not the same word: it returns the correctly rounded 1/3 (probe page
  frcp-frsq-precision), the TA stores RZ at w = 3 (E754).
- So no candidate rule exists to freeze. What can be frozen is H-MANT.

### 3.3 The band check that would have caught round 4's slip [data]

`rw_band.py` applies "every frozen window coordinate 32 + 32 v / w inside the viewport [0, 64]"
to R4's frozen design: it flags rw-15 to rw-20 (windows from -62.4 to 120.9) and no other job,
exactly the six whose words were not read. With x and y scaled by the job's own power-of-two
scale S (w unchanged) the same six sit at 8.4 to 54.2, and S x, S y are exact in float32.

A note on the brief: E831's band is the ZLS *store* band (x < 1.25 W). sgx-pipe does not model
the TA's clip guard band (-16 and 80 at 64 x 64, E777, E842 post hoc); `mte.rs` `band_w` refuses
any vertex outside the viewport at w other than 1. The plan therefore keeps every vertex inside
the viewport, which is `band_w`'s own condition and inside the guard band by 16 pixels.

## 4. Q230 rows: stage g5-rw (48 jobs; 28 without the dense table)

R4's g4-rw shape and scorer. New template `vtx_zws.s`: `vtx_zw.s` with o0 = S x and o1 = S y
(two `fmad` with a zero addend), so the window is that of the scale-1 job at any S.

| rows | jobs | set | frozen |
|---|---|---|---|
| rw-k0 to rw-k3, R4's programs | 4 | control | the known words exact, as E842 |
| rw-k4 (w 0.3, S 1/4), rw-k5 (w 0.7, S 1/2) | 2 | control | RZ and RZ + 1 (E795, E796) |
| q-15 to q-20: R4's quarter jobs, S 1/4 | 6 | HELD OUT | shape; RZ or RZ + 1; H-MANT 4 words |
| m-01 to m-07: rw-01 to rw-07 at S 1/2 | 7 | HELD OUT | H-MANT: R4's delta, 21 words |
| m-08 to m-14: rw-08 to rw-14 at S 16 | 7 | HELD OUT | H-MANT: R4's delta, 21 words |
| rw-07 and rw-10 unchanged | 2 | replicate | the same six words |
| d-01 to d-20: 60 new mantissas | 20 | table | RZ or RZ + 1; split by sha256 |

The two new controls test the new template at w below 1 against known words. "Shape" is 3
vertices at the frozen window and depth 0x3f000000. The m rows hold 4 and 7 RZ + 1 words of R4.
The dense table is 1 + k/64 for odd k and 28 hashed mantissas, with a FIT / HELD OUT split
frozen by sha256 for a later fit.

- Verdict H-MANT: held iff the controls pass and 42 of 42 m-words equal R4's delta (11 RZ + 1
  among them: a chance pass is out of reach); one miss refutes it, unless the replicates differ
  from R4 (then "not deterministic", cannot tell).
- The 18 q-words answer "w below 1" for the frozen assertion only.
- Stop: a control word off stops the stage. A table job without 3 vertices at the frozen window
  is void and printed as FAILED shape; three such stop the stage (the design is wrong again).
- After the run (offline, at the fold): new families are declared before any fit, fitted on the
  FIT half of all mantissas, scored on the HELD OUT half; the stop condition is R4's.
- Will not close: which mantissas store RZ + 1 (unless a family then fits), the made vertex's
  1/w, the depth formula. If H-MANT holds, sgx-pipe's `PERSPECTIVE_W` / `ALIKE_W` lists can
  become a mantissa table (a fold item, test first).

## 5. v-stock-4096: no longer matters

Its question was H-STALL against H-PHASE: does a long TA phase that progresses latch bit 7.
E839 answered it at 2048 x 2048, 2 of 2, bit 7 clear with L of 11.2 ms, 86 times the 129.5 us
threshold. A 4096 row would only stretch L further; it cannot separate anything the 2048 rows
left together. The void was a premise failure (default pages on rgn4, where R3's g-c4 set the
page count by debugfs), already disclosed in E839. Recommendation: do not rerun; no record
change. If wanted anyway it is one job with `render_pb_pages` set as g-c4 did.

## 6. Dry runs that would have caught round 4's slips, per stage

Round 4's slips were a control of another shape (o2), a scorer looking for a wrong file name
(t), and here a design note that checked z and not the window (g4-rw).

| check | p5-o4 | g5-rw |
|---|---|---|
| controls have the stage's shape | every command is C_BASE | every command is CMD |
| scorer on real kept files | R4's p4-o4 directory | R4's g4-rw directory |
| design premise | immediates re-assembled | viewport check on every job |
| mock worlds | one a model, "none", dead c-all4 | hidden mantissa rule; clipped q jobs |
| program in the simulator | not needed | `vtx_zws.s` in sgx-sim |
| runner end to end | R4's `run_mock.sh`, new tables | the same |

- Shape: a test asserts that every row of a stage, controls included, differs from the stage's
  command template only in the program name (o2's slip).
- Real files: the new o4 scorer must read class A for R4's c-v-a4 and bits 5:4 = 3 for
  c-e709-x; the 1/w scorer must reproduce R4's 42 words and six FAILED shapes byte for byte.
  A scorer that looks for a wrong file name finds nothing here and fails (t's slip).
- Premise: each o4 program is disassembled and its eight immediates compared with the table;
  the viewport check runs on every 1/w job, with R4's design as the fixture that must fail
  (done in 3.3: it flags exactly rw-15 to rw-20).
- Mock worlds: the o4 scorer must name each of the nine models, say "family refuted" for a
  tenth, and void the stage when c-all4 reads 0; the 1/w scorer must find a hidden mantissa rule
  and print FAILED shape, not "cannot tell", for q jobs clipped to 5 to 7 vertices.
- Simulator: every g5-rw program of the new template runs in sgx-sim, o0 to o3 exact.

## 7. Reuse, counts, time, risk, order

- **Reuse:** the published `render/closing-r4-pixel` framework (runner, freeze, scorekit, r4lib,
  score_o4's reader, score_rw, rwdesign, rwfam for reference, tests, mock). **New:** `r5_o4.py`
  and its model table (from `o4_family.py`), `score_o5.py`, `rwdesign5.py` (S, the m and d rows,
  the viewport assert), `r5_rw.py`, `vtx_zws.s`, the tests of section 6. Pins at main ab08eb0.
- **Jobs:** p5-o4 58, g5-rw 48: 106 (86 without the dense table, 74 without P3 either). R4 ran
  5.3 s a job (36 jobs in 190 s): about 10 minutes of jobs, 15 with staging and health.
- **Risk:** low. Userspace only, the shapes of 97 and 24 kept jobs with no fault and no hang, no
  debugfs write but `reset`, no firmware `str`, no clock-gate write, no kernel or tool build.
- **Reboot:** none if the laptop is still on the rgn4 boot (module 99CD90DA), which the bridge
  controls assume. If it has been rebooted to stock Arch, a one-shot boot of the test kernel
  needs the user's OK first.
- **Order:** p5-o4 then g5-rw; no fresh boot needed, no planned fault, so before any session
  with planned faults (render4x) and after EDM stages that want a fresh boot.
- **Build effort:** one Sonnet builder, about the size of half of R4-pixel's build.

## 8. Records to touch (at the fold, or before as dated notes)

- E838: appended correction (1.1). Q276: note (1.1 to 1.3), question line reworded after p5-o4.
- Q230 and E842: dated note (3.1, 3.2); no claim changes.
- New records after the run: one for p5-o4, one for g5-rw. Offline scripts cited through
  `scratch_cites.py --publish`.
- Lead's brief line "sgx-pipe now models the band (E831)": see 3.3; no record says otherwise.

## 9. User decisions

1. **Q276, land the offline result now** (E838 correction, Q276 note: "clears bits 5:3" refuted,
   nine models left).
   a. Yes, before the run, as dated notes and the appended correction (recommended).
   b. Only at the fold of p5-o4, with the new record.
   c. Not at all until the walk has run.
2. **Q276 rows.**
   a. Stage p5-o4 as written: walk, four independent rows, both gated predicate sets, 58 jobs
      (recommended).
   b. Without the o3 predicate set P3: 46 jobs.
   c. Walk and controls only: 26 jobs; predicate rows in a later round.
   d. No rows; Q276 stays at the offline narrowing.
3. **Q276, E406's real four-output setup** (ISP word 0 bit and CR_REG_0148 bit 0 by kpoke).
   a. Not this round: settle the plain shape first, 97 kept jobs bridge it (recommended).
   b. Add the walk in that setup too: 16 jobs more, one new knob in the runner.
4. **Q230, the frozen g4-rw analysis.**
   a. Record it as decided offline (0 of 225 on the read FIT words) and do not try to complete
      it; the 18 words are rerun for "w below 1" and H-MANT (recommended).
   b. Complete it anyway as frozen (six jobs), accepting the known verdict.
5. **Q230 rows.**
   a. Stage g5-rw with the dense table: 48 jobs (recommended; the table is the only input a
      later rule search can get).
   b. Core only (controls, q, m, replicates): 28 jobs.
   c. The six quarter jobs and controls only: 12 jobs.
   d. Park the 1/w clause; no rows.
6. **v-stock-4096.**
   a. Drop it; E839's 2 of 2 at 2048 x 2048 answers its question (recommended).
   b. One job with the page count set as g-c4, for completeness.
7. **Session.**
   a. One session r5-pixel, p5-o4 then g5-rw, on the current rgn4 boot, no reboot
      (recommended).
   b. Two sessions, Q276 first, Q230 after its fold.
   c. Fold both stages into another area's session to save a staging pass.
