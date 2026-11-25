# r46-n3k-n3

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below, **and the one-shot boot onto the new module first** (the r46-kernel
module, srcversion 10BBF3BFBD51D559106589F, sha256
17676836aaf507de5badd76336916129a87cb6817b94b2fa96a6b8f9841a207f; `boot-test-kernel.sh`,
`test-session.sh 192.168.12.137 6666`, then the gma500 srcversion against the installed one).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 eaee04a42721 (branch r46-n3k on
main 908b7e96, not merged: the landr and landp images, the after-read blobs emitsb_sb043s and
emitsb_sb803s, the fork pin at c5094783eb88 and the kit's `pds=landr|landp`, K10) and resgx545-data
72e07b2d6416, laptop prefix `r46k3`, HostKeyAlias `cedar`. Question Q128 (N3k): which page land's
stop keeps, whether two fills write attribute 1, and B5/B6. Design: `closing29/n3k/design.md` (§2
the rows, §4 the frozen predictions, §10 the user's decisions A=a, B=b, C=a, D=a, E=a, F=b, the B
rows and the run order). Built offline, frozen, not staged, not run.

**When:** after N2: wd plants M1, lf3f runs land after fill-fill-fill and ends in the planned stop.
The round's order (design §10.3): the one-shot boot, B5, B6, N1-N8; the whole session in one `run`.

**Module.** fork r46-kernel c5094783eb88 (r45-kernel plus the landr and landp images), srcversion
10BBF3BFBD51D559106589F, loaded = installed after the one-shot boot: control SV.

## Stage wd: row W, 1 row of 1 job, flagged, on_stop "end", own_gate = "none", end_draws = "none"

Plant M1 in attribute 1 and read it back with no pass after (T3 stops the tick), row W of E1184 byte
for byte. No gate (own_gate none) and no end draws (end_draws none): between this plant's emit and
the next stage's emit run only the disarm reset, the next stage's begin reset (with its begin draws)
and its arm.

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
again. **rounds 42-45's bytes: mark as every W row ran it (E1184-E1232)**; V0 and V2 are the
kernel's own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-45 snap0).

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

### Outcomes of stage wd (predictions/wd.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 0x005d1000 [HW, 24 runs E1184-E1232] (postsa1 = 0x005d1000) | **held** |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 [HW] (postsa13 = 0x005d3000, postpa1 = 0x005d3000) | **held** |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) [HW] (snap9:0x0c08 = 0x0) | **held** |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) (fault1 = yes) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), SV (the stage log's installed and loaded srcversion are
the r46-kernel build's), and, read in each job's own record and never on the row-end page (the H3
slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with
its run id, done; else CANNOT TELL and stop the session). The RULE line `Q128-N3K-WD RULE:` names
the outcomes held; one PREDICTION line per outcome. Printed, never scored: the arm line, each job's
Δtick, K5's words (pre, mid, post), the survey (pre, post sa0-sa31, post pa0-pa15), attributes 3-12,
every fault page against job 1's post sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the
AFTER line, the KC lines and H-KC's word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: stop the session (the read stage needs the plant). W-SA1 failing: the
next stage's attribute-1 outcomes read cannot tell (the scorer reads it in this attempt's plant
stage); the read runs, printed. W-FAULT (snap9 BIF_FAULT not 0 after job 1): the hooks stop the
session (rc 24, on_stop end) for the user. WA is also the build control on the r46-kernel module
(design §10.3): WA failing any outcome stops the round's N rows for the user.

## Stage lf3f: row LF3F, 1 row of 2 jobs, flagged, on_stop "end", begin_draws = "fill,fill,fill"

land after three fills (begin_draws "fill,fill,fill", design §4.5): M1, the second draw's 0x04000010
(H-FL2) or the last's 0x06000010 (H-FLL). Ends in the planned stop.

