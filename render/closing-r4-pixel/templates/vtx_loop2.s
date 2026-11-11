; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; R4 / q4-v template (Q082; templates/vtx_loop.s with the body reduced to the counter and the branch): a vertex program that loops
; {N} times with a RELATIVE branch on a body of TWO instructions (the counter update and the branch).  There is no depth accumulator
; in the body, so the loop proof is the counter itself: after the loop o2 = (0x3e800000 + 4 N) xor counter, the counter being 0 only
; if the loop ran to its end (N iterations); a loop that did not run leaves the counter at N, o2 then differs and the stored depth
; word is not 0x3f200000 + N (the same proof word as the other vertex bodies).  Relative branch as vtx_loop.s (E770, E476).
        phas #14, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y
        mov.skipinv r1, #{N}                            ; iteration counter
        mov.skipinv r2, #0xFFFFFFFF                     ; -1
        mov.skipinv r12, #{ZN}                          ; 0.25 + 4 N ulp as a word
        iadd32.skipinv.testtanz.chan0 r1, p1, r1, r2    ; counter -= 1, p1 = (counter != 0)
        p1 br -#0x00000001                              ; back to the counter update (relative)
        xor.skipinv o2, r12, r1                         ; z = 0.25 + 4 N ulp iff the counter is 0
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
