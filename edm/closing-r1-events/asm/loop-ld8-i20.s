; SPDX-License-Identifier: MIT
; loop-ld8-i20: ITER = 20, body 8 instructions (ldad, wdf, four multiply-adds); own source for Q082 (closing2/r1-events)
phas #0, #0, pixel, end, parallel
mov.skipinv r1, #20
mov.skipinv r2, #0xFFFFFFFF
mov.skipinv r3, #0x00000003
mov.skipinv r29, #0x5CAF0000                     ; the scratch buffer's address (patched by the tool)
ldad.bypassl1 r10, [r29,+#0], drc0
wdf drc0
imae.u r4, r3.low, r3.low, r3, u32
imae.u r5, r3.low, r3.low, r3, u32
imae.u r6, r3.low, r3.low, r3, u32
imae.u r7, r3.low, r3.low, r3, u32
iadd32.skipinv.testtanz.chan0 r1, p0, r1, r2
p0 ba #0x00000005
mov.skipinv.end o0, r1
