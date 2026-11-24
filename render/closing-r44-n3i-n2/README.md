# r44-n3i-n2

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. No build and no boot: the laptop runs the r42-kernel module
(srcversion 079DD0D13F231EEAC52FE0F).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 ce01a0c4deb7 (branch r44-n3i on
main 9076992b, not merged: K8, the draw lists of begin_draws and end_draws) and resgx545-data
b3df8fc21aff, laptop prefix `r44i2`, HostKeyAlias `cedar`. Question Q128 (N3i): what the client
draws write into attribute 1, and land's early stop with a planted sa1. Design:
`closing29/n3i/design.md` (§3 the rows, §6 order and time, §8 the user's decisions A-E, all (a),
2026-11-23). Built offline, frozen, not staged, not run.

**When:** after N1 (decision E (a)): wl plants M1, lm runs land on that bank with no draws and ends
in the runner's planned stop (row LM); no build, no boot. The round's order: N1, then N2, then N3
(decision E (a)); the whole session in one `run`.

**Module.** fork r42-kernel ec6511d5de87, srcversion 079DD0D13F231EEAC52FE0F, loaded = installed
since round 42: mark, crumb3 and land are its images, sbc43 its form; no fork change.

## Stage wl: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick). No gate (own_gate
none) and no end draws (end_draws none): between this plant's emit and the next stage's emit run
only the disarm reset, the next stage's begin reset (with its begin draws, or the register health
when it declares none) and its arm.

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

### Outcomes of stage wl (predictions/wl.tsv, frozen; score/score.py)

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
`Q128-N3I-WL RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never scored:
the arm line, each job's Δtick, K5's words (pre, mid, post), the survey, attributes 3-12 as post
sa3-sa12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen"
lines.

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
read stage's outcomes read cannot tell (the scorer reads it in this attempt's plant stage); the read
runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage lm: row LM, 1 row of 2 jobs, flagged, on_stop "end", begin_draws = "none"

land on W's bank, no draws (begin_draws none: the register health stands in): does the early stop
read sa0 then sa1 (H-SA0: the stop at M1's page) or stop at page 0 whatever the bank holds (H-IMG)?
Jobs: the emit, then command 6 on the next tick pass. Ends in the runner's planned stop (job 2 not
done: rc 4, reset, strict health with both draws).

**The arm.** `slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image land (`asm/fwtask/pds/land.s`, 3 rows, control word
0x01800100).

Row lm1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms), no kick (the next tick pass).
Then the page, snap0/snap9 and the record (each job's K5 BIF words), after an ok end the gate (the
fill then the triangle), the disarm and the end draws.

### The firmware-page write of stage lm

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 16 dwords at #14's buffer address + 0x100, [0x100, 0x140) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 40-41's bytes: land as rows L, H3 and LC2 ran it (round 42 did not run land; its
first run on the r42 module)**, byte for byte (design §3); land has no V0 or V2 words (its fill flag
is 0): its words 4 and 5 are Ma and Mb.

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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every round 42-43
row). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word `emitpds.tasks.taske #0,
r2, r3, r4, #0xc43` (sideband 0xc43, bit 10).

### Outcomes of stage lm (predictions/lm.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| LM-V0 | job 1's post sa0 = V0 and sa2 = V2 (kept from WL) [infer, as E1185] (postsa0 = @V0, postsa2 = @V2) | **held** |
| LM-KEEP | post sa1 = M1 [HW, E1185] (postsa1 = 0x005d1000) | **held** |
| LM-EARLY1 | job 2 not done; K5 BIF_FAULT CID 15 at post sa1's page (M1) [infer] (j2 = notdone, j2fault = @post1) | **held** |
| LM-EARLY0 | the same at page 0 [infer; held under H-IMG] (j2 = notdone, j2fault = cid15 page 0x00000000) | failed |
| LM-EARLY13 | the same at post sa13's page (M13) [HW against: E1185] (j2 = notdone, j2fault = @post13) | failed |
| LM-SERVE | job 2 done [HW against: E1176, E1178, E1183, E1185] (j2 = done) | failed |
| LM-OTHER | any other fault page (j2 = notdone, j2fault = @other) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact,
no other draw between the begin reset and the arm), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, done; else CANNOT TELL and stop the session), J2 (job 2 done,
slot 6 = M6, run id 2; printed). The RULE line `Q128-N3I-LM RULE:` names the outcomes held; one
PREDICTION line per outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre,
mid, post), the survey, attributes 3-12 as post sa3-sa12, every fault page against job 1's post sa0,
sa1, sa2 and sa13, the kernel's "events seen" lines.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop. PLANT failed: LM-KEEP and the LM-EARLY outcomes
read cannot tell for the row. LM-V0 failed with post sa0 below 0x1000: page 0 is then sa0's page
under both readings, so LM-EARLY0 cannot split H-SA0 from H-IMG (CANNOT TELL for the row; the survey
says what rewrote attribute 0 with no draws). LM-V0 failed with another sa0: printed, and the page
is read against post sa0, sa1, sa2 and sa13.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wl1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- lm1-a (land, 16 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00001800 0x5a5a3a18
  0x5a5a3a1a 0x00001a00 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x07040606 0x07042ca6
  0x07000305 0xaf000000

## Risk

Stage wl: W's [HW]. Stage lm: V's and LV's (E1183, E1185): the EDM stops after the emit's pass; the
runner's stop (rc 4), then the kit's reset and strict health with both draws recovered it each time
[HW]. The bank equals V's under LM-V0. It ends in the runner's stop, the planned end, so it is last
in N2.

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
N2 wl lm` (stage, run, score, health draw); after a stop: `python3 score/score.py wl out/ATT/wl`,
`python3 score/score.py lm out/ATT/lm`.
