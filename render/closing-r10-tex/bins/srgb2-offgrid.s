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
mov.skipinv r31, #0x7dd59eb9
stad [r30,+#3], r31
mov.skipinv r31, #0xd57df9e6
stad [r30,+#4], r31
mov.skipinv r31, #0x2f87cf0a
stad [r30,+#11], r31
mov.skipinv r31, #0x872f43c0
stad [r30,+#12], r31
mov.skipinv r31, #0x24789957
stad [r30,+#19], r31
mov.skipinv r31, #0x78248f4b
stad [r30,+#20], r31
mov.skipinv r31, #0x4c019113
stad [r30,+#27], r31
mov.skipinv r31, #0x014c43ef
stad [r30,+#28], r31
mov.skipinv r31, #0xde07c4a6
stad [r30,+#35], r31
mov.skipinv r31, #0x07ded106
stad [r30,+#36], r31
mov.skipinv r31, #0xcbff216d
stad [r30,+#43], r31
mov.skipinv r31, #0xffcb35c1
stad [r30,+#44], r31
mov.skipinv r31, #0x63770fdc
stad [r30,+#51], r31
mov.skipinv r31, #0x7763947f
stad [r30,+#52], r31
mov.skipinv r31, #0xf1ea7489
stad [r30,+#59], r31
mov.skipinv r31, #0xeaf1759d
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x1c5f8846
stad [r30,+#3], r31
mov.skipinv r31, #0x5f1c8683
stad [r30,+#4], r31
mov.skipinv r31, #0x0dae8836
stad [r30,+#11], r31
mov.skipinv r31, #0xae0dcf1c
stad [r30,+#12], r31
mov.skipinv r31, #0x0db4be42
stad [r30,+#19], r31
mov.skipinv r31, #0xb40d5666
stad [r30,+#20], r31
mov.skipinv r31, #0xdb7d8cdc
stad [r30,+#27], r31
mov.skipinv r31, #0x7ddb47c3
stad [r30,+#28], r31
mov.skipinv r31, #0xfdc6bba5
stad [r30,+#35], r31
mov.skipinv r31, #0xc6fdc4c4
stad [r30,+#36], r31
mov.skipinv r31, #0xba16bb01
stad [r30,+#43], r31
mov.skipinv r31, #0x16ba3932
stad [r30,+#44], r31
mov.skipinv r31, #0xee71cc7a
stad [r30,+#51], r31
mov.skipinv r31, #0x71eefbc9
stad [r30,+#52], r31
mov.skipinv r31, #0x2dd1c05c
stad [r30,+#59], r31
mov.skipinv r31, #0xd12dfa09
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0x280962f1
stad [r30,+#3], r31
mov.skipinv r31, #0x09281117
stad [r30,+#4], r31
mov.skipinv r31, #0x1870c276
stad [r30,+#11], r31
mov.skipinv r31, #0x70185ded
stad [r30,+#12], r31
mov.skipinv r31, #0xba6e3000
stad [r30,+#19], r31
mov.skipinv r31, #0x6eba077d
stad [r30,+#20], r31
mov.skipinv r31, #0x0b846dc0
stad [r30,+#27], r31
mov.skipinv r31, #0x840bde25
stad [r30,+#28], r31
mov.skipinv r31, #0x77ec09fd
stad [r30,+#35], r31
mov.skipinv r31, #0xec77b976
stad [r30,+#36], r31
mov.skipinv r31, #0xe256df4b
stad [r30,+#43], r31
mov.skipinv r31, #0x56e24260
stad [r30,+#44], r31
mov.skipinv r31, #0x3ca97cc2
stad [r30,+#51], r31
mov.skipinv r31, #0xa93c5ad2
stad [r30,+#52], r31
mov.skipinv r31, #0xdb66db9e
stad [r30,+#59], r31
mov.skipinv r31, #0x66db07d1
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0x7ad10369
stad [r30,+#3], r31
mov.skipinv r31, #0xd17a7c5d
stad [r30,+#4], r31
mov.skipinv r31, #0x0188b18a
stad [r30,+#11], r31
mov.skipinv r31, #0x8801574f
stad [r30,+#12], r31
mov.skipinv r31, #0x01955f8b
stad [r30,+#19], r31
mov.skipinv r31, #0x9501de26
stad [r30,+#20], r31
mov.skipinv r31, #0x7b20976b
stad [r30,+#27], r31
mov.skipinv r31, #0x207b9d5f
stad [r30,+#28], r31
mov.skipinv r31, #0x2ae60181
stad [r30,+#35], r31
mov.skipinv r31, #0xe62aa165
stad [r30,+#36], r31
mov.skipinv r31, #0xa228bc93
stad [r30,+#43], r31
mov.skipinv r31, #0x28a2634e
stad [r30,+#44], r31
mov.skipinv r31, #0xa378e07c
stad [r30,+#51], r31
mov.skipinv r31, #0x78a39b24
stad [r30,+#52], r31
mov.skipinv r31, #0x027ef0b0
stad [r30,+#59], r31
mov.skipinv r31, #0x7e020661
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xd2fb98d6
stad [r30,+#3], r31
mov.skipinv r31, #0xfbd214c7
stad [r30,+#4], r31
idf drc0, bif
wdf drc0
and.skipinv r1, pa0, #0x3f
shl.skipinv r1, r1, #17
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3e000000
mov.skipinv r3, #0x3ea0c000
fmad.skipinv r24, r1, r2, r3
shr.skipinv r1, pa0, #16
shl.skipinv r1, r1, #18
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x3f000000
mov.skipinv r3, #0xbef94800
fmad.skipinv r25, r1, r2, r3
mov r20, #0x08001e00
mov r21, #0xcc00703f
mov r22, #0x5caf0000
mov r23, #0xa0800000
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
