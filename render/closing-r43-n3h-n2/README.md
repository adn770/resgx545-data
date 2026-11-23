# r43-n3h-n2

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. No build and no boot: the laptop runs the r42-kernel module
(srcversion 079DD0D13F231EEAC52FE0F).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 1f49335c4523 (branch r43-n3h on
main 4993566e, not merged: K6, the kick-only job and K5's mid read; K7, the stage keys begin_draws,
end_draws and own_gate) and resgx545-data fadfa30ad550, laptop prefix `r43h2`, HostKeyAlias `cedar`.
Question Q128 (N3h): who writes attribute 1, what the tick pass reads and which pass faults. Design:
`closing29/n3h/design.md` (§3 the rows, §6 order and time, §8 the user's decisions A-E, all (a),
2026-11-23). Built offline, frozen, not staged, not run.

**When:** after N1 (decision E (a)): stage w2 plants M1 again (N1's recovery draws rewrite it),
stage f after the fill alone, its kick-only job and job 3; ends in K-STALL's stop or the gate's
planned fault. The round's order: N1 (w then v), then N2 (w2 then f).

**Module.** fork r42-kernel ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, loaded = installed
since round 42: mark, landv and crumb3 are its images, sbc43 its form; no fork change.

## Stage w2: row W2, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Row W again, byte for byte (design §3.3): N1's recovery draws (V's stop) overwrite attribute 1 under
H-EVT.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row w21-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words; a kicked job's mid), no gate (own_gate none), the disarm and the
register health (end_draws none).

### The firmware-page write of stage w2

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

### Outcomes of stage w2 (predictions/w2.tsv, frozen; score/score.py)

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
`Q128-N3H-W2 RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick and kick reply, K5's words (pre, mid, post), the survey, attributes
3-12 as post sa3-sa12, every fault page against job 1's post sa0, sa1 and sa13, the kernel's "events
seen" lines.

**Cannot tell.** J1 not DONE: stop N2. W2's W-SA1 failing: F's F-FILL4 and F-KEEP read cannot tell;
F's Q3 jobs still run. W-FAULT: the hooks stop the session for the user.

## Stage f: row F, 1 row of 3 jobs, flagged, on_stop "end", begin_draws = "fill", on_gate_fail = "score"

crumb3 after one stock fill (begin_draws fill): does the fill alone rewrite attribute 1 (Q1), then a
kick-only pass and a command 6 on a kick (Q3). The gate after an ok row stays (fill, tri;
on_gate_fail score); K-STALL ends it in the runner's stop.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row f1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: kick-only (K6: `{"cmd": 0,
"kick": "miscinfo", "expect": "notdone", "timeout_ms": 50}`: no command, a GETMISCINFO kick, its BIF
words pre, mid and post; not done is its expected end); job 3: command 6 as above on a GETMISCINFO
kick (M's job 2). Then the page, snap0/snap9 and the record (each job's K5 BIF words; a kicked job's
mid), after an ok end the gate (the fill then the triangle), the disarm and the end draws.

### The firmware-page write of stage f

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **Round 42's bytes**: crumb3 as G2 q ran it, byte for byte (design §3); V0 and V2 are the
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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as G1 m and G3 lv).
The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0, r2,
r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage f (predictions/f.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| F-FILL4 | job 1's post sa1 an event word, bits 23:0 = 0x000010 (H-EVT, E747) (sa1kind = EVT4) | **held** |
| F-KEEP | post sa1 = M1 (the fill does not write it; the triangle does) (sa1kind = M1) | failed |
| F-OTHER | any other post sa1 (0x400000 in bits 23:0 included) (sa1kind = @notin:EVT4,M1) | printed |
| K-QUIET | job 2's K5 pre BIF_FAULT 0 (j2pre = 0x0) | **held** |
| K-KICK | job 2's K5 mid or post: CID 15 at post sa13's page (M13) (j2kick = @post13) | **held** |
| K-KICKOK | job 2's K5 post BIF_FAULT 0 (j2post = 0x0) | failed |
| K-REPLY | job 2's kick answered (GETMISCINFO line) (j2reply = answered) | **held** |
| K-STALL | job 3 not done, its kick not answered (500 ms) (j3 = notdone, j3reply = error) | **held** |
| K-SERVE | job 3 done, its after-read = job 1's post (j3 = done, after3 = REBASE) | failed |
| F-GATE | if reached, the gate's fill faults, CID 15, at post sa13's page (gate1page = @post13) | **held if reached** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), and, read in each job's own record and never on the
row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1
DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session), J2 (job 2 not done,
cmd_after 0, kicked), J3 (job 3 done, slot 6 = M6, run id 3; printed). The RULE line `Q128-N3H-F
RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm
line, each job's Δtick and kick reply, K5's words (pre, mid, post), the survey, attributes 3-12 as
post sa3-sa12, every fault page against job 1's post sa0, sa1 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop. W2-SA1 failed: F-FILL4, F-KEEP cannot tell. K-KICK
and K-KICKOK both unread (job 2's record missing): Q3 cannot tell (a NOTE line). K-STALL ends the
row in the runner's stop (rc 4): F-GATE "not reached".

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (round 42's bytes; V0, V2 the kernel's at the arm):

- w21-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- f1-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000

## Risk

Stage w2: W's. Stage f: X's, M's and Q's emit (E1174, G1 m, G2 q). New: a kick on an EDM that may be
stalled (job 3): the kernel's GETMISCINFO gives up after 500 ms, the runner stops, the kit's reset
recovers it, as K's stop did (E1155) [HW]. The stray `[sa14 + 0xb0]` append stays as in X [infer].

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
- F's job 2 carries no `ticks` (the design's job spec has none); its Δtick is not printed.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses bit 10's douta landing
(596cc74b), so the replay is `refused` with that reason (design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage without begin draws), or `bash closing29/r43-n3h-logs/runone.sh N2
w2 f` (stage, run, score, health draw); after a stop: `python3 score/score.py w2 out/ATT/w2`,
`python3 score/score.py f out/ATT/f`.
