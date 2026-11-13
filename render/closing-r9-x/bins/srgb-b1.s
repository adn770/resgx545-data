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
mov.skipinv r31, #0xc7a04b00
stad [r30,+#0], r31
mov.skipinv r31, #0x67bfc92b
stad [r30,+#1], r31
mov.skipinv r31, #0xa7f7004b
stad [r30,+#2], r31
mov.skipinv r31, #0x50e52bc9
stad [r30,+#3], r31
mov.skipinv r31, #0x773224b9
stad [r30,+#4], r31
mov.skipinv r31, #0x078afb45
stad [r30,+#5], r31
mov.skipinv r31, #0xa6d158eb
stad [r30,+#6], r31
mov.skipinv r31, #0x1bebab77
stad [r30,+#7], r31
mov.skipinv r31, #0x46facf1d
stad [r30,+#8], r31
mov.skipinv r31, #0x968f0639
stad [r30,+#9], r31
mov.skipinv r31, #0xc10e8fd5
stad [r30,+#10], r31
mov.skipinv r31, #0x6558c558
stad [r30,+#11], r31
mov.skipinv r31, #0xf8748c1b
stad [r30,+#12], r31
mov.skipinv r31, #0x49643841
stad [r30,+#13], r31
mov.skipinv r31, #0xd8ff8f18
stad [r30,+#14], r31
mov.skipinv r31, #0x84f99b91
stad [r30,+#15], r31
mov.skipinv r31, #0xf331939b
stad [r30,+#16], r31
mov.skipinv r31, #0x5c424d91
stad [r30,+#17], r31
mov.skipinv r31, #0xbaccbdbf
stad [r30,+#18], r31
mov.skipinv r31, #0xeeffa7f8
stad [r30,+#19], r31
mov.skipinv r31, #0x68d7de7f
stad [r30,+#20], r31
mov.skipinv r31, #0xd798f7ac
stad [r30,+#21], r31
mov.skipinv r31, #0xa505c567
stad [r30,+#22], r31
mov.skipinv r31, #0x697b2386
stad [r30,+#23], r31
mov.skipinv r31, #0x020e89a0
stad [r30,+#24], r31
mov.skipinv r31, #0xddb6d8ac
stad [r30,+#25], r31
mov.skipinv r31, #0xdfbdaf90
stad [r30,+#26], r31
mov.skipinv r31, #0x965b2e3b
stad [r30,+#27], r31
mov.skipinv r31, #0xfdf4a0e1
stad [r30,+#28], r31
mov.skipinv r31, #0x0f591bef
stad [r30,+#29], r31
mov.skipinv r31, #0xa5065c4c
stad [r30,+#30], r31
mov.skipinv r31, #0x2e2c82dd
stad [r30,+#31], r31
mov.skipinv r31, #0x706270e6
stad [r30,+#32], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xa0c768ff
stad [r30,+#0], r31
mov.skipinv r31, #0xbf67a7d5
stad [r30,+#1], r31
mov.skipinv r31, #0xf7a7ff68
stad [r30,+#2], r31
mov.skipinv r31, #0xe550d5a7
stad [r30,+#3], r31
mov.skipinv r31, #0x327792d5
stad [r30,+#4], r31
mov.skipinv r31, #0x8a074ae8
stad [r30,+#5], r31
mov.skipinv r31, #0xd1a67fdb
stad [r30,+#6], r31
mov.skipinv r31, #0xeb1bcaed
stad [r30,+#7], r31
mov.skipinv r31, #0xfa46ae53
stad [r30,+#8], r31
mov.skipinv r31, #0x8f96dcbe
stad [r30,+#9], r31
mov.skipinv r31, #0x0ec129c0
stad [r30,+#10], r31
mov.skipinv r31, #0x586512f8
stad [r30,+#11], r31
mov.skipinv r31, #0x74f81b10
stad [r30,+#12], r31
mov.skipinv r31, #0x64494005
stad [r30,+#13], r31
mov.skipinv r31, #0xffd83a3a
stad [r30,+#14], r31
mov.skipinv r31, #0xf9849e1f
stad [r30,+#15], r31
mov.skipinv r31, #0x31f319bf
stad [r30,+#16], r31
mov.skipinv r31, #0x425cccc2
stad [r30,+#17], r31
mov.skipinv r31, #0xccbaab7d
stad [r30,+#18], r31
mov.skipinv r31, #0xffeecfa4
stad [r30,+#19], r31
mov.skipinv r31, #0xd7686987
stad [r30,+#20], r31
mov.skipinv r31, #0x98d775b5
stad [r30,+#21], r31
mov.skipinv r31, #0x05a521b4
stad [r30,+#22], r31
mov.skipinv r31, #0x7b69c5da
stad [r30,+#23], r31
mov.skipinv r31, #0x0e02fc77
stad [r30,+#24], r31
mov.skipinv r31, #0xb6dd3bee
stad [r30,+#25], r31
mov.skipinv r31, #0xbddfe7d8
stad [r30,+#26], r31
mov.skipinv r31, #0x5b962925
stad [r30,+#27], r31
mov.skipinv r31, #0xf4fd3808
stad [r30,+#28], r31
mov.skipinv r31, #0x590fa8ef
stad [r30,+#29], r31
mov.skipinv r31, #0x06a58eda
stad [r30,+#30], r31
mov.skipinv r31, #0x2c2eaf5b
stad [r30,+#31], r31
mov.skipinv r31, #0x62708881
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
