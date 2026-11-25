# r45-n3j-n2

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. No build and no boot: the laptop runs the r42-kernel module
(srcversion 079DD0D13F231EEAC52FE0F).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 94f9e5010d60 (branch r45-n3j on
main 1c8dc10e, not merged: K9, the command count of the scorer's DK control) and resgx545-data
ebfeaa7754e4, laptop prefix `r45j2`, HostKeyAlias `cedar`. Question Q128 (N3j): which client event
lands in attribute 1, second reads, and what land's page follows. Design: `closing29/n3j/design.md`
(§3 the rows, §6 order and time, §8 the user's decisions A=a, B=a, C=a, D=b, F=a). Built offline,
frozen, not staged, not run.

**When:** after N1 (decision F (a)): wg plants M1, lf2 runs land after one fill again and ends in
the runner's planned stop (row LF2); no build, no boot. The round's order: N1, then N2, then N3,
then N4 (decision F (a), D (b)); the whole session in one `run`.

**Module.** fork r42-kernel ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, loaded = installed
since round 42: mark, crumb3 and land are its images, sbc43 its form; no fork change.

## Stage wg: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row wg1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage wg

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

### Outcomes of stage wg (predictions/wg.tsv, frozen; score/score.py)

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
`Q128-N3J-WG RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines, the KC lines (the begin and end command counts) and H-KC's word of each entry of the declared
list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage lf2: row LF2, 1 row of 2 jobs, flagged, on_stop "end", begin_draws = "fill"

land after one fill (begin_draws "fill"), LF again (E1200): sa0 2, sa1 M1, sa2 a timer word, the
stop at page 0. Jobs: the emit, then command 6 on the next tick pass. Ends in the runner's planned
stop (job 2 not done: rc 4, reset, strict health with both draws).

**The arm.** `slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image land (`asm/fwtask/pds/land.s`, 3 rows, control word
0x01800100).

Row lf21-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms), no kick (the next tick pass).
Then the page, snap0/snap9 and the record (each job's K5 BIF words), after an ok end the gate (the
fill then the triangle), the disarm and the end draws.

### The firmware-page write of stage lf2

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 16 dwords at #14's buffer address + 0x100, [0x100, 0x140) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 40-44's bytes: land as rows L, H3, LC2, LM and LF ran it (E1198, E1200)**, byte for
byte (design §3); land has no V0 or V2 words (its fill flag is 0): its words 4 and 5 are Ma and Mb.

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00001800 | ds1[1]: douta control 0x1800 (attribute 24) |
| 0x110 | 0x5a5a3a18 | ds0[2]: Ma 0x5a5a3a18 |
| 0x114 | 0x5a5a3a1a | ds0[3]: Mb 0x5a5a3a1a |
| 0x118 | 0x00001a00 | ds1[2]: douta control 0x1a00 (attribute 26) |
| 0x11c | 0x00000000 | ds1[3]: 0 |
| 0x120 | 0x00000000 | 0 |
| 0x124 | 0x00000000 | 0 |
| 0x128 | 0x00000000 | 0 |
| 0x12c | 0x00000000 | 0 |
| 0x130 | 0x07040606 | movs douta (Ma to attribute 24) |
| 0x134 | 0x07042ca6 | movs douta (Mb to attribute 26) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-44
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage lf2 (predictions/lf2.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| LF2-SA1 | post sa1 = M1 [HW once, E1200; H-TRI] (postsa1 = 0x005d1000) | **held** |
| LF2-SA0 | post sa0 = 0x00000002 [HW once, E1200] (postsa0 = 0x00000002) | **held** |
| LF2-SA2 | post sa2 top byte 0x01, bits 23:0 < 400000, != 0x061a70 [HW once, E1200] (sa2shape = TIMER) | **held** |
| LF2-TICK | post sa1 = 0x01000000 (F's word) [infer; H-RACE] (postsa1 = 0x01000000) | failed |
| LF2-AOTHER | any other sa0, sa2 (sa02kind = @notin:LF) | printed |
| LF2-PAGE | job 2 not done; K5 BIF_FAULT CID 15 at the H-SA0 rule's page (design §0.4) (j2 = notdone, j2fault = @hsa0) | **held** |
| LF2-EARLY0 | the same at page 0 [HW once; H-SA0 with LF2-SA0, H-HIST] (j2 = notdone, j2fault = cid15 page 0x00000000) | **held** |
| LF2-EARLY1 | the same at post sa1's page (j2 = notdone, j2fault = @post1) | failed |
| LF2-SERVE | job 2 done [HW against: E1176, E1178, E1183, E1185, E1198, E1200] (j2 = done) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), DK (K9: the begin command count, ccb_sent from
the begin load to the arm's load, is 2 + 2 x fills + 6 x tris, no retry), and, read in each job's
own record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run
id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the
session), J2 (job 2 done, slot 6 = M6, run id 2; printed). The RULE line `Q128-N3J-LF2 RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the KC lines (the
begin and end command counts) and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop. PLANT failed: the stage's attribute-1 outcome and the page
outcomes cannot tell. DR failed: cannot tell. DK failed: the -SA outcomes cannot tell.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wg1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- lf21-a (land, 16 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00001800 0x5a5a3a18
  0x5a5a3a1a 0x00001a00 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x07040606 0x07042ca6
  0x07000305 0xaf000000

## Risk

Stage wg: W's [HW]. Stage lf2: LF's (E1200): a stop at page 0 through the EDM's list, recovered
every time by the runner's stop (rc 4), the kit's reset and strict health with both draws [HW]. It
ends in the runner's stop, so it is last in N2.

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
N2 wg lf2` (stage, run, score, health draw); after a stop: `python3 score/score.py wg out/ATT/wg`,
`python3 score/score.py lf2 out/ATT/lf2`.
