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
mov.skipinv r31, #0x79a24b00
stad [r30,+#3], r31
mov.skipinv r31, #0xa27968ff
stad [r30,+#4], r31
mov.skipinv r31, #0x00fec92b
stad [r30,+#11], r31
mov.skipinv r31, #0xfe00a7d5
stad [r30,+#12], r31
mov.skipinv r31, #0xb47f004b
stad [r30,+#19], r31
mov.skipinv r31, #0x7fb4ff68
stad [r30,+#20], r31
mov.skipinv r31, #0x4b402bc9
stad [r30,+#27], r31
mov.skipinv r31, #0x404bd5a7
stad [r30,+#28], r31
mov.skipinv r31, #0xaf92505d
stad [r30,+#35], r31
mov.skipinv r31, #0x92af1237
stad [r30,+#36], r31
mov.skipinv r31, #0x4c4061ea
stad [r30,+#43], r31
mov.skipinv r31, #0x404cf5f9
stad [r30,+#44], r31
mov.skipinv r31, #0x11ef9f3e
stad [r30,+#51], r31
mov.skipinv r31, #0xef118871
stad [r30,+#52], r31
mov.skipinv r31, #0xee580618
stad [r30,+#59], r31
mov.skipinv r31, #0x58ee639b
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0100
mov.skipinv r31, #0x655aec5a
stad [r30,+#3], r31
mov.skipinv r31, #0x5a65c62c
stad [r30,+#4], r31
mov.skipinv r31, #0x27203118
stad [r30,+#11], r31
mov.skipinv r31, #0x20276ba6
stad [r30,+#12], r31
mov.skipinv r31, #0x32b96cff
stad [r30,+#19], r31
mov.skipinv r31, #0xb932690a
stad [r30,+#20], r31
mov.skipinv r31, #0x2f0e8950
stad [r30,+#27], r31
mov.skipinv r31, #0x0e2f7be6
stad [r30,+#28], r31
mov.skipinv r31, #0x4878ea85
stad [r30,+#35], r31
mov.skipinv r31, #0x78484863
stad [r30,+#36], r31
mov.skipinv r31, #0x88262267
stad [r30,+#43], r31
mov.skipinv r31, #0x2688abac
stad [r30,+#44], r31
mov.skipinv r31, #0xaaf6a4d6
stad [r30,+#51], r31
mov.skipinv r31, #0xf6aacddd
stad [r30,+#52], r31
mov.skipinv r31, #0xf6286e7f
stad [r30,+#59], r31
mov.skipinv r31, #0x28f6d6ed
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0200
mov.skipinv r31, #0x0107000a
stad [r30,+#3], r31
mov.skipinv r31, #0x07010f14
stad [r30,+#4], r31
mov.skipinv r31, #0x10d82133
stad [r30,+#11], r31
mov.skipinv r31, #0xd8101a3e
stad [r30,+#12], r31
mov.skipinv r31, #0xab961caa
stad [r30,+#19], r31
mov.skipinv r31, #0x96ab6241
stad [r30,+#20], r31
mov.skipinv r31, #0xe13c2e3d
stad [r30,+#27], r31
mov.skipinv r31, #0x3ce1006a
stad [r30,+#28], r31
mov.skipinv r31, #0xe412efa9
stad [r30,+#35], r31
mov.skipinv r31, #0x12e4671b
stad [r30,+#36], r31
mov.skipinv r31, #0xddb1c059
stad [r30,+#43], r31
mov.skipinv r31, #0xb1dd91d8
stad [r30,+#44], r31
mov.skipinv r31, #0xf241418c
stad [r30,+#51], r31
mov.skipinv r31, #0x41f2eb36
stad [r30,+#52], r31
mov.skipinv r31, #0x9c7967d7
stad [r30,+#59], r31
mov.skipinv r31, #0x799c73cb
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0300
mov.skipinv r31, #0xd8fff833
stad [r30,+#3], r31
mov.skipinv r31, #0xffd88bca
stad [r30,+#4], r31
mov.skipinv r31, #0x96691a5d
stad [r30,+#11], r31
mov.skipinv r31, #0x699667c0
stad [r30,+#12], r31
mov.skipinv r31, #0x118b2a57
stad [r30,+#19], r31
mov.skipinv r31, #0x8b11548d
stad [r30,+#20], r31
mov.skipinv r31, #0xe2548f3a
stad [r30,+#27], r31
mov.skipinv r31, #0x54e29dc2
stad [r30,+#28], r31
mov.skipinv r31, #0x30a46c54
stad [r30,+#35], r31
mov.skipinv r31, #0xa4308f94
stad [r30,+#36], r31
mov.skipinv r31, #0xe9dafdaf
stad [r30,+#43], r31
mov.skipinv r31, #0xdae9a059
stad [r30,+#44], r31
mov.skipinv r31, #0xbd2cd5b5
stad [r30,+#51], r31
mov.skipinv r31, #0x2cbd2ef1
stad [r30,+#52], r31
mov.skipinv r31, #0xf0d614e8
stad [r30,+#59], r31
mov.skipinv r31, #0xd6f07186
stad [r30,+#60], r31
mov.skipinv r30, #0x5CAF0400
mov.skipinv r31, #0xb9297906
stad [r30,+#3], r31
mov.skipinv r31, #0x29b91977
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
