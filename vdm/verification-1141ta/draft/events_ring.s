; SPDX-License-Identifier: MIT
; SPDX-FileCopyrightText: 2026 Josep Torra
; events_ring.s -- p1141/ta draft: a ring log of events, each with CR_TIMER (not landed).
; Rules as events_m.s: r0 to r31 only, no sa write, no emit, no lock, no str, same value every lane.

@entry 0
        mov r1, #0xdeadbeef                 ; @patch res+512
        mov r4, pa0
        mov r5, pa1
        mov r6, pa2
        ldr r8, #81, drc0
        wdf drc0
s0_0:
        ldad.bypassl1 r7, [r1,+#0], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_1
        mov r7, #0x00000001
        stad [r1,+#0], r7
        stad [r1,+#1], r4
        stad [r1,+#2], r5
        stad [r1,+#3], r6
        stad [r1,+#4], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_1:
        ldad.bypassl1 r7, [r1,+#8], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_2
        mov r7, #0x00000001
        stad [r1,+#8], r7
        stad [r1,+#9], r4
        stad [r1,+#10], r5
        stad [r1,+#11], r6
        stad [r1,+#12], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_2:
        ldad.bypassl1 r7, [r1,+#16], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_3
        mov r7, #0x00000001
        stad [r1,+#16], r7
        stad [r1,+#17], r4
        stad [r1,+#18], r5
        stad [r1,+#19], r6
        stad [r1,+#20], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_3:
        ldad.bypassl1 r7, [r1,+#24], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_4
        mov r7, #0x00000001
        stad [r1,+#24], r7
        stad [r1,+#25], r4
        stad [r1,+#26], r5
        stad [r1,+#27], r6
        stad [r1,+#28], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_4:
        ldad.bypassl1 r7, [r1,+#32], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_5
        mov r7, #0x00000001
        stad [r1,+#32], r7
        stad [r1,+#33], r4
        stad [r1,+#34], r5
        stad [r1,+#35], r6
        stad [r1,+#36], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_5:
        ldad.bypassl1 r7, [r1,+#40], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_6
        mov r7, #0x00000001
        stad [r1,+#40], r7
        stad [r1,+#41], r4
        stad [r1,+#42], r5
        stad [r1,+#43], r6
        stad [r1,+#44], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_6:
        ldad.bypassl1 r7, [r1,+#48], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_7
        mov r7, #0x00000001
        stad [r1,+#48], r7
        stad [r1,+#49], r4
        stad [r1,+#50], r5
        stad [r1,+#51], r6
        stad [r1,+#52], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_7:
        ldad.bypassl1 r7, [r1,+#56], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s0_8
        mov r7, #0x00000001
        stad [r1,+#56], r7
        stad [r1,+#57], r4
        stad [r1,+#58], r5
        stad [r1,+#59], r6
        stad [r1,+#60], r8
        idf drc0, bif
        wdf drc0
        br @s0_8
s0_8:
        mov r30, #0xdeadbeef                ; @patch cont0
        mov pclink, r30
        lapc
@entry 1
        mov r1, #0xdeadbeef                 ; @patch res+768
        mov r4, pa0
        mov r5, pa1
        mov r6, pa2
        ldr r8, #81, drc0
        wdf drc0
s1_0:
        ldad.bypassl1 r7, [r1,+#0], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_1
        mov r7, #0x00000001
        stad [r1,+#0], r7
        stad [r1,+#1], r4
        stad [r1,+#2], r5
        stad [r1,+#3], r6
        stad [r1,+#4], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_1:
        ldad.bypassl1 r7, [r1,+#8], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_2
        mov r7, #0x00000001
        stad [r1,+#8], r7
        stad [r1,+#9], r4
        stad [r1,+#10], r5
        stad [r1,+#11], r6
        stad [r1,+#12], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_2:
        ldad.bypassl1 r7, [r1,+#16], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_3
        mov r7, #0x00000001
        stad [r1,+#16], r7
        stad [r1,+#17], r4
        stad [r1,+#18], r5
        stad [r1,+#19], r6
        stad [r1,+#20], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_3:
        ldad.bypassl1 r7, [r1,+#24], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_4
        mov r7, #0x00000001
        stad [r1,+#24], r7
        stad [r1,+#25], r4
        stad [r1,+#26], r5
        stad [r1,+#27], r6
        stad [r1,+#28], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_4:
        ldad.bypassl1 r7, [r1,+#32], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_5
        mov r7, #0x00000001
        stad [r1,+#32], r7
        stad [r1,+#33], r4
        stad [r1,+#34], r5
        stad [r1,+#35], r6
        stad [r1,+#36], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_5:
        ldad.bypassl1 r7, [r1,+#40], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_6
        mov r7, #0x00000001
        stad [r1,+#40], r7
        stad [r1,+#41], r4
        stad [r1,+#42], r5
        stad [r1,+#43], r6
        stad [r1,+#44], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_6:
        ldad.bypassl1 r7, [r1,+#48], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_7
        mov r7, #0x00000001
        stad [r1,+#48], r7
        stad [r1,+#49], r4
        stad [r1,+#50], r5
        stad [r1,+#51], r6
        stad [r1,+#52], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_7:
        ldad.bypassl1 r7, [r1,+#56], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s1_8
        mov r7, #0x00000001
        stad [r1,+#56], r7
        stad [r1,+#57], r4
        stad [r1,+#58], r5
        stad [r1,+#59], r6
        stad [r1,+#60], r8
        idf drc0, bif
        wdf drc0
        br @s1_8
s1_8:
        mov r30, #0xdeadbeef                ; @patch cont1
        mov pclink, r30
        lapc
@entry 2
        mov r1, #0xdeadbeef                 ; @patch res+1024
        mov r4, pa0
        mov r5, pa1
        mov r6, pa2
        ldr r8, #81, drc0
        wdf drc0
s2_0:
        ldad.bypassl1 r7, [r1,+#0], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_1
        mov r7, #0x00000001
        stad [r1,+#0], r7
        stad [r1,+#1], r4
        stad [r1,+#2], r5
        stad [r1,+#3], r6
        stad [r1,+#4], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_1:
        ldad.bypassl1 r7, [r1,+#8], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_2
        mov r7, #0x00000001
        stad [r1,+#8], r7
        stad [r1,+#9], r4
        stad [r1,+#10], r5
        stad [r1,+#11], r6
        stad [r1,+#12], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_2:
        ldad.bypassl1 r7, [r1,+#16], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_3
        mov r7, #0x00000001
        stad [r1,+#16], r7
        stad [r1,+#17], r4
        stad [r1,+#18], r5
        stad [r1,+#19], r6
        stad [r1,+#20], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_3:
        ldad.bypassl1 r7, [r1,+#24], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_4
        mov r7, #0x00000001
        stad [r1,+#24], r7
        stad [r1,+#25], r4
        stad [r1,+#26], r5
        stad [r1,+#27], r6
        stad [r1,+#28], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_4:
        ldad.bypassl1 r7, [r1,+#32], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_5
        mov r7, #0x00000001
        stad [r1,+#32], r7
        stad [r1,+#33], r4
        stad [r1,+#34], r5
        stad [r1,+#35], r6
        stad [r1,+#36], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_5:
        ldad.bypassl1 r7, [r1,+#40], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_6
        mov r7, #0x00000001
        stad [r1,+#40], r7
        stad [r1,+#41], r4
        stad [r1,+#42], r5
        stad [r1,+#43], r6
        stad [r1,+#44], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_6:
        ldad.bypassl1 r7, [r1,+#48], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_7
        mov r7, #0x00000001
        stad [r1,+#48], r7
        stad [r1,+#49], r4
        stad [r1,+#50], r5
        stad [r1,+#51], r6
        stad [r1,+#52], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_7:
        ldad.bypassl1 r7, [r1,+#56], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s2_8
        mov r7, #0x00000001
        stad [r1,+#56], r7
        stad [r1,+#57], r4
        stad [r1,+#58], r5
        stad [r1,+#59], r6
        stad [r1,+#60], r8
        idf drc0, bif
        wdf drc0
        br @s2_8
s2_8:
        mov r30, #0xdeadbeef                ; @patch cont2
        mov pclink, r30
        lapc
@entry 3
        mov r1, #0xdeadbeef                 ; @patch res+1280
        mov r4, pa0
        mov r5, pa1
        mov r6, pa2
        ldr r8, #81, drc0
        wdf drc0
s3_0:
        ldad.bypassl1 r7, [r1,+#0], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_1
        mov r7, #0x00000001
        stad [r1,+#0], r7
        stad [r1,+#1], r4
        stad [r1,+#2], r5
        stad [r1,+#3], r6
        stad [r1,+#4], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_1:
        ldad.bypassl1 r7, [r1,+#8], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_2
        mov r7, #0x00000001
        stad [r1,+#8], r7
        stad [r1,+#9], r4
        stad [r1,+#10], r5
        stad [r1,+#11], r6
        stad [r1,+#12], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_2:
        ldad.bypassl1 r7, [r1,+#16], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_3
        mov r7, #0x00000001
        stad [r1,+#16], r7
        stad [r1,+#17], r4
        stad [r1,+#18], r5
        stad [r1,+#19], r6
        stad [r1,+#20], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_3:
        ldad.bypassl1 r7, [r1,+#24], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_4
        mov r7, #0x00000001
        stad [r1,+#24], r7
        stad [r1,+#25], r4
        stad [r1,+#26], r5
        stad [r1,+#27], r6
        stad [r1,+#28], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_4:
        ldad.bypassl1 r7, [r1,+#32], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_5
        mov r7, #0x00000001
        stad [r1,+#32], r7
        stad [r1,+#33], r4
        stad [r1,+#34], r5
        stad [r1,+#35], r6
        stad [r1,+#36], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_5:
        ldad.bypassl1 r7, [r1,+#40], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_6
        mov r7, #0x00000001
        stad [r1,+#40], r7
        stad [r1,+#41], r4
        stad [r1,+#42], r5
        stad [r1,+#43], r6
        stad [r1,+#44], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_6:
        ldad.bypassl1 r7, [r1,+#48], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_7
        mov r7, #0x00000001
        stad [r1,+#48], r7
        stad [r1,+#49], r4
        stad [r1,+#50], r5
        stad [r1,+#51], r6
        stad [r1,+#52], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_7:
        ldad.bypassl1 r7, [r1,+#56], drc0
        wdf drc0
        and.testtanz.chan0 !c0, p0, r7, r7  ; p0 = slot taken
        p0 br @s3_8
        mov r7, #0x00000001
        stad [r1,+#56], r7
        stad [r1,+#57], r4
        stad [r1,+#58], r5
        stad [r1,+#59], r6
        stad [r1,+#60], r8
        idf drc0, bif
        wdf drc0
        br @s3_8
s3_8:
        mov r30, #0xdeadbeef                ; @patch cont3
        mov pclink, r30
        lapc
