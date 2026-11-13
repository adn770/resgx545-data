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
mov.skipinv r31, #0x81d7feff
stad [r30,+#3], r31
mov.skipinv r31, #0xd781feff
stad [r30,+#4], r31
mov.skipinv r31, #0x37f9f9fb
stad [r30,+#11], r31
mov.skipinv r31, #0xf937f9fb
stad [r30,+#12], r31
mov.skipinv r31, #0xb0c3f5f3
stad [r30,+#19], r31
mov.skipinv r31, #0xc3b0f5f3
stad [r30,+#20], r31
mov.skipinv r31, #0x71e7ebee
stad [r30,+#27], r31
mov.skipinv r31, #0xe771ebee
stad [r30,+#28], r31
mov.skipinv r31, #0xd095e7e3
stad [r30,+#35], r31
mov.skipinv r31, #0x95d0e7e3
stad [r30,+#36], r31
mov.skipinv r31, #0x5dbbe2ce
stad [r30,+#43], r31
mov.skipinv r31, #0xbb5de2ce
stad [r30,+#44], r31
mov.skipinv r31, #0x2071d7ba
stad [r30,+#51], r31
mov.skipinv r31, #0x7120d7ba
stad [r30,+#52], r31
mov.skipinv r31, #0x0e48d4af
stad [r30,+#59], r31
mov.skipinv r31, #0x480ed4af
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x0bfcd1a6
stad [r30,+#3], r31
mov.skipinv r31, #0xfc0bd1a6
stad [r30,+#4], r31
mov.skipinv r31, #0x04d6d0a3
stad [r30,+#11], r31
mov.skipinv r31, #0xd604d0a3
stad [r30,+#12], r31
mov.skipinv r31, #0x9f83cf9c
stad [r30,+#19], r31
mov.skipinv r31, #0x839fcf9c
stad [r30,+#20], r31
mov.skipinv r31, #0x7ea3c89a
stad [r30,+#27], r31
mov.skipinv r31, #0xa37ec89a
stad [r30,+#28], r31
mov.skipinv r31, #0x61d9c697
stad [r30,+#35], r31
mov.skipinv r31, #0xd961c697
stad [r30,+#36], r31
mov.skipinv r31, #0x7156b994
stad [r30,+#43], r31
mov.skipinv r31, #0x5671b994
stad [r30,+#44], r31
mov.skipinv r31, #0x5677b892
stad [r30,+#51], r31
mov.skipinv r31, #0x7756b892
stad [r30,+#52], r31
mov.skipinv r31, #0xcf6cac87
stad [r30,+#59], r31
mov.skipinv r31, #0x6ccfac87
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0x41799785
stad [r30,+#3], r31
mov.skipinv r31, #0x79419785
stad [r30,+#4], r31
mov.skipinv r31, #0xa7999077
stad [r30,+#11], r31
mov.skipinv r31, #0x99a79077
stad [r30,+#12], r31
mov.skipinv r31, #0x836f8e68
stad [r30,+#19], r31
mov.skipinv r31, #0x6f838e68
stad [r30,+#20], r31
mov.skipinv r31, #0x2e8b8c5a
stad [r30,+#27], r31
mov.skipinv r31, #0x8b2e8c5a
stad [r30,+#28], r31
mov.skipinv r31, #0xd52b8958
stad [r30,+#35], r31
mov.skipinv r31, #0x2bd58958
stad [r30,+#36], r31
mov.skipinv r31, #0x63636a4d
stad [r30,+#43], r31
mov.skipinv r31, #0x63636a4d
stad [r30,+#44], r31
mov.skipinv r31, #0x189a5b4b
stad [r30,+#51], r31
mov.skipinv r31, #0x9a185b4b
stad [r30,+#52], r31
mov.skipinv r31, #0x71293d4a
stad [r30,+#59], r31
mov.skipinv r31, #0x29713d4a
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0x4c463c49
stad [r30,+#3], r31
mov.skipinv r31, #0x464c3c49
stad [r30,+#4], r31
mov.skipinv r31, #0x52412a40
stad [r30,+#11], r31
mov.skipinv r31, #0x41522a40
stad [r30,+#12], r31
mov.skipinv r31, #0xde03293c
stad [r30,+#19], r31
mov.skipinv r31, #0x03de293c
stad [r30,+#20], r31
mov.skipinv r31, #0x52902736
stad [r30,+#27], r31
mov.skipinv r31, #0x90522736
stad [r30,+#28], r31
mov.skipinv r31, #0x0f5d232b
stad [r30,+#35], r31
mov.skipinv r31, #0x5d0f232b
stad [r30,+#36], r31
mov.skipinv r31, #0xdf3e1728
stad [r30,+#43], r31
mov.skipinv r31, #0x3edf1728
stad [r30,+#44], r31
mov.skipinv r31, #0x40ca0c16
stad [r30,+#51], r31
mov.skipinv r31, #0xca400c16
stad [r30,+#52], r31
mov.skipinv r31, #0x0136090a
stad [r30,+#59], r31
mov.skipinv r31, #0x3601090a
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0x37290503
stad [r30,+#3], r31
mov.skipinv r31, #0x29370503
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
mov.skipinv.end o0, r10
