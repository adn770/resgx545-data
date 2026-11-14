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
mov.skipinv r31, #0x3500b2a6
stad [r30,+#3], r31
mov.skipinv r31, #0x10019e9a
stad [r30,+#4], r31
mov.skipinv r31, #0xc600d220
stad [r30,+#11], r31
mov.skipinv r31, #0x14022e8a
stad [r30,+#12], r31
mov.skipinv r31, #0x22002155
stad [r30,+#19], r31
mov.skipinv r31, #0xb2036838
stad [r30,+#20], r31
mov.skipinv r31, #0x7a00e184
stad [r30,+#27], r31
mov.skipinv r31, #0x7b01e420
stad [r30,+#28], r31
mov.skipinv r31, #0xda00013b
stad [r30,+#35], r31
mov.skipinv r31, #0xc702df16
stad [r30,+#36], r31
mov.skipinv r31, #0xe000d5d6
stad [r30,+#43], r31
mov.skipinv r31, #0xa7034457
stad [r30,+#44], r31
mov.skipinv r31, #0xd2004aba
stad [r30,+#51], r31
mov.skipinv r31, #0xc001efa7
stad [r30,+#52], r31
mov.skipinv r31, #0x4500b2a4
stad [r30,+#59], r31
mov.skipinv r31, #0xd202bfc1
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x99001c21
stad [r30,+#3], r31
mov.skipinv r31, #0x5503c71d
stad [r30,+#4], r31
mov.skipinv r31, #0x58000803
stad [r30,+#11], r31
mov.skipinv r31, #0x2e01b687
stad [r30,+#12], r31
mov.skipinv r31, #0xe0006256
stad [r30,+#19], r31
mov.skipinv r31, #0xf90265ef
stad [r30,+#20], r31
mov.skipinv r31, #0x4700d693
stad [r30,+#27], r31
mov.skipinv r31, #0x67036632
stad [r30,+#28], r31
mov.skipinv r31, #0x5800508a
stad [r30,+#35], r31
mov.skipinv r31, #0xff011216
stad [r30,+#36], r31
mov.skipinv r31, #0x240010fe
stad [r30,+#43], r31
mov.skipinv r31, #0x82021f64
stad [r30,+#44], r31
mov.skipinv r31, #0x9d0019dc
stad [r30,+#51], r31
mov.skipinv r31, #0xd10307e5
stad [r30,+#52], r31
mov.skipinv r31, #0x3b007daa
stad [r30,+#59], r31
mov.skipinv r31, #0xd201454b
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0x430082eb
stad [r30,+#3], r31
mov.skipinv r31, #0x330269bb
stad [r30,+#4], r31
mov.skipinv r31, #0x67004f93
stad [r30,+#11], r31
mov.skipinv r31, #0x920362a6
stad [r30,+#12], r31
mov.skipinv r31, #0x99003c53
stad [r30,+#19], r31
mov.skipinv r31, #0xb30126c0
stad [r30,+#20], r31
mov.skipinv r31, #0xd70062b6
stad [r30,+#27], r31
mov.skipinv r31, #0x0a022766
stad [r30,+#28], r31
mov.skipinv r31, #0x53006a43
stad [r30,+#35], r31
mov.skipinv r31, #0xd103b8e1
stad [r30,+#36], r31
mov.skipinv r31, #0xa70035bf
stad [r30,+#43], r31
mov.skipinv r31, #0xeb015d8a
stad [r30,+#44], r31
mov.skipinv r31, #0x9500ca8b
stad [r30,+#51], r31
mov.skipinv r31, #0xe9020a1f
stad [r30,+#52], r31
mov.skipinv r31, #0x12007315
stad [r30,+#59], r31
mov.skipinv r31, #0x85033a63
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0xa200960b
stad [r30,+#3], r31
mov.skipinv r31, #0xee01e9f2
stad [r30,+#4], r31
mov.skipinv r31, #0xfa0034d9
stad [r30,+#11], r31
mov.skipinv r31, #0x6f02cff1
stad [r30,+#12], r31
mov.skipinv r31, #0xb200d2c3
stad [r30,+#19], r31
mov.skipinv r31, #0x6d03bc15
stad [r30,+#20], r31
mov.skipinv r31, #0x99001115
stad [r30,+#27], r31
mov.skipinv r31, #0x7101c68a
stad [r30,+#28], r31
mov.skipinv r31, #0x6e00e431
stad [r30,+#35], r31
mov.skipinv r31, #0x7902bf50
stad [r30,+#36], r31
mov.skipinv r31, #0xc100da11
stad [r30,+#43], r31
mov.skipinv r31, #0x45030884
stad [r30,+#44], r31
mov.skipinv r31, #0xc90061e8
stad [r30,+#51], r31
mov.skipinv r31, #0xbe012342
stad [r30,+#52], r31
mov.skipinv r31, #0xa100d381
stad [r30,+#59], r31
mov.skipinv r31, #0xc002f4d3
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x14006fbc
stad [r30,+#3], r31
mov.skipinv r31, #0xf003ec6e
stad [r30,+#4], r31
idf drc0, bif
wdf drc0
and.skipinv r1, pa0, #0x3f
shl.skipinv r1, r1, #17
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3e000000
mov.skipinv r3, #0x3ea00000
fmad.skipinv r24, r1, r2, r3
shr.skipinv r1, pa0, #16
shl.skipinv r1, r1, #18
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3f000000
mov.skipinv r3, #0xbef86000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc00703f
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r11
