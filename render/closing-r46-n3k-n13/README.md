# r46-n3k-n13

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below. It runs on the boot round 46's B5, B6 and N1-N4 ran on (the
r46-kernel module, srcversion 10BBF3BFBD51D559106589F, sha256
17676836aaf507de5badd76336916129a87cb6817b94b2fa96a6b8f9841a207f; sa12 = V0 since B6): no rebuild,
no install, no boot. If the laptop rebooted, design §11.8: the one-shot boot with the user's OK, B6
again, then this.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 b4e31c761438 (branch r46-n3k2 on
r46-n3k eaee04a4, not merged: round 46's images, blobs, fork pin and K10, plus K11, the PAD control
`kitscore.kc_pad`) and resgx545-data 72e07b2d6416, laptop prefix `r46k13`, HostKeyAlias `cedar`.
Question Q128 (N3k addendum): after N1-N4 stopped at M1 with sa0 2, which candidate decides the stop
page (C-FILL, C-K, C-E0/C-E0+, C-BOOT, C-MOD). Design: `closing29/n3k/design.md` §11 (§11.3 the
rows, §11.4 the frozen predictions, §11.9 the user's decisions G=a, H=a, I=a, J=a, K=a). Built
offline, frozen, not staged, not run. N5-N8 stay frozen and unrun.

**When:** after N11 (decision I (a)): w13 plants M1, r runs landr with no draws (N5's stages byte
for byte, plus E12 and R-SUM) and ends in the planned stop. The addendum's order (design §11.3): N9,
N10, N11, N13, N14, N15, N16, then N12 (the pad) last; the whole session in one `run`.

**Module.** fork r46-kernel c5094783eb88 (r45-kernel plus the landr and landp images), srcversion
10BBF3BFBD51D559106589F, loaded = installed on round 46's boot: control SV.

## Stage w13: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick), row W of E1184 byte
for byte (design §11.4). No gate (own_gate none) and no end draws (end_draws none): between this
plant's emit and the next stage's emit run only the disarm reset, the next stage's begin reset (with
its begin draws) and its arm.

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word
0x01800100).

