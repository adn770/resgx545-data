; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; A plain USE task for the pixel-event probes (sgxfive-test probe --tri pixev:N --slot
; pixtask=task_dump.bin): the probe's pixel-event program passes its results on with douta,
; then starts this task with the U0 the host put in its data dword 11 and U1 = 0 (no PBE),
; before the end-of-tile task, whose secondary attributes hold the tile's colours. It stores
; sa0-sa15 to scratch dwords 0-15. No .skipinv: in an end-of-tile task a .skipinv mov did
phas #0, #0, pixel, end, parallel
mov r0, #0x5CAF0000
stad [r0,+#0], sa0
stad [r0,+#1], sa1
stad [r0,+#2], sa2
stad [r0,+#3], sa3
stad [r0,+#4], sa4
stad [r0,+#5], sa5
stad [r0,+#6], sa6
stad [r0,+#7], sa7
stad [r0,+#8], sa8
stad [r0,+#9], sa9
stad [r0,+#10], sa10
stad [r0,+#11], sa11
stad [r0,+#12], sa12
stad [r0,+#13], sa13
stad [r0,+#14], sa14
stad [r0,+#15], sa15
idf drc0, bif
wdf drc0
nop.end
