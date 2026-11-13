# C3 (Q107 / Q038): E996's store-order rule on overflowed G = 1 jobs

Verdict: the E996 overlay rule is REFUTED for the overflowed 1024 x 768 jobs (0 of 10 held);
every rival fails too; the non-overflow control holds (6 of 6). Rule frozen before any G = 1 dump
was opened.

## Rule (frozen) and sha256
`q107_rule.py`, sha256 8863d62163db7c9fc0f5907cfe19629be96a1b3b38d2de8b7721a49e9d19ca0d
(`q107_rule.sha256`, `FREEZE.log`). RULE: G = 1 slot s = 2 ty + tx holds, whole, the G = 33 dump's
tile (slot 34 ty + tx) of the tile visited last in header order (r10-x gen/z.py header_rank, n = 4
macrotiles, 8 x 12 regions each), zero and half-zero tiles included, sign as stored (E629: sign set
iff raised, same in both G). Rivals: R-FIRST, R-RASTER (last in raster order), R-ZEROFIX (zero where
the G = 33 dump is zero at the same dword index, else RULE). Pass: all scored dwords equal.
Read before the freeze: cases.tsv (metadata), ONE G = 33 dump's length and first 16 bytes and the
G = 1 twin's length only, the E996/E628/E629 texts.

## Data
Pairs (same scene and P, all 1024 x 768, `D/dpm/partial-model-batch/dumps/depth-safe.c1` and
`.c26`, `dp-<scene>-g{1,33}-<P>-r{1,2}.depth.1.bin.gz`): z05 at 0x23, 0x28, 0x30; ramp at 0x28,
0x30 (ramp 0x30 g33 r1 in c1, r2 in c26). Fit side: the 10 G = 33 dumps (E628 read their zero
shape). Held out: the 10 G = 1 dumps. The E996 slot map applies (same address rule, 512 * (ty
(G + 1) + tx); E996's own targets were 64 x 32 to 256 x 64, so 1024 x 768 is an extension of it).
Control: E489 `D/zls/store-layout-dumps/dumps/fit-1024x768-G{0,1,2,33}-ramp{x,y}.bin.gz`.
Scorer-side handling, not a rule change: the dumps are 802816 dwords (1568 slots), so tiles of G33
slot >= 1568 (tile rows 46-47) are not in the dump; slots they own are "cannot tell" and left out.

## Results (`q107_score.out`, rerun: `python -I q107_score.py`)
Scored dwords of RULE per G = 1 dump: 61440 (ramp, z05 0x23/0x28) / 61440 (all five cells), slots
120 of 126 decidable.
- RULE: held 0 of 10 dumps. Dwords equal: z05 0x23 and 0x28 32201/61440 (60/120 slots); z05 0x30
  51968/61440 (101/120); ramp 0x28 and 0x30 51968/61440 (101/120). Run 1 and 2 give the same counts.
- R-FIRST 0 of 10, R-RASTER 0 of 10, R-ZEROFIX 0 of 10 (e.g. ZEROFIX 16341-17408 of 64256).
  The sign-masked counts equal the full counts (sign is not the cause).
- Bridge control (non overflow, E489, ramp x and y at G 0, 1, 2 from G 33): RULE held 6 of 6 (every
  dword: 40448, 64512, 88576 each); R-FIRST 0 of 6, R-RASTER 0 of 6; R-ZEROFIX 6 of 6 (a null
  rival there, the control has no zeros). So the overlay itself is sound at 1024 x 768 without
  partial renders.
- [post hoc] `q107_posthoc.py` / `.out`: in all 10 G = 1 dumps the zero stores are slots 0-28 plus
  256 dwords of slot 29 (15104 dwords, the same in every cell and run); the slots after that hold
  content identical to one common G33 tile's (the dictionary names (3,46) or (10,39), i.e. repeated
  content, not each slot's owner), 2 of 120 slots hold the owner's content in z05-0x30. So the
  zero region is a prefix of the dump (first 15104 dwords), not the G33 shape moved by the overlay,
  and the rest is not the overlay of G33 tiles.
- Noise floor: G33 r1 vs r2 equal at 766976/802816 dwords in every cell (35840 differ), so the
  G33 source is not run-exact either; RULE's failure (up to 29239 dwords) is larger in 4 cells and
  the G1 runs r1 and r2 agree with each other in score.

## Refutes / reading
Refutes: the G = 1 store of an overflowed job is not E996's overlay of the G = 33 tile contents:
slots 30+ do not hold their last-visited tile. [infer] The partial renders and final load/store
make the G = 1 store a different sequence of overlapping writes (the zero prefix of 15104 dwords
is the G = 1 count E628 already hit), so "tile order of the store" in Q107/Q038 is not settled by
E996 for jobs with partial renders. Not shown: which write order explains the G = 1 slots (the
slots after the prefix look as if one tile's content was written to many slots).
Records: E996, E628, E629, E489 (E977, E987 not needed: sign copied as stored, masked = same).
Corrections: E996's "What it does not show" already excludes larger targets; an appended note that
its rule fails for overflowed jobs at 1024 x 768 would be warranted. E628's "tile order of the
store not shown" stands. E629 unaffected.
Publishable: all files are scripts/counts over our own dumps; no firmware-derived content.
