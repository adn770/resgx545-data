# r43-n3h-n1

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. No build and no boot: the laptop runs the r42-kernel module
(srcversion 079DD0D13F231EEAC52FE0F).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 1f49335c4523 (branch r43-n3h on
main 4993566e, not merged: K6, the kick-only job and K5's mid read; K7, the stage keys begin_draws,
end_draws and own_gate) and resgx545-data fadfa30ad550, laptop prefix `r43h1`, HostKeyAlias `cedar`.
Question Q128 (N3h): who writes attribute 1, what the tick pass reads and which pass faults. Design:
`closing29/n3h/design.md` (§3 the rows, §6 order and time, §8 the user's decisions A-E, all (a),
2026-11-23). Built offline, frozen, not staged, not run.

**When:** first of round 43 (decision E (a)): stage w plants M1, stage v reads it with no draws
between and ends in the runner's planned stop (V-EARLY1); no build, no boot. The round's order: N1
(w then v), then N2 (w2 then f).

**Module.** fork r42-kernel ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, loaded = installed
since round 42: mark, landv and crumb3 are its images, sbc43 its form; no fork change.

## Stage w: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between W's emit and V's emit run only W's disarm reset,
V's begin reset (with the register health, no draw) and V's arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row w1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words; a kicked job's mid), no gate (own_gate none), the disarm and the
register health (end_draws none).

### The firmware-page write of stage w

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **Round 42's bytes**: mark as G1 m ran it, byte for byte (design §3); V0 and V2 are the
kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42 snap0).

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as G1 m and G3 lv).
The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0, r2,
r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage w (predictions/w.tsv, frozen; score/score.py)

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
`Q128-N3H-W RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick and kick reply, K5's words (pre, mid, post), the survey, attributes
3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1 and sa13, the kernel's "events
seen" lines.

**Cannot tell.** J1 not DONE: stop N1 (V needs the plant). W-SA1 failing: V's V-KEEP, V-EVT and V-V1
read cannot tell (the scorer reads it in this attempt's w); V runs for Q2 only. W-FAULT (snap9
BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24, on_stop end) for the user.

## Stage v: row V, 1 row of 2 jobs, flagged, on_stop "end", begin_draws = "none"

landv with the tick running and no begin draws (begin_draws none): does attribute 1 keep M1 with no
client event since W (Q1), and does the tick pass stop at sa1's page (Q2). Ends in the runner's
planned stop (job 2 not done: rc 4, reset, strict health with both draws).

**The arm.** `slots=0x1 entry=0 pds=landv pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image landv (`asm/fwtask/pds/landv.s`, 3 rows, control word
0x01800100).

Row v1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms), no kick (the next tick pass).
Then the page, snap0/snap9 and the record (each job's K5 BIF words; a kicked job's mid), after an ok
end the gate (the fill then the triangle), the disarm and the end draws.

