; r16-usse u-ctl-rpt (gen/progs.py)
phas #0, #0, pixel, end, parallel
mov.skipinv r29, #0x5CAF0000
mov.skipinv r1, #0x00008000
mov.skipinv r2, #0x00008000
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#0], r10
mov.skipinv r1, #0x0000FFFF
mov.skipinv r2, #0x00000001
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#1], r10
mov.skipinv r1, #0xFFFFFFFF
mov.skipinv r2, #0x00000001
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#2], r10
mov.skipinv r1, #0x7FFFFFFF
mov.skipinv r2, #0x00000001
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#3], r10
mov.skipinv r1, #0xFFFFFFFF
mov.skipinv r2, #0x00000002
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#4], r10
mov.skipinv r1, #0x7C23A2BD
mov.skipinv r2, #0x47B003F0
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#5], r10
mov.skipinv r1, #0xB99EDE85
mov.skipinv r2, #0x87261F80
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#6], r10
mov.skipinv r1, #0x12345678
mov.skipinv r2, #0x11111111
iaddu32.testtaz.chan0 r10, p0, r1, r2
stad [r29,+#7], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