Row w131-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass). Then the page, snap0/snap9 and the
record (each job's K5 BIF words), no gate (own_gate none), the disarm and the register health
(end_draws none).

### The firmware-page write of stage w13

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 42-46's bytes: mark as every W row ran it (E1184-E1232, round 46's WA-WE)**; V0 and
V2 are the kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-45
snap0).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | ds0[0]: U0 (the kernel's) |
| 0x104 | 0x00000000 | ds0[1]: U1, no flag |
| 0x108 | 0x00000000 | ds1[0]: U2 |
| 0x10c | 0x00000000 | ds1[1]: douta control, attribute 0; T1's value |
| 0x110 | V0 | ds0[2]: V0 (the kernel's) |
| 0x114 | V2 | ds0[3]: V2 (the kernel's) |
| 0x118 | 0x00000200 | ds1[2]: douta control, attribute 2; T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3's value |
| 0x120 | 0x005d3000 | ds0[4]: M13, the marker to attribute 13 |
| 0x124 | 0x005d1000 | ds0[5]: M1, the marker to attribute 1 |
| 0x128 | 0x00000d00 | ds1[4]: douta control, attribute 13 |
| 0x12c | 0x00000100 | ds1[5]: douta control, attribute 1 |
| 0x130 | 0x07001fe7 | movs tim, ds1[1], ds1[1], ds1[1], ds1[1] (T1: tim <- 0x000) |
| 0x134 | 0x07040606 | movs douta, ds0[2], ds1[1], ds0[2], ds0[2] (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta, ds0[3], ds1[2], ds0[3], ds0[3] (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4], ds0[4], ds0[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5], ds0[5], ds0[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim, ds1[2], ds1[2], ds1[2], ds1[2] (T2: tim <- 0x200) |
| 0x148 | 0x07000305 | movs doutu, ds0[0], ds0[1], ds1[0], ds0[0] (start entry 1 of the blob) |
| 0x14c | 0x07003fe7 | movs tim, ds1[3], ds1[3], ds1[3], ds1[3] (T3: tim <- 0x005a3305) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every after-read
row since round 41). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word
`emitpds.tasks.taske #0, r2, r3, r4, #0xc43` (sideband 0xc43).

### Outcomes of stage w13 (predictions/w13.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 [HW, 29 of 29 plants so far] (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 [HW] (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) [HW] (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r46-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3K-W13 RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey (pre, post sa0-sa31, post pa0-pa15), attributes 3-12,
every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the
AFTER line, the KC lines and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
next stage's -SA outcome reads cannot tell (the scorer reads it in this attempt's plant stage); the
read runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the session (rc 24,
on_stop end) for the user.

## Stage r: row R, 1 row of 2 jobs, flagged, on_stop "end", begin_draws = "none"

landr after no draw (design §4.8, §11.4, decision I (a)): N5's stages byte for byte, sa0 0x04400000
over sa1 M1: R-LOW (M1's page) against R-SA0 (sa0's), plus E12 and R-SUM (C-E0+: 0x36404000 = sa0 +
sa12). Ends in the planned stop.

**The arm.** `slots=0x1 entry=0 pds=landr pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image landr (`asm/fwtask/pds/landr.s`, 3 rows, control word
0x01800100).

Row r1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms), no kick (the next tick pass).
Then the page, snap0/snap9 and the record (each job's K5 BIF words); the land read ends in the
runner's planned stop.

### The firmware-page write of stage r

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 18 dwords at #14's buffer address + 0x100, [0x100, 0x148) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **round 46's bytes (design §3.2, unrun so far): landq with 0x04400000 for its dword 8 (the
word to attribute 0) and nothing else; the fork's sgx_own_pds.h at c5094783eb88 carries them**;
landr has no V0 or V2 words (its fill flag is 0): its words 4 and 5 are Ma and Mb.

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | ds0[0]: U0 (the kernel's) |
| 0x104 | 0x00000000 | ds0[1]: U1, no flag |
| 0x108 | 0x00000000 | ds1[0]: U2 |
| 0x10c | 0x00001800 | ds1[1]: douta control, attribute 24 |
| 0x110 | 0x5a5a3a18 | ds0[2]: Ma |
| 0x114 | 0x5a5a3a1a | ds0[3]: Mb |
| 0x118 | 0x00001a00 | ds1[2]: douta control, attribute 26 |
| 0x11c | 0x00000000 | ds1[3]: unused (crumb3's T3) |
| 0x120 | 0x04400000 | ds0[4]: L4, the word to attribute 0 |
| 0x124 | 0x005d1000 | ds0[5]: M1, the word to attribute 1 |
| 0x128 | 0x00000000 | ds1[4]: douta control, attribute 0 |
| 0x12c | 0x00000100 | ds1[5]: douta control, attribute 1 |
| 0x130 | 0x07040606 | movs douta, ds0[2], ds1[1], ds0[2], ds0[2] (Ma to attribute 24) |
| 0x134 | 0x07042ca6 | movs douta, ds0[3], ds1[2], ds0[3], ds0[3] (Mb to attribute 26) |
| 0x138 | 0x07084406 | movs douta, ds0[4], ds1[4], ds0[4], ds0[4] (L4 to attribute 0) |
| 0x13c | 0x07084ea6 | movs douta, ds0[5], ds1[5], ds0[5], ds0[5] (M1 to attribute 1) |
| 0x140 | 0x07000305 | movs doutu, ds0[0], ds0[1], ds1[0], ds0[0] (start entry 1 of the blob) |
| 0x144 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every after-read
row since round 41). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word
`emitpds.tasks.taske #0, r2, r3, r4, #0xc43` (sideband 0xc43).

### Outcomes of stage r (predictions/r.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| R-WRITE | job 1 done; sa0 = 0x04400000, sa1 = M1 [infer: Q-WRITE's douta, E1233] (j1 = DONE, postsa0 = 0x04400000, postsa1 = 0x005d1000) | **held** |
| R-LOW | job 2 not done; BIF_FAULT 0x005d100f (list 15, M1's page) [infer, R-LOW] (j2 = notdone, j2fault = cid15 page 0x005d1000) | **held** |
| R-SA0 | the same at 0x0440000f (sa0's page) [held under R-SA0 and R-SA0'] (j2 = notdone, j2fault = cid15 page 0x04400000) | failed |
| R-OTHER | a fault at any other page (sa2's, sa13's, page 0; not the SUM page) (j2fault = @faultnotin:cid15 page 0x005d1000,cid15 page 0x04400000,cid15 page 0x36404000) | printed |
| R-SERVE | job 2 done [HW against: every land row] (j2 = done) | failed |
| R-E12 | post sa12 = V0 (B6's pa0 still there) [HW, 10 reads on this boot]; failed: the row's C-E0 column cannot tell (postsa12 = @V0) | **held** |
| R-SUM | job 2 not done; list 15 at 0x36404000 (sa0 + sa12) [C-E0+, A0 first, unmapped] (j2 = notdone, j2fault = cid15 page 0x36404000) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR and DK (printed here, not scored), PLANT (W-SA1 of
the plant right before it in the attempt), SV (the stage log's installed and loaded srcversion are
the r46-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session), J2 (job 2 done, slot 6 = M6, run id 2;
printed). The RULE line `Q128-N3K-R RULE:` names the outcomes held; one PREDICTION line per outcome.
Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey (pre,
post sa0-sa31, post pa0-pa15), attributes 3-12, every fault page against job 1's post sa0, sa1, sa2
and sa13, the kernel's "events seen" lines, the AFTER line, the KC lines and H-KC's word of each
entry of the declared list (HKC).

**Cannot tell.** J1 not DONE, or the row's -WRITE failed (the image's words not in sa0 and sa1):
every page outcome (SUM included) cannot tell. PLANT, DR and DK are printed, not scored (the image
writes sa0 and sa1 itself; no draws). -E12 not held: the C-E0 column cannot tell (a NOTE). SV as the
other stages.

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- w131-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- r1-a (landr, 18 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00001800 0x5a5a3a18
  0x5a5a3a1a 0x00001a00 0x00000000 0x04400000 0x005d1000 0x00000000 0x00000100 0x07040606 0x07042ca6
  0x07084406 0x07084ea6 0x07000305 0xaf000000

## Risk

The plant: W's [HW, 29 of 29]. The land read: the runner's stop (rc 4), the kit's reset and strict
health recovered every land stop so far (14 of 14) [HW]. A list-15 fault at a new page (LTK's
0x02400000, R's 0x36404000, P's 0x64008000) is the class LV and Q2 recovered from [HW]; a failed
reset (rc 13 or 5) is the user's ordinary reboot (then design §11.8: B6 again before any remaining
row). It ends in the stop, so it is last in its session.

## Stops

Design §11.8. J1 not DONE: CANNOT TELL, stop the session. W-FAULT or a plant's W-SA1 failing: stop.
E12 failing in a row with no reboot before it: stop (pa0 moved under us). LFK and LFK2 disagreeing:
stop the N12-N16 rows for the user (H-RACE). A fault at a page no outcome names in a quiet stage:
stop. SV failing: the session does not run. A runner stop (a job not done, any fault outside the
gate) ends the session after reset and strict health (rc 4, both draws); the lead scores it by hand
(`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A failed reset (rc 13 or 5) is the
user's ordinary reboot to the default entry. A stage with its own begin draws runs only right after
its plant in the same attempt (the driver refuses --from or --only there: status 46).

## Deviations from the design (builder)

- Built from resgx545 r46-n3k2 (r46-n3k plus K11, kitscore.kc_pad), not the design's `r46-n3k-b`
  (the lead's name for the branch).
- No build control in the addendum (WA was round 46's); every plant is row W, a W-FAULT or W-SA1
  failing stops the session (design §11.8).
- DK failing or unread makes -SA, -PAGE0 and -M1 cannot tell (LTK: -SA, -PAGE0, -SA1, -PAST): the
  design says only "the list did not run as one fill"; the builder named the outcomes that read the
  list's effect.
- PLANT scopes -SA (design §11.4) in LFK, LFK2, LFKP and, by the same rule, LTK.
- E12 and PAD do not enter the RULE's premise: their failure is a NOTE naming the column that cannot
  tell (design §11.4), the outcomes are still scored.
- R-OTHER's and P-OTHER's `@faultnotin` lists gain the SUM pages (design §11.4); -SUM joins the
  outcomes that need -WRITE.
- The scorer's fixtures: round 45's LF2 (E1213), LT (E1215), LFF, Q (pinned at resgx545-data
  72e07b2d6) and round 46's n1 lff2 and n4 q2, byte copies of the kept files under tests/fixtures/
  (not yet in resgx545-data), each checked against its kept raw.sha256.
- No frozen prediction was altered. Doubts about the design are in the builder's report.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses an own task's douta landing, so
the replay is `refused` with that reason.

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage with its own begin draws), or `bash closing29/r46-n3k-logs/runone.sh
N13 w13 r` (srcversion check, stage, run, score, health draw); after a stop: `python3 score/score.py
w13 out/ATT/w13`, `python3 score/score.py r out/ATT/r`.
