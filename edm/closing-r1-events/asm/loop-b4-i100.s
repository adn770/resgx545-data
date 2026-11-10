; SPDX-License-Identifier: MIT
; loop-b4-i100: ITER = 100, body 4 instructions (two multiply-adds); own source for Q082 (closing2/r1-events)
phas #0, #0, pixel, end, parallel
mov.skipinv r1, #100
mov.skipinv r2, #0xFFFFFFFF
mov.skipinv r3, #0x00000003
imae.u r4, r3.low, r3.low, r3, u32
imae.u r5, r3.low, r3.low, r3, u32
iadd32.skipinv.testtanz.chan0 r1, p0, r1, r2
p0 ba #0x00000004
mov.skipinv.end o0, r1
