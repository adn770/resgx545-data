; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; vtx_coords.s with a coordinate set of the vertex's clip z and clip x (o4 = z, o5 = x) instead of x
; and y: z is a value of its own at each vertex (--tri-z), x is the vertex's window x, so the
; iterated o4 is a plane through three independent values and o5 a plane of the pixel's own x.
; One instruction more than vtx_coords.s: the second phase at #9.
        phas #9, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv o4, pa2                             ; o4 = z
        mov.skipinv o5, pa0                             ; o5 = x
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
