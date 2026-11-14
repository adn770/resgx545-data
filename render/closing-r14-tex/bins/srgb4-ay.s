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
mov.skipinv r31, #0xc8005542
stad [r30,+#0], r31
mov.skipinv r31, #0x8200b499
stad [r30,+#1], r31
mov.skipinv r31, #0xa8001b89
stad [r30,+#2], r31
mov.skipinv r31, #0xe50030af
stad [r30,+#3], r31
mov.skipinv r31, #0x300092aa
stad [r30,+#4], r31
mov.skipinv r31, #0xf00069f7
stad [r30,+#5], r31
mov.skipinv r31, #0x9c00fa2c
stad [r30,+#6], r31
mov.skipinv r31, #0x0a00c0c9
stad [r30,+#7], r31
mov.skipinv r31, #0x470088e8
stad [r30,+#8], r31
mov.skipinv r31, #0x1e005132
stad [r30,+#9], r31
mov.skipinv r31, #0x9d00a208
stad [r30,+#10], r31
mov.skipinv r31, #0xba00438d
stad [r30,+#11], r31
mov.skipinv r31, #0x87001413
stad [r30,+#12], r31
mov.skipinv r31, #0xe9008fed
stad [r30,+#13], r31
mov.skipinv r31, #0x8f007d83
stad [r30,+#14], r31
mov.skipinv r31, #0xb9002989
stad [r30,+#15], r31
mov.skipinv r31, #0x850043d7
stad [r30,+#16], r31
mov.skipinv r31, #0xea00620c
stad [r30,+#17], r31
mov.skipinv r31, #0x3500c0ad
stad [r30,+#18], r31
mov.skipinv r31, #0xdf00a0f4
stad [r30,+#19], r31
mov.skipinv r31, #0xe1007007
stad [r30,+#20], r31
mov.skipinv r31, #0x3400bb63
stad [r30,+#21], r31
mov.skipinv r31, #0xe400d532
stad [r30,+#22], r31
mov.skipinv r31, #0x2b007641
stad [r30,+#23], r31
mov.skipinv r31, #0xf600a562
stad [r30,+#24], r31
mov.skipinv r31, #0x920079d3
stad [r30,+#25], r31
mov.skipinv r31, #0x57007086
stad [r30,+#26], r31
mov.skipinv r31, #0x2a00f103
stad [r30,+#27], r31
mov.skipinv r31, #0xfa00ddf1
stad [r30,+#28], r31
mov.skipinv r31, #0x30009bd2
stad [r30,+#29], r31
mov.skipinv r31, #0xf6008412
stad [r30,+#30], r31
mov.skipinv r31, #0xdc00ec86
stad [r30,+#31], r31
mov.skipinv r31, #0x36009bbb
stad [r30,+#32], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x4701b60a
stad [r30,+#0], r31
mov.skipinv r31, #0xbc0298ad
stad [r30,+#1], r31
mov.skipinv r31, #0x3203058c
stad [r30,+#2], r31
mov.skipinv r31, #0x3c014cde
stad [r30,+#3], r31
mov.skipinv r31, #0xb902ade1
stad [r30,+#4], r31
mov.skipinv r31, #0x9a03e58e
stad [r30,+#5], r31
mov.skipinv r31, #0x5001db61
stad [r30,+#6], r31
mov.skipinv r31, #0xfe02fc55
stad [r30,+#7], r31
mov.skipinv r31, #0x260388f3
stad [r30,+#8], r31
mov.skipinv r31, #0x6201d8bf
stad [r30,+#9], r31
mov.skipinv r31, #0xab02136e
stad [r30,+#10], r31
mov.skipinv r31, #0xd703a04a
stad [r30,+#11], r31
mov.skipinv r31, #0x9b01a120
stad [r30,+#12], r31
mov.skipinv r31, #0xcf028e20
stad [r30,+#13], r31
mov.skipinv r31, #0xd503ddf9
stad [r30,+#14], r31
mov.skipinv r31, #0xdc01d867
stad [r30,+#15], r31
mov.skipinv r31, #0xbe029c4c
stad [r30,+#16], r31
mov.skipinv r31, #0x58036c0b
stad [r30,+#17], r31
mov.skipinv r31, #0x4401b603
stad [r30,+#18], r31
mov.skipinv r31, #0xd902995a
stad [r30,+#19], r31
mov.skipinv r31, #0x8603c557
stad [r30,+#20], r31
mov.skipinv r31, #0xe401b54a
stad [r30,+#21], r31
mov.skipinv r31, #0x02022ddb
stad [r30,+#22], r31
mov.skipinv r31, #0x0803093b
stad [r30,+#23], r31
mov.skipinv r31, #0x3801e4f4
stad [r30,+#24], r31
mov.skipinv r31, #0x5e02fc75
stad [r30,+#25], r31
mov.skipinv r31, #0xe8031dda
stad [r30,+#26], r31
mov.skipinv r31, #0xf801eb2a
stad [r30,+#27], r31
mov.skipinv r31, #0x1c026b74
stad [r30,+#28], r31
mov.skipinv r31, #0xd7032c5f
stad [r30,+#29], r31
mov.skipinv r31, #0xcc01211a
stad [r30,+#30], r31
mov.skipinv r31, #0x8a02af6f
stad [r30,+#31], r31
mov.skipinv r31, #0x53034fa8
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
mov.skipinv.end o0, r11
