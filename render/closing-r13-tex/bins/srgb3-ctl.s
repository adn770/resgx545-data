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
mov.skipinv r31, #0xd854fb03
stad [r30,+#0], r31
mov.skipinv r31, #0x20426005
stad [r30,+#1], r31
mov.skipinv r31, #0x87906809
stad [r30,+#2], r31
mov.skipinv r31, #0xa7295e0d
stad [r30,+#3], r31
mov.skipinv r31, #0xe6382411
stad [r30,+#4], r31
mov.skipinv r31, #0x96db3015
stad [r30,+#5], r31
mov.skipinv r31, #0x368a2218
stad [r30,+#6], r31
mov.skipinv r31, #0xf1f2051d
stad [r30,+#7], r31
mov.skipinv r31, #0x721a6622
stad [r30,+#8], r31
mov.skipinv r31, #0x223d8524
stad [r30,+#9], r31
mov.skipinv r31, #0x2cf6522b
stad [r30,+#10], r31
mov.skipinv r31, #0xd3471d2f
stad [r30,+#11], r31
mov.skipinv r31, #0x0c74e730
stad [r30,+#12], r31
mov.skipinv r31, #0x1ce3e134
stad [r30,+#13], r31
mov.skipinv r31, #0xd30f4639
stad [r30,+#14], r31
mov.skipinv r31, #0x1505893f
stad [r30,+#15], r31
mov.skipinv r31, #0x0d5d7243
stad [r30,+#16], r31
mov.skipinv r31, #0x3c00cd46
stad [r30,+#17], r31
mov.skipinv r31, #0xef39c94b
stad [r30,+#18], r31
mov.skipinv r31, #0x0612a74c
stad [r30,+#19], r31
mov.skipinv r31, #0x8e88b952
stad [r30,+#20], r31
mov.skipinv r31, #0xf7e0de55
stad [r30,+#21], r31
mov.skipinv r31, #0xb35ffe5a
stad [r30,+#22], r31
mov.skipinv r31, #0x7d20555e
stad [r30,+#23], r31
mov.skipinv r31, #0x0cb17e60
stad [r30,+#24], r31
mov.skipinv r31, #0x2ee70966
stad [r30,+#25], r31
mov.skipinv r31, #0xe8442b68
stad [r30,+#26], r31
mov.skipinv r31, #0x552ed56d
stad [r30,+#27], r31
mov.skipinv r31, #0xcb33ee72
stad [r30,+#28], r31
mov.skipinv r31, #0x4f11da76
stad [r30,+#29], r31
mov.skipinv r31, #0x1a940d78
stad [r30,+#30], r31
mov.skipinv r31, #0xdd2bb27e
stad [r30,+#31], r31
mov.skipinv r31, #0x2eceb780
stad [r30,+#32], r31
mov.skipinv r31, #0x1c6bc685
stad [r30,+#33], r31
mov.skipinv r31, #0x240b9a89
stad [r30,+#34], r31
mov.skipinv r31, #0xc777038f
stad [r30,+#35], r31
mov.skipinv r31, #0x810a7892
stad [r30,+#36], r31
mov.skipinv r31, #0xc3d41596
stad [r30,+#37], r31
mov.skipinv r31, #0x1426809a
stad [r30,+#38], r31
mov.skipinv r31, #0x98de769d
stad [r30,+#39], r31
mov.skipinv r31, #0xcc699da0
stad [r30,+#40], r31
mov.skipinv r31, #0x85c896a7
stad [r30,+#41], r31
mov.skipinv r31, #0x7f163fa9
stad [r30,+#42], r31
mov.skipinv r31, #0x858f4bad
stad [r30,+#43], r31
mov.skipinv r31, #0xb43f18b2
stad [r30,+#44], r31
mov.skipinv r31, #0x4e5de9b7
stad [r30,+#45], r31
mov.skipinv r31, #0x412e11b9
stad [r30,+#46], r31
mov.skipinv r31, #0xaf9c34bd
stad [r30,+#47], r31
mov.skipinv r31, #0xa770adc3
stad [r30,+#48], r31
mov.skipinv r31, #0xeb3c4cc6
stad [r30,+#49], r31
mov.skipinv r31, #0x741d8fc9
stad [r30,+#50], r31
mov.skipinv r31, #0x75e4f3cd
stad [r30,+#51], r31
mov.skipinv r31, #0xa5faf4d0
stad [r30,+#52], r31
mov.skipinv r31, #0x60e2a0d5
stad [r30,+#53], r31
mov.skipinv r31, #0x6926c3da
stad [r30,+#54], r31
mov.skipinv r31, #0xeaeaa9de
stad [r30,+#55], r31
mov.skipinv r31, #0xfd6092e1
stad [r30,+#56], r31
mov.skipinv r31, #0xa8d92fe7
stad [r30,+#57], r31
mov.skipinv r31, #0xd8a26de9
stad [r30,+#58], r31
mov.skipinv r31, #0xbd3b43ee
stad [r30,+#59], r31
mov.skipinv r31, #0xd52dd0f3
stad [r30,+#60], r31
mov.skipinv r31, #0x279339f4
stad [r30,+#61], r31
mov.skipinv r31, #0x575cbdfb
stad [r30,+#62], r31
mov.skipinv r31, #0x14b45afe
stad [r30,+#63], r31
idf drc0, bif
wdf drc0
and.skipinv r1, pa0, #0x3f
shl.skipinv r1, r1, #17
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3e000000
mov.skipinv r3, #0x3e800000
fmad.skipinv r24, r1, r2, r3
shr.skipinv r1, pa0, #16
shl.skipinv r1, r1, #18
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3d800000
mov.skipinv r3, #0x3ea00000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc007007
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
