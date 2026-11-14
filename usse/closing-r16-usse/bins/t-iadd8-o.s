; r16-usse t-iadd8-o: iadd8 lanes, the o join, chan0-or02 by the nine named fields (gen/progs.py)
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
iadd8.testtot.chan0 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.chan0 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.chan0 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.chan0 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#1], r10
mov.skipinv r10, r28
iadd8.testtot.chan1 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.chan1 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.chan1 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.chan1 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#2], r10
mov.skipinv r10, r28
iadd8.testtot.chan2 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.chan2 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.chan2 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.chan2 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#3], r10
mov.skipinv r10, r28
iadd8.testtot.chan3 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.chan3 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.chan3 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.chan3 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#4], r10
mov.skipinv r10, r28
iadd8.testtot.andall !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.andall !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.andall !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.andall !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.andall !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.andall !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.andall !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.andall !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.andall !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#5], r10
mov.skipinv r10, r28
iadd8.testtot.orall !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.orall !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.orall !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.orall !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.orall !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.orall !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.orall !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.orall !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.orall !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#6], r10
mov.skipinv r10, r28
iadd8.testtot.and02 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.and02 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.and02 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.and02 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.and02 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.and02 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.and02 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.and02 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.and02 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#7], r10
mov.skipinv r10, r28
iadd8.testtot.or02 !c0, p0, r1, r2
p0 or r10, r10, r12
iadd8.testtoz.or02 !c0, p0, r1, r2
p0 or r10, r10, r13
iadd8.testtonz.or02 !c0, p0, r1, r2
p0 or r10, r10, r14
iadd8.testnot.or02 !c0, p0, r1, r2
p0 or r10, r10, r16
iadd8.testnoz.or02 !c0, p0, r1, r2
p0 or r10, r10, r17
iadd8.testnonz.or02 !c0, p0, r1, r2
p0 or r10, r10, r18
iadd8.testpot.or02 !c0, p0, r1, r2
p0 or r10, r10, r20
iadd8.testpoz.or02 !c0, p0, r1, r2
p0 or r10, r10, r21
iadd8.testponz.or02 !c0, p0, r1, r2
p0 or r10, r10, r22
stad [r29,+#8], r10
idf drc0, bif
wdf drc0
mov.skipinv.end o0, r10
