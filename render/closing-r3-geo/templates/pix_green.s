; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; pix_green.s -- a plain pixel shader writing green (slot pixel), for the probes whose case
; replaces another slot, so that the triangle's pixels have a colour the readers know.
phas #0, #0, pixel, end, parallel
mov.skipinv.end o0, #0xFF00FF00
