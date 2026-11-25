# r45-n3j-n1

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. No build and no boot: the laptop runs the r42-kernel module
(srcversion 079DD0D13F231EEAC52FE0F).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 94f9e5010d60 (branch r45-n3j on
main 1c8dc10e, not merged: K9, the command count of the scorer's DK control) and resgx545-data
ebfeaa7754e4, laptop prefix `r45j1`, HostKeyAlias `cedar`. Question Q128 (N3j): which client event
lands in attribute 1, second reads, and what land's page follows. Design: `closing29/n3j/design.md`
(§3 the rows, §6 order and time, §8 the user's decisions A=a, B=a, C=a, D=b, F=a). Built offline,
frozen, not staged, not run.

**When:** first of round 45 (decisions A (a), F (a)): five plants and the second reads after
fill-fill, tri and tri-fill, the new tri-tri, a third read of one fill, then F2b with no plant; all
quiet, no planned stop; no build, no boot. The round's order: N1, then N2, then N3, then N4
(decision F (a), D (b)); the whole session in one `run`.

**Module.** fork r42-kernel ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, loaded = installed
since round 42: mark, crumb3 and land are its images, sbc43 its form; no fork change.

## Stage wa: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wa1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wa

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it**, byte for byte (design
§3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round
42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x005d3000 | ds0[4]: M13 0x005d3000 |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage wa (predictions/wa.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-WA RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage ff2: row FF2, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill,fill", own_gate = "none"

The second read of FF (E1191, M1 kept): crumb3 after two fills (begin_draws "fill,fill", run once,
each draw kept under its own name). M1 again (H-TRI, H-FIRST), or a fill's 3:4 word, or a tick's
(H-RACE).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row ff21-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage ff2

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: crumb3 as G2 q and round 44's FF, T, TF and F2 ran it**, byte for
byte (design §3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in
every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage ff2 (predictions/ff2.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| FF2-KEEP | M1 (FF's read, E1191) [HW once; H-TRI, H-FIRST] (postsa1 = 0x005d1000) | **held** |
| FF2-FILL | 0x04000010 (the 2nd fill's 3:4 at K 4) or 0x02000010 (the 1st's at K 2) [infer] (postsa1 = @any:0x04000010,0x02000010) | failed |
| FF2-TICK | bits 23:0 = 0, top byte 1-4 (a tick) [infer; held only under H-RACE] (postsa1 = @any:tick) | failed |
| FF2-OTHER | any other word (postsa1 = @notany:0x005d1000,0x04000010,0x02000010,tick) | printed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session). The RULE line `Q128-N3J-FF2 RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and
sa13, the kernel's "events seen" lines, the KC lines (the begin and end command counts) and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (FF2-FILL, T2-34, TF2-FILL, TT-LAST, TT-FIRST,
TT-KEEP, F3-TICK, F3-FILL) read cannot tell; the -KEEP and -SAME outcomes still stand. B failing (a
fault with no pass planned): stop the session for the user.

## Stage wb: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wb1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wb

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it**, byte for byte (design
§3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round
42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x005d3000 | ds0[4]: M13 0x005d3000 |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage wb (predictions/wb.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-WB RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage t2: row T2, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri", own_gate = "none"

The second read of T (E1193, 0x02400000): crumb3 after a triangle alone (begin_draws "tri"). The
same word, the 3:4 variant, or M1.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row t21-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage t2

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: crumb3 as G2 q and round 44's FF, T, TF and F2 ran it**, byte for
byte (design §3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in
every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage t2 (predictions/t2.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| T2-SAME | 0x02400000 (T's read, E1193; the 3:22 at K 2) [HW once; H-TRI, H-FIRST] (postsa1 = 0x02400000) | **held** |
| T2-34 | 0x02000010 (the triangle's 3:4, X's variant) [infer; H-RACE allows it] (postsa1 = 0x02000010) | failed |
| T2-KEEP | M1 [infer] (postsa1 = 0x005d1000) | failed |
| T2-OTHER | any other word (postsa1 = @notany:0x02400000,0x02000010,0x005d1000) | printed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session). The RULE line `Q128-N3J-T2 RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and
sa13, the kernel's "events seen" lines, the KC lines (the begin and end command counts) and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (FF2-FILL, T2-34, TF2-FILL, TT-LAST, TT-FIRST,
TT-KEEP, F3-TICK, F3-FILL) read cannot tell; the -KEEP and -SAME outcomes still stand. B failing (a
fault with no pass planned): stop the session for the user.

## Stage wc: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wc1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wc

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it**, byte for byte (design
§3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round
42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x005d3000 | ds0[4]: M13 0x005d3000 |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage wc (predictions/wc.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-WC RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage tf2: row TF2, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri,fill", own_gate = "none"

The second read of TF (E1195, 0x02400000): crumb3 after a triangle then a fill (begin_draws
"tri,fill"). The same word, the fill's 3:4 at K 8, or M1.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row tf21-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage tf2

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: crumb3 as G2 q and round 44's FF, T, TF and F2 ran it**, byte for
byte (design §3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in
every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage tf2 (predictions/tf2.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| TF2-SAME | 0x02400000 (TF's read, E1195) [HW once; H-TRI, H-FIRST] (postsa1 = 0x02400000) | **held** |
| TF2-FILL | 0x08000010 (the fill's 3:4 at K 8) [infer; H-RACE allows it] (postsa1 = 0x08000010) | failed |
| TF2-KEEP | M1 [infer] (postsa1 = 0x005d1000) | failed |
| TF2-OTHER | any other word (postsa1 = @notany:0x02400000,0x08000010,0x005d1000) | printed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session). The RULE line `Q128-N3J-TF2 RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and
sa13, the kernel's "events seen" lines, the KC lines (the begin and end command counts) and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (FF2-FILL, T2-34, TF2-FILL, TT-LAST, TT-FIRST,
TT-KEEP, F3-TICK, F3-FILL) read cannot tell; the -KEEP and -SAME outcomes still stand. B failing (a
fault with no pass planned): stop the session for the user.

## Stage wd: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wd1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wd

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it**, byte for byte (design
§3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round
42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x005d3000 | ds0[4]: M13 0x005d3000 |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage wd (predictions/wd.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-WD RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage tt: row TT, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri,tri", own_gate = "none"

New: crumb3 after two triangles (begin_draws "tri,tri"). Splits H-TRI (the last triangle writes:
0x08400000) from H-FIRST (only the first after a load: 0x02400000).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row tt1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage tt

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: crumb3 as G2 q and round 44's FF, T, TF and F2 ran it**, byte for
byte (design §3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in
every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage tt (predictions/tt.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| TT-LAST | 0x08400000 (or its 3:4 variant 0x08000010) [infer, H-TRI] (postsa1 = @any:0x08400000,0x08000010) | **held** |
| TT-FIRST | 0x02400000 (or 0x02000010) [infer; held under H-FIRST] (postsa1 = @any:0x02400000,0x02000010) | failed |
| TT-KEEP | M1 [infer] (postsa1 = 0x005d1000) | failed |
| TT-OTHER | any other word (postsa1 = @notany:0x08400000,0x08000010,0x02400000,0x02000010,0x005d1000) | printed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session). The RULE line `Q128-N3J-TT RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and
sa13, the kernel's "events seen" lines, the KC lines (the begin and end command counts) and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (FF2-FILL, T2-34, TF2-FILL, TT-LAST, TT-FIRST,
TT-KEEP, F3-TICK, F3-FILL) read cannot tell; the -KEEP and -SAME outcomes still stand. B failing (a
fault with no pass planned): stop the session for the user.

## Stage we: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row we1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage we

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it**, byte for byte (design
§3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round
42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x005d3000 | ds0[4]: M13 0x005d3000 |
| 0x124 | 0x005d1000 | ds0[5]: M1 0x005d1000 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage we (predictions/we.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-WE RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage f3: row F3, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill", own_gate = "none"

The third read of one fill after a plant (begin_draws "fill"): M1 as LF (E1200) and FF, or
0x01000000 as F (E1187).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row f31-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage f3

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: crumb3 as G2 q and round 44's FF, T, TF and F2 ran it**, byte for
byte (design §3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in
every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage f3 (predictions/f3.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| F3-KEEP | M1 (as LF, E1200, and FF) [infer, H-TRI] (postsa1 = 0x005d1000) | **held** |
| F3-TICK | 0x01000000 (as F, E1187) [infer; H-RACE allows it] (postsa1 = 0x01000000) | failed |
| F3-FILL | 0x02000010 (the fill's 3:4 at K 2) [infer] (postsa1 = 0x02000010) | failed |
| F3-OTHER | any other word (postsa1 = @notany:0x005d1000,0x01000000,0x02000010) | printed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session). The RULE line `Q128-N3J-F3 RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and
sa13, the kernel's "events seen" lines, the KC lines (the begin and end command counts) and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (FF2-FILL, T2-34, TF2-FILL, TT-LAST, TT-FIRST,
TT-KEEP, F3-TICK, F3-FILL) read cannot tell; the -KEEP and -SAME outcomes still stand. B failing (a
fault with no pass planned): stop the session for the user.

## Stage f2b: row F2B, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill", own_gate = "none"

A second unplanted read, right after F3 whose end draws (fill, triangle) are the default: F2's
0x05400000 again (E1196), or a tick's, or a fill's 3:4. N1's only unplanted read.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row f2b1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage f2b

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: crumb3 as G2 q and round 44's FF, T, TF and F2 ran it**, byte for
byte (design §3); V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in
every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim (T2) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | movs tim (T3) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage f2b (predictions/f2b.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| F2b-SAME | 0x05400000 (F2's read, E1196) [HW once; H-KC, H-TRI] (postsa1 = 0x05400000) | **held** |
| F2b-TICK | 0x01000000 [infer; H-RACE] (postsa1 = 0x01000000) | failed |
| F2b-FILL | 0x02000010 [infer] (postsa1 = 0x02000010) | failed |
| F2b-OTHER | any other word (postsa1 = @notany:0x05400000,0x01000000,0x02000010) | printed |
| F2b-QUIET | snap9 BIF_FAULT 0 (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session). The RULE line `Q128-N3J-F2B RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and
sa13, the kernel's "events seen" lines, the KC lines (the begin and end command counts) and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE. DR or DK failed. F3's end health not exact, or F3's end command count
not 10 (the end triangle's K is then not 5): F2b-SAME and its siblings cannot tell.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wa1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- ff21-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6
  0x07003547 0x07000305 0x07003fe7 0xaf000000
- wb1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- t21-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- wc1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- tf21-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6
  0x07003547 0x07000305 0x07003fe7 0xaf000000
- wd1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- tt1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- we1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- f31-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- f2b1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6
  0x07003547 0x07000305 0x07003fe7 0xaf000000

## Risk

The plants: W's, run many times [HW, E1184-E1199]: quiet, no pass after the emit. The reads: FF's,
T's, TF's, F's and F2's job 1 (E1187-E1196), with no kick and no gate: quiet in every run [HW]. New:
two triangles in one health call (`tri,tri`), both stock client draws; a triangle after a triangle
runs in every recovery's retry already [HW].

## Stops

J1 not DONE in any row: CANNOT TELL, stop the session. W-FAULT, or B failing in a read row: stop for
the user. Any fault other than the ones the land stage names: stop for the user. A runner stop (a
job not done, any fault outside the gate) ends the session after reset and strict health (rc 4, both
draws); the lead scores it by hand (`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A
failed reset (rc 13 or 5) is the user's ordinary reboot to the default entry, end of the day. A
stage with its own begin draws runs only right after its plant in the same attempt (the driver
refuses --from or --only there: status 46).

## Deviations from the design (builder)

- K9 (round 45): the scorer reads the command count from the kernel log (kit/kitscore.py `kc`): DK
  is a control that can fail, row-scoped, and prints KC and HKC lines; DK failing makes only the
  outcomes that name a K cannot tell (the design's §3.2 list), DR failing is the RULE's CANNOT TELL
  as before.
- The design's "-SA outcomes" for DK in the land rows are read as LF2-SA1, LF2-SA0 and LF2-SA2;
  LT-SA1 and LT-TRIPLE; LFF-SA1, LFF-SA0 and LFF-V0. The plant's cannot-tell set for the land rows
  is the attribute-1 outcome and the page outcomes, SERVE included (as round 44's LF did).
- The X-OTHER-like outcomes (FF2-OTHER, T2-OTHER, TF2-OTHER, TT-OTHER, F3-OTHER, F2b-OTHER,
  LF2-AOTHER, LT-AOTHER) are frozen with the prediction `printed`. Each reads "any other word" as:
  any post sa1 that is none of the words the stage's other outcomes name (FF2-OTHER also excludes a
  tick's), and for the land rows any sa0, sa2 that the stage's A outcomes do not match (LF2-AOTHER:
  not sa0 2 with a timer sa2; LT-AOTHER: neither LC's triple nor V0, V2).
- FF2-TICK reads "bits 23:0 = 0, top byte 1-4"; the scorer's word `tick` is that test.
- The H-SA0 page (LF2-PAGE, LT-PAGE, LFF-PAGE) is read from job 1's post sa0 and sa1: page 0 when
  post sa0 < 0x1000, post sa1's page when post sa0 = V0, and unread (cannot tell) for any other sa0,
  which the design's §0.4 rule does not cover.
- DR is read from the kernel log (exactly one `health begin try 1 LIST` between `row begin` and
  `owntask-arm`, LIST the stage's declared list) and the kept draw outputs (each exact). A begin
  health at try 2 or more is DK failed too (K9).
- The plant a read or land stage reads is the one right before it in the same attempt (wa-ff2,
  wb-t2, wc-tf2, wd-tt, we-f3; wg-lf2, wh-lt, wi-lff; test_score pins the pairing); F2b has none and
  reads F3's end health and end command count from the f3 directory beside it (a missing directory
  reads cannot tell).
- The job controls are printed CONTROL lines that can fail but do not decide the RULE (as round 42's
  J2): J2 (job 2 done, M6, run id 2) fails by design when the early stop holds.
- W-FAULT reads snap9's BIF_FAULT and the disarm record's (owntask.reset.json health bif_fault);
  unread (cannot tell) when snap9 is 0 and the disarm record is missing. The hooks stop the session
  on snap9's in a plant or read stage; a fault at the disarm fails the end's register health (rc
  16).
- The scorer's test attempts are round 44's kept stages (N1 wa and ff, N3 lf, pinned at
  resgx545-data ebfeaa775) as the tokens edit them, the kernel log's `ccb_sent` lines rewritten to
  the declared lists' counts.
- No frozen prediction was altered. Doubts about the design are in the lead's report.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses bit 10's douta landing, so the
replay is `refused` with that reason (design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage with its own begin draws), or `bash closing29/r45-n3j-logs/runone.sh
N1 wa ff2 wb t2 wc tf2 wd tt we f3 f2b` (stage, run, score, health draw); after a stop: `python3
score/score.py wa out/ATT/wa`, `python3 score/score.py ff2 out/ATT/ff2`, `python3 score/score.py wb
out/ATT/wb`, `python3 score/score.py t2 out/ATT/t2`, `python3 score/score.py wc out/ATT/wc`,
`python3 score/score.py tf2 out/ATT/tf2`, `python3 score/score.py wd out/ATT/wd`, `python3
score/score.py tt out/ATT/tt`, `python3 score/score.py we out/ATT/we`, `python3 score/score.py f3
out/ATT/f3`, `python3 score/score.py f2b out/ATT/f2b`.
