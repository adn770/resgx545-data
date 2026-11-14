; r16-usse t-or7-a: or #7, the a join, fields 0-15 over six pairs (sgx-sim's rule) (gen/progs.py)
phas #0, #0, pixel, end, parallel
mov.skipinv r29, #0x5CAF0000
mov.skipinv r28, #0x5A5A0000
mov.skipinv r12, #0x00000001
mov.skipinv r13, #0x00000002
mov.skipinv r14, #0x00000004
mov.skipinv r15, #0x00000008
mov.skipinv r16, #0x00000010
mov.skipinv r17, #0x00000020
mov.skipinv r18, #0x00000040
mov.skipinv r19, #0x00000080
mov.skipinv r20, #0x00000100
mov.skipinv r21, #0x00000200
mov.skipinv r22, #0x00000400
mov.skipinv r23, #0x00000800
mov.skipinv r24, #0x00001000
mov.skipinv r25, #0x00002000
mov.skipinv r26, #0x00004000
mov.skipinv r27, #0x00008000
mov.skipinv r1, #0x00000000
or.testtat.chan0 r3, p0, r1, #7
stad [r29,+#0], r3
mov.skipinv r10, r28
or.testtat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r12
or.testtaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r13
or.testtanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r14
.long 0x48091381200C4087
p0 or r10, r10, r15
or.testnat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r16
or.testnaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r17
or.testnanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r18
.long 0x48091781200C4087
p0 or r10, r10, r19
or.testpat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r20
or.testpaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r21
or.testpanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r22
.long 0x48091B81200C4087
p0 or r10, r10, r23
.long 0x48091C81200C4087
p0 or r10, r10, r24
.long 0x48091D81200C4087
p0 or r10, r10, r25
.long 0x48091E81200C4087
p0 or r10, r10, r26
.long 0x48091F81200C4087
p0 or r10, r10, r27
stad [r29,+#1], r10
mov.skipinv r1, #0x00000008
or.testtat.chan0 r3, p0, r1, #7
stad [r29,+#2], r3
mov.skipinv r10, r28
or.testtat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r12
or.testtaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r13
or.testtanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r14
.long 0x48091381200C4087
p0 or r10, r10, r15
or.testnat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r16
or.testnaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r17
or.testnanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r18
.long 0x48091781200C4087
p0 or r10, r10, r19
or.testpat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r20
or.testpaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r21
or.testpanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r22
.long 0x48091B81200C4087
p0 or r10, r10, r23
.long 0x48091C81200C4087
p0 or r10, r10, r24
.long 0x48091D81200C4087
p0 or r10, r10, r25
.long 0x48091E81200C4087
p0 or r10, r10, r26
.long 0x48091F81200C4087
p0 or r10, r10, r27
stad [r29,+#3], r10
mov.skipinv r1, #0x7FFFFFF8
or.testtat.chan0 r3, p0, r1, #7
stad [r29,+#4], r3
mov.skipinv r10, r28
or.testtat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r12
or.testtaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r13
or.testtanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r14
.long 0x48091381200C4087
p0 or r10, r10, r15
or.testnat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r16
or.testnaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r17
or.testnanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r18
.long 0x48091781200C4087
p0 or r10, r10, r19
or.testpat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r20
or.testpaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r21
or.testpanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r22
.long 0x48091B81200C4087
p0 or r10, r10, r23
.long 0x48091C81200C4087
p0 or r10, r10, r24
.long 0x48091D81200C4087
p0 or r10, r10, r25
.long 0x48091E81200C4087
p0 or r10, r10, r26
.long 0x48091F81200C4087
p0 or r10, r10, r27
stad [r29,+#5], r10
mov.skipinv r1, #0x80000000
or.testtat.chan0 r3, p0, r1, #7
stad [r29,+#6], r3
mov.skipinv r10, r28
or.testtat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r12
or.testtaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r13
or.testtanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r14
.long 0x48091381200C4087
p0 or r10, r10, r15
or.testnat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r16
or.testnaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r17
or.testnanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r18
.long 0x48091781200C4087
p0 or r10, r10, r19
or.testpat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r20
or.testpaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r21
or.testpanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r22
.long 0x48091B81200C4087
p0 or r10, r10, r23
.long 0x48091C81200C4087
p0 or r10, r10, r24
.long 0x48091D81200C4087
p0 or r10, r10, r25
.long 0x48091E81200C4087
p0 or r10, r10, r26
.long 0x48091F81200C4087
p0 or r10, r10, r27
stad [r29,+#7], r10
mov.skipinv r1, #0xFFFFFFF8
or.testtat.chan0 r3, p0, r1, #7
stad [r29,+#8], r3
mov.skipinv r10, r28
or.testtat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r12
or.testtaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r13
or.testtanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r14
.long 0x48091381200C4087
p0 or r10, r10, r15
or.testnat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r16
or.testnaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r17
or.testnanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r18
.long 0x48091781200C4087
p0 or r10, r10, r19
or.testpat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r20
or.testpaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r21
or.testpanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r22
.long 0x48091B81200C4087
p0 or r10, r10, r23
.long 0x48091C81200C4087
p0 or r10, r10, r24
.long 0x48091D81200C4087
p0 or r10, r10, r25
.long 0x48091E81200C4087
p0 or r10, r10, r26
.long 0x48091F81200C4087
p0 or r10, r10, r27
stad [r29,+#9], r10
mov.skipinv r1, #0x12345670
or.testtat.chan0 r3, p0, r1, #7
stad [r29,+#10], r3
mov.skipinv r10, r28
or.testtat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r12
or.testtaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r13
or.testtanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r14
.long 0x48091381200C4087
p0 or r10, r10, r15
or.testnat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r16
or.testnaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r17
or.testnanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r18
.long 0x48091781200C4087
p0 or r10, r10, r19
or.testpat.chan0 !c0, p0, r1, #7
p0 or r10, r10, r20
or.testpaz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r21
or.testpanz.chan0 !c0, p0, r1, #7
p0 or r10, r10, r22
.long 0x48091B81200C4087
p0 or r10, r10, r23
.long 0x48091C81200C4087
p0 or r10, r10, r24
.long 0x48091D81200C4087
p0 or r10, r10, r25
.long 0x48091E81200C4087
p0 or r10, r10, r26
.long 0x48091F81200C4087
p0 or r10, r10, r27
stad [r29,+#11], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
