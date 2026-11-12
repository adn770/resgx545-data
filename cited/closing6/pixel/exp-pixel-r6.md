# Round 6 proposal, area PIXEL: Q276 (where o4 to o7 go, the o4 predicate), Q230 (the 1/w word)

Planning only, 2026-11-12. Offline and read-only: nothing here touched the laptop, cachix or a
repo. Scripts and outputs are in this directory (`closing6/pixel/`); they read only published
sessions of resgx545-data (`render/closing-r4-pixel`, `render/closing-r5-pixel`,
`usse/output-room-tiles`, `usse/output-registers`), use the standard library only and hold nothing
firmware-derived, so a record may cite them after `tools/records/scratch_cites.py --publish`.
Sections 1 and 3 are offline results that were **run** here; sections 2 and 4 are the rows.

## 0. Short version

- **Q276, offline.** The own words of o4 to o7 reach no pixel of any kept image: 0 of 12143
  image words in the eight walk jobs where only o4, o5, o6 or o7 carried bit 4 (E858's data,
  positive controls 1944, 1007, 106 and 78 words for o0 to o3); no tag-8 word and no "regular"
  tag-5 to tag-7 word in 221662 marker words of E570's 68 jobs at ten target shapes; and E081's
  o4 to o7 images are pixel for pixel the image of the job before (a leftover, E373). So the
  image cannot answer "where do they land", and the predicate clause cannot be read from pairs.
- **Q276, rows.** Stage p6-rd reads each output register back inside the instance
  (`mov r10, oN`, then o0 = r10: the own pixel shows what oN held). If o4 reads back, the
  predicate clause is read per lane at the own pixel, with no pair counting. 58 jobs, plus two
  optional sets (8 and 22 jobs).
- **Q230, offline.** The fit E859 left undone was run: 512703 declared models (a wider
  table-plus-Newton family and binary32 compositions), none fits the 99 FIT mantissas; the HELD
  OUT half was not read for it. One reading of the FIT half was then frozen and tested on the
  HELD OUT half: **H-FRAC, "a mantissa whose exact 1/w lies less than half an ulp above RZ never
  stores RZ + 1", held 13 of 13** (all 8 held-out RZ + 1 words at frac >= 0.5; chance 0.4
  percent). The stored word behaves as floor(1/w + e), 0 <= e < 0.5 ulp, e erratic in the
  mantissa.
- **Q230, rows.** Stage g6-rw: local windows of 36 neighbouring mantissas at three strides (is e
  smooth in the mantissa, and on what scale), 72 words at six exponents outside -2 to 4, and
  boundary mantissas around frac 0.5. 114 jobs.
- One laptop session `r6-pixel`, userspace only, no kernel change, no build, no reboot if the
  laptop is still on the rgn4 boot (99CD90DA). 172 to 202 jobs, about 15 to 18 minutes of jobs.

## 1. Q276 offline: what the kept images decide (run)

| step | script -> output | data | status |
|---|---|---|---|
| O1 | `o47_scan.py` -> `o47_scan.out` | E858, p5-o4, 54 marker jobs | post hoc, by the walk |
| O2 | `o47_disp.py` -> `o47_disp.out` | E858, 27 configurations | exploration |
| O3 | `o47_e570.py` -> `o47_e570.out` | E570, 68 jobs, 10 shapes | post hoc |
| O4 | `o47_p3.py` -> `o47_p3.out` | E858, P3 jobs | exploration |
| O5 | `o47_mem.py` -> `o47_mem.out` | E858, walk dumps | exploration |
| O6 | `o47_e081.py` -> `o47_e081.out` | E081, 16 cases | post hoc |

### 1.1 O1: no word of o4 to o7 is in the image of the walk [data]

In walk row w-j only o_j's word carries bit 4 (every other output carries bit 5), so any image
word with the job's marker and bit 4 is, or contains by OR, o_j's word. E858 printed this for
paired words only; O1 counts every word of both images of each row:

