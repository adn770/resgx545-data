# r44-n3i-n1

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. No build and no boot: the laptop runs the r42-kernel module
(srcversion 079DD0D13F231EEAC52FE0F).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 ce01a0c4deb7 (branch r44-n3i on
main 9076992b, not merged: K8, the draw lists of begin_draws and end_draws) and resgx545-data
b3df8fc21aff, laptop prefix `r44i1`, HostKeyAlias `cedar`. Question Q128 (N3i): what the client
draws write into attribute 1, and land's early stop with a planted sa1. Design:
`closing29/n3i/design.md` (§3 the rows, §6 order and time, §8 the user's decisions A-E, all (a),
2026-11-23). Built offline, frozen, not staged, not run.

**When:** first of round 44 (decision E (a)): four plants and the reads after fill-tri, fill-fill,
tri and tri-fill, then F2 with no plant; all quiet, no planned stop; no build, no boot. The round's
order: N1, then N2, then N3 (decision E (a)); the whole session in one `run`.

**Module.** fork r42-kernel ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, loaded = installed
since round 42: mark, crumb3 and land are its images, sbc43 its form; no fork change.

## Stage wa: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws, or the register health
when it declares none) and its arm.

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
again. **rounds 42-43's bytes: mark as G1 m and round 43's W ran it**, byte for byte (design §3); V0
and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
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
`Q128-N3I-WA RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage ft: row FT, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill,tri", own_gate = "none"

The control (design §3.2): crumb3 after the default draws fill,tri written out (begin_draws
"fill,tri", the kit's retrying health path), one quiet job. Does the plant-based read give the seven
earlier rows' word 0x04400000 (or 0x04000010)?

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row ft1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage ft

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-43's bytes: crumb3 as G2 q and round 43's F ran it**, byte for byte (design §3);
V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage ft (predictions/ft.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| FT-SAME | 0x04400000 or 0x04000010 [HW: the seven rows of §0.1] (postsa1 = @any:0x04400000,0x04000010) | **held** |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| X-KEEP | post sa1 = M1: the draws did not write it [HW for a fill, E1187; infer for a triangle, the seven FT rows] (postsa1 = 0x005d1000) | failed |
| X-OTHER | any word the stage's outcomes do not name (postsa1 = @notany:0x005d1000,0x04400000,0x04000010) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3I-FT RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. FT-SAME failing (N1's FT): comparisons with
the seven earlier rows read cannot tell; FF, T and TF still compare among themselves (one frame). B
failing (a fault with no pass planned): stop the session for the user.

## Stage wb: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws, or the register health
when it declares none) and its arm.

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
again. **rounds 42-43's bytes: mark as G1 m and round 43's W ran it**, byte for byte (design §3); V0
and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
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
`Q128-N3I-WB RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage ff: row FF, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill,fill", own_gate = "none"

crumb3 after two fills (K8: begin_draws "fill,fill", run once, each draw kept under its own name):
an event count (0x02, H-N), a per-kind constant (0x01, H-LAST) or the kick count (H-K).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row ff1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage ff

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-43's bytes: crumb3 as G2 q and round 43's F ran it**, byte for byte (design §3);
V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage ff (predictions/ff.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| FF-N | 0x02000000 [infer, H-N; H-ACC alike] (postsa1 = 0x02000000) | **held** |
| FF-LAST | 0x01000000 [infer, H-LAST] (postsa1 = 0x01000000) | failed |
| FF-K | 0x04000010 [infer, H-K] (postsa1 = 0x04000010) | failed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| X-KEEP | post sa1 = M1: the draws did not write it [HW for a fill, E1187; infer for a triangle, the seven FT rows] (postsa1 = 0x005d1000) | failed |
| X-OTHER | any word the stage's outcomes do not name (postsa1 = @notany:0x005d1000,0x02000000,0x01000000,0x04000010) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3I-FF RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. FT-SAME failing (N1's FT): comparisons with
the seven earlier rows read cannot tell; FF, T and TF still compare among themselves (one frame). B
failing (a fault with no pass planned): stop the session for the user.

