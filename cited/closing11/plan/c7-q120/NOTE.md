# c7-q120: Q120, the 'fewer dwords' layouts of formats 5, 6 and 7 (offline, round 11)
Verdict: PARTIAL decode. Format 6 under constant rows and format 7 under a constant stencil
decode byte for byte; formats 5, 7 under an index stencil and format 6's edge tiles do not.

## Rules (frozen: c7_rule.py, sha256
4d87c5ad9082cbcd3045e5b3f776df305ba81246633c5c817e7cb4d57a94342c; FREEZE.log; score.py
sha d7eb408b... frozen with it)
- F6C: a format-6 tile block (512 dwords, E985's block order) is 4 groups of 12 dwords, 4 tile
  rows each, when every pixel of the 4 rows is equal (the row's format-0 float v, sign not set).
  Row r (mod 4) writes 0x9e, v LE, 0x00 at byte 6 + {0,20,8,28}[r]; bytes 46, 47 are 0x9e and
  the low byte of v of row 2; mask words 0x3f000000 sit at dwords {1:0, 0:3, 2:5, 3:10}[r].
- F7K: with a constant stencil fill S, format 7 stores 12 dwords at the start of each 256-dword
  block, the 48 bytes TEMPLATE = ASBASBASBASBASBABASBASBASBASBASBSBASBASBASBASBAS
  (A = 0x3f, B = 0x1f, S = fill). The template is not period 3: a one-byte shift sits at bytes
  15..17 and 31..33 [infer: the f3 address rule's 17-byte period reappears].
- Rivals: F6RAW (E985's raw format 6 on the same dwords); F7K with S fixed at 0xa5.

## Data and the split
Jobs: z2y-f6 (y ramp, 64 x 32), z2e-f6 (40 x 20 edge), z2d-f6, z2x-f7-{s00,sff,sa5}, in
resgx545-data/render/closing-r10-zls/out/20261113-102039/zst2 (E986). Fit: z2y-f6 block 0,
z2x-f7-sa5. NOT blind: before the freeze I printed all four z2y-f6 blocks, z2y-f5 block 0,
z2y-f7 block 0, z2e-f6 block 1 and the symbol positions of z2x-f7 s00/sff blocks 0 and 1 (E986's
look.out showed the first dwords). So z2y-f6 blocks 1, 2 are structurally seen; the truly
unread parts are z2x-f7 s00/sff blocks 2, 3 and the 'no other dword changes' test.

## Results (score.out; dwords)
- F6C z2y-f6: fit block 0 4 of 4 groups held (48 of 48 dwords). Held-out: blocks 1 and 2, 2
  applicable groups each, 4 of 4 held (48 dwords); F6RAW 0 equal on all of them.
  Not predicted by F6C: block 1 groups 2-3 (24), block 2 groups 2-3 (32), block 3 (60): 116
  of 212 changed dwords.
- F6C z2e-f6, z2d-f6: no applicable group (z2d: every row has 32 values; z2e: rows ramp), so
  cannot tell: z2e-f6's three compressed blocks (852 dwords) stay undecoded.
- F7K: sa5 fit 48 of 48; s00 and sff held-out 48 of 48 each, no changed dword outside the 4 x
  12; the S-free rival fails 0 of 48 on both.
  Fills 3f and 1f (S equal to a marker) were not run. Plane x only
  (y, d planes run the index fill).
- Format 7 under the index stencil (784 dwords, y/d planes; 2064 at 96 x 48; z2d-f7 equals the
  r9 x-ramp dump, z2y-f7 differs in 13 dwords of the sparse marker words): NOT decoded.
  Only that the dwords are stencil lane-0 bytes in row groups, 3f/1f markers between them.
- Format 5 (z2y-f5, 988 dwords; z2d-f5 is bytewise f3): NOT decoded. Its first dwords repeat
  F6C's (559e0000 003e8155 3f000000) with the stencil bytes as 1 dword each between them.

## [post hoc] (posthoc.py, posthoc.out; fitted after reading blocks 1, 2)
Rule B: a row of v for 32 - n pixels and v + 1 for the last n gives record v and mask
0x3f000000 | 1 << (24 - n) (n = one-hot of the last-pixel run, 0 -> plain 0x3f000000). Block
1 groups 2, 3 (n = 1, 3, 0, 7 and 9, 0, 13, 15): 4 of 4 groups, 48 of 48 dwords. Total post
hoc decoded for z2y-f6: 120 of 212 (block 2's deviants step v - 1 and the stream turns
variable length, so groups 2-3 of block 2 and block 3 stay undecoded; z2e-f6's stream is a
byte-unaligned variable-length run of floats with 3f/c0 markers).

## What would refute it
A second y-ramp job at another size or origin whose constant 4-row group is not that template;
a constant fill 0x3f or 0x1f for F7K; F6C on a plane with equal rows in a different tile.

## Records and notes
Rests on E985, E986 (E978 for the r9 dumps). [infer] the format is a plane/run compression with
a count mask; no mechanism known. No landed claim needs correction: E986's 'compressed form
keyed by the row's values' is consistent (the key is the row's equality). Q120's text could
append: F6C and F7K layouts. All files are publishable (no closed-source content).
Rerun: PYTHONPATH=. .venv python -B score.py (score.py imports lib.py; -I cannot find lib).
