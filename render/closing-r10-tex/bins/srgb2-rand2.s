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
mov.skipinv r31, #0x0fc8f9c6
stad [r30,+#0], r31
mov.skipinv r31, #0xc807a267
stad [r30,+#1], r31
mov.skipinv r31, #0x4cc414b8
stad [r30,+#2], r31
mov.skipinv r31, #0xaa4e456c
stad [r30,+#3], r31
mov.skipinv r31, #0x6a631b44
stad [r30,+#4], r31
mov.skipinv r31, #0xdb444904
stad [r30,+#5], r31
mov.skipinv r31, #0xf9b3f29e
stad [r30,+#6], r31
mov.skipinv r31, #0xf7aa2ff0
stad [r30,+#7], r31
mov.skipinv r31, #0x09f17026
stad [r30,+#8], r31
mov.skipinv r31, #0x5e681018
stad [r30,+#9], r31
mov.skipinv r31, #0x17746b02
stad [r30,+#10], r31
mov.skipinv r31, #0xd4ff6487
stad [r30,+#11], r31
mov.skipinv r31, #0x5a717466
stad [r30,+#12], r31
mov.skipinv r31, #0xb244d5ac
stad [r30,+#13], r31
mov.skipinv r31, #0x6fa86bce
stad [r30,+#14], r31
mov.skipinv r31, #0x5bcd33e3
stad [r30,+#15], r31
mov.skipinv r31, #0x0f4c0267
stad [r30,+#16], r31
mov.skipinv r31, #0x420e9184
stad [r30,+#17], r31
mov.skipinv r31, #0x648fd154
stad [r30,+#18], r31
mov.skipinv r31, #0x3e0e75a8
stad [r30,+#19], r31
mov.skipinv r31, #0x6622a585
stad [r30,+#20], r31
mov.skipinv r31, #0xb0c04520
stad [r30,+#21], r31
mov.skipinv r31, #0x088ede2b
stad [r30,+#22], r31
mov.skipinv r31, #0x2222f768
stad [r30,+#23], r31
mov.skipinv r31, #0x33b59ffc
stad [r30,+#24], r31
mov.skipinv r31, #0x81e21361
stad [r30,+#25], r31
mov.skipinv r31, #0x1ab296a2
stad [r30,+#26], r31
mov.skipinv r31, #0x90ac2557
stad [r30,+#27], r31
mov.skipinv r31, #0x9eda5c68
stad [r30,+#28], r31
mov.skipinv r31, #0xae5bf62a
stad [r30,+#29], r31
mov.skipinv r31, #0xb4abddd1
stad [r30,+#30], r31
mov.skipinv r31, #0x6c3cc652
stad [r30,+#31], r31
mov.skipinv r31, #0xcbf1a4e4
stad [r30,+#32], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xc80fece2
stad [r30,+#0], r31
mov.skipinv r31, #0x07c8e6b2
stad [r30,+#1], r31
mov.skipinv r31, #0xc44c9c51
stad [r30,+#2], r31
mov.skipinv r31, #0x4eaa3e9e
stad [r30,+#3], r31
mov.skipinv r31, #0x636a27de
stad [r30,+#4], r31
mov.skipinv r31, #0x44db48e8
stad [r30,+#5], r31
mov.skipinv r31, #0xb3f99b48
stad [r30,+#6], r31
mov.skipinv r31, #0xaaf7b209
stad [r30,+#7], r31
mov.skipinv r31, #0xf1094f81
stad [r30,+#8], r31
mov.skipinv r31, #0x685e2fd5
stad [r30,+#9], r31
mov.skipinv r31, #0x74175f03
stad [r30,+#10], r31
mov.skipinv r31, #0xffd4a23d
stad [r30,+#11], r31
mov.skipinv r31, #0x715aeab0
stad [r30,+#12], r31
mov.skipinv r31, #0x44b2dd57
stad [r30,+#13], r31
mov.skipinv r31, #0xa86f7efb
stad [r30,+#14], r31
mov.skipinv r31, #0xcd5b3260
stad [r30,+#15], r31
mov.skipinv r31, #0x4c0fbbb4
stad [r30,+#16], r31
mov.skipinv r31, #0x0e429835
stad [r30,+#17], r31
mov.skipinv r31, #0x8f6418c5
stad [r30,+#18], r31
mov.skipinv r31, #0x0e3e6450
stad [r30,+#19], r31
mov.skipinv r31, #0x226699cf
stad [r30,+#20], r31
mov.skipinv r31, #0xc0b09119
stad [r30,+#21], r31
mov.skipinv r31, #0x8e08e309
stad [r30,+#22], r31
mov.skipinv r31, #0x22224051
stad [r30,+#23], r31
mov.skipinv r31, #0xb53358ed
stad [r30,+#24], r31
mov.skipinv r31, #0xe2816a13
stad [r30,+#25], r31
mov.skipinv r31, #0xb21aea48
stad [r30,+#26], r31
mov.skipinv r31, #0xac90dc79
stad [r30,+#27], r31
mov.skipinv r31, #0xda9ef2da
stad [r30,+#28], r31
mov.skipinv r31, #0x5bae44dc
stad [r30,+#29], r31
mov.skipinv r31, #0xabb42162
stad [r30,+#30], r31
mov.skipinv r31, #0x3c6cf350
stad [r30,+#31], r31
mov.skipinv r31, #0xf1cb05cb
stad [r30,+#32], r31
idf drc0, bif
wdf drc0
shr.skipinv r1, pa0, #16
shl.skipinv r1, r1, #18
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3f000000
mov.skipinv r3, #0xbef76000
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