| row | words with bit 4, by tag | words without |
|---|---|---|
| w-0 | tag 1: 1845, tag 5: 96, tag 3: 3 | 1096 |
| w-1 | tag 2: 983, tag 12: 11, tag 6: 11, tag 3: 2 | 2044 |
| w-2 | tag 3: 106 | 2941 |
| w-3 | tag 5: 72, tag 6: 6 | 3004 |
| w-4, w-5, w-6, w-7 | none | 3048, 3033, 3030, 3032 |

- 0 of 12143 words in the 8 jobs of w-4 to w-7; no word of another marker in any job.
- The same table reads every combined word: tag 5 = o0 OR o3 (E858), tag 6 = o1 OR o3, the few
  tag-3 words with bits 5:4 = 3 = o0 OR o1 (w-0, w-1, w-2 y) [infer for 6 and 3: few words].
  Every word of the 54 jobs is a word of o0 to o3 or an OR of them.
- Rests on E858's kept files. Refuted by: one marker word with bit 4 in w-4 to w-7 (none).
  Needs no held-out check: the walk's design fixes the reading and its own rows w-0 to w-3 are
  the positive controls. Not held out against a frozen prediction: a post hoc count.

### 1.2 O3: E570's ten target shapes show the same [data]

E570's shader writes all eight outputs with tags 1 to 8 (no private bit). A word is "regular" if
it sits at its source's place in another 32 x 16 tile (how o1 to o3 land, E570) and "irregular"
otherwise. Over 34 configurations (68 jobs, 64 x 64 to 256 x 128, PDS_SIZE 0 to 3), pairs:

| tag | own | regular | irregular | irregular sources |
|---|---|---|---|---|
| 1 (o0) | 64116 | 0 | 0 | |
| 2 (o1) | 0 | 14342 | 40 | |
| 3 (o2) | 2 | 3318 | 1597 | (even, even) but 4 |
| 4 (o3) | 0 | 1480 | 11 | |
| 5, 6, 7 | 0 | **0** | 1818, 247, 328 | (even, even), 2393 of 2393 |
| 8 (o7) | 0 | 0 | 0 | |

- No tag-8 word among 221662 single-image marker words (tags 1 to 7: 147078, 42439, 16905, 6244,
  6405, 1138, 1453). 8 is the one tag no OR of 1 to 4 can make.
- Tags 5 to 7 never land the regular way, at any shape: they are the irregular words from
  (even, even) sources, as E858's OR words (5 = 1|4, 6 = 2|4, 7 = 3|4 or 1|2|4) [infer: E570's
  words have no private bit, so the OR reading of its tags 5 to 7 rests on E858's walk]. The 1597
  irregular tag-3 words fit o0 OR o1 the same way.
- So a larger target does not bring o4 to o7 out either. Refuted by: a tag-8 word, or a regular
  tag-5 to tag-7 pair, in E570's data (none).

### 1.3 O6: E081's o4 to o7 counts are leftovers [data]

E081 wrote pa0 to one register oN, no o0 write, no marker, one run. Its o4, o5, o6 and o7 images
equal the image of the case before at every non-background pixel: 348 of 348, 348 of 348, 348 of
348, 312 of 312 (x) and 348, 348, 312, 276 (y). The writes added nothing; the pixels are what
earlier cases left (E373).

**Correction this needs (appended, E081).** The claim's "o1-o7 write fewer pixels (508, 604, 400,
348, 348, 348, 312)" and "203, 203, 178, 178 the instance's own pixel" are, for o4 to o7, counts
of the case before's image, not of the oN write; E081's [infer] "oN past what the task was given
reaches the bank of another tile in flight" holds for o1 to o3 only. E858's "What it does not
show" and Q276 get a dated note (1.1, 1.2); no claim of E858 changes.

### 1.4 Explorations (not results)

