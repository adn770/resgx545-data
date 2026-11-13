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
mov.skipinv r31, #0x56e90300
stad [r30,+#3], r31
mov.skipinv r31, #0xe9560002
stad [r30,+#4], r31
mov.skipinv r31, #0x5feb0100
stad [r30,+#11], r31
mov.skipinv r31, #0xeb5f0002
stad [r30,+#12], r31
mov.skipinv r31, #0xcc380100
stad [r30,+#19], r31
mov.skipinv r31, #0x38cc0003
stad [r30,+#20], r31
mov.skipinv r31, #0x91ce0100
stad [r30,+#27], r31
mov.skipinv r31, #0xce910002
stad [r30,+#28], r31
mov.skipinv r31, #0x66370100
stad [r30,+#35], r31
mov.skipinv r31, #0x37660003
stad [r30,+#36], r31
mov.skipinv r31, #0x953f0200
stad [r30,+#43], r31
mov.skipinv r31, #0x3f950002
stad [r30,+#44], r31
mov.skipinv r31, #0xf3020200
stad [r30,+#51], r31
mov.skipinv r31, #0x02f30003
stad [r30,+#52], r31
mov.skipinv r31, #0x2df20100
stad [r30,+#59], r31
mov.skipinv r31, #0xf22d0002
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x5b860300
stad [r30,+#3], r31
mov.skipinv r31, #0x865b0003
stad [r30,+#4], r31
mov.skipinv r31, #0x8c980200
stad [r30,+#11], r31
mov.skipinv r31, #0x988c0002
stad [r30,+#12], r31
mov.skipinv r31, #0xab280200
stad [r30,+#19], r31
mov.skipinv r31, #0x28ab0001
stad [r30,+#20], r31
mov.skipinv r31, #0x0ed80200
stad [r30,+#27], r31
mov.skipinv r31, #0xd80e0003
stad [r30,+#28], r31
mov.skipinv r31, #0x375c0300
stad [r30,+#35], r31
mov.skipinv r31, #0x5c370001
stad [r30,+#36], r31
mov.skipinv r31, #0x8b410200
stad [r30,+#43], r31
mov.skipinv r31, #0x418b0001
stad [r30,+#44], r31
mov.skipinv r31, #0xcd820300
stad [r30,+#51], r31
mov.skipinv r31, #0x82cd0003
stad [r30,+#52], r31
mov.skipinv r31, #0xe5020200
stad [r30,+#59], r31
mov.skipinv r31, #0x02e50003
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0x30090100
stad [r30,+#3], r31
mov.skipinv r31, #0x09300002
stad [r30,+#4], r31
mov.skipinv r31, #0xd6e50100
stad [r30,+#11], r31
mov.skipinv r31, #0xe5d60001
stad [r30,+#12], r31
mov.skipinv r31, #0xa08f0100
stad [r30,+#19], r31
mov.skipinv r31, #0x8fa00002
stad [r30,+#20], r31
mov.skipinv r31, #0xc04e0100
stad [r30,+#27], r31
mov.skipinv r31, #0x4ec00002
stad [r30,+#28], r31
mov.skipinv r31, #0x82ef0100
stad [r30,+#35], r31
mov.skipinv r31, #0xef820003
stad [r30,+#36], r31
mov.skipinv r31, #0x52110300
stad [r30,+#43], r31
mov.skipinv r31, #0x11520003
stad [r30,+#44], r31
mov.skipinv r31, #0x0d1c0200
stad [r30,+#51], r31
mov.skipinv r31, #0x1c0d0003
stad [r30,+#52], r31
mov.skipinv r31, #0x26720100
stad [r30,+#59], r31
mov.skipinv r31, #0x72260003
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0x223c0200
stad [r30,+#3], r31
mov.skipinv r31, #0x3c220002
stad [r30,+#4], r31
mov.skipinv r31, #0xa40a0200
stad [r30,+#11], r31
mov.skipinv r31, #0x0aa40003
stad [r30,+#12], r31
mov.skipinv r31, #0x67070100
stad [r30,+#19], r31
mov.skipinv r31, #0x07670003
stad [r30,+#20], r31
mov.skipinv r31, #0x7a250200
stad [r30,+#27], r31
mov.skipinv r31, #0x257a0003
stad [r30,+#28], r31
mov.skipinv r31, #0xa7630100
stad [r30,+#35], r31
mov.skipinv r31, #0x63a70003
stad [r30,+#36], r31
mov.skipinv r31, #0xa1cf0100
stad [r30,+#43], r31
mov.skipinv r31, #0xcfa10003
stad [r30,+#44], r31
mov.skipinv r31, #0xf58f0100
stad [r30,+#51], r31
mov.skipinv r31, #0x8ff50001
stad [r30,+#52], r31
mov.skipinv r31, #0x21790100
stad [r30,+#59], r31
mov.skipinv r31, #0x79210002
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xa3060300
stad [r30,+#3], r31
mov.skipinv r31, #0x06a30003
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
mov.skipinv r3, #0xbefb6000
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc00703f
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
