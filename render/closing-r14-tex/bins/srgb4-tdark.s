; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The 11.32 texture maps (gen/build.py writes the three inputs from a case's spec). Run as
; probe --coords --pixels: pa0 = (y << 16) | x for each of the fill's 2048 pixels. PRE writes
; texture data into the scratch buffer (compressed and YUV blocks) and waits for it; SETUP
; builds the coordinates in r24, r25 (and r26 to r29 for a third coordinate, a LOD or
; gradients), the four state words in r20 to r23 and the T2 address in the scratch buffer;
; SMP is one sample into r10, the pixel. The scratch buffer's dword i is 0xD0000000 | i, so a
; texel read names its dword; r10 keeps 0xA0A1A2A3 when the sample writes nothing.
phas #0, #0, pixel, end, parallel
mov.skipinv r10, #0xA0A1A2A3
mov.skipinv r30, #0x5CAF0000
mov.skipinv r31, #0xa55a0202
stad [r30,+#0], r31
mov.skipinv r31, #0xa55a0002
stad [r30,+#1], r31
mov.skipinv r31, #0xa55a0203
stad [r30,+#2], r31
mov.skipinv r31, #0xa55a0200
stad [r30,+#3], r31
mov.skipinv r31, #0xa55a0002
stad [r30,+#4], r31
mov.skipinv r31, #0xa55a0303
stad [r30,+#5], r31
mov.skipinv r31, #0xa55a0000
stad [r30,+#6], r31
mov.skipinv r31, #0xa55a0100
stad [r30,+#7], r31
mov.skipinv r31, #0xa55a0102
stad [r30,+#8], r31
mov.skipinv r31, #0xa55a0001
stad [r30,+#9], r31
mov.skipinv r31, #0xa55a0101
stad [r30,+#10], r31
mov.skipinv r31, #0xa55a0000
stad [r30,+#11], r31
mov.skipinv r31, #0xa55a0001
stad [r30,+#12], r31
mov.skipinv r31, #0xa55a0100
stad [r30,+#13], r31
mov.skipinv r31, #0xa55a0300
stad [r30,+#14], r31
mov.skipinv r31, #0xa55a0100
stad [r30,+#15], r31
mov.skipinv r31, #0xa55a0098
stad [r30,+#16], r31
mov.skipinv r31, #0xa55a0074
stad [r30,+#17], r31
mov.skipinv r31, #0xa55a0175
stad [r30,+#18], r31
mov.skipinv r31, #0xa55a01bb
stad [r30,+#19], r31
mov.skipinv r31, #0xa55a0265
stad [r30,+#20], r31
idf drc0, bif
wdf drc0
and.skipinv r1, pa0, #0x3f
shl.skipinv r1, r1, #17
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3f800000
mov.skipinv r3, #0xbf7e0000
fmad.skipinv r24, r1, r2, r3
shr.skipinv r1, pa0, #16
shl.skipinv r1, r1, #18
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3f800000
mov.skipinv r3, #0xbf7c0000
fmad.skipinv r25, r1, r2, r3
mov.skipinv r26, #0x3e000000
mov r20, #0x0ffc1600
mov r21, #0x0c003003
mov r22, #0x5caf0000
mov r23, #0x00800800
smp2dreplace r10, r24, r20, r26, drc0
wdf drc0
mov.skipinv.end o0, r10
