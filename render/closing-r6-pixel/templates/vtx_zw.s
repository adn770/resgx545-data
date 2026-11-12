; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; R1 / T3 template (decision R2-15; its rows are NOT in R1): z = {A} x + {B} and w = {C} x + {D} from the
; vertex's own x, so a clip-made vertex has w != 1 (1/w of clip-made vertices, geometry proposal T3).
; As vtx_zab.s plus the w line; two instructions more, so the second phase is at #14.  Temporaries r1-r2.
        phas #14, #0, pixel, vcull, parallel
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
        fmad.skipinv o3, pa0, r1, r2                    ; w = C x + D
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
