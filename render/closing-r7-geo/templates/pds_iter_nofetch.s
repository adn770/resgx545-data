; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; pds_tex_iter.s without the fetch: {A} DOUTI word 0, {B} DOUTI word 1, {U} the shader's U1
; (0x02000004 waits for the fetch, DOUTU1.WAIT_FETCH; 4 does not). The texture state stays
; in the data, but no doutt is issued.

        .word 0          ; dword 0  = ds0[0]: U0 of the pixel shader (patched)
        .word 0          ; dword 1  = ds0[1]: U1 (patched: 4; not used)
        .word 0          ; dword 2  = ds1[0]: U2 = 0
        .word {U}        ; dword 3  = ds1[1]: U1
        .word {A}        ; dword 4  = ds0[2]: DOUTI word 0
        .word {B}        ; dword 5  = ds0[3]: DOUTI word 1
        .word 0x5CAF0000 ; dword 6  = ds1[2]: T2, the scratch buffer (patched)
        .word 0x00800800 ; dword 7  = ds1[3]: T3
        .word 0x07fe0000 ; dword 8  = ds0[4]: T0, nearest, repeat
        .word 0x0d00f00f ; dword 9  = ds0[5]: T1, RGBA8888, POT, 16x16
        .word 0          ; dword 10 = ds1[4]: unused
        .word 0          ; dword 11 = ds1[5]: unused

        movs doutu, ds0[0], ds1[1], ds1[0], ds0[0]
        movs douti, ds0[2], ds0[3], ds0[2], ds0[2]
        halt
