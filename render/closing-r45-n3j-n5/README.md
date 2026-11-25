# r45-n3j-n5

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below, **and the one-shot boot onto the new module first** (the r45-kernel
module, srcversion EC553F41FD8324BB6BF1764; the laptop's installed module is the r42-kernel one
until then: `boot-test-kernel.sh`, `test-session.sh`, then the gma500 srcversion against the
installed one, as round 42 did).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 cf20aa8703f7 (branch r45-n3j-z on
r45-n3j and main 1c8dc10e, not merged: K9, the crumbz and landq images, the fork pin at b1089172b2e7
and the kit's `pds=crumbz|landq`) and resgx545-data ebfeaa7754e4, laptop prefix `r45j5`,
HostKeyAlias `cedar`. Question Q128 (N3j): which client event lands in attribute 1, what crumbz and
landq read, and which unmapped word land's stop faults at. Design: `closing29/n3j/design.md` (§9 the
rebuild rows, §9.6 order and time; §8 the user's decisions A=a, B=a, C=a, D=b, E=c, F=a). Built
offline, frozen, not staged, not run.

**When:** after the user's OK and the one-shot boot onto the r45-kernel module (decision F (a)): the
W build control wj, then crumbz after no draw, tri, fill-tri, fill, fill-fill, tri-fill and tri-tri,
each right after its plant wk-wp; quiet, no planned stop. The round's order: N1-N4 (done), the
one-shot boot, then N5, then N6 (decision F (a)); the whole session in one `run`.

**Module.** fork r45-kernel b1089172b2e7 (r42-kernel plus the crumbz and landq images), srcversion
EC553F41FD8324BB6BF1764, loaded = installed after the one-shot boot: control SV. mark, crumbz and
landq are its images, sbc43 its form.

## Stage wj: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wj1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wj

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wj (predictions/wj.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WJ RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage zn: row ZN, 1 row of 1 job, flagged, on_stop "end", begin_draws = "none", own_gate = "none"

crumbz after no draw (begin_draws "none"; LM's and V's history, E1198, E1185): crumbz writes no
attribute, so post sa0, sa1, sa2 are what the bank held before the emit: V0, M1, V2 (control ZN:
when it fails every later Z row's sa0 and sa2 outcomes read cannot tell).

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row zn1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage zn

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage zn (predictions/zn.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZN-SAME | post sa0 = V0, sa1 = M1, sa2 = V2 [HW for land, landv: E1198, E1185] (zn = SAME) | **held** |
| ZN-OTHER | any other: control ZN fails (§9.2) (zn = OTHER) | failed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), and, read in each job's own record and
never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after
0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The
RULE line `Q128-N3J-ZN RULE:` names the outcomes held; one PREDICTION line per outcome. Printed,
never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes
3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's
"events seen" lines, the KC lines (the begin and end command counts) and H-KC's word of each entry
of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Stage wk: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wk1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wk

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wk (predictions/wk.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WK RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage zt: row ZT, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri", own_gate = "none"

crumbz after a triangle (begin_draws "tri"; the triangle's 3:22 at K 2): a triangle's triple (LT's
question without the stop): sa1 0x02400000, sa0 0 and sa2 a timer word (H-KC's triple), or sa0 V0
and sa2 V2 (attribute 1 alone).

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row zt1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage zt

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage zt (predictions/zt.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZT-SA1 | sa1 = 0x02400000 [HW T E1193; H-TRI, H-FIRST] (postsa1 = 0x02400000) | **held** |
| ZT-TRIPLE | sa0 = 0, sa2 timer [infer, H-KC's triple, LC's] (sa02kind = @in:TRIPLE) | **held** |
| ZT-ONE | sa0 = V0, sa2 = V2 (a triangle writes attribute 1 alone) [infer] (sa02kind = @in:ONE) | failed |
| ZT-AOTHER | any other sa0, sa2 (sa02kind = @notin:TRIPLE,ONE) | printed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), ZN (the stage zn of the attempt read
ZN-SAME; scopes the sa0 and sa2 outcomes), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-ZT RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Stage wl: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wl1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wl

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wl (predictions/wl.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WL RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage zft: row ZFT, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill,tri", own_gate = "none"

crumbz after a fill then a triangle (begin_draws "fill,tri"; the triangle's 3:22 at K 4): fill,tri's
triple (LC's, E1176, E1178) on this module.

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row zft1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage zft

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage zft (predictions/zft.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZFT-SA1 | sa1 = 0x04400000 (or X's 0x04000010) [HW, eight reads, E1189 and n3i §0.1] (postsa1 = @any:0x04400000,0x04000010) | **held** |
| ZFT-TRIPLE | sa0 = 0, sa2 timer [HW under land twice: LC, LC2, E1176, E1178] (sa02kind = @in:TRIPLE) | **held** |
| ZFT-ONE | sa0 = V0, sa2 = V2 [infer] (sa02kind = @in:ONE) | failed |
| ZFT-AOTHER | any other sa0, sa2 (sa02kind = @notin:TRIPLE,ONE) | printed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), ZN (the stage zn of the attempt read
ZN-SAME; scopes the sa0 and sa2 outcomes), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-ZFT RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never
scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as
post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events
seen" lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the
declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Stage wm: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wm1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wm

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wm (predictions/wm.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WM RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage zf: row ZF, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill", own_gate = "none"

crumbz after one fill (begin_draws "fill"): does the fill or land's tick give LF's sa0 2 and sa2
(R-DRAW), or does crumbz read the plant's V0 and V2 (R-TICK)?

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row zf1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage zf

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage zf (predictions/zf.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZF-SA1 | sa1 = M1 [HW LF E1200; H-TRI] (postsa1 = 0x005d1000) | **held** |
| ZF-TICK1 | sa1 = 0x01000000 (F, E1187) [infer; H-RACE allows it] (postsa1 = 0x01000000) | failed |
| ZF-DRAW | sa0 = 0x00000002, sa2 timer (LF's shape) [infer, R-DRAW] (sa02kind = @in:LF) | **held** |
| ZF-PLANT | sa0 = V0, sa2 = V2 [infer; held under R-TICK] (sa02kind = @in:ONE) | failed |
| ZF-AOTHER | any other sa0, sa2 (sa02kind = @notin:LF,ONE) | printed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), ZN (the stage zn of the attempt read
ZN-SAME; scopes the sa0 and sa2 outcomes), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-ZF RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Stage wn: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wn1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wn

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wn (predictions/wn.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WN RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage zff: row ZFF, 1 row of 1 job, flagged, on_stop "end", begin_draws = "fill,fill", own_gate = "none"

crumbz after two fills (begin_draws "fill,fill"): fill,fill's sa0 and sa2 (LFF's question without
the stop), R-DRAW against R-TICK again.

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row zff1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage zff

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage zff (predictions/zff.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZFF-SA1 | sa1 = M1 [HW FF E1191; H-TRI] (postsa1 = 0x005d1000) | **held** |
| ZFF-DRAW | sa0 = 0x00000002, sa2 timer [infer, R-DRAW; §3.6's LFF-SA0] (sa02kind = @in:LF) | **held** |
| ZFF-PLANT | sa0 = V0, sa2 = V2 [infer; held under R-TICK; LFF-V0's shape] (sa02kind = @in:ONE) | failed |
| ZFF-AOTHER | any other sa0, sa2 (sa02kind = @notin:LF,ONE) | printed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), ZN (the stage zn of the attempt read
ZN-SAME; scopes the sa0 and sa2 outcomes), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-ZFF RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never
scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as
post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events
seen" lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the
declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Stage wo: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wo1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wo

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wo (predictions/wo.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WO RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage ztf: row ZTF, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri,fill", own_gate = "none"

crumbz after a triangle then a fill (begin_draws "tri,fill"; the triangle's 3:22 at K 2): does the
fill rewrite sa0 and sa2 and keep sa1?

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row ztf1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage ztf

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage ztf (predictions/ztf.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZTF-SA1 | sa1 = 0x02400000 [HW TF E1195; H-TRI, H-FIRST] (postsa1 = 0x02400000) | **held** |
| ZTF-DRAW | sa0 = 2, sa2 timer (the fill rewrites sa0 and sa2 only) [infer, R-DRAW] (sa02kind = @in:LF) | **held** |
| ZTF-TRIPLE | sa0 = 0, sa2 timer (the triangle's triple kept) [infer; held under R-TICK] (sa02kind = @in:TRIPLE) | failed |
| ZTF-AOTHER | any other sa0, sa2 (sa02kind = @notin:LF,TRIPLE) | printed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), ZN (the stage zn of the attempt read
ZN-SAME; scopes the sa0 and sa2 outcomes), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-ZTF RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never
scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as
post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events
seen" lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the
declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Stage wp: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wp1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wp

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-44's bytes: mark as G1 m and round 44's W rows ran it, and the rebuild touches no
other image (WJ is the build control)**; V0 and V2 are the kernel's own TA3DCtl words at the arm
(0x32004000, 0x32002000 in every round 42-44 snap0).

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

### Outcomes of stage wp (predictions/wp.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r45-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3J-WP RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user. WJ is also the build control (design §9.3): WJ failing any outcome stops
N5 for the user (the rebuild changed the arm path or the mark bytes), no Z row runs.

## Stage ztt: row ZTT, 1 row of 1 job, flagged, on_stop "end", begin_draws = "tri,tri", own_gate = "none"

crumbz after two triangles (begin_draws "tri,tri"): the second triangle's 3:22 at K 8 (H-TRI:
0x08400000) or 2 (H-FIRST: 0x02400000), and the triple beside it.

**The arm.** `slots=0x1 entry=0 pds=crumbz pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumbz (`asm/fwtask/pds/crumbz.s`, 3 rows, control
word 0x01800100).

Row ztt1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the end draws (fill,
triangle).

### The firmware-page write of stage ztt

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 17 dwords at #14's buffer address + 0x100, [0x100, 0x144) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **NEW bytes (design §9.0): crumb3's 12 data dwords unchanged and crumb3's program without its
two douta; the fork's sgx_own_pds.h at b1089172b2e7 carries them**; V0 and V2 are the kernel's own
TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-44 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | V0 (the kernel's, unread: crumbz has no douta) |
| 0x114 | V2 | V2 (the kernel's, unread: crumbz has no douta) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | ds0[4]: 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07003547 | movs tim (T2) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0x07003fe7 | movs tim (T3) |
| 0x140 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage ztt (predictions/ztt.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| ZTT-LAST | sa1 = 0x08400000 (or 0x08000010) [infer, H-TRI] (postsa1 = @any:0x08400000,0x08000010) | **held** |
| ZTT-FIRST | sa1 = 0x02400000 (or 0x02000010) [infer; held under H-FIRST] (postsa1 = @any:0x02400000,0x02000010) | failed |
| ZTT-TRIPLE | sa0 = 0, sa2 timer [infer, H-KC's triple] (sa02kind = @in:TRIPLE) | **held** |
| ZTT-ONE | sa0 = V0, sa2 = V2 [infer] (sa02kind = @in:ONE) | failed |
| ZTT-AOTHER | any other sa0, sa2 (sa02kind = @notin:TRIPLE,ONE) | printed |
| Z-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) (snap9:0x0c08 = 0x0) | **held** |
| Z-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), SV (the stage log's
installed and loaded srcversion are the r45-kernel build's), ZN (the stage zn of the attempt read
ZN-SAME; scopes the sa0 and sa2 outcomes), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session). The RULE line
`Q128-N3J-ZTT RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never
scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as
post sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events
seen" lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the
declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the row's outcomes read
cannot tell; the row runs, printed. DR failed (a draw missing, failed or retried: a retry adds a
reset and draws, so it changes the count): cannot tell. DK failed (the begin command count is not 2
+ 2 x fills + 6 x tris): the outcomes that name a K (ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
ZTT-FIRST) read cannot tell. ZN failed (the stage zn of the attempt did not read ZN-SAME): the sa0
and sa2 outcomes of every other Z row cannot tell; the sa1 outcomes still stand. B failing (a fault
with no pass planned, Z-FAULT): the row's read stands, stop the session for the user. SV (design
§9.2): the stage log's installed and loaded srcversion are not EC553F41FD8324BB6BF1764: cannot tell
(the kit's preflight refuses it first).

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wj1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- zn1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305 0x07003fe7
  0xaf000000
- wk1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- zt1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305 0x07003fe7
  0xaf000000
- wl1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- zft1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305
  0x07003fe7 0xaf000000
- wm1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- zf1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305 0x07003fe7
  0xaf000000
- wn1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- zff1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305
  0x07003fe7 0xaf000000
- wo1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- ztf1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305
  0x07003fe7 0xaf000000
- wp1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- ztt1-a (crumbz, 17 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2
  0x00000200 0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07003547 0x07000305
  0x07003fe7 0xaf000000

## Risk

The plants: W's, run many times [HW, E1184-E1199] (WJ on the new module is the build control). The Z
rows: crumb3's (E1189-E1196): quiet, no kick, no gate [HW]; new is crumbz itself (no douta): after
the emit sa0 may hold 0 or 2 (unmapped) with the tick stopped by T1-T3, and before the emit the same
banks were quiet under crumb3 (FT, T, TF) [HW]; LC's stop needed land's running tick [infer]. Quiet,
no planned stop.

## Stops

J1 not DONE in any row: CANNOT TELL, stop the session. W-FAULT, or B failing in a Z row: stop for
the user; WJ failing any outcome: stop N5 for the user, no Z row runs. SV failing: N5 and N6 do not
run. Any fault other than the ones the land stage names: stop for the user. A runner stop (a job not
done, any fault outside the gate) ends the session after reset and strict health (rc 4, both draws);
the lead scores it by hand (`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A failed
reset (rc 13 or 5) is the user's ordinary reboot to the default entry, end of the day. A stage with
its own begin draws runs only right after its plant in the same attempt (the driver refuses --from
or --only there: status 46).

## Deviations from the design (builder)

- K9 (round 45): the scorer reads the command count from the kernel log (kit/kitscore.py `kc`): DK
  is a control that can fail, row-scoped, and prints KC and HKC lines; DK failing makes only the
  outcomes that name a K cannot tell (design §9.4: ZT-SA1, ZFT-SA1, ZF-TICK1, ZTF-SA1, ZTT-LAST,
  ZTT-FIRST), DR failing is the RULE's CANNOT TELL.
- SV (design §9.2) is read from the attempt's stage log (STAGE.log beside the kept directory: the
  preflight's `## installed module` and `## loaded module` lines): both must be
  EC553F41FD8324BB6BF1764; a missing log reads cannot tell, and SV decides the RULE with PG, E0, T0,
  J1 and DR. runone.sh checks the loaded srcversion first (exit 7).
- ZN (design §9.2, session-scoped) is read from the stage zn of the same attempt (its kept directory
  beside KEPT_DIR, or in ROOTS): ZN-SAME there (post sa0 V0, sa1 M1, sa2 V2). A missing zn reads
  cannot tell, never a pass. It makes the sa0 and sa2 outcomes of ZT, ZFT, ZF, ZFF, ZTF and ZTT
  cannot tell (the -SA1, -LAST, -FIRST and -TICK1 outcomes stand); ZN itself is a Z row with its
  plant wj.
- The Z rows' outcome kinds: TRIPLE is sa0 = 0 with a timer sa2, LF (the draw's) sa0 = 2 with a
  timer sa2, ONE sa0 = V0 with sa2 = V2; an -AOTHER outcome is any sa0, sa2 the row's other outcomes
  do not name (ZT, ZFT, ZTT: neither TRIPLE nor ONE; ZF, ZFF: neither LF nor ONE; ZTF: neither LF
  nor TRIPLE, so ONE reads -AOTHER there). It is frozen with the prediction `printed`.
- Q-OTHER reads "a fault at any other page" as a fault (not none) at neither 0x005d2000 nor
  0x005d1000; Q-LOW held reads cannot tell on the PREDICTION line (design §9.5: 'lowest page'
  against 'sa0 mapped').
- DR is read from the kernel log (exactly one `health begin try 1 LIST` between `row begin` and
  `owntask-arm`, LIST the stage's declared list; none: the register health) and the kept draw
  outputs (each exact). A begin health at try 2 or more is DK failed too (K9). Q prints DR and DK
  (no draws, design §9.5), it does not score them.
- The plant a Z stage reads is the one right before it in the same attempt (wj-zn, wk-zt, wl-zft,
  wm-zf, wn-zff, wo-ztf, wp-ztt; test_score pins the pairing); q has none.
- The job controls are printed CONTROL lines that can fail but do not decide the RULE (as round 42's
  J2): J2 (job 2 done, M6, run id 2) fails by design when the early stop holds.
- W-FAULT reads snap9's BIF_FAULT and the disarm record's (owntask.reset.json health bif_fault);
  unread (cannot tell) when snap9 is 0 and the disarm record is missing. The hooks stop the session
  on snap9's in a plant or Z stage; a fault at the disarm fails the end's register health (rc 16).
  Z-FAULT is the same reading in a Z row.
- The scorer's test attempts are round 44's kept stages (N1 wa and ff, N2 lm, pinned at
  resgx545-data ebfeaa775) as the tokens edit them (ff for every Z row, lm for q), the kernel log's
  `ccb_sent` lines rewritten to the declared lists' counts; no kept data exists for crumbz or landq.
- N6 has a plant stage wq before q (design §9.5 says q is N6's only stage, no plant): the kit's K7
  refuses `begin_draws` on a session's first stage (session.py lint), and row Q's begin draws are
  `none`. wq is row W as WJ (mark, M1 planted, no end draws) and q follows it as LM followed WL in
  round 44; Q's outcomes do not read wq (landq writes Q0 and M1 itself), the scorer prints no PLANT
  line for q. The alternative, a kit change letting a first stage declare `none`, is the lead's to
  decide.
- No frozen prediction was altered. Doubts about the design are in the builder's report.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses bit 10's douta landing, so the
replay is `refused` with that reason (design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage with its own begin draws), or `bash
closing29/r45-n3j-z-logs/runone.sh N5 wj zn wk zt wl zft wm zf wn zff wo ztf wp ztt` (stage, run,
score, health draw); after a stop: `python3 score/score.py wj out/ATT/wj`, `python3 score/score.py
zn out/ATT/zn`, `python3 score/score.py wk out/ATT/wk`, `python3 score/score.py zt out/ATT/zt`,
`python3 score/score.py wl out/ATT/wl`, `python3 score/score.py zft out/ATT/zft`, `python3
score/score.py wm out/ATT/wm`, `python3 score/score.py zf out/ATT/zf`, `python3 score/score.py wn
out/ATT/wn`, `python3 score/score.py zff out/ATT/zff`, `python3 score/score.py wo out/ATT/wo`,
`python3 score/score.py ztf out/ATT/ztf`, `python3 score/score.py wp out/ATT/wp`, `python3
score/score.py ztt out/ATT/ztt`.