- O2: tag 2 lands at (-32, 0) or (+32, -16), tag 3 at (0, -16), tag 12 at (+32, -16): 12986 of
  13002, 1286 of 1303 and 64 of 64 at the source's place in the tile, none on a pixel the
  triangle covers. Tag-5 words: 523 of 523 from (even, even) sources, 502 in the source's own
  tile, 323 on triangle pixels, at x offsets 3 to 12 in pairs: another mechanism than the tile
  step [infer].
- O4: in P3 at k = 0 the x and y job hold tag-5 words on the same pixels (13 and 17), the x word
  without bit 4 and the y word with it, both halves decoding to an (even, even) source. So the
  o3 word that enters the OR is the `p1` word in the x job and the `!p1` word in the y job at one
  pixel, deterministic over two orders. A lane reading (the y job's o3 from the lane beside
  lane 0) is a hypothesis for set L3 below, not a result.
- O5: no marker word of w-4 to w-7 in the kept parameter-buffer and TA-data dumps (0 of 8 x
  1157120 dwords). Those buffers are not where the image lives; a weak zero.

### 1.5 What follows for the rows

"Where do o4 to o7's own words land" has the offline answer "on no pixel, at any shape tried".
What a run can still ask: is an o4 to o7 write **stored at all** (readable back in the instance),
and with a readable word, does the predicate gate the write. E373 shows `mov r10, oN` runs on the
hardware (it read o0 and o1), so the instance can copy oN to its own pixel.

## 2. Q276 rows: stage p6-rd (58 jobs) and two optional sets

E709's command unchanged (`C_BASE` of R5's `gen/r5_o4.py`, byte for byte), R5's word layout
(marker << 6 | bits 5:4 << 4 | tag), R5's decode (`score_o4.py`), x and y job a configuration.
TRI = the pixels whose word is their own in c-rd-0 (both jobs).

### 2.1 Readback rows rd-1 to rd-7 (14 jobs, HELD OUT)

Program rd-j: the walk row w-j (o_j with bit 4, every other output with bit 5, o1 written twice
as R5), then `mov.skipinv r10, o_j` and `mov.skipinv.end o0, r10` as the last two instructions.
Class of a configuration, read at the TRI pixels of both jobs (>= 90 percent of them one class,
the source decoding to the pixel itself unless the class says otherwise):

| class | own-pixel word | meaning |
|---|---|---|
| S | tag j + 1, bits 5:4 = 1 | o_j holds the word the instance wrote |
| A0 | tag 1, bits 5:4 = 2 | the read returned o0's word |
| A4 | tag j - 3, bits 5:4 = 2 (j >= 4) | o_j reads as o_(j-4) |
| X | fewer than 5 percent carry the job's marker | the read returned something not written here |
| O:t.b | another marker word, recorded with tag, bits and source offset | |

Frozen models, one vector over j = 1 to 7: **H-STORE** S at all seven; **H-FOUR** S at 1 to 3
and not S at 4 to 7 (four registers exist); **H-O0** A0 at all seven; **H-MOD4** S at 1 to 3, A4
at 4 to 7. A vector that is none of them is recorded as it is. No model is favoured: E373's
unwritten o1 read back what o0 had held, which fits H-O0 as well as a leftover.
The displaced words of each job are reported as in the walk (tags 2, 3, 5, 6 and 12 with their
bits, to compare with w-j of R5), not scored.

### 2.2 Controls (14 jobs; each can fail)

- c-e709, c-u, c-all4: R5's programs byte for byte, R5's gates (G-o4, G-o1 >= 0.98, 5:1).
- c-ow: o0 = tag 1 with bits 2, then o0 = tag 1 with bits 1 (`.end`): frozen "bits 1 at >= 95
  percent of own words" (the last o0 write is the pixel). If not, the stage is void.
