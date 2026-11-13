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
mov.skipinv r31, #0x57514b00
stad [r30,+#3], r31
mov.skipinv r31, #0x515768ff
stad [r30,+#4], r31
mov.skipinv r31, #0x63e7c92b
stad [r30,+#11], r31
mov.skipinv r31, #0xe763a7d5
stad [r30,+#12], r31
mov.skipinv r31, #0xe36a004b
stad [r30,+#19], r31
mov.skipinv r31, #0x6ae3ff68
stad [r30,+#20], r31
mov.skipinv r31, #0xd9cb2bc9
stad [r30,+#27], r31
mov.skipinv r31, #0xcbd9d5a7
stad [r30,+#28], r31
mov.skipinv r31, #0xff6cf408
stad [r30,+#35], r31
mov.skipinv r31, #0x6cff490a
stad [r30,+#36], r31
mov.skipinv r31, #0x5621d581
stad [r30,+#43], r31
mov.skipinv r31, #0x2156cb11
stad [r30,+#44], r31
mov.skipinv r31, #0x655723e9
stad [r30,+#51], r31
mov.skipinv r31, #0x57656f15
stad [r30,+#52], r31
mov.skipinv r31, #0xf6f37f51
stad [r30,+#59], r31
mov.skipinv r31, #0xf3f654b6
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0xc03c3e18
stad [r30,+#3], r31
mov.skipinv r31, #0x3cc0a5a3
stad [r30,+#4], r31
mov.skipinv r31, #0xcaff1769
stad [r30,+#11], r31
mov.skipinv r31, #0xffca6f82
stad [r30,+#12], r31
mov.skipinv r31, #0x5a06b6b6
stad [r30,+#19], r31
mov.skipinv r31, #0x065a50e4
stad [r30,+#20], r31
mov.skipinv r31, #0x1276af88
stad [r30,+#27], r31
mov.skipinv r31, #0x76122cf1
stad [r30,+#28], r31
mov.skipinv r31, #0xbc384f75
stad [r30,+#35], r31
mov.skipinv r31, #0x38bc62c0
stad [r30,+#36], r31
mov.skipinv r31, #0x40eb747f
stad [r30,+#43], r31
mov.skipinv r31, #0xeb4079b3
stad [r30,+#44], r31
mov.skipinv r31, #0x5d72cfae
stad [r30,+#51], r31
mov.skipinv r31, #0x725dc518
stad [r30,+#52], r31
mov.skipinv r31, #0xcc6a37aa
stad [r30,+#59], r31
mov.skipinv r31, #0x6acca41e
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0xa6b02d99
stad [r30,+#3], r31
mov.skipinv r31, #0xb0a6f758
stad [r30,+#4], r31
mov.skipinv r31, #0x54505b55
stad [r30,+#11], r31
mov.skipinv r31, #0x5054b796
stad [r30,+#12], r31
mov.skipinv r31, #0x818644df
stad [r30,+#19], r31
mov.skipinv r31, #0x8681c32f
stad [r30,+#20], r31
mov.skipinv r31, #0x762f73e3
stad [r30,+#27], r31
mov.skipinv r31, #0x2f76132b
stad [r30,+#28], r31
mov.skipinv r31, #0xd8448b05
stad [r30,+#35], r31
mov.skipinv r31, #0x44d89aa4
stad [r30,+#36], r31
mov.skipinv r31, #0x0a737891
stad [r30,+#43], r31
mov.skipinv r31, #0x730aeeac
stad [r30,+#44], r31
mov.skipinv r31, #0x95fc7058
stad [r30,+#51], r31
mov.skipinv r31, #0xfc953cd4
stad [r30,+#52], r31
mov.skipinv r31, #0x6f04fdc5
stad [r30,+#59], r31
mov.skipinv r31, #0x046f9274
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0xa723dd01
stad [r30,+#3], r31
mov.skipinv r31, #0x23a7f6a1
stad [r30,+#4], r31
mov.skipinv r31, #0x57d40596
stad [r30,+#11], r31
mov.skipinv r31, #0xd45717a5
stad [r30,+#12], r31
mov.skipinv r31, #0xc376c6f4
stad [r30,+#19], r31
mov.skipinv r31, #0x76c340c6
stad [r30,+#20], r31
mov.skipinv r31, #0x5c7d7908
stad [r30,+#27], r31
mov.skipinv r31, #0x7d5cf661
stad [r30,+#28], r31
mov.skipinv r31, #0xfc21d3e3
stad [r30,+#35], r31
mov.skipinv r31, #0x21fc224d
stad [r30,+#36], r31
mov.skipinv r31, #0xfd5d0eb2
stad [r30,+#43], r31
mov.skipinv r31, #0x5dfd56a3
stad [r30,+#44], r31
mov.skipinv r31, #0x8269026f
stad [r30,+#51], r31
mov.skipinv r31, #0x6982c308
stad [r30,+#52], r31
mov.skipinv r31, #0xe5f98abf
stad [r30,+#59], r31
mov.skipinv r31, #0xf9e5ed5e
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x16295913
stad [r30,+#3], r31
mov.skipinv r31, #0x29165a65
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
mov.skipinv r3, #0xbef6a000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc00703f
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
