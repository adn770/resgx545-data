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

and.skipinv r1, pa0, #0x3f
shr.skipinv r2, pa0, #10
and.skipinv r2, r2, #0x40
or.skipinv r1, r1, r2
shl.skipinv r1, r1, #16
or.skipinv r1, r1, #0x3f800000
mov.skipinv r2, #0x40800000
mov.skipinv r3, #0xc0bf8000
fmad.skipinv r24, r1, r2, r3
mov.skipinv r25, #0x3f020000
mov r20, #0x07fe0100
mov r21, #0x0c01f03f
mov r22, #0x5cafc000
mov r23, #0x00800800
smp2d r10, r24, r20, drc0
wdf drc0
mov.skipinv.end o0, r10
