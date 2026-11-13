; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; r8-ldpm stage v (Q210, plan P3): the triangle's vertex shader with eight coordinate output
; dwords, every one written (slot vtxuse, --vtx-coords 8), in the form of
; probes/tsp/templates/vtx_coord4.s: o4, o5 = the vertex's clip-space x and y, o6 = 0.25,
; o7 = 0.5, o8, o9 = x and y again, o10 = 0.75, o11 = 1.0. The second phase at #13.
        phas #13, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y
        mov.skipinv o6, #0x3E800000                     ; 0.25
        mov.skipinv o7, #0x3F000000                     ; 0.5
        mov.skipinv.repeat2 o8, pa0                     ; o8, o9 = x, y
        mov.skipinv o10, #0x3F400000                    ; 0.75
        mov.skipinv o11, #0x3F800000                    ; 1.0
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
