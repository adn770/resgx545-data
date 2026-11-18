; SPDX-License-Identifier: MIT
; r35-pk's colour ramp (Q302), the pixel shader of every ramp row: --tri pixel with
; pds_iter_xy in pixpds (pa0 = x + 0.5, pa1 = y + 0.5 as singles, E382). X and Y as integers
; from 2^22 + v (exact: the spacing of singles at 2^22 is 0.5, so the mantissa holds 2v =
; 2X + 1), then o0 = XOR of X << {0, 8, 16, 20, 25} and Y << {4, 11, 19, 22, 29}: on the 1062
; pixels of the 64 x 64 triangle every colour is unique and each byte lane takes all 256 values
; (gen/pk.py ramp_word, tests/test_gen.py). Assembled by tools/usse-asm into bins/ramp_xy.bin.
phas #0, #0, pixel, end, parallel
mov.skipinv r4, #0x3F800000
mov.skipinv r5, #0x4A800000
fmad.skipinv r0, pa0, r4, r5
fmad.skipinv r1, pa1, r4, r5
shr.skipinv r0, r0, #1
and.skipinv r0, r0, #0x3F
shr.skipinv r1, r1, #1
and.skipinv r1, r1, #0x3F
mov.skipinv r3, r0
shl.skipinv r2, r0, #8
xor.skipinv r3, r3, r2
shl.skipinv r2, r0, #16
xor.skipinv r3, r3, r2
shl.skipinv r2, r0, #20
xor.skipinv r3, r3, r2
shl.skipinv r2, r0, #25
xor.skipinv r3, r3, r2
shl.skipinv r2, r1, #4
xor.skipinv r3, r3, r2
shl.skipinv r2, r1, #11
xor.skipinv r3, r3, r2
shl.skipinv r2, r1, #19
xor.skipinv r3, r3, r2
shl.skipinv r2, r1, #22
xor.skipinv r3, r3, r2
shl.skipinv r2, r1, #29
xor.skipinv r3, r3, r2
mov.skipinv.end o0, r3