- c-rd-0: o0 = W_A (bits 2); `mov r10, o0`; o0 = W_B (bits 3); `mov.end o0, r10`: frozen W_A at
  >= 95 percent (a read of a register known to hold its word, through r10, E373). If it reads
  W_B or neither, readback cannot be read and the stage is void.
- c-prd-0 at k = 1 and k = 7 (4 jobs): o0 = W_0 (bits 2); `xor.testtaz.chan0 !c0, p1, g25, #k`;
  `p1 or.skipinv.end o0, pa, #W_1` (bits 1). Frozen [infer from E808's o1 result]: k = 1, W_1 at
  >= 95 percent of the (odd x, even y) TRI pixels and W_0 at >= 95 percent of the others; k = 7,
  W_0 everywhere. Gates the predicate rows only.

### 2.3 Independent rows (8 jobs, HELD OUT) and the replicate (2)

- n-rd-1, n-rd-4: read o_j with **no** write to o_j. Frozen: not class S (a marker word with
  bit 4 cannot exist in the job). Reported: what an unwritten o1 and o4 read.
- x-rd-4, x-rd-5: rd-j with o_j's word tag 9 + j (13, 14): class S must show the new tag (the
  read follows the written word, not the register's number).
- Replicate: rd-4 again; same class.

### 2.4 Predicate rows by readback (20 jobs, HELD OUT, gated)

prd-j-k, j = 3 and 4, k = 0, 1, 2, 3, 7: the base words; `xor.testtaz.chan0 !c0, p1, g25, #k`
after o0; `or.skipinv o_j` with bits 0 (unpredicated); `p1 or.skipinv o_j` with bit 4; then the
readback pair. Read per lane of TRI (lane = (x & 1) | (y & 1) << 1, E808):

| model | lane k | other lanes | k = 7 |
|---|---|---|---|
| gated | bit 4 | bits 0 | bits 0 everywhere |
| ignored (the write lands) | bit 4 | bit 4 | bit 4 everywhere |
| never (the `p1` write is dropped) | bits 0 | bits 0 | bits 0 everywhere |

Frozen gate: prd-j is scored only if rd-j read class S and c-prd-0 passed; otherwise "cannot
tell by design". A lane reads a word with >= 95 percent of its TRI pixels. Verdict "the predicate
gates the o_j write" iff gated at k = 0, 1, 2, 3 and 7; four lanes at their own pixels, so no
pair count and no wandering range (E772's and E808's control problem) enters.

### 2.5 Optional set L3 (8 jobs): which instance's o3 enters the OR

R5's P3 programs p3-pa-k0 and p3-pa-k3 byte for byte (4 jobs: must read as R5, x 5:0 / y 5:1 and
5:1 / 5:1: the determinism control) and new p3-pa-k1, p3-pa-k2 (HELD OUT). Frozen: x job 5:1 at
k = 1 and 2 (its o3 word is lane 0's, R5); y job **H-Y1** 5:0 at k = 1 and 5:1 at k = 2,
**H-Y2** the reverse, **H-YN** 5:1 at both. Explains, or not, R5's undecided k = 0 rows.

### 2.6 Optional set S (22 jobs, own table p6-s, last): the walk in E406's full setup

E406's setup (`--blk 1=0x05d00200`, `--kpoke rd:9=1`, word 4 as now): tags 1 and 5 only, 27 of
27. Rows: c-s-all4 (must show E406's pattern: tag-2 to tag-4 words <= 2 a job and >= 10 tag-5
words, else the set is void), s-0 to s-7 (the walk), s-n4 (no o4 write). Frozen at the tag-5
words: **H-OR** 3, 2, 2, 3, 2, 2, 2, 2 and tag 5 at s-n4; **H-OWN4** 2, 2, 2, 2, 1, 2, 2, 2 and
no tag 5 at s-n4. Then `--kpoke rd:9=0` and c-u again (2 jobs) must pass G-o1: the restore
check. This serves Q023 (which outputs the setup shows), not Q276's line; it needs `kpoke` in
the runner's allowed knobs (R5's guard forbade it) and E406 saw hangs only at 5 to 7 data rows.

