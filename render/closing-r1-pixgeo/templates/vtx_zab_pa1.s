; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; R1 / T2 (decision R2-15): probes/mte/templates/vtx_zab.s with ONE line changed: the clip-space depth
; is z = {A} y + {B} from the vertex's own y (pa1), not from x (pa0).  Everything else is the landed
; template byte for byte (the second phase stays at #11).  Temporaries r1-r2.
        phas #11, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y
        mov.skipinv r1, #{A}
        mov.skipinv r2, #{B}
        fmad.skipinv o2, pa1, r1, r2                    ; z = A y + B   (the one changed line: pa1)
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