## Stage wc: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws, or the register health
when it declares none) and its arm.

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
again. **rounds 42-43's bytes: mark as G1 m and round 43's W ran it**, byte for byte (design §3); V0
and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
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
`Q128-N3I-WC RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage t: row T, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri", own_gate = "none"

crumb3 after a triangle alone (begin_draws "tri"): 0x03 (H-N) or 0x04 (H-LAST).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row t1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage t

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-43's bytes: crumb3 as G2 q and round 43's F ran it**, byte for byte (design §3);
V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage t (predictions/t.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| T-N | 0x03400000 or 0x03000010 [infer, H-N; H-ACC alike] (postsa1 = @any:0x03400000,0x03000010) | **held** |
| T-LAST | 0x04400000 or 0x04000010 [infer, H-LAST] (postsa1 = @any:0x04400000,0x04000010) | failed |
| T-K | 0x02400000 or 0x02000010 [infer, H-K] (postsa1 = @any:0x02400000,0x02000010) | failed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| X-KEEP | post sa1 = M1: the draws did not write it [HW for a fill, E1187; infer for a triangle, the seven FT rows] (postsa1 = 0x005d1000) | failed |
| X-OTHER | any word the stage's outcomes do not name (postsa1 = @notany:0x005d1000,0x03400000,0x03000010,0x04400000,0x04000010,0x02400000,0x02000010) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3I-T RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. FT-SAME failing (N1's FT): comparisons with
the seven earlier rows read cannot tell; FF, T and TF still compare among themselves (one frame). B
failing (a fault with no pass planned): stop the session for the user.

## Stage wd: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws, or the register health
when it declares none) and its arm.

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
again. **rounds 42-43's bytes: mark as G1 m and round 43's W ran it**, byte for byte (design §3); V0
and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
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
`Q128-N3I-WD RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage tf: row TF, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri,fill", own_gate = "none"

