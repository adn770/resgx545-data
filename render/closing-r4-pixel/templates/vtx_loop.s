; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; R3 / q-v template (Q082; R2's T5 template with the body as a parameter): a vertex program that loops {N} times with a RELATIVE branch and carries the loop count
; into the vertex's depth, so that a loop that did not run on every vertex shows in the object the TA stores.
;
; Why a relative branch: the tool places a vtxuse program at instruction 0x40 of its page, and absolute indices
; count from the code base (E476: the placement rounded down to 512 KiB, a jump counted from the program start
; faults or hangs), so `ba #label` lands in the wrong program (E770: R1-events' pixel loops used `ba` and wrote
; their result in 16 of 64 pixels).  `br -#7` counts from the branch itself (E075: `br #1` is the next
; instruction), whatever the placement; tests/test_t5loop.py runs it in sgx-sim at five code indices.
;
; Loop body ({BODY} instructions an iteration: b8v = E784's, five imae; b16v 13 imae; b4v 1 imae): the imae, the depth
; accumulator, the counter update (sets p1 while the counter is non-zero), the branch.  The imae write r4-r8 in turn.
; Depth: z = {ZB} + 4 N as a float32 word (ZB = 0x3e800000, 0.25), so the stored depth 0.5 + 0.5 z is the word 0x3f200000 + N exactly (z has 2^-23 steps).  x, y, w pass
; through from the vertex buffer (w = 1), o4/o5 = x, y as vtx_zab.s.  Temporaries r1-r13 (probe temps = 16).
        phas #{PH2}, #0, pixel, vcull, parallel
        nop.nosched
        and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0
        p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0
        wdf drc0
        mov.skipinv.repeat4 o0, pa0                     ; o0-o3 = x, y, z, w
        mov.skipinv.repeat2 o4, pa0                     ; o4, o5 = x, y
        mov.skipinv r1, #{N}                            ; iteration counter
        mov.skipinv r2, #0xFFFFFFFF                     ; -1
        mov.skipinv r3, #0x00000003
        mov.skipinv r12, #{ZB}                          ; depth accumulator, 0.25
        mov.skipinv r13, #0x00000004                    ; its step: 4 ulp = 2^-23
{IMAE}
        iadd32.skipinv.testtanz.chan0 r12, p2, r13, r12 ; z += 4 ulp (iadd32 adds sext16(src1) to src2)
        iadd32.skipinv.testtanz.chan0 r1, p1, r1, r2    ; counter -= 1, p1 = (counter != 0)
        p1 br -#{BACK}                              ; back to the first body instruction (relative)
        mov.skipinv o2, r12                             ; z = 0.25 + 4 N ulp
        emitvcbvtx.end.twopart #0, #0
        phas #0, #0, pixel, end, parallel
        emitmtevtx.end.twopart.freep #0, #0, #0