### 2.7 Stop, verdict, what it will not close

- Stop: R5's (fault, hang, STATUS2 not 0x400 after a reset, failed health); a failed bridge
  control or c-ow / c-rd-0 stops the session for the lead. No fault is expected in p6-rd (the
  command of 155 kept clean jobs of R3 to R5; only `mov` from an o register is new, run in E373).
- Verdict line: the rd vector's model; then per j the predicate verdict or "cannot tell".
- If rd-4 is not S, the o4 write has no observable effect in this command (no pixel, no
  readable word) and the predicate clause of Q276 cannot be asked by any run known: propose to
  retire the clause as "not observable" (user decision 3).
- Will not close: why o0 and o3 combine and at which pixels; the pair counts; the setup's rows
  unless S runs.

## 3. Q230 offline: the fit, and H-FRAC held out (run)

Scripts: `rw6_data.py` (loader), `rw6_look.py`, `rw6_fit.py`, `rw6_hfrac.py`,
`rw6_sepchance.py` and their `.out` files; hashes `rw6_fit.sha256`, `rw6_hfrac.sha256`.

**Split.** HELD OUT = the 30 dense-table mantissas E859's frozen hash marked HELD OUT
(`score/rwdesign5.py` `split()`, column `half` of `score-g5-rw.txt`). FIT = the other 100
mantissas (all explored before: E851, E859 section C). `rw6_data.load()` does not parse a HELD
OUT row's word. Disclosure: `fold/posthoc_r5.txt` prints all 130 deltas unlabelled and I read
that file; I computed nothing on a HELD OUT mantissa before the freeze below.

### 3.1 The fold-time fit: no model [data]

Families declared in `rw6_fit.py` before it ran (hash and time in `rw6_fit.sha256`; a shift
bug was fixed before any score was printed): A, table plus Newton-Raphson wider than E851's
(index 4 to 10 bits, three table points, three entry roundings, 1 or 2 steps, separate
truncations of the two products 24 to 36 bits, exact or one's-complement `2 - v`, two final
cuts: 511056 models); B, binary32 compositions (reciprocal of reciprocal, one Newton step from
a p-bit quotient in three forms, every rounding: 1539); C, RZ of 1/w' with w cut to 12 to 23
bits (108). On the 99 FIT mantissas (w = 1 left out, 15 RZ + 1): **0 of 512703 fit**; best of B
and C 89 of 99 against 84 for "always RZ". Step 2 (HELD OUT) had nothing to score and did not
run. Rests on E842, E859. Refuted by: a parsing error only. The dense table's HELD OUT half
stays unread for model fits.

### 3.2 H-FRAC: read on FIT, frozen, held on HELD OUT [data]

With frac = the fractional part of 2^47 / M (how far the exact 1/w lies above RZ, in ulp of the
stored word), on FIT only (`rw6_look.out`): 0 of 51 mantissas with frac < 0.5 store RZ + 1; the
15 RZ + 1 have frac 0.583 to 0.995; share by frac decile from 0.5: 1 of 13, 2 of 11, 2 of 8,
3 of 9, 7 of 8. Frozen in `rw6_hfrac.predictions.txt` (sha256 a1424db9..., 11:23:33Z) before
`rw6_hfrac.py` ran: "no HELD OUT mantissa with frac < 0.5 stores RZ + 1", with its cannot-tell
rule. Result (`rw6_hfrac.out`, counts only): 30 mantissas, 13 with frac < 0.5, 8 RZ + 1, **0
of them below 0.5: H-FRAC HELD**; the chance of that with the delta independent of frac is
0.0042. Reported: RZ + 1 share 2 of 7 in [0.5, 0.75) and 6 of 10 in [0.75, 1).

