; r16-usse t-iadd32-a: iadd32 r2, the a join, fields 0-15 over six pairs (sgx-sim's rule) (gen/progs.py)
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
mov.skipinv r2, #0x00000000
iadd32.testtat.chan0 r3, p0, r1, r2
stad [r29,+#0], r3
mov.skipinv r10, r28
iadd32.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd32.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd32.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
.long 0x4808138100070082
p0 or r10, r10, r15
iadd32.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd32.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd32.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
.long 0x4808178100070082
p0 or r10, r10, r19
iadd32.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd32.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd32.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
.long 0x48081B8100070082
p0 or r10, r10, r23
.long 0x48081C8100070082
p0 or r10, r10, r24
.long 0x48081D8100070082
p0 or r10, r10, r25
.long 0x48081E8100070082
p0 or r10, r10, r26
.long 0x48081F8100070082
p0 or r10, r10, r27
stad [r29,+#1], r10
mov.skipinv r1, #0x00000001
mov.skipinv r2, #0xFFFFFFFF
iadd32.testtat.chan0 r3, p0, r1, r2
stad [r29,+#2], r3
mov.skipinv r10, r28
iadd32.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd32.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd32.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
.long 0x4808138100070082
p0 or r10, r10, r15
iadd32.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd32.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd32.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
.long 0x4808178100070082
p0 or r10, r10, r19
iadd32.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd32.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd32.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
.long 0x48081B8100070082
p0 or r10, r10, r23
.long 0x48081C8100070082
p0 or r10, r10, r24
.long 0x48081D8100070082
p0 or r10, r10, r25
.long 0x48081E8100070082
p0 or r10, r10, r26
.long 0x48081F8100070082
p0 or r10, r10, r27
stad [r29,+#3], r10
mov.skipinv r1, #0x00008000
mov.skipinv r2, #0x00008000
iadd32.testtat.chan0 r3, p0, r1, r2
stad [r29,+#4], r3
mov.skipinv r10, r28
iadd32.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd32.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd32.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
.long 0x4808138100070082
p0 or r10, r10, r15
iadd32.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd32.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd32.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
.long 0x4808178100070082
p0 or r10, r10, r19
iadd32.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd32.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd32.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
.long 0x48081B8100070082
p0 or r10, r10, r23
.long 0x48081C8100070082
p0 or r10, r10, r24
.long 0x48081D8100070082
p0 or r10, r10, r25
.long 0x48081E8100070082
p0 or r10, r10, r26
.long 0x48081F8100070082
p0 or r10, r10, r27
stad [r29,+#5], r10
mov.skipinv r1, #0x00000005
mov.skipinv r2, #0x00000003
iadd32.testtat.chan0 r3, p0, r1, r2
stad [r29,+#6], r3
mov.skipinv r10, r28
iadd32.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd32.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd32.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
.long 0x4808138100070082
p0 or r10, r10, r15
iadd32.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd32.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd32.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
.long 0x4808178100070082
p0 or r10, r10, r19
iadd32.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd32.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd32.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
.long 0x48081B8100070082
p0 or r10, r10, r23
.long 0x48081C8100070082
p0 or r10, r10, r24
.long 0x48081D8100070082
p0 or r10, r10, r25
.long 0x48081E8100070082
p0 or r10, r10, r26
.long 0x48081F8100070082
p0 or r10, r10, r27
stad [r29,+#7], r10
mov.skipinv r1, #0x0000FFFF
mov.skipinv r2, #0x00000000
iadd32.testtat.chan0 r3, p0, r1, r2
stad [r29,+#8], r3
mov.skipinv r10, r28
iadd32.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd32.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd32.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
.long 0x4808138100070082
p0 or r10, r10, r15
iadd32.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd32.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd32.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
.long 0x4808178100070082
p0 or r10, r10, r19
iadd32.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd32.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd32.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
.long 0x48081B8100070082
p0 or r10, r10, r23
.long 0x48081C8100070082
p0 or r10, r10, r24
.long 0x48081D8100070082
p0 or r10, r10, r25
.long 0x48081E8100070082
p0 or r10, r10, r26
.long 0x48081F8100070082
p0 or r10, r10, r27
stad [r29,+#9], r10
mov.skipinv r1, #0x00007FFF
mov.skipinv r2, #0x7FFFFFFF
iadd32.testtat.chan0 r3, p0, r1, r2
stad [r29,+#10], r3
mov.skipinv r10, r28
iadd32.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd32.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd32.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
.long 0x4808138100070082
p0 or r10, r10, r15
iadd32.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd32.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd32.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
.long 0x4808178100070082
p0 or r10, r10, r19
iadd32.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd32.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd32.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
.long 0x48081B8100070082
p0 or r10, r10, r23
.long 0x48081C8100070082
p0 or r10, r10, r24
.long 0x48081D8100070082
p0 or r10, r10, r25
.long 0x48081E8100070082
p0 or r10, r10, r26
.long 0x48081F8100070082
p0 or r10, r10, r27
stad [r29,+#11], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