### The firmware-page write of stage v

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 18 dwords at #14's buffer address + 0x100, [0x100, 0x148) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **Round 42's bytes**: landv as G3 lv ran it, byte for byte (design §3); V0 and V2 are the
kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42 snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0) |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 42 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 42 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2) |
| 0x11c | 0x00001800 | ds1[3]: douta control 0x1800 (attribute 24) |
| 0x120 | 0x5a5a3a18 | ds0[4]: Ma 0x5a5a3a18 |
| 0x124 | 0x5a5a3a1a | ds0[5]: Mb 0x5a5a3a1a |
| 0x128 | 0x00001a00 | ds1[4]: douta control 0x1a00 (attribute 26) |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x134 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x138 | 0x07082606 | movs douta, ds0[4], ds1[3] (Ma to attribute 24) |
| 0x13c | 0x07084ca6 | movs douta, ds0[5], ds1[4] (Mb to attribute 26) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as G1 m and G3 lv).
The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0, r2,
r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage v (predictions/v.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| V-KEEP | job 1's post sa1 = M1 (H-EVT: no client event since W) (sa1kind = M1) | **held** |
| V-EVT | post sa1 an event word: bits 31:24 in 1-15, bits 23:0 = 0x000010 or 0x400000 (sa1kind = @in:EVT4,EVT22) | failed |
| V-V1 | post sa1 = 0x32005000 (V1: the boot's #11 writes attribute 1, H-BOOT) (sa1kind = V1) | failed |
| V-OTHER | any other post sa1 (H-EMIT) (sa1kind = OTHER) | printed |
| V-V | post sa0 = V0 and sa2 = V2; post sa13 = M13 (postsa0 = @V0, postsa2 = @V2, postsa13 = 0x005d3000) | **held** |
| V-EARLY1 | job 2 not done; its K5 BIF_FAULT CID 15 at job 1's post sa1 page (j2 = notdone, j2fault = @post1) | **held** |
| V-EARLY13 | the same at the page of post sa13 (M13) (j2 = notdone, j2fault = @post13) | failed |
| V-EARLY0 | the same at page 0 (j2 = notdone, j2fault = cid15 page 0x00000000) | failed |
| V-SERVE | job 2 done (j2 = done) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session), J2 (job 2 done, slot
6 = M6, run id 2; printed). The RULE line `Q128-N3H-V RULE:` names the outcomes held; one PREDICTION
line per outcome. Printed, never scored: the arm line, each job's Δtick and kick reply, K5's words
(pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's
post sa0, sa1 and sa13, the kernel's "events seen" lines.

**Cannot tell.** J1 not DONE: CANNOT TELL. W-SA1 failed: V-KEEP, V-EVT, V-V1 cannot tell. V-EARLY1
with post sa1 = 0x04400000: LV again, Q2 not advanced (a NOTE line). No fault and V-SERVE: printed,
the tick-pass reading of design §0.2 fails.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (round 42's bytes; V0, V2 the kernel's at the arm):

- w1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- v1-a (landv, 18 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x00001800 0x5a5a3a18 0x5a5a3a1a 0x00001a00 0x00000000 0x07040606 0x07042ca6 0x07082606 0x07084ca6
  0x07000305 0xaf000000

## Risk

Stage w: E1177's emit shape (one job, no kick) with mark's bytes (run in G1 m); the gate's planned
fault of M does not happen (no gate). New: the stage ends without draws: the disarm reset's own
checks (alive, rate, miscinfo, register health) and the register health stand in for them, and V's
arm checks again [infer: low]. Stage v: LV's (the highest of round 42) [HW, G3 lv: stopped after one
tick pass, the kit's reset and health recovered it], with sa1 = M1 instead of 0x04400000, both below
0x10000000 where no REV1 heap lies [infer: unmapped]. If M1's page were mapped, the tick pass's
HostCtl store would land there; the reset rebuilds the firmware's buffers.

## Stops

J1 not DONE in any row: CANNOT TELL, stop the session. W-FAULT: stop for the user. Any fault outside
the ones V and F name: stop for the user. A runner stop (a job not done, any fault outside the gate)
ends the session after reset and strict health (rc 4, both draws); the lead scores it by hand
(`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A failed reset (rc 13 or 5) is the
user's ordinary reboot to the default entry, end of the day. A stage without begin draws runs only
right after its planting stage in the same attempt (the driver refuses --from or --only there:
status 46).

## Deviations from the design (builder)

- K7's keys are owntask-stage keys only (the register health is the kit's fwtask_run.py `reghealth`,
  which only an owntask stage calls); the design names own_gate for an owntask stage and leaves the
  draw keys' scope open.
- The guard rule "begin_draws other than the default on a session's first stage unless the stage
  before it ... ended its own draws" is read as: lint refuses a non-default begin_draws on a
  session's first stage, and the driver refuses (status 46) to start an attempt (--from, --only) at
  a stage that declares one, so it runs only right after the stage before it.
- A boundary without draws whose register health is not ok resets, draws both (the recovery) and
  stops the stage (rc 16); a boundary with one draw that fails does the same. The design names only
  the recovery paths.
- A kick-only job that ends done stops the list (the task posted without a command); the design
  names only its not-done end. Lint also refuses a kick-only job with params or slots, or without
  `expect`.
- The job controls are printed CONTROL lines that can fail but do not decide the RULE (as round 42's
  J2): V's J2 (job 2 done, M6, run id 2) fails by design when V-EARLY1 holds; F's J2 is the
  kick-only shape (not done, cmd_after 0, kicked), F's J3 (job 3 done, M6, run id 3) fails by design
  when K-STALL holds.
- W-FAULT reads snap9's BIF_FAULT and the disarm record's (owntask.reset.json health bif_fault);
  unread (cannot tell) when snap9 is 0 and the disarm record is missing. The hooks stop the session
  on snap9's (W-FAULT: stop the session); a fault at the disarm fails the end's register health (rc
  16).
- The attribute-1 outcomes of V and F read W-SA1 in the planting stage of the same attempt (w beside
  v, w2 beside f, else the ROOTS); without it they read cannot tell.
- V-OTHER and F-OTHER are frozen with the prediction `printed` (read held or FAILED, never a
  verdict). V-EVT and F-FILL4 read an event word as bits 31:24 in 1-15 with bits 23:0 = 0x000010
  (EVT4) or 0x400000 (EVT22): round 42's LV word 0x04400000 is EVT22.
- The scorer's test attempts are round 42's kept stages (G1 m, G3 lv, pinned at resgx545-data
  fadfa30ad550) as the tokens edit them; F's kick-only record and stalled job 3 are built from m's
  job 2 record.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses bit 10's douta landing
(596cc74b), so the replay is `refused` with that reason (design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage without begin draws), or `bash closing29/r43-n3h-logs/runone.sh N1 w
v` (stage, run, score, health draw); after a stop: `python3 score/score.py w out/ATT/w`, `python3
score/score.py v out/ATT/v`.
