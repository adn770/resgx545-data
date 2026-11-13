# c8-q078: T3 bits 11 and 12 on the twiddled 64x64 chain (Q078)

Verdict: DECODED (what is read), NOT DECIDED (why). Post hoc only: no independent held-out job.

## Inventory (searched: all probes/texture/*.toml and probes/*/ r23 words, p1132, r9-x t3)
- Twiddled/mip-on jobs with T3 bit 11 clear or bit 12 set: exactly two, both E564's tx-afilt
  an-t3b11 (T3 0x00800000) and an-t3b12 (T3 0x00801800), data texture/p1132/tx-lod/*.txt.gz,
  against the control an-ctl (0x00800800). Same jobs, same 64x64 32-bit chain, T0 0x07fc1400,
  smp2dgrad, gradient LOD 3.0 to 3.98 (ratio 8 control: level 3 for x <= 26, else 4).
- r9-x t3 (render/closing-r9-x/out/20261113-081821/t3/an-*.txt.gz): the same three images byte
  for byte (3 of 3): replicates, not held-out data.
- Strided jobs (E566's, r9-x b11/b12-s64x32) change nothing; they are not a twiddled chain.
- All other twiddled jobs have bit 11 set (E041 mips, tx-lod, tx-shapes) or bit 11 clear with
  T0 bits 26:21 = 0 (sampler.toml; mips off anyway, no information).

## Decode (counting fill: dword i = 0xD0000000 | i, so every texel is named uniquely)
Inverse map by the E561 tile law over the 7-level chain (offsets 0, 4096, 5120, 5376, 5440,
5456, 5460): 5461 dwords, 5461 distinct entries.
- Bit 11 cleared: all 2048 pixels read level 0, texel (x, y): 2048 distinct names, 2048 of 2048
  exact. The bit-11-set control reads levels 3 (864 px) and 4 (1184 px), as round(log2 lod) says.
- Bit 12 set (bit 11 set): all 2048 pixels read dword 5460 = level 6 (1x1), texel (0, 0).

## Rules (q078_rule.py, sha256 f95d5bdf...6a7f, frozen AFTER reading both images: post hoc)
- B11-LEVEL0 (level forced to 0 / mips off): 2048 of 2048 (E564), 2048 of 2048 (r9-x replicate).
- B12-LAST (last level forced): 2048 of 2048, replicate 2048 of 2048.
- Refuted rivals: stride instead of twiddle 8 of 2048; control's level with offset chain 0:
  1 of 2048; bit-10 clone (base dword) 0 of 2048; bit 12 changes nothing (control level) 0 of 2048;
  the 2048 distinct names also refute any level-3/4 reading (at most 64 and 16 texels).
- NOT separated (identical image): level forced vs mips off vs LOD bias. Bit 11: bias -k
  exact for k >= 28 eighths (101 of 129 tried). Bit 12: bias +k exact for k >= 20 eighths (109 of
  129); a constant dword 5460 (address) vs "last level" is also one image here.
- Also not separated: nearest vs bilinear. At the texel centres (fx = fy = 0) a bilinear read at
  level 0 gives the pure name, and at 1x1 four taps of one texel too; "names are pure" says
  nothing about the filter. (The control's values are blends, not names, so it filtered.)

## Why it stops here
One gradient (LOD 3..4), one size (64x64), one T0, one job per bit: every mechanism that gives
level 0 (or 6) at that LOD yields the same image. A decision needs: other LODs with bit 11
clear (smp2dreplace at LOD 0..6; a bias that passes level 0 shows LOD 2 or 5), a second chain
size (offset 5460 vs a constant), bit 12 at LOD 0 and with T0 max-level field < 6, bit 11
clear with T0 mips off (control for the field), and bits 12:11 = 10. [infer] A 2-bit LOD-mode
field (00 level 0, 01 gradient, 11 coarsest) fits the three values seen; value 10 untested.

## What would refute
B11-LEVEL0: any twiddled mip-on bit-11-clear job reading a level above 0 at some LOD.
B12-LAST: any bit-12 job reading a level other than the last (e.g. at T0 max level < 6).

## Records
E564 (data), E975 (replicates), E041 (chain), E561 (tile law), E722 (offset chain), E566.
Landed claims: E564 "bit 11 cleared reads 2048 distinct names from the start of level 0" is
confirmed and sharpened (level 0, texel (x, y)); "bit 12 set reads the constant 0xd0001554" is
the 1x1 level of the chain (dword 5460). An appended note to E975 ("read-out not decoded") and
Q078 would be warranted; sgx-sim tex.rs comment "bits 11/12 change nothing on strided" stands.

## Files (all publishable: counting-fill data and arithmetic, nothing firmware-derived)
common.py, q078_rule.py(+.sha256), score_q078.py/.out, FREEZE.log, NOTE.md.
Re-run: /Users/jtorra/src/resgx545/.venv/bin/python -I score_q078.py > score_q078.out