crumb3 after a triangle then a fill (K8: begin_draws "tri,fill"): the low bits and the count 4
(H-N), a per-kind constant (H-LAST), the kick count (H-K) or the triangle's word surviving the fill
(TF-TRI).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row tf1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage tf

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-43's bytes: crumb3 as G2 q and round 43's F ran it**, byte for byte (design §3);
V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage tf (predictions/tf.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| TF-N | 0x04000000 [infer, H-N; H-ACC alike] (postsa1 = 0x04000000) | **held** |
| TF-LAST | 0x01000000 [infer, H-LAST] (postsa1 = 0x01000000) | failed |
| TF-K | 0x08000010 [infer, H-K] (postsa1 = 0x08000010) | failed |
| TF-TRI | 0x04400000 or 0x04000010 (the triangle's word survives the fill) [infer] (postsa1 = @any:0x04400000,0x04000010) | failed |
| X-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| X-KEEP | post sa1 = M1: the draws did not write it [HW for a fill, E1187; infer for a triangle, the seven FT rows] (postsa1 = 0x005d1000) | failed |
| X-OTHER | any word the stage's outcomes do not name (postsa1 = @notany:0x005d1000,0x04000000,0x01000000,0x08000010,0x04400000,0x04000010) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3I-TF RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. FT-SAME failing (N1's FT): comparisons with
the seven earlier rows read cannot tell; FF, T and TF still compare among themselves (one frame). B
failing (a fault with no pass planned): stop the session for the user.

## Stage f2: row F2, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill", own_gate = "none"

crumb3 after a fill with no plant (begin_draws "fill"), right after TF whose end draws (fill,
triangle) are the default: does a fill write 0x01000000 whatever the word before (H-N, H-LAST), or
add to it (H-ACC)? N1's only unplanted read.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row f21-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage f2

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-43's bytes: crumb3 as G2 q and round 43's F ran it**, byte for byte (design §3);
V0 and V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-43
snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage f2 (predictions/f2.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| F2-N | 0x01000000 (F again, whatever the word before) [HW, E1187; infer] (postsa1 = 0x01000000) | **held** |
| F2-ACC | 0x09000000 [infer, H-ACC] (postsa1 = 0x09000000) | failed |
| F2-K | 0x02000010 [infer, H-K] (postsa1 = 0x02000010) | failed |
| F2-PRIOR | 0x04400000 or 0x04000010 (the fill did not write it) [HW against: E1187] (postsa1 = @any:0x04400000,0x04000010) | failed |
| F2-OTHER | any other (postsa1 = @notany:0x01000000,0x09000000,0x02000010,0x04400000,0x04000010) | printed |
| F2-QUIET | snap9 BIF_FAULT 0 (snap9:0x0c08 = 0x0) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3I-F2 RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE. DR failed. TF's end health not ok at try 1 (the word before F2's fill
is then not the one assumed): F2-ACC and F2-PRIOR cannot tell; F2-N still stands.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wa1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- ft1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- wb1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- ff1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- wc1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- t1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- wd1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- tf1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000
- f21-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000

## Risk

The plants: W's, run twice [HW, E1184, E1186]: quiet, no pass after the emit. The reads: B11's, W's
and F's job 1 (E1172, E1184, E1187), with no kick and no gate: quiet in every run [HW]. New:
`fill,fill` and `tri,fill` as begin draws, which are stock client draws; a triangle right after a
reset already runs in every recovery path [HW]. The stray `[sa14 + 0xb0]` append stays as in X
[infer].

## Stops

J1 not DONE in any row: CANNOT TELL, stop the session. W-FAULT, or B failing in a read row: stop for
the user. Any fault other than the ones LM and LF name: stop for the user. A runner stop (a job not
done, any fault outside the gate) ends the session after reset and strict health (rc 4, both draws);
the lead scores it by hand (`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A failed
reset (rc 13 or 5) is the user's ordinary reboot to the default entry, end of the day. A stage with
its own begin draws runs only right after its plant in the same attempt (the driver refuses --from
or --only there: status 46).

## Deviations from the design (builder)

- K8 (round 44): `begin_draws` as a list, run once through `health_ok`, each draw kept under its own
  name (`begin.fill1.1`, `begin.fill1.2`, ...); the default `fill,tri` keeps today's retrying path
  and names. The design's wording "FT written out" is the default string, so FT's DR reads
  `begin.fill1` and `begin.health1` (no index).
- X-OTHER (the reads) and F2-OTHER, LM-OTHER, LF-AOTHER are frozen with the prediction `printed`
  (read held or FAILED, never a verdict). The design's "any word no row names" for X-OTHER is read
  as: any post sa1 that is none of the words the stage's outcomes and X-KEEP name.
- DR is read from the kernel log (exactly one `health begin try 1 LIST` between `row begin` and
  `owntask-arm`, LIST the stage's declared list) and the kept draw outputs (each exact; none: the
  register health json ok). It decides the RULE in the read stages, F2 and LF; in LM it is a control
  read and printed (the design's cannot-tell rules for LM do not name it).
- The plant a read stage reads is the one right before it in the same attempt (wa-ft, wb-ff, wc-t,
  wd-tf, wl-lm, wf-lf; test_score pins the pairing); LF's outcomes all read cannot tell when the
  plant failed (the design's cannot-tell list for LF names PLANT without singling out outcomes),
  LM's only LM-KEEP and the LM-EARLY ones.
- F2 reads TF's end health from the tf directory beside it (exactly one `health end` mark,
  `fill,tri`, each kept draw exact); a missing tf directory reads cannot tell.
- LM-OTHER reads job 2 not done with a fault page that is none of post sa1's, page 0's and post
  sa13's; LF-EVT, LF-TICK, LF-ONE and LF-AOTHER read the derived `sa02kind` of job 1's post sa0 and
  sa2.
- The job controls are printed CONTROL lines that can fail but do not decide the RULE (as round 42's
  J2): J2 (job 2 done, M6, run id 2) fails by design when the early stop holds.
- W-FAULT reads snap9's BIF_FAULT and the disarm record's (owntask.reset.json health bif_fault);
  unread (cannot tell) when snap9 is 0 and the disarm record is missing. The hooks stop the session
  on snap9's in a plant or read stage; a fault at the disarm fails the end's register health (rc
  16).
- The scorer's test attempts are round 43's kept stages (N1 w and v, N2 f, pinned at resgx545-data
  b3df8fc21) as the tokens edit them; the read stages' kept draws are f's begin fill and
  strict-health triangle (as kept), the register health v's.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses bit 10's douta landing, so the
replay is `refused` with that reason (design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage with its own begin draws), or `bash closing29/r44-n3i-logs/runone.sh
N1 wa ft wb ff wc t wd tf f2` (stage, run, score, health draw); after a stop: `python3
score/score.py wa out/ATT/wa`, `python3 score/score.py ft out/ATT/ft`, `python3 score/score.py wb
out/ATT/wb`, `python3 score/score.py ff out/ATT/ff`, `python3 score/score.py wc out/ATT/wc`,
`python3 score/score.py t out/ATT/t`, `python3 score/score.py wd out/ATT/wd`, `python3
score/score.py tf out/ATT/tf`, `python3 score/score.py f2 out/ATT/f2`.
