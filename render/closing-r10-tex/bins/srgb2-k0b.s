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
mov.skipinv r31, #0x59370d1e
stad [r30,+#0], r31
mov.skipinv r31, #0x8bfbebb2
stad [r30,+#1], r31
mov.skipinv r31, #0x27b63316
stad [r30,+#2], r31
mov.skipinv r31, #0x84f4fef0
stad [r30,+#3], r31
mov.skipinv r31, #0x2c83233c
stad [r30,+#4], r31
mov.skipinv r31, #0x60a4a7ba
stad [r30,+#5], r31
mov.skipinv r31, #0x60663c2c
stad [r30,+#6], r31
mov.skipinv r31, #0x36a8e4b1
stad [r30,+#7], r31
mov.skipinv r31, #0xf3712934
stad [r30,+#8], r31
mov.skipinv r31, #0xb001dbda
stad [r30,+#9], r31
mov.skipinv r31, #0x56a10b2d
stad [r30,+#10], r31
mov.skipinv r31, #0x8b88a9cd
stad [r30,+#11], r31
mov.skipinv r31, #0xdf9e1204
stad [r30,+#12], r31
mov.skipinv r31, #0x7c78b8d9
stad [r30,+#13], r31
mov.skipinv r31, #0x57460d37
stad [r30,+#14], r31
mov.skipinv r31, #0x230befe2
stad [r30,+#15], r31
mov.skipinv r31, #0x86b72c29
stad [r30,+#16], r31
mov.skipinv r31, #0x77dae1bf
stad [r30,+#17], r31
mov.skipinv r31, #0xa95e303b
stad [r30,+#18], r31
mov.skipinv r31, #0x40fdebc8
stad [r30,+#19], r31
mov.skipinv r31, #0xbabc1921
stad [r30,+#20], r31
mov.skipinv r31, #0xf7ede0e6
stad [r30,+#21], r31
mov.skipinv r31, #0xd7161721
stad [r30,+#22], r31
mov.skipinv r31, #0x9f89eac3
stad [r30,+#23], r31
mov.skipinv r31, #0x2ff92d0f
stad [r30,+#24], r31
mov.skipinv r31, #0x838fafeb
stad [r30,+#25], r31
mov.skipinv r31, #0x2ee60c27
stad [r30,+#26], r31
mov.skipinv r31, #0x0b22a6e0
stad [r30,+#27], r31
mov.skipinv r31, #0xd4da3031
stad [r30,+#28], r31
mov.skipinv r31, #0x5ba0ddaa
stad [r30,+#29], r31
mov.skipinv r31, #0xda820b10
stad [r30,+#30], r31
mov.skipinv r31, #0x875ff5b1
stad [r30,+#31], r31
mov.skipinv r31, #0x0fbb0a19
stad [r30,+#32], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x3759edf6
stad [r30,+#0], r31
mov.skipinv r31, #0xfb8b519d
stad [r30,+#1], r31
mov.skipinv r31, #0xb62749ca
stad [r30,+#2], r31
mov.skipinv r31, #0xf4842213
stad [r30,+#3], r31
mov.skipinv r31, #0x832c0ad7
stad [r30,+#4], r31
mov.skipinv r31, #0xa4609790
stad [r30,+#5], r31
mov.skipinv r31, #0x6660c9e0
stad [r30,+#6], r31
mov.skipinv r31, #0xa83627bc
stad [r30,+#7], r31
mov.skipinv r31, #0x71f35529
stad [r30,+#8], r31
mov.skipinv r31, #0x01b015fa
stad [r30,+#9], r31
mov.skipinv r31, #0xa1560f16
stad [r30,+#10], r31
mov.skipinv r31, #0x888b7385
stad [r30,+#11], r31
mov.skipinv r31, #0x9edfd8d2
stad [r30,+#12], r31
mov.skipinv r31, #0x787ca292
stad [r30,+#13], r31
mov.skipinv r31, #0x46570566
stad [r30,+#14], r31
mov.skipinv r31, #0x0b23380a
stad [r30,+#15], r31
mov.skipinv r31, #0xb786ebba
stad [r30,+#16], r31
mov.skipinv r31, #0xda77f5f3
stad [r30,+#17], r31
mov.skipinv r31, #0x5ea99ba9
stad [r30,+#18], r31
mov.skipinv r31, #0xfd40cd45
stad [r30,+#19], r31
mov.skipinv r31, #0xbcba2883
stad [r30,+#20], r31
mov.skipinv r31, #0xedf70621
stad [r30,+#21], r31
mov.skipinv r31, #0x16d79e05
stad [r30,+#22], r31
mov.skipinv r31, #0x899f9204
stad [r30,+#23], r31
mov.skipinv r31, #0xf92fc4fa
stad [r30,+#24], r31
mov.skipinv r31, #0x8f83a478
stad [r30,+#25], r31
mov.skipinv r31, #0xe62e2e7b
stad [r30,+#26], r31
mov.skipinv r31, #0x220b69b2
stad [r30,+#27], r31
mov.skipinv r31, #0xdad4cac7
stad [r30,+#28], r31
mov.skipinv r31, #0xa05b154d
stad [r30,+#29], r31
mov.skipinv r31, #0x82daf6bc
stad [r30,+#30], r31
mov.skipinv r31, #0x5f873d88
stad [r30,+#31], r31
mov.skipinv r31, #0xbb0f0f7a
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
