; r16-usse u-rpt4 (gen/progs.py)
phas #0, #0, pixel, end, parallel
mov.skipinv r29, #0x5CAF0000
mov.skipinv r10, #0xA0A1A2A3
mov.skipinv r11, #0xA4A5A6A7
mov.skipinv r12, #0xA8A9AAAB
mov.skipinv r13, #0xACADAEAF
mov.skipinv r1, #0x00008000
mov.skipinv r2, #0x00008001
mov.skipinv r3, #0x0000ABCD
mov.skipinv r4, #0x0000FFFF
mov.skipinv r5, #0x00008000
mov.skipinv r6, #0x7FFF0000
mov.skipinv r7, #0x00000001
mov.skipinv r8, #0xFFFFFFFF
iaddu32.testtaz.chan0 r10.xyzw, p0, r1, r5
stad [r29,+#0], r10
stad [r29,+#1], r11
stad [r29,+#2], r12
stad [r29,+#3], r13
mov.skipinv r10, #0xA0A1A2A3
mov.skipinv r11, #0xA4A5A6A7
mov.skipinv r12, #0xA8A9AAAB
mov.skipinv r13, #0xACADAEAF
mov.skipinv r1, #0x00007FFF
mov.skipinv r2, #0xFFFF8000
mov.skipinv r3, #0x1234FEDC
mov.skipinv r4, #0xFFFFFFFF
mov.skipinv r5, #0x00008001
mov.skipinv r6, #0x12345678
mov.skipinv r7, #0x80000000
mov.skipinv r8, #0x00010000
iaddu32.testtaz.chan0 r10.xyzw, p0, r1, r5
stad [r29,+#4], r10
stad [r29,+#5], r11
stad [r29,+#6], r12
stad [r29,+#7], r13
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
