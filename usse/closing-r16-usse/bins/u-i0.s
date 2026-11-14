; r16-usse u-i0 (gen/progs.py)
phas #0, #0, pixel, end, parallel
mov.skipinv r29, #0x5CAF0000
mov.skipinv r1, #0x00008000
mov.skipinv r2, #0x00008000
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#0], r3
mov.skipinv r1, #0x00008001
mov.skipinv r2, #0x7FFF0000
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#1], r3
mov.skipinv r1, #0x0000ABCD
mov.skipinv r2, #0x00000001
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#2], r3
mov.skipinv r1, #0x0000FFFF
mov.skipinv r2, #0xFFFFFFFF
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#3], r3
mov.skipinv r1, #0x00007FFF
mov.skipinv r2, #0x00008001
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#4], r3
mov.skipinv r1, #0xFFFF8000
mov.skipinv r2, #0x12345678
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#5], r3
mov.skipinv r1, #0x1234FEDC
mov.skipinv r2, #0x80000000
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#6], r3
mov.skipinv r1, #0xFFFFFFFF
mov.skipinv r2, #0x00010000
iaddu32.testtaz.chan0 i0, p0, r1, r2
mov r3, i0
stad [r29,+#7], r3
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r3
