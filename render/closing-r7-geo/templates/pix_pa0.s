; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; A pixel shader for the iteration probes (--slot pixel=pix_pa0.bin): the colour is primary
; attribute 0, as the copy shader passes its texel on (asm/transfer/use_copy.s).
phas #0, #0, pixel, end, parallel
mov.skipinv.end o0, pa0
