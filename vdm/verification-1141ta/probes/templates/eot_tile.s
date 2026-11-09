; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; The per-tile end-of-tile program of the triangle probes (--slot eot=eot_tile.bin): as
; eot_dump.s, but each tile stores sa0-sa15 to its own 16 dwords. The probe's pixel-event
; program passes the tile's slot in sa15 as (64 << 16) | slot (pixev_dump.s computes it in
; ds0[63]), the register offset of the stores: high x low = 64 x slot bytes (the measured
; ldad/stad [rN,+rM] rule, probe ldad-reg-off). So scratch dwords 16 x slot + k hold the
; tile's sak, and dword 16 x slot + 15 its slot word, which tags it. 1024 slots fill the
; 64 KiB scratch buffer. The slot word is clamped to that (low 10 bits, stride 64): on a
; multi-tile render some tiles' tasks do not get the attributes the event passed on
; buffer; such a tile's 16 dwords lack the markers the probe passed.
;
; As use_eot.s, instructions 1-4 are the four movs the host patches with PBE words 0-3
; (registers r0-r3) and the last instruction is the emitpix2 that gets the sideband.
; Temporaries r0-r5: run with --temps 8.
phas #0, #0, pixel, end, parallel
mov.skipinv r0, #0x00000000
mov.skipinv r0, #0x00000000
mov.skipinv r0, #0x00000000
mov.skipinv r0, #0x00000000
and r5, sa15, #0x3ff
or r5, r5, #0x00400000
mov r4, #0x5CAF0000
stad [r4,+r5], sa0
mov r4, #0x5CAF0004
stad [r4,+r5], sa1
mov r4, #0x5CAF0008
stad [r4,+r5], sa2
mov r4, #0x5CAF000C
stad [r4,+r5], sa3
mov r4, #0x5CAF0010
stad [r4,+r5], sa4
mov r4, #0x5CAF0014
stad [r4,+r5], sa5
mov r4, #0x5CAF0018
stad [r4,+r5], sa6
mov r4, #0x5CAF001C
stad [r4,+r5], sa7
mov r4, #0x5CAF0020
stad [r4,+r5], sa8
mov r4, #0x5CAF0024
stad [r4,+r5], sa9
mov r4, #0x5CAF0028
stad [r4,+r5], sa10
mov r4, #0x5CAF002C
stad [r4,+r5], sa11
mov r4, #0x5CAF0030
stad [r4,+r5], sa12
mov r4, #0x5CAF0034
stad [r4,+r5], sa13
mov r4, #0x5CAF0038
stad [r4,+r5], sa14
mov r4, #0x5CAF003C
stad [r4,+r5], sa15
idf drc0, bif
wdf drc0
emitpix1.freep #0 /* incp */, r0, r1
emitpix2.end.freep #0 /* incp */, r2, r3, r0, #0x00000000
