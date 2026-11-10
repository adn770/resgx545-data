; SPDX-License-Identifier: MIT
; loop-b16-i56: ITER = 56, body 16 instructions (fourteen multiply-adds); own source for Q082 (closing2/r1-events)
phas #0, #0, pixel, end, parallel
mov.skipinv r1, #56
mov.skipinv r2, #0xFFFFFFFF
mov.skipinv r3, #0x00000003
imae.u r4, r3.low, r3.low, r3, u32
imae.u r5, r3.low, r3.low, r3, u32
imae.u r6, r3.low, r3.low, r3, u32
imae.u r7, r3.low, r3.low, r3, u32
imae.u r8, r3.low, r3.low, r3, u32
imae.u r9, r3.low, r3.low, r3, u32
imae.u r10, r3.low, r3.low, r3, u32
imae.u r11, r3.low, r3.low, r3, u32
imae.u r12, r3.low, r3.low, r3, u32
imae.u r13, r3.low, r3.low, r3, u32
imae.u r14, r3.low, r3.low, r3, u32
imae.u r15, r3.low, r3.low, r3, u32
imae.u r16, r3.low, r3.low, r3, u32
imae.u r17, r3.low, r3.low, r3, u32
iadd32.skipinv.testtanz.chan0 r1, p0, r1, r2
p0 ba #0x00000004
mov.skipinv.end o0, r1
