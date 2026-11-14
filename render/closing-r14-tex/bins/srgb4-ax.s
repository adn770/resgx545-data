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
mov.skipinv r31, #0x53001802
stad [r30,+#3], r31
mov.skipinv r31, #0x810112c2
stad [r30,+#4], r31
mov.skipinv r31, #0xc10012b6
stad [r30,+#11], r31
mov.skipinv r31, #0x4f026cdf
stad [r30,+#12], r31
mov.skipinv r31, #0x3000491b
stad [r30,+#19], r31
mov.skipinv r31, #0x3c03fb83
stad [r30,+#20], r31
mov.skipinv r31, #0x9f005b6b
stad [r30,+#27], r31
mov.skipinv r31, #0xd8012b45
stad [r30,+#28], r31
mov.skipinv r31, #0xf4005253
stad [r30,+#35], r31
mov.skipinv r31, #0x19022ee3
stad [r30,+#36], r31
mov.skipinv r31, #0xaa007baf
stad [r30,+#43], r31
mov.skipinv r31, #0x61037990
stad [r30,+#44], r31
mov.skipinv r31, #0x8b007f31
stad [r30,+#51], r31
mov.skipinv r31, #0xbd014c2f
stad [r30,+#52], r31
mov.skipinv r31, #0x56006386
stad [r30,+#59], r31
mov.skipinv r31, #0x7c025518
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x7200ed8d
stad [r30,+#3], r31
mov.skipinv r31, #0xaf037b97
stad [r30,+#4], r31
mov.skipinv r31, #0xa400c22d
stad [r30,+#11], r31
mov.skipinv r31, #0x33010c54
stad [r30,+#12], r31
mov.skipinv r31, #0x4f004525
stad [r30,+#19], r31
mov.skipinv r31, #0x320231be
stad [r30,+#20], r31
mov.skipinv r31, #0x1900cadd
stad [r30,+#27], r31
mov.skipinv r31, #0x600349df
stad [r30,+#28], r31
mov.skipinv r31, #0x15008193
stad [r30,+#35], r31
mov.skipinv r31, #0xe5015947
stad [r30,+#36], r31
mov.skipinv r31, #0x5d00accf
stad [r30,+#43], r31
mov.skipinv r31, #0xa002e96f
stad [r30,+#44], r31
mov.skipinv r31, #0xec005f73
stad [r30,+#51], r31
mov.skipinv r31, #0x8503318f
stad [r30,+#52], r31
mov.skipinv r31, #0xba00db31
stad [r30,+#59], r31
mov.skipinv r31, #0x47017233
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0x9000d800
stad [r30,+#3], r31
mov.skipinv r31, #0x180246fe
stad [r30,+#4], r31
mov.skipinv r31, #0x3400ad23
stad [r30,+#11], r31
mov.skipinv r31, #0x0e0322bc
stad [r30,+#12], r31
mov.skipinv r31, #0x3800ba22
stad [r30,+#19], r31
mov.skipinv r31, #0x7b014eb7
stad [r30,+#20], r31
mov.skipinv r31, #0x21002f85
stad [r30,+#27], r31
mov.skipinv r31, #0xff02c3fa
stad [r30,+#28], r31
mov.skipinv r31, #0x19009e8c
stad [r30,+#35], r31
mov.skipinv r31, #0x1b037d97
stad [r30,+#36], r31
mov.skipinv r31, #0x93002393
stad [r30,+#43], r31
mov.skipinv r31, #0x2d01d349
stad [r30,+#44], r31
mov.skipinv r31, #0x8700f9a9
stad [r30,+#51], r31
mov.skipinv r31, #0xf9027411
stad [r30,+#52], r31
mov.skipinv r31, #0x2f000ae5
stad [r30,+#59], r31
mov.skipinv r31, #0x47033d23
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0xaa005a2a
stad [r30,+#3], r31
mov.skipinv r31, #0x280166be
stad [r30,+#4], r31
mov.skipinv r31, #0x92003901
stad [r30,+#11], r31
mov.skipinv r31, #0xf00279cb
stad [r30,+#12], r31
mov.skipinv r31, #0x9a00a6d3
stad [r30,+#19], r31
mov.skipinv r31, #0x8c033d7d
stad [r30,+#20], r31
mov.skipinv r31, #0xc700c996
stad [r30,+#27], r31
mov.skipinv r31, #0xe90179a5
stad [r30,+#28], r31
mov.skipinv r31, #0xa500e5cc
stad [r30,+#35], r31
mov.skipinv r31, #0x5002d8a2
stad [r30,+#36], r31
mov.skipinv r31, #0xbe00ec9a
stad [r30,+#43], r31
mov.skipinv r31, #0x72035c19
stad [r30,+#44], r31
mov.skipinv r31, #0xa800b2e5
stad [r30,+#51], r31
mov.skipinv r31, #0x51016826
stad [r30,+#52], r31
mov.skipinv r31, #0xdc0000d2
stad [r30,+#59], r31
mov.skipinv r31, #0x9c02985a
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xf00087fe
stad [r30,+#3], r31
mov.skipinv r31, #0xa60386ab
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
mov.skipinv r3, #0xbefc0000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc00703f
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r11
