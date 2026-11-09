; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; Pixel-event probe template (sgxfive-test probe --tri pixev:60 --slot eot=eot_dump.bin or
; eot_tile.bin): asm/transfer/pds_pixevent.s, the triangle's pixel-event program, with the
; operation(s) under test OP run on the end-of-tile event just before it starts the
; end-of-tile task. OP passes its results on with douta into the task's secondary
; attributes sa0-sa15, which eot_dump.s or eot_tile.s store to the scratch buffer.
;
; Rows 0-4 are pds_pixevent.s's data segment, dword for dword: the host patches dwords 0-5
; and 12 as it does the default's (sgxfive_tri_probe.h), and the dispatch below is the
; temporaries ds0/ds1[48..63], and must leave ds0[48] and ds1[48] free for the dispatch
; (it overwrites them after OP) and never write tim (a movs tim stops the counter until
; the GPU is reset).
;
; Rows 5-12: ds0[10+k] = 0x7E570000 | k, a marker per attribute k (0-15); ds1[10+k] the
; douta control word of attribute k (k << 8). So "movs douta, ds0[n], ds1[10+k], ds0[n],
; ds0[n]" passes ds0[n] to sak, "movs douta, ir0.l, ds1[10+k], ir0.l, ir0.l" ir0.
; Row 13: ds0[26] = 0x3FF (tile_y mask), ds1[26] = 64 << 16, ds1[27] = 3 (tile_x mask).
; Row 14: zeros (ds0[28], ds0[29], ds1[28], ds1[29]).
;
; Before OP, ds0[63] = (64 << 16) | slot, slot = tile_y x 4 + (tile_x & 3), with tile_x =
; ir0[8:0] and tile_y = ir0[18:9] as pds_pixevent.s builds the task's U1 from them [infer];
; eot_tile.s stores each tile's attributes at 64 x slot bytes when OP passes ds0[63] to sa15.

        .word 0          ; dword 0  = ds0[0]: PTOFF task U0 (patched)
        .word 0          ; dword 1  = ds0[1]: PTOFF task U1 (patched: 0)
        .word 0          ; dword 2  = ds1[0]: unused (patched: 0)
        .word 0          ; dword 3  = ds1[1]: EOT task U0 (patched)
        .word 0          ; dword 4  = ds0[2]: EOR task U0 (patched)
        .word 0          ; dword 5  = ds0[3]: EOR task U1 (patched: 0x00c00000)
        .word 0x00000008 ; dword 6  = ds1[2]: ir1 bit 3, PTOFF
        .word 0x00000002 ; dword 7  = ds1[3]: ir1 bit 1, end of tile
        .word 0x00000100 ; dword 8  = ds0[4]: ir1 bit 8, end of render instead
        .word 0x00000FF8 ; dword 9  = ds0[5]: tile_x mask, U1 [11:3]
        .word 0x00000004 ; dword 10 = ds1[4]: ir1 bit 2, end of render
        .word 0          ; dword 11 = ds1[5]: unused
        .word 0          ; dword 12 = ds0[6]: EOT task U1 base (patched: 0x00800000)
        .word 0x003FF000 ; dword 13 = ds0[7]: tile_y mask, U1 [21:12]
        .word 0          ; dword 14 = ds1[6]: unused
        .word 0          ; dword 15 = ds1[7]: unused
        .word 0x00400000 ; dword 16 = ds0[8]: ENDOFRENDER, U1 bit 22
        .word 0          ; dword 17 = ds0[9]: unused
        .word 0          ; dword 18 = ds1[8]: unused
        .word 0          ; dword 19 = ds1[9]: unused
        .word 0x7E570000, 0x7E570001, 0x000, 0x100      ; rows 5-12: markers, controls
        .word 0x7E570002, 0x7E570003, 0x200, 0x300
        .word 0x7E570004, 0x7E570005, 0x400, 0x500
        .word 0x7E570006, 0x7E570007, 0x600, 0x700
        .word 0x7E570008, 0x7E570009, 0x800, 0x900
        .word 0x7E57000A, 0x7E57000B, 0xA00, 0xB00
        .word 0x7E57000C, 0x7E57000D, 0xC00, 0xD00
        .word 0x7E57000E, 0x7E57000F, 0xE00, 0xF00
        .word 0x000003FF, 0, 0x00400000, 0x00000003     ; row 13: masks
        .word 0, 0, 0, 0                                ; row 14: zeros

        ; PTOFF: ir1 bit 3.
        and ds1[48], ir1, ds1[2]
        tstz p0, ds1[48]
        (p0) bra not_ptoff
        movs doutu, ds0[0], ds0[1], ds0[0], ds0[0]
        halt

not_ptoff:
        ; End of tile: ir1 bit 1.
        and ds1[48], ir1, ds1[3]
        tstz p0, ds1[48]
        (p0) bra not_eot
        ; With ir1 bit 8 also set, run the end-of-render task instead.
        not ds1[48], ir1
        and ds1[48], ds0[4], ds1[48]
        tstz p0, ds1[48]
        (p0) bra eor
        ; The tile's slot word in ds0[63].
        shr ds1[63], ir0, 9
        and ds0[63], ds0[26], ds1[63]                   ; tile_y
        shl ds1[63], ds0[63], 2
        and ds0[62], ir0, ds1[27]                       ; tile_x & 3
        or ds0[63], ds0[62], ds1[63]
        or ds0[63], ds0[63], ds1[26]                    ; (64 << 16) | slot

        {OP}

        ; U1 = base | tile_x | tile_y | ENDOFRENDER, as pds_pixevent.s.
        shl ds1[48], ir0, 3
        and ds1[48], ds0[5], ds1[48]
        or ds0[48], ds0[6], ds1[48]
        shl ds1[48], ir0, 3
        and ds1[48], ds0[7], ds1[48]
        or ds0[48], ds0[48], ds1[48]
        shl ds1[48], ir1, 20
        and ds1[48], ds0[8], ds1[48]
        or ds0[48], ds0[48], ds1[48]
        movs doutu, ds1[1], ds0[48], ds0[48], ds0[48]
        halt

not_eot:
        ; End of render: ir1 bit 2.
        and ds1[48], ir1, ds1[4]
        tstz p0, ds1[48]
        (p0) bra done
eor:
        movs doutu, ds0[2], ds0[3], ds0[2], ds0[2]
done:
        halt
