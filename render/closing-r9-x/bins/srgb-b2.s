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
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0xe7ad4b00
stad [r30,+#0], r31
mov.skipinv r31, #0xb3e0c92b
stad [r30,+#1], r31
mov.skipinv r31, #0xe2f5004b
stad [r30,+#2], r31
mov.skipinv r31, #0x35d72bc9
stad [r30,+#3], r31
mov.skipinv r31, #0xb49d2bd1
stad [r30,+#4], r31
mov.skipinv r31, #0x22c48835
stad [r30,+#5], r31
mov.skipinv r31, #0xe1d3aa96
stad [r30,+#6], r31
mov.skipinv r31, #0x7e2f70e5
stad [r30,+#7], r31
mov.skipinv r31, #0xa7dd6d4e
stad [r30,+#8], r31
mov.skipinv r31, #0x511cd16a
stad [r30,+#9], r31
mov.skipinv r31, #0xf495aa7e
stad [r30,+#10], r31
mov.skipinv r31, #0xd5ae7e52
stad [r30,+#11], r31
mov.skipinv r31, #0x4d2c5ca7
stad [r30,+#12], r31
mov.skipinv r31, #0xc4564abc
stad [r30,+#13], r31
mov.skipinv r31, #0x16c98e3f
stad [r30,+#14], r31
mov.skipinv r31, #0xa838d861
stad [r30,+#15], r31
mov.skipinv r31, #0xcd5d10a5
stad [r30,+#16], r31
mov.skipinv r31, #0xe3aa8899
stad [r30,+#17], r31
mov.skipinv r31, #0xc4f76739
stad [r30,+#18], r31
mov.skipinv r31, #0xfd0fe057
stad [r30,+#19], r31
mov.skipinv r31, #0xefff1cdd
stad [r30,+#20], r31
mov.skipinv r31, #0xdb09c74f
stad [r30,+#21], r31
mov.skipinv r31, #0x30fbdd0f
stad [r30,+#22], r31
mov.skipinv r31, #0x36299246
stad [r30,+#23], r31
mov.skipinv r31, #0x04c207b6
stad [r30,+#24], r31
mov.skipinv r31, #0xfb86e8a5
stad [r30,+#25], r31
mov.skipinv r31, #0x09b6c712
stad [r30,+#26], r31
mov.skipinv r31, #0xe584e3b8
stad [r30,+#27], r31
mov.skipinv r31, #0xaaf3984f
stad [r30,+#28], r31
mov.skipinv r31, #0x34c93964
stad [r30,+#29], r31
mov.skipinv r31, #0x3c3f8f20
stad [r30,+#30], r31
mov.skipinv r31, #0x0b47ae79
stad [r30,+#31], r31
mov.skipinv r31, #0x29d7190c
stad [r30,+#32], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xade768ff
stad [r30,+#0], r31
mov.skipinv r31, #0xe0b3a7d5
stad [r30,+#1], r31
mov.skipinv r31, #0xf5e2ff68
stad [r30,+#2], r31
mov.skipinv r31, #0xd735d5a7
stad [r30,+#3], r31
mov.skipinv r31, #0x9db40fd0
stad [r30,+#4], r31
mov.skipinv r31, #0xc4224062
stad [r30,+#5], r31
mov.skipinv r31, #0xd3e1f0a4
stad [r30,+#6], r31
mov.skipinv r31, #0x2f7e441b
stad [r30,+#7], r31
mov.skipinv r31, #0xdda7c483
stad [r30,+#8], r31
mov.skipinv r31, #0x1c5143e3
stad [r30,+#9], r31
mov.skipinv r31, #0x95f4448b
stad [r30,+#10], r31
mov.skipinv r31, #0xaed52509
stad [r30,+#11], r31
mov.skipinv r31, #0x2c4d44ca
stad [r30,+#12], r31
mov.skipinv r31, #0x56c4f0ea
stad [r30,+#13], r31
mov.skipinv r31, #0xc9163b13
stad [r30,+#14], r31
mov.skipinv r31, #0x38a8cf9f
stad [r30,+#15], r31
mov.skipinv r31, #0x5dcd0f0a
stad [r30,+#16], r31
mov.skipinv r31, #0xaae32284
stad [r30,+#17], r31
mov.skipinv r31, #0xf7c4d60e
stad [r30,+#18], r31
mov.skipinv r31, #0x0ffdef08
stad [r30,+#19], r31
mov.skipinv r31, #0xffef1e01
stad [r30,+#20], r31
mov.skipinv r31, #0x09dbe98c
stad [r30,+#21], r31
mov.skipinv r31, #0xfb30442f
stad [r30,+#22], r31
mov.skipinv r31, #0x29364d3b
stad [r30,+#23], r31
mov.skipinv r31, #0xc2047242
stad [r30,+#24], r31
mov.skipinv r31, #0x86fbe35c
stad [r30,+#25], r31
mov.skipinv r31, #0xb6090ee5
stad [r30,+#26], r31
mov.skipinv r31, #0x84e5b307
stad [r30,+#27], r31
mov.skipinv r31, #0xf3aa75bc
stad [r30,+#28], r31
mov.skipinv r31, #0xc934ade0
stad [r30,+#29], r31
mov.skipinv r31, #0x3f3c7f36
stad [r30,+#30], r31
mov.skipinv r31, #0x470b1db7
stad [r30,+#31], r31
mov.skipinv r31, #0xd729b106
stad [r30,+#32], r31
idf drc0, bif
wdf drc0
shr.skipinv r1, pa0, #16
shl.skipinv r1, r1, #18
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3f000000
mov.skipinv r3, #0xbefc0000
fmad.skipinv r24, r1, r2, r3
and.skipinv r1, pa0, #0x3f
shl.skipinv r1, r1, #17
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3e000000
mov.skipinv r3, #0x3ea00000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x080e1e00
mov r21, #0xcc03f007
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
