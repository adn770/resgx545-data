# r46-n3k-b5

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready), for the session and for
its firmware-page writes below, **and the one-shot boot onto the new module first** (the r46-kernel
module, srcversion 10BBF3BFBD51D559106589F, sha256
17676836aaf507de5badd76336916129a87cb6817b94b2fa96a6b8f9841a207f; `boot-test-kernel.sh`,
`test-session.sh 192.168.12.137 6666`, then the gma500 srcversion against the installed one).

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 eaee04a42721 (branch r46-n3k on
main 908b7e96, not merged: the landr and landp images, the after-read blobs emitsb_sb043s and
emitsb_sb803s, the fork pin at c5094783eb88 and the kit's `pds=landr|landp`, K10) and resgx545-data
72e07b2d6416, laptop prefix `r46k5b`, HostKeyAlias `cedar`. Question Q128 (N3k): which page land's
stop keeps, whether two fills write attribute 1, and B5/B6. Design: `closing29/n3k/design.md` (§2
the rows, §4 the frozen predictions, §10 the user's decisions A=a, B=b, C=a, D=a, E=a, F=b, the B
rows and the run order). Built offline, frozen, not staged, not run.

**When:** first after the one-shot boot onto the r46-kernel module and the srcversion check
(decision F (b), design §10.3): quiet expected. The round's order (design §10.3): the one-shot boot,
B5, B6, N1-N8; the whole session in one `run`.

**Module.** fork r46-kernel c5094783eb88 (r45-kernel plus the landr and landp images), srcversion
10BBF3BFBD51D559106589F, loaded = installed after the one-shot boot: control SV.

## Stage b5: row B5, 1 row of 2 jobs, flagged, on_stop "end", on_gate_fail = "score"

crumb3 with sideband 0x043 (design §10.1, decision B (b): rebuilt on today's kit): does it run the
program to DONE (today's rule: bits 1:0 = 3 start it, E1162-E1172), and, new against round 40's B5,
an after-read of the EDM's own sa0-sa31 on a GETMISCINFO kick (job 2, round 41's row C) with K5's
BIF words and K9's command counts, job 1's post sa0-sa31 and pa0-pa15, then the gate (the fill and
the triangle; its failure is the stage's planned end, on_gate_fail score).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sb043`; blob `emitsb_sb043s`
(`emitsb_sb043` with the cmd 6 branch). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control
word 0x01800100).

Row b51-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the emit on the timer pass); job 2: command 6 (dwords 224-255
filled with 0xdeadc0de and read as result slots 40-47, ticks, 200 ms) on a GETMISCINFO kick (round
41's row C, E1173). Then the page, snap0/snap9 and the record (each job's K5 BIF words), after an ok
end the gate (the fill then the triangle; its failure the planned end), the disarm and the end
draws.

### The firmware-page write of stage b5

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again. **rounds 38-45's bytes: crumb3 as every B, C and FF row ran it**; V0 and V2 are the kernel's
own TA3DCtl words at the arm (0x32004000, 0x32002000 in every round 42-45 snap0).

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
| 0x120 | 0x00000000 | ds0[4]: the third row, unused |
| 0x124 | 0x00000000 | ds0[5] |
| 0x128 | 0x00000000 | ds1[4] |
| 0x12c | 0x00000000 | ds1[5] |
| 0x130 | 0x07001fe7 | movs tim, ds1[1], ds1[1], ds1[1], ds1[1] (T1: tim <- 0x000) |
| 0x134 | 0x07040606 | movs douta, ds0[2], ds1[1], ds0[2], ds0[2] (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta, ds0[3], ds1[2], ds0[3], ds0[3] (V2 to attribute 2) |
| 0x13c | 0x07003547 | movs tim, ds1[2], ds1[2], ds1[2], ds1[2] (T2: tim <- 0x200) |
| 0x140 | 0x07000305 | movs doutu, ds0[0], ds0[1], ds1[0], ds0[0] (start entry 1 of the blob) |
| 0x144 | 0x07003fe7 | movs tim, ds1[3], ds1[3], ds1[3], ds1[3] (T3: tim <- 0x005a3305) |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sb043s`'s entry 1, as every after-read
row since round 41). The emit's s0 is 0x01800100, s1 the address >> 4, s2 0; the emit word
`emitpds.tasks.taske #0, r2, r3, r4, #0x43` (sideband 0x043).

### Outcomes of stage b5 (predictions/b5.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| B5-NEVER | S1 fill, T running: the program never started [HW against: bits 1:0 = 3, E1164, E1162] (start = NEVER) | failed |
| B5-T1 | T 0, S1 fill: stopped at a douta (start = T1) | failed |
| B5-T2 | T 0x200, S1 fill: stopped at the doutu (start = T2) | failed |
| B5-T3 | T 0x005a3305, S1 fill: entry 1 never stored (start = T3) | failed |
| B5-E1 | S1, no M4: entry 1 started, stopped after S1 (start = E1) | failed |
| B5-DONE | S1, M4 with the run id, state 2 [infer: today's rule, bits 1:0 = 3 run the program to done, E1162-E1172] (start = DONE) | **held** |
| B5-RUN | any of T1..DONE [infer, the rule] (start = @in:T1,T2,T3,E1,DONE) | **held** |
| B5-HID | post sa0-sa31 = pre sa0-sa31 [HW for 0x843 and 0x003, E1162, E1164; infer here] (prepost = SAME) | **held** |
| B5-SAME | job 2 done; its after-read = job 1's pre sa0-sa31 [HW for 0x843, C E1173; infer: no bit 10] (j2 = done, after2 = @in:PRE,BOTH) | **held** |
| B5-REBASE | job 2 done; after = job 1's post, post != pre [held with bit 10: X, Y E1174, E1175] (j2 = done, after2 = POST) | failed |
| B5-AOTHER | job 2 done; after neither pre nor post (j2 = done, after2 = OTHER) | printed |
| B5-NOKICK | job 2 not done 200 ms after its kick (j2 = notdone) | failed |
| B5-GATE | the gate's fill and triangle exact [HW for 0x843, C E1173; B1's post E1164] (gate1 = exact, gate2 = exact) | **held** |
| B5-FILL | the gate's fill not exact (a fault, a hang) [held with bit 10: X-FILL, Y-FILL E1174, E1175] (gate1 = @notin:exact) | failed |
| B5-QUIET | snap9 BIF_FAULT 0 after the row (snap9:0x0c08 = 0x0) | **held** |
| B5-LAND4 | V0 at pa0, pa4, pa8, pa12 and V2 at pa2, pa6, pa10, pa14 (as 0x003, E1164) (landing = EVERY4) | printed |
| B5-LANDNONE | no V0 or V2 in pa0-pa15 (as 0x843, E1162) (landing = NONE) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 in snap9; a
fault is read by the outcomes that name it), DR and DK (printed here, not scored), SV (the stage
log's installed and loaded srcversion are the r46-kernel build's), and, read in each job's own
record and never on the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id,
cmd_after 0), J1 (job 1 DONE: X0, S1, M4 with its run id, done; in the B rows the start is the
reading, so J1 does not decide the RULE), J2 (job 2 done, slot 6 = M6, run id 2; printed). The RULE
line `Q128-N3K-B5 RULE:` names the outcomes held; one PREDICTION line per outcome. Printed, never
scored: the arm line, each job's Δtick, K5's words (pre, mid, post), the survey (pre, post sa0-sa31,
post pa0-pa15), attributes 3-12, every fault page against job 1's post sa0, sa1, sa2 and sa13, the
kernel's "events seen" lines, the AFTER line, the KC lines and H-KC's word of each entry of the
declared list (HKC).

