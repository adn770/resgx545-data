; r16-usse t-iadd8-a: iadd8 lanes, the a join, chan0-or02 by the nine named fields (gen/progs.py)
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
mov.skipinv r1, #0x05F00100
mov.skipinv r2, #0x03010200
iadd8.testtat.chan0 r3, p0, r1, r2
stad [r29,+#0], r3
mov.skipinv r10, r28
iadd8.testtat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#1], r10
mov.skipinv r10, r28
iadd8.testtat.chan1 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.chan1 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.chan1 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#2], r10
mov.skipinv r10, r28
iadd8.testtat.chan2 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.chan2 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.chan2 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#3], r10
mov.skipinv r10, r28
iadd8.testtat.chan3 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.chan3 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.chan3 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#4], r10
mov.skipinv r10, r28
iadd8.testtat.andall !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.andall !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.andall !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.andall !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.andall !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.andall !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.andall !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.andall !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.andall !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#5], r10
mov.skipinv r10, r28
iadd8.testtat.orall !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.orall !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.orall !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.orall !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.orall !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.orall !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.orall !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.orall !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.orall !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#6], r10
mov.skipinv r10, r28
iadd8.testtat.and02 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.and02 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.and02 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.and02 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.and02 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.and02 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.and02 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.and02 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.and02 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#7], r10
mov.skipinv r10, r28
iadd8.testtat.or02 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtaz.or02 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtanz.or02 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnat.or02 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnaz.or02 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnanz.or02 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpat.or02 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpaz.or02 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testpanz.or02 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#8], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
