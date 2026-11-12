; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; R5-pixel g5-rw template (closing5/pixel/exp-pixel-r5.md 4): R4's vtx_zw.s (z = {A} x + {B}, w = {C} x + {D} from the vertex's own
; x) with o0 = {S} x and o1 = {S} y (two fmad with a zero addend; S a power of two, exact), so the window 32 + 32 S x / w of a job at
; scale S is that of the scale-1 job and every vertex stays inside the viewport.  Four instructions more than vtx_zw.s: the second
; phase is at #18.  Temporaries r1-r2.
        phas #18, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y
        mov.skipinv r1, #{A}
        mov.skipinv r2, #{B}
        fmad.skipinv o2, pa0, r1, r2                    ; z = A x + B
        mov.skipinv r1, #{C}
        mov.skipinv r2, #{D}
        fmad.skipinv o3, pa0, r1, r2                    ; w = C x + D (unscaled x)
        mov.skipinv r1, #{S}
        mov.skipinv r2, #0x00000000
        fmad.skipinv o0, pa0, r1, r2                    ; o0 = S x
        fmad.skipinv o1, pa1, r1, r2                    ; o1 = S y
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
