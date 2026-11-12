; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; pix_posstore.s (round 7 plan, Q291; a draft for the session builder, not landed): a triangle's
; pixel shader that stores each instance's iterated attributes at a scratch slot formed from the
; instance's own place in its tile, so that instances of the tile area past the target (where
; the colour store writes nothing) can be read.  slot = g24 << 5 | g23 (g23 = x mod 32, g24 = y
; mod 16 in a triangle's pixel program, E808), 16 bytes a slot, 512 slots = 8 KiB of the 64 KiB
; scratch buffer:
;   dword 0  pa0 of every instance that runs (no .skipinv: all four of a touched quad, E111)
;   dword 1  pa0 of the valid instances only (.skipinv)
;   dword 2  pa1 of the valid instances only
;   dword 3  0x7E570000 | g25 of the valid instances (the lane, a check of the slot: g25 must be
;            (x & 1) | (y & 1) << 1 of the slot's own x and y)
; Only g23, g24 and g25 are read (the registers sgx-sim models in a triangle's pixel task), so
; two tiles of a job would share slots: each job's triangle touches ONE tile (the plan's rows).
; The register offset of a store is high x low bytes (the measured stad [rN,+rM] rule,
; probes/pds/templates/eot_tile.s): 16 x slot.  The slot is masked to 9 bits before the stride is
; set, so that an instance whose g23 or g24 is not a tile position (an invalid instance of a
; touched quad: not measured) still stores inside the first 8 KiB of the scratch buffer.
; Temporaries r0-r2: run with --temps 4 or more.
phas #0, #0, pixel, end, parallel
shl r1, g24, #5
or r1, r1, g23
and r1, r1, #0x1ff
or r1, r1, #0x00100000
or r2, g25, #0x7E570000
mov r0, #0x5CAF0000
stad [r0,+r1], pa0
mov r0, #0x5CAF0004
stad.skipinv [r0,+r1], pa0
mov r0, #0x5CAF0008
stad.skipinv [r0,+r1], pa1
mov r0, #0x5CAF000C
stad.skipinv [r0,+r1], r2
idf drc0, bif
wdf drc0
mov.skipinv.end o0, pa0