- What it shows: the stored word is floor(1/w + e) with 0 <= e < 0.5 ulp, or the same thing
  said as a round-to-nearest of an under-estimate [infer: the bound 0.5 is the FIT set's own
  cut; the smallest RZ + 1 frac read is 0.583]. e is not smooth across the table (FIT: e < 0.06
  at 1.0625, e >= 0.42 at 1.0696, e >= 0.09 at 1.09375).
- Refuted by: one RZ + 1 word at a mantissa with frac < 0.5 (none of 64). The held-out half was
  used once, for counts; a second use on H-FRAC variants would not be held out.
- Use: a simulator could give RZ for an unread mantissa with frac < 0.5 (half of all mantissas).
  I would wait for g6-rw's new words, which test it again (decision 6).

### 3.3 What the rows must ask

Which mantissas store RZ + 1 is "where is e(M) >= 1 - frac(M)". A blind search has failed three
times (225, 32000, 512703 models). The data that would give a family its shape is **how e
varies between neighbouring mantissas**: if e is locally constant, the words of a window of
neighbours are split exactly by a threshold on frac (delta = [frac >= 1 - e]), and the stride
at which that stops is the scale of the algorithm's table. `rw6_sepchance.out`: if e were
independent between neighbours, 18 words are separable by chance in 26 percent of windows, 36
words in 3.3 to 5.2 percent; so windows hold 36 words and each stride has two.

## 4. Q230 rows: stages g6-rwa (8 jobs) and g6-rw (106 jobs)

R5's g5-rw command, template `vtx_zws.s`, design module and scorer (`rwdesign5.py`,
`score_rw5.py`): w = C x + D exact, o0 = S x, o1 = S y, every vertex inside the viewport
asserted by the generator. A job (n1, j) at scale S stores the mantissas n1, n1 + 3j, n1 + 12j.

| rows | jobs | set | frozen |
|---|---|---|---|
| rw-k0 to rw-k5, R5's programs | 6 | control (g6-rwa) | the known words exact |
| d-01, d-02 of R5, byte for byte | 2 | control (g6-rwa) | R5's six words (2 RZ + 1) |
| L: windows, strides 1, 2^8, 2^16, two bases each | 72 | HELD OUT | H-FRAC; H-SMOOTH per stride |
| E: 4 of R4's rows at S = 2^-12, 2^-6, 2^-3, 2^5, 2^8, 2^12 | 24 | HELD OUT | shape; H-MANT |
| B: mantissas with frac 0.42 to 0.62 | 8 | HELD OUT | H-FRAC; reported by frac |
| two L jobs again | 2 | replicate | the same six words |

- **L.** Window (base Bw, stride s): jobs n1 = Bw + i s for i = 0, 1, 2, 6, 7, 8, 21, 22, 23,
  27, 28, 29 with j = s: 36 mantissas Bw + o s, o in 0 to 41. Bases from sha256 of
  `r6-rw-win-<n>`, S = 1, the whole window inside [2^23, 2^24) and clear of the 130 read
  mantissas. Frozen per window: "separable" iff every RZ + 1 word has a larger frac than every
  RZ word; scored only with >= 4 RZ + 1 words and >= 4 RZ words above 0.5 (else cannot tell).
  **H-SMOOTH(s)** held iff both windows of the stride are separable (chance <= 0.3 percent if e
  were independent), refuted iff both have an inversion, mixed otherwise. No stride is
  predicted to hold: the two outcomes at s = 1 (e locally constant, or e set by the low bits)
  point at different algorithm families, which is what the row is for. H-FRAC is scored on all
  216 words (about 108 below 0.5 expected).