**The arm.** `slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch). Image land (`asm/fwtask/pds/land.s`, 3 rows, control word
0x01800100).

Row lf3f1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms), no kick (the next tick pass).
Then the page, snap0/snap9 and the record (each job's K5 BIF words); the land read ends in the
runner's planned stop.

### The firmware-page write of stage lf3f

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 16 dwords at #14's buffer address + 0x100, [0x100, 0x140) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 40-45's bytes: land as LF, LF2, LT and LFF ran it (E1200-E1217)**; land has no V0 or
V2 words (its fill flag is 0): its words 4 and 5 are Ma and Mb.

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
| 0x120 | 0x00000000 | ds0[4]: the third row, unused |
| 0x124 | 0x00000000 | ds0[5] |
| 0x128 | 0x00000000 | ds1[4] |
| 0x12c | 0x00000000 | ds1[5] |
| 0x130 | 0x07040606 | movs douta, ds0[2], ds1[1], ds0[2], ds0[2] (Ma to attribute 24) |
| 0x134 | 0x07042ca6 | movs douta, ds0[3], ds1[2], ds0[3], ds0[3] (Mb to attribute 26) |
| 0x138 | 0x07000305 | movs doutu, ds0[0], ds0[1], ds1[0], ds0[0] (start entry 1 of the blob) |
| 0x13c | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, as every after-read
row since round 41). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word
`emitpds.tasks.taske #0, r2, r3, r4, #0xc43` (sideband 0xc43).