**Cannot tell.** PG, E0, T0 or SV failed: CANNOT TELL. The start (NEVER, T1, T2, T3, E1, DONE) is
the row's reading, so J1 does not decide the RULE; a start other than DONE makes the after-read, HID
and landing outcomes cannot tell. DR and DK are printed (the default begin draws).

## Firmware-page bytes per row (the user's OK)

NEEDS THE USER'S OK BEFORE RUNNING. Every row writes PDS #14's page slack at the arm, [0x100, end),
with exactly these dwords (V0, V2 the kernel's at the arm):

- b51-a (crumb3, 19 dwords from 0x100): 0x080401ef 0x00000000 0x00000000 0x00000000 V0 V2 0x00000200
  0x005a3305 0x00000000 0x00000000 0x00000000 0x00000000 0x07001fe7 0x07040606 0x07042ca6 0x07003547
  0x07000305 0x07003fe7 0xaf000000

## Risk

crumb3's job and the after-read kick of round 41's row C (E1173) with the sideband word the only
change; both words are on the module's list since round 40. RUN: the row ends ok and the kit's gate
runs (only bit 10 was read breaking the gate fill, 0xc43 and 0x403, E1174, E1175 [HW]; infer for
these). NEVER: the tick stops, rc 4, the kit's reset (every own-task stop recovered so far). A fault
(bits 1:0 = 1 only so far): stop for the user.

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
B5 b5` (srcversion check, stage, run, score, health draw); after a stop: `python3 score/score.py b5
out/ATT/b5`.
