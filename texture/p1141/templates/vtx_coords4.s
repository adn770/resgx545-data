; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The triangle's vertex shader with a coordinate set of four dwords (--slot
; vtxuse=vtx_coords4.bin, --vtx-coords 4), as probes/texture/templates/vtx_coords.s (which
; writes two): o4, o5 = the vertex's clip-space x and y, o6 = 0.25, a constant, and
; o7 = x + y, which varies across the triangle and is neither 1.0 nor a constant. Q021: a
; four-component douti then reads a fourth component that is not 1.0, so pa3 = 1.0 (a constant
; of the iterator) and pa3 = the iterated x + y (a component) are told apart.
        phas #8, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y
        mov.skipinv o6, #0x3e800000                     ; o6 = 0.25
        mov.skipinv r2, #0x3f800000
        fmad.skipinv r3, pa0, r2, pa1                   ; r3 = x * 1.0 + y
        mov.skipinv o7, r3                              ; o7 = x + y
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