### Outcomes of stage lf3f (predictions/lf3f.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| LF3F-KEEP | sa1 = M1 [infer, H-TRI] (postsa1 = 0x005d1000) | **held** |
| LF3F-SECOND | sa1 = 0x04000010 (the 2nd draw's 3:4, as LFF and X) [held under H-FL2] (postsa1 = 0x04000010) | failed |
| LF3F-LAST | sa1 = 0x06000010 (the 3rd fill's 3:4 at K 6) [held under H-FLL] (postsa1 = 0x06000010) | failed |
| LF3F-FIRST | sa1 = 0x02000010 (postsa1 = 0x02000010) | failed |
| LF3F-OTHER | any other sa1 (postsa1 = @notany:0x005d1000,0x04000010,0x06000010,0x02000010) | printed |
| LF3F-PAGE0 | job 2 not done; page 0 [infer: every fill leaves sa0 below a page] (j2 = notdone, j2fault = cid15 page 0x00000000) | **held** |
| LF3F-SERVE | job 2 done (j2 = done) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR (the declared begin draws ran at try 1, each exact),
DK (K9: the begin command count is 2 + 2 x fills + 6 x tris, no retry), PLANT (W-SA1 of the plant
right before it in the attempt), SV (the stage log's installed and loaded srcversion are the
r46-kernel build's), and, read in each job's own record and never on the row-end page (the H3 slip,
E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its
run id, done; else CANNOT TELL and stop the session), J2 (job 2 done, slot 6 = M6, run id 2;
printed). The RULE line `Q128-N3K-LF3F RULE:` names the outcomes held; one PREDICTION line per
outcome. Printed, never scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the
survey (pre, post sa0-sa31, post pa0-pa15), attributes 3-12, every fault page against job 1's post
sa0, sa1, sa2 and sa13, the kernel's "events seen" lines, the AFTER line, the KC lines and H-KC's
word of each entry of the declared list (HKC).

**Cannot tell.** J1 not DONE: CANNOT TELL, stop the session. PLANT failed: the attribute-1 outcomes
(-KEEP, -FILL*, -SECOND, -LAST, -FIRST) read cannot tell. DR failed (a draw missing, failed or
retried): every outcome cannot tell. DK failed (the begin command count is not 2 + 2 x fills): the
outcomes that name a K read cannot tell. SV: the stage log's installed and loaded srcversion are not
10BBF3BFBD51D559106589F: cannot tell (the kit's preflight refuses it first).

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- wd1-a (mark, 21 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x005d3000 0x005d1000 0x00000d00 0x00000100 0x07001fe7 0x07040606 0x07042ca6 0x07084406
  0x07084ea6 0x07003547 0x07000305 0x07003fe7 0xaf000000
- lf3f1-a (land, 16 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00001800 0x5a5a3a18
  0x5a5a3a1a 0x00001a00 0x00000000 0x00000000 0x00000000 0x00000000 0x00000000 0x07040606 0x07042ca6
  0x07000305 0xaf000000

## Risk

The plant: W's [HW]. The land read: the runner's stop (rc 4), the kit's reset and strict health
recovered every land stop so far (LC, LC2, LV, V, LM, LF, LF2, LT, LFF, Q) [HW]. It ends in the
stop, so it is last in its session.

## Stops

J1 not DONE in an N row: CANNOT TELL, stop the session. W-FAULT, or a fault in a quiet read (ZFF2):
stop for the user. WA failing any outcome: stop the round's N rows for the user. SV failing: the
session does not run. Any fault at a page no outcome names in a quiet stage: stop. A B row reading
NEVER or a fault: stop the B rows for the user. A runner stop (a job not done, any fault outside the
gate) ends the session after reset and strict health (rc 4, both draws); the lead scores it by hand
(`python3 score/score.py STAGE out/ATT/STAGE`, or runone.sh). A failed reset (rc 13 or 5) is the
user's ordinary reboot to the default entry. A stage with its own begin draws runs only right after
its plant in the same attempt (the driver refuses --from or --only there: status 46).

## Deviations from the design (builder)

- Every session runs on the r46-kernel module (decision F (b)), so the build control moves from WF
  to WA, the first plant of the round's run order on the new module (design §10.3).
- K9 (round 45): DK is a control that can fail, row-scoped, and prints KC and HKC lines; it is
  scored in ZFF2, LFF2, LFF3 and LF3F, printed in the page rows (Q2, R, P, R2, P2) and the B rows
  (no draws of their own; the B rows keep the kit's default fill,tri).
- ZFF2's -KEEP and -FILL2 are each one reading of three words (sa1, sa0, sa2), the scorer's
  `zffkind`; -OTHER is any other triple, frozen `printed`. ZFF2-FAULT (a fault in the quiet read) is
  the design's stop condition as an outcome, predicted failed.
- The -OTHER outcomes of LFF2, LFF3, LF3F (any sa1 not named), Q2, R and P (a fault at a page not
  named, the scorer's @faultnotin) are frozen `printed`. P-MAPPED is the scorer's `@notin` (job 2
  done, or a fault at any other page, none included).
- PLANT is a control of every read and land stage (W-SA1 of the plant right before it); it scopes
  the attribute-1 outcomes of ZFF2, LFF2, LFF3 and LF3F and is printed in the page rows, whose
  images write sa0 and sa1 themselves.
- The B rows' outcomes (§10.1) are new predictions on today's kit, not round 40's; round 40's H-DM
  and H-ALL lines are not carried (decision B (b)).
- The scorer's test attempts are round 45's kept stages (N4 wi and lff, N5 zff, N6 q, pinned at
  resgx545-data 72e07b2d6) and round 41's H1 c (the B rows' base) as the tokens edit them, the
  kernel log's `ccb_sent` lines rewritten to the declared lists' counts; the design's fixtures (LFF
  E1217, LF2 E1213, Q E1233 and Q doctored at 0x005d200f) are replayed whole.
- No frozen prediction was altered. Doubts about the design are in the builder's report.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses an own task's douta landing, so
the replay is `refused` with that reason.

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`
(never --from or --only a stage with its own begin draws), or `bash closing29/r46-n3k-logs/runone.sh
N3 wd lf3f` (srcversion check, stage, run, score, health draw); after a stop: `python3
score/score.py wd out/ATT/wd`, `python3 score/score.py lf3f out/ATT/lf3f`.