- **E.** The 4 rows of rw-01 to rw-14 (E842) with the most RZ + 1 words, ties by name, at six
  scales: 72 words at exponents -12, -6, -3, 5, 8 and 12. H-MANT (the mantissa's delta of E842,
  held at -1 and 4 in E859) per exponent: held iff 12 of 12; an exponent whose jobs fail the
  shape (3 vertices at the frozen window) is "no object at this exponent", recorded, not a
  refutation. -3 and 5 sit next to the read range so that a failure far out can be placed.
- **B.** Eight jobs found by a frozen search for (n1, j) whose three mantissas all have frac in
  [0.42, 0.62): 24 words on both sides of H-FRAC's cut. Reported: the smallest frac that stores
  RZ + 1.
- Gate: g6-rwa's eight controls exact before g6-rw runs. Stop: a control word off, three
  FAILED shapes among L and B (the design is wrong), R5's fault and health stops.
- After the run (fold, offline): each separable window gives an interval for e; a family is
  declared from the scale found, before any fit, fitted on FIT (now with L and B), scored on
  the dense table's HELD OUT half, which is still unread for fits.
- Will not close: the rule itself unless the family then fits; the made vertex's 1/w; the depth
  formula.

## 5. Dry runs, mocks, slips designed out

| check | p6-rd (and L3, S) | g6-rw |
|---|---|---|
| controls have the stage's shape | `C_BASE` + program (S: own table) | `CMD` + program |
| scorer on real kept files | R5's p5-o4: w-j reads "not S" | R5's 126 words byte for byte |
| design premise | programs disassembled, last two lines | viewport, exactness, windows |
| program in the simulator | every rd / prd program in sgx-sim | every new program, o0 to o3 |
| mock worlds | list M-P below | list M-G below |
| dump name the scorer reads | a fake-tool file and a real R5 file | the same |

- **M-P (mock worlds, p6-rd):** H-STORE, H-FOUR, H-O0, H-MOD4 and a fifth vector; gated, ignored
  and never; a dead c-rd-0; a c-ow where the first write wins. Each must give its own verdict.
- **M-G (mock worlds, g6-rw):** e smooth in the mantissa, e hashed, one RZ + 1 below frac 0.5,
  a delta that depends on the exponent, jobs clipped at S = 2^12 (FAILED shape, not a miss).
- **Design premise, g6-rw:** every window is disjoint from the 130 read mantissas and inside
  [2^23, 2^24); R4's design stays the fixture the viewport check must flag.

