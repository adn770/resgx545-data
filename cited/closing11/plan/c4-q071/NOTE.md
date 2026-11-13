# c4-q071: does E997's linear layout (ZLS bits 12, 16, 20 clear) explain E989?

Verdict: NO. The linear layout predicts a test on the loaded bytes at other offsets, which draws
1024 pixels; E989 drew 2048. Only H-ZEROLOAD (the test reads 0) held, 2 of 2 rows, all bytes.

## Rule (frozen before any q071-* output or dump was opened)
- File q071_rule.py, sha256 5f705c493cec7a6b2a4684291766ccab005b27e289cb0796b95d6009be4a8528
  (q071_rule.sha256, FREEZE.log). Test per E988: pixel drawn iff (byte & mask) == 0, store byte
  ^0xff where drawn, loaded buffer 73728 bytes (fill bytes: o & 0xff; lane: 0x03020100 repeating).
- H-LINLOAD-A: byte offset 64 y + x (E997's H-STRIDE index at G 1, one byte a pixel).
- H-LINLOAD-B: offset 512 slot + 32 y0 + x0 (raster inside tiles, E997's H-LIN, E988's H-RASTER).
- H-LINLOAD-C: offset 4 (64 y + x) (stencil byte as byte 0 of the H-STRIDE dword).
- H-ZEROLOAD: byte read 0 everywhere, all pass, 0xff at the twiddled 2048 bytes (E989 [infer]).
- H-TWIDLOAD (control): the base rows' model (E988 H-DEPTHORD), expected on the base rows only.
- Pass: drawn set exact and all 73728 store bytes exact (unwritten = 0xdeadbeef pattern).
- Held-out: q071-b0, q071-l1 (r10-st1 out/20261113-103934/st1/); never read before the freeze
  (only the name list). Fit/control rows: st1-b0 and st1-lane1 (E988's base rows, read for one
  format probe of st1-b0 before the freeze, scored after).

## Results (q071_score.py, q071_score.out)
- Controls st1-b0, st1-lane1: H-TWIDLOAD 2 of 2 exact; A and B each 512 extra, 512 missing
  pixels (1024 of 2048 agree), C and ZEROLOAD miss 1024 drawn pixels.
- Held-out q071-b0 and q071-l1 (observed 2048 drawn, store 0xff at all first 2048 bytes,
  deadbeef after, loaded buffer == fill pattern in both):
  - H-ZEROLOAD: HELD 2 of 2 (2048 of 2048 pixels, 73728 of 73728 bytes, both rows).
  - H-LINLOAD-A: FAILED 2 of 2 (1024 extra pixels; store 71696 / 72192 of 73728 bytes).
  - H-LINLOAD-B: same as A (same counts on these rows).
  - H-LINLOAD-C: FAILED 2 of 2 (pixels 2048 of 2048 agree by coincidence of all passing, but
    store writes at spread offsets up to 8188: 70176 / 70656 of 73728 bytes).
  - H-TWIDLOAD: FAILED 2 of 2 (1024 extra pixels).
- [infer] Any bijective offset map over bytes 0..2047 passes exactly half the pixels (one mask
  bit); 2048 drawn needs the loaded byte unread. The store (0xff over 2048 bytes) cannot tell
  layouts apart when all pixels pass.

## Other rows with a subset of bits 12/16/20 cleared
- Searched every --depth-ctl value in resgx545-data (*.txt, *.tsv, *.sh, *.py; list in
  ctl_all.txt, 56 values; r10-x tables/*.txt, r10-st1 tables/st1.txt). Clear-set rows are only
  the full triple: 0x60014 (zb-clr-f0), 0xf8e68014 (zb-all-f0), 0xf9e68014 (zb-all-f1),
  0xf8e6c00e (zb-all-load), 0xf8e6a00e (q071-b0, q071-l1). The "half alone" rows of E997 are
  the set half (15, 21-23, 27-31) and the clear triple, not a subset of 12/16/20.
- E411's single clears of 12, 16, 20 (zls/control-bits) show page counts only (constant 1.0
  fill), no layout read; no kept row separates which bit gives the linear layout, nor which
  one switches the stencil read off. [infer: only new rows (12, 16, 20 alone, pairs) can.]

## E997's rows and y (post hoc, yread.py / yread2.py, labelled [post hoc])
- E997 said the y of a row is not named. The ramp is x only in its trend, but the dumps do
  vary by row (zb-clr-f0 etc.: 38 distinct rows of 96 dwords, edge steps). Comparing with the
  control dumps (r9-x z242-c-f0/-f1, twiddled) at the control pixel (x, y): dword 96 y + x
  equals the control's value at (x, y) for 4608 of 4608 in zb-clr-f0, zb-all-f0 (f0) and
  zb-all-f1 (f1); using row y +-1 gives 4441 / 4444, +-8 3350 / 3368. So y is read, rows are
  in order with stride 96 dwords, not only x. A uniquely y-naming value exists for only 2 dwords,
  the reading rests on the edge-varying values.
## Refutation / what would change this
- H-LINLOAD would need a half image on a linear-offset pattern under this mask; E989 shows 2048.
## Records
E997 (zls), E989 (isp), E988 (zls), E985, E411. E989's claim holds as written (stencil reads 0
or the load is off). E997's "y not named" ([post hoc] sentence) would need an appended
correction: the 4608 dwords match the control by (x, y), not x only. Offered, not applied.
All files here are derived from published data only (no firmware content); publishable.
Files: q071_rule.py, q071_score.py/.out, yread.py/.out, yread2.py/.out, ctl_all.txt.
