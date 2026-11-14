; r16-usse u-ctl-e498 (gen/progs.py)
phas #0, #0, pixel, end, parallel
mov.skipinv r29, #0x5CAF0000
mov.skipinv r1, #0x00000000
mov.skipinv r2, #0x00000000
iaddu32.testtaz.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#0], r10
iaddu32.testtanz.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#1], r10
iaddu32.testnat.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#2], r10
iaddu32.testpat.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#3], r10
mov.skipinv r1, #0x00008000
mov.skipinv r2, #0x00008000
iaddu32.testtaz.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#4], r10
iaddu32.testtanz.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#5], r10
iaddu32.testnat.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#6], r10
iaddu32.testpat.chan0 !c0, p0, r1, r2
mov r10, #0
p0 mov r10, #1
stad [r29,+#7], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