- **No timing in any mock.** The fake tool is a pure function of its argv and program bytes
  (R5-pixel's `fake_o4.py` / `fake_rw.py` pattern); no ring window, no sleep, no clock read.
  `tests/run_all.sh` must pass under load (run it once with a busy loop on every core).
- **Laptop paths.** Run, stage, out and work dirs under `~/scratch/r6p/` only; work dirs by
  `mktemp -d ~/scratch/tmp/r6p.XXXXXX`, removed after each job is copied; a free-space check
  per job (200 MB, HACKING.md); nothing in `/tmp`. A test greps the runner for `/tmp`.
- **Control shape (R4's o2 slip).** A test asserts each row differs from its stage's command
  only in the program name; S's rows differ from p6-rd's by the two frozen options only.
- **Scorer file names (R4's t slip).** The scorer runs on R5's real kept directory in the tests.
- **Leftovers (E373, O6).** Every class is counted on words carrying the job's own marker; the
  X class exists so that a leftover is named, not misread.

## 6. Reuse, counts, time, risk, order

- **Reuse:** the published `render/closing-r5-pixel` session (runner, freeze, scorekit, r4lib,
  `score_o4.py` decode, `o5model.py` words, `rwdesign5.py`, `score_rw5.py`, tests, mock). **New:**
  `r6_rd.py` and `score_rd.py` (classes at own pixels, per-lane read), `rwdesign6.py` (windows,
  E and B rows), `score_rw6.py` (separability, per-exponent H-MANT, H-FRAC), the path change to
  `~/scratch/r6p/`, the tests of section 5. Pins at main d3de0b1.
- **Jobs:** p6-rd 58, L3 8, S 22, g6-rwa 8, g6-rw 106: 202 (172 without S and L3). R5 ran 106
  jobs in about 9 minutes: 15 to 18 minutes of jobs, 25 to 30 with staging and health.
- **Risk:** low. Userspace only; the commands of 155 and 72 kept clean jobs; no debugfs write
  but `reset`; no firmware `str`, no clock-gate write, no kernel or tool build. S adds one
  `kpoke` (render details dword 9, as E406's 27 clean jobs) with a restore and a check.
- **Reboot:** none if the laptop is still on the rgn4 boot (99CD90DA), which the bridge
  controls assume. If it has gone back to stock Arch, a one-shot boot of the test kernel needs
  the user's OK first.
- **Order:** p6-rd, (L3), g6-rwa, g6-rw, (S last). No fresh boot needed, no planned fault: before
  any session with planned faults.
- **Build:** one Sonnet builder; about the size of R5-pixel's build.

## 7. Records to touch

- Before the run (offline fold): one record for Q276 (O1, O3, O6; E081's appended correction
  of 1.3; dated notes on E858 and Q276), one for Q230 (3.1, 3.2; dated note on E859: "no fit
  family was declared at the fold" now has its fit; Q230's line gains H-FRAC).
- After the run: one record for p6-rd (L3, S if run), one for g6-rw.
- sgx-pipe: no change now; H-FRAC as a rule for unread mantissas is decision 6; the mantissa
  table grows by the new words at the fold (test first).

## 8. User decisions

1. **Land the offline results now** (Q276: o4 to o7 on no pixel, E081 correction; Q230: the fit
   with no model, H-FRAC held out 13 of 13).
   a. Yes, as two records and the appended correction before the freeze, so that the
      predictions cite landed text (recommended).
   b. Only with the session's fold.
   c. Q230's only; hold Q276's until p6-rd has run.
2. **Q276 rows.**
   a. p6-rd as written, 58 jobs: readback rd-1 to rd-7, controls, independent rows, predicate
      rows on o3 and o4 by readback (recommended).
   b. Without the predicate rows: 34 jobs; the predicate in a later round if rd-4 reads S.
   c. No rows; Q276 narrowed to the offline answer.
3. **Q276 if o4 does not read back** (rd-4 not class S).
   a. Retire the predicate clause as not observable in this command and keep "where the words
      go" answered by the offline record and the rd vector (recommended).
   b. Keep the clause open for the E406 setup (set S or a later round).
4. **Optional set L3** (which instance's o3 enters the OR; 8 jobs).
   a. Run it: it is the one unexplained reading of R5 and costs 45 seconds (recommended).
   b. Skip.
5. **Optional set S** (the walk in E406's full setup; 22 jobs, one `kpoke`, serves Q023).
   a. Run it last in the session, with the restore check (recommended: the plain shape is now
      settled, which was round 5's reason to wait).
   b. Not this round.
   c. A later session of its own.
6. **H-FRAC in sgx-pipe** (RZ for an unread mantissa with frac < 0.5).
   a. After g6-rw, if its new words below 0.5 are all RZ (about 108 expected); until then the
      table of read mantissas only (recommended).
   b. Now, on 64 of 64.
   c. Never: read mantissas only.
7. **Q230 rows.**
   a. g6-rwa and g6-rw as written, 114 jobs: L at three strides, E at six exponents, B
      (recommended).
   b. L at strides 1 and 2^16 only, E, no B: 82 jobs.
   c. E only (the exponent seed) with the controls: 32 jobs.
   d. No rows; Q230's 1/w clause stays at H-FRAC and the table.
8. **Session.**
   a. One session r6-pixel on the current rgn4 boot, no reboot, files under `~/scratch/r6p/`
      (recommended).
   b. Two sessions: Q230 first (no new instruction form), Q276 after its fold.
