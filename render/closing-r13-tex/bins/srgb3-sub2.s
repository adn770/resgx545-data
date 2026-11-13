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
mov.skipinv r31, #0xbcbc0200
stad [r30,+#3], r31
mov.skipinv r31, #0xbcbc0003
stad [r30,+#4], r31
mov.skipinv r31, #0x01950100
stad [r30,+#11], r31
mov.skipinv r31, #0x95010003
stad [r30,+#12], r31
mov.skipinv r31, #0x64a10300
stad [r30,+#19], r31
mov.skipinv r31, #0xa1640001
stad [r30,+#20], r31
mov.skipinv r31, #0xd8940100
stad [r30,+#27], r31
mov.skipinv r31, #0x94d80001
stad [r30,+#28], r31
mov.skipinv r31, #0xc4e90100
stad [r30,+#35], r31
mov.skipinv r31, #0xe9c40003
stad [r30,+#36], r31
mov.skipinv r31, #0xa2450200
stad [r30,+#43], r31
mov.skipinv r31, #0x45a20001
stad [r30,+#44], r31
mov.skipinv r31, #0x48760100
stad [r30,+#51], r31
mov.skipinv r31, #0x76480001
stad [r30,+#52], r31
mov.skipinv r31, #0xf8a50300
stad [r30,+#59], r31
mov.skipinv r31, #0xa5f80002
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0xe0d50200
stad [r30,+#3], r31
mov.skipinv r31, #0xd5e00003
stad [r30,+#4], r31
mov.skipinv r31, #0xd8980200
stad [r30,+#11], r31
mov.skipinv r31, #0x98d80001
stad [r30,+#12], r31
mov.skipinv r31, #0x88350200
stad [r30,+#19], r31
mov.skipinv r31, #0x35880001
stad [r30,+#20], r31
mov.skipinv r31, #0x8b000100
stad [r30,+#27], r31
mov.skipinv r31, #0x008b0003
stad [r30,+#28], r31
mov.skipinv r31, #0x83410200
stad [r30,+#35], r31
mov.skipinv r31, #0x41830003
stad [r30,+#36], r31
mov.skipinv r31, #0x28dc0100
stad [r30,+#43], r31
mov.skipinv r31, #0xdc280003
stad [r30,+#44], r31
mov.skipinv r31, #0xa5e80300
stad [r30,+#51], r31
mov.skipinv r31, #0xe8a50002
stad [r30,+#52], r31
mov.skipinv r31, #0x00450100
stad [r30,+#59], r31
mov.skipinv r31, #0x45000002
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0xd5480200
stad [r30,+#3], r31
mov.skipinv r31, #0x48d50001
stad [r30,+#4], r31
mov.skipinv r31, #0xc69e0300
stad [r30,+#11], r31
mov.skipinv r31, #0x9ec60001
stad [r30,+#12], r31
mov.skipinv r31, #0xbce30300
stad [r30,+#19], r31
mov.skipinv r31, #0xe3bc0003
stad [r30,+#20], r31
mov.skipinv r31, #0xfaa70100
stad [r30,+#27], r31
mov.skipinv r31, #0xa7fa0001
stad [r30,+#28], r31
mov.skipinv r31, #0xe7090300
stad [r30,+#35], r31
mov.skipinv r31, #0x09e70001
stad [r30,+#36], r31
mov.skipinv r31, #0x7a2c0300
stad [r30,+#43], r31
mov.skipinv r31, #0x2c7a0001
stad [r30,+#44], r31
mov.skipinv r31, #0x866d0100
stad [r30,+#51], r31
mov.skipinv r31, #0x6d860002
stad [r30,+#52], r31
mov.skipinv r31, #0x5e4e0200
stad [r30,+#59], r31
mov.skipinv r31, #0x4e5e0002
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0x0daf0100
stad [r30,+#3], r31
mov.skipinv r31, #0xaf0d0002
stad [r30,+#4], r31
mov.skipinv r31, #0xd2b50100
stad [r30,+#11], r31
mov.skipinv r31, #0xb5d20002
stad [r30,+#12], r31
mov.skipinv r31, #0xf4590100
stad [r30,+#19], r31
mov.skipinv r31, #0x59f40002
stad [r30,+#20], r31
mov.skipinv r31, #0x63a70100
stad [r30,+#27], r31
mov.skipinv r31, #0xa7630001
stad [r30,+#28], r31
mov.skipinv r31, #0x026a0100
stad [r30,+#35], r31
mov.skipinv r31, #0x6a020001
stad [r30,+#36], r31
mov.skipinv r31, #0xd0730200
stad [r30,+#43], r31
mov.skipinv r31, #0x73d00001
stad [r30,+#44], r31
mov.skipinv r31, #0xd5e90300
stad [r30,+#51], r31
mov.skipinv r31, #0xe9d50001
stad [r30,+#52], r31
mov.skipinv r31, #0xb4d50100
stad [r30,+#59], r31
mov.skipinv r31, #0xd5b40002
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x93ad0100
stad [r30,+#3], r31
mov.skipinv r31, #0xad930001
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
mov.skipinv.end o0, r10
