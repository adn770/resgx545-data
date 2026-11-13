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
mov.skipinv r31, #0xdb59603b
stad [r30,+#3], r31
mov.skipinv r31, #0x59dbe134
stad [r30,+#4], r31
mov.skipinv r31, #0xa835a725
stad [r30,+#11], r31
mov.skipinv r31, #0x35a844ef
stad [r30,+#12], r31
mov.skipinv r31, #0xe7787084
stad [r30,+#19], r31
mov.skipinv r31, #0x78e7d933
stad [r30,+#20], r31
mov.skipinv r31, #0xac905262
stad [r30,+#27], r31
mov.skipinv r31, #0x90ac0ac7
stad [r30,+#28], r31
mov.skipinv r31, #0x96a899cd
stad [r30,+#35], r31
mov.skipinv r31, #0xa896d893
stad [r30,+#36], r31
mov.skipinv r31, #0x9eb3ae88
stad [r30,+#43], r31
mov.skipinv r31, #0xb39ed4eb
stad [r30,+#44], r31
mov.skipinv r31, #0xf045d892
stad [r30,+#51], r31
mov.skipinv r31, #0x45f08c7b
stad [r30,+#52], r31
mov.skipinv r31, #0xd2d8ec3c
stad [r30,+#59], r31
mov.skipinv r31, #0xd8d23cfa
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x5e1dc19b
stad [r30,+#3], r31
mov.skipinv r31, #0x1d5e0f76
stad [r30,+#4], r31
mov.skipinv r31, #0xe9024fe7
stad [r30,+#11], r31
mov.skipinv r31, #0x02e9c1f8
stad [r30,+#12], r31
mov.skipinv r31, #0xdb84ae9b
stad [r30,+#19], r31
mov.skipinv r31, #0x84dbcde9
stad [r30,+#20], r31
mov.skipinv r31, #0x89a7231a
stad [r30,+#27], r31
mov.skipinv r31, #0xa789a3b3
stad [r30,+#28], r31
mov.skipinv r31, #0x5127887a
stad [r30,+#35], r31
mov.skipinv r31, #0x2751397c
stad [r30,+#36], r31
mov.skipinv r31, #0xc92210ef
stad [r30,+#43], r31
mov.skipinv r31, #0x22c9f78b
stad [r30,+#44], r31
mov.skipinv r31, #0x1132ef85
stad [r30,+#51], r31
mov.skipinv r31, #0x32117824
stad [r30,+#52], r31
mov.skipinv r31, #0x2d118430
stad [r30,+#59], r31
mov.skipinv r31, #0x112d257c
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0xff31303e
stad [r30,+#3], r31
mov.skipinv r31, #0x31ff3e27
stad [r30,+#4], r31
mov.skipinv r31, #0x7c3d8c3a
stad [r30,+#11], r31
mov.skipinv r31, #0x3d7c8f99
stad [r30,+#12], r31
mov.skipinv r31, #0x18a4af08
stad [r30,+#19], r31
mov.skipinv r31, #0xa41847ab
stad [r30,+#20], r31
mov.skipinv r31, #0xf1aebf4a
stad [r30,+#27], r31
mov.skipinv r31, #0xaef1c8db
stad [r30,+#28], r31
mov.skipinv r31, #0x2a23dfeb
stad [r30,+#35], r31
mov.skipinv r31, #0x232ab623
stad [r30,+#36], r31
mov.skipinv r31, #0xd24f8c1d
stad [r30,+#43], r31
mov.skipinv r31, #0x4fd2adeb
stad [r30,+#44], r31
mov.skipinv r31, #0xe0fb3815
stad [r30,+#51], r31
mov.skipinv r31, #0xfbe076de
stad [r30,+#52], r31
mov.skipinv r31, #0xc3f97054
stad [r30,+#59], r31
mov.skipinv r31, #0xf9c330d7
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0x4e5420d2
stad [r30,+#3], r31
mov.skipinv r31, #0x544ee101
stad [r30,+#4], r31
mov.skipinv r31, #0x6ff8ba7b
stad [r30,+#11], r31
mov.skipinv r31, #0xf86f34eb
stad [r30,+#12], r31
mov.skipinv r31, #0x41ab5bd6
stad [r30,+#19], r31
mov.skipinv r31, #0xab41e19a
stad [r30,+#20], r31
mov.skipinv r31, #0xd8d798ff
stad [r30,+#27], r31
mov.skipinv r31, #0xd7d8312d
stad [r30,+#28], r31
mov.skipinv r31, #0xd9594b53
stad [r30,+#35], r31
mov.skipinv r31, #0x59d90114
stad [r30,+#36], r31
mov.skipinv r31, #0x1a5a1767
stad [r30,+#43], r31
mov.skipinv r31, #0x5a1a1b80
stad [r30,+#44], r31
mov.skipinv r31, #0xfcf4848f
stad [r30,+#51], r31
mov.skipinv r31, #0xf4fc1079
stad [r30,+#52], r31
mov.skipinv r31, #0x1e462ec0
stad [r30,+#59], r31
mov.skipinv r31, #0x461ebde0
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x68a4ce5f
stad [r30,+#3], r31
mov.skipinv r31, #0xa468e61c
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
mov.skipinv r3, #0xbefa6000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc00703f
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
