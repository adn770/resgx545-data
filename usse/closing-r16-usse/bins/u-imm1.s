; r16-usse u-imm1 (gen/progs.py)
phas #0, #0, pixel, end, parallel
mov.skipinv r29, #0x5CAF0000
mov.skipinv r1, #0x00008000
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#0], r10
mov.skipinv r1, #0x00008001
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#1], r10
mov.skipinv r1, #0x0000ABCD
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#2], r10
mov.skipinv r1, #0x0000FFFF
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#3], r10
mov.skipinv r1, #0x00007FFF
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#4], r10
mov.skipinv r1, #0xFFFF8000
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#5], r10
mov.skipinv r1, #0x1234FEDC
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#6], r10
mov.skipinv r1, #0xFFFFFFFF
iaddu32.testtaz.chan0 r10, p0, r1, #1
stad [r29,+#7], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
