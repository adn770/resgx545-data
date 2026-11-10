; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; R1 / T4 template (decision R2-15; its rows are NOT in R1): probes/mte/templates/vtx_wclip.s plus one
; line, `mov o2, #{Z}`: the clip-space z of every vertex is {Z}, w = {A} x + {B} and x, y are scaled by {S}
; (depth at w != 1, geometry proposal T4).  The second phase moves from #14 to #15.  Temporaries r1-r3.
        phas #15, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv r1, #{S}
        mov.skipinv r3, #0x00000000
        fmad.skipinv o0, pa0, r1, r3                    ; x * S
        fmad.skipinv o1, pa1, r1, r3                    ; y * S
        mov.skipinv r1, #{A}
        mov.skipinv r2, #{B}
        fmad.skipinv o3, pa0, r1, r2                    ; w = A x + B
        mov.skipinv o2, #{Z}                            ; z = Z (the added line)
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
