# r42-n3g-g2

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready). It needs the r42-kernel
module, built on cachix, installed and booted once by the lead with the user's OK first.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 c0e2dc367496 (branch r42-n3g, not
on main: the words sb402 and sb400, the blob emitsb_sb402s, the images mark and landv, the kit's arm
grammar for them, K5's per-job BIF words, the fork pin at r42-kernel) and resgx545-data
5e9c84b22ace, laptop prefix `r42g2`, HostKeyAlias `cedar`. Question Q128 (N3g): where sa13's page
comes from under sideband bit 10, bit 10 with bits 1:0 = 2, and `land` with V0/V2. Design:
`closing29/n3g/design.md` (§3 the rows, §6 risks and order, §8 the user's decisions A-F, all (a),
2026-11-21). Built offline, frozen with a placeholder srcversion, not staged, not run.

**When:** after G1 (decision C (a)): stage s (row C again, after M's resets), then stage q (sb402);
s failing as a control stops the session. The round's order: G1 (C then M), G2 (S then Q), G3 (LV).

**Module.** fork r42-kernel ec6511d5de87 (`drm/gma500: let own_arm take sb402, sb400 and the mark
and landv images`; r42-red the same tests with stubs). Its KUnit suite on the Mac shim plus one
suite on the three after-read blobs armed with every row's arm line, 48 of 48
(`closing29/r42-n3g-logs/shim-r42.log`); r42-red 38 of 48 (`shim-r42-red.log`); the extra suite
fails when a blob's form is wrong (`shim-r42-neg.log`). srcversion is the placeholder
`UNBUILT-r42-kernel-ec6511d5de87` until the boot.

**Before staging** (the lead): build the module on cachix (`closing29/kernel39c/deliver-cachix.sh
send|start|fetch r42-kernel r42-red`), install and boot it once with the user's OK, check srcversion
loaded = installed, then set `srcversion` in session.toml (or rerun `stamp.py G2 SRCV` from
`closing29/r42-n3g-logs/sessgen`), `python3 kit/session.py freeze .` and `bash tests/run_all.sh`.

## Stage s: row S, 1 row of 2 jobs, flagged, on_stop "end"

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14`; blob `emitsb14s` (`emitsb14d` with
the cmd 6 branch), emit word `emitpds.tasks.taske #0, r2, r3, r4, #0x843` (sideband 0x843). Image
crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control word 0x01800100).

Row s1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 (dwords 224-255 filled with
0xdeadc0de and read as result slots 40-47, ticks, 200 ms) on a GETMISCINFO kick (`"kick":
"miscinfo"`). Then the page, snap0/snap9, the record (each job's K5 BIF words before and after it),
and after an ok end the gate (the fill then the triangle; the tools' whole outputs and the
devcoredumps kept), the disarm.

### The firmware-page write of stage s

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again:

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 41 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 41 snap0) |
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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb14s`'s entry 1, at its base's index: the
cmd 6 branch sits after the base's last line). The emit's s0 is 0x01800100, s1 the address >> 4, s2
0. Row C's bytes again (E1173): what S reads is attribute 13 after M's resets.

### Outcomes of stage s (predictions/s.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| S-KEEP | job 1's post pa1 = M13, the other odd pa as in nine kept rows (§0.1) (postpa1 = 0x005d3000, postpa3 = 0x01555620, postpa5 = 0x00000000, postpa7 = 0x03c3cdac, postpa9 = 0xdc531a54, postpa11 = 0x5d50716f, postpa13 = 0x82e151b5, postpa15 = 0x11b5d77a) | **held** |
| S-BACK | job 1's post pa1 = 0x00043000 (a writer we do not run restores it) (postpa1 = 0x00043000) | failed |
| S-OTHER | another word in pa1 (postpa1 = @notof:0x005d3000,0x00043000) | printed |
| C-SAME | job 2 done; after sa0-31 = job 1's pre (E1173) (j2 = done, after2 = SAME) | **held** |
| C-DIFF | after differs from pre (j2 = done, after2 = DIFF) | failed |
| C-NOKICK | job 2 not done 200 ms after its kick (j2 = notdone) | failed |
| C-GATE | the gate's fill and triangle exact (E1173) (gate1 = exact, gate2 = exact) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 after the
row; a fault is read by the outcomes that name it), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder), J2 (job
2 done, slot 6 = M6 and run id 2). The after-reads are each job's own record's slots 40-47. The RULE
line `Q128-N3G-S RULE:` names the outcomes held; one PREDICTION line per outcome says predicted,
read and held or FAILED. Printed, never scored: the arm line, each job's Δtick, kick reply and K5's
BIF words, the survey (pre, post, each after-read and where they differ), the gate's tools, the
devcoredumps, every fault page against job 1's post words.

**This stage is a control.** The hooks stop it (rc 24) when the after-read is not the pre survey or
sa0-sa3 moved (C-DIFF); a stop (C-NOKICK) or a failed gate (rc 16) ends the session. Its disarm
reset ends the stage; the next stage arms.

## Stage q: row Q, 1 row of 2 jobs, flagged, on_stop "end", on_gate_fail "score"

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sb402`; blob `emitsb_sb402s`
(`emitsb_sb402` with the cmd 6 branch), emit word `emitpds.tasks.taske #0, r2, r3, r4, #0x402`
(sideband 0x402). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control word 0x01800100).

Row q1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 (dwords 224-255 filled with
0xdeadc0de and read as result slots 40-47, ticks, 200 ms) on a GETMISCINFO kick (`"kick":
"miscinfo"`). Then the page, snap0/snap9, the record (each job's K5 BIF words before and after it),
and after an ok end the gate (the fill then the triangle; the tools' whole outputs and the
devcoredumps kept), the disarm.

### The firmware-page write of stage q

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again:

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 41 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 41 snap0) |
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

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sb402s`'s entry 1, at its base's index:
the cmd 6 branch sits after the base's last line). The emit's s0 is 0x01800100, s1 the address >> 4,
s2 0. crumb3's bytes, as every DONE row since round 38 [HW, E1154, E1162-E1175]. **What is new is
the emit word** (0x402: bit 10 with bits 1:0 = 2, never run), not the page.

### Outcomes of stage q (predictions/q.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| Q-REBASE | job 2's after = job 1's post in all 32, post != pre (j2 = done, after2 = REBASE) | **held** |
| Q-REP | post sa4 = sa8 = sa12 = V0, sa6 = sa10 = sa14 = V2 (E1168, E1175) (postsa4 = @V0, postsa8 = @V0, postsa12 = @V0, postsa6 = @V2, postsa10 = @V2, postsa14 = @V2) | **held** |
| Q-FILL | the gate's fill faults, CID 15, at the page of job 1's post sa13 (gate1page = @post13) | **held** |
| Q-NONE | after = pre and the gate exact (bit 10 acts only with bits 1:0 = 3) (j2 = done, after2 = NONE, gate1 = exact) | failed |
| Q-OTHER | any other after (printed with indices) (j2 = done, after2 = OTHER) | printed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 after the
row; a fault is read by the outcomes that name it), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder), J2 (job
2 done, slot 6 = M6 and run id 2). The after-reads are each job's own record's slots 40-47. The RULE
line `Q128-N3G-Q RULE:` names the outcomes held; one PREDICTION line per outcome says predicted,
read and held or FAILED. Printed, never scored: the arm line, each job's Δtick, kick reply and K5's
BIF words, the survey (pre, post, each after-read and where they differ), the gate's tools, the
devcoredumps, every fault page against job 1's post words.

The gate's failure is this stage's planned end (rc 16, scored: on_gate_fail "score"); its hooks
print an sa0-sa3 change or an after-read that is not the pre survey to the runner log and never stop
on it.

## Risk

Stage s: row C's risk, none new. Stage q: Y's risk (E1175) with bits 1:0 = 2 (B8's 0x002 ran,
E1168): an emit word never run, its gate's planned fill fault (design §6).

## Stops

If G1's m read M-MISS, S is printed only (its S-* outcomes say nothing). s failing as a control
(C-DIFF, C-NOKICK, its gate) stops the session. J1 not DONE: CANNOT TELL, stop the ladder; a fault
at #14's page + 0x10 is round 40's FAULT outcome (E1171), its own reading. A runner stop (a job not
done, any fault outside the gate) ends the session after reset and health (rc 4); the lead scores it
by hand (`python3 score/score.py STAGE out/ATT/STAGE`). A failed reset (rc 13 or 5) is the user's
ordinary reboot to the default entry, end of the day. Any fault outside the gate other than the ones
M, Q and LV name: stop for the user.

## Deviations from the design (builder)

- J2 (job 2's record: done, slot 6 = M6 and run id 2) is printed as a control and can fail, but the
  RULE does not need it: a job 2 not done is the NOKICK or EARLY reading (design §3's tables), and
  the after-read outcomes then read cannot tell.
- B (BIF_FAULT 0 in snap9) fails when a fault came before the gate, as in X and Y (E1174, E1175); no
  outcome of M, S or Q names it, so the RULE adds the FAULT note as X's did (the rule frozen in X
  and LC2); only LV-EARLY0 and LV-EARLY name it.
- The scorer's test attempts are round 41's kept stages (H1 c and x, H2 y, LC2 lc, pinned at
  resgx545-data 5e9c84b22ace) as the tokens edit them, where round 41's were round 40's with
  fabricated jobs.
- srcversion is the placeholder `UNBUILT-r42-kernel-ec6511d5de87` until the lead sets the booted
  module's and refreezes (the brief).
- S-OTHER and Q-OTHER, which the design prints and does not predict, are frozen with the prediction
  `printed`: the outcome is read (held or FAILED) and its PREDICTION line says printed, never a
  verdict.
- "If M read M-MISS, S is printed only" is the lead's reading of G1's RULE line; the scorer of G2
  cannot see G1's result.
- Q-REP reads V0 and V2 from the row's snap0 (TA3DCtl dwords 0 and 2), cannot tell without them.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses sb402 (bit 10 with bits 1:0 = 2
is unmeasured) and bit 10's douta landing (596cc74b), so the replay is `refused` with that reason
(design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop (after the boot and the srcversion): `python3 kit/session.py stage
.`, `python3 kit/session.py run .`, or `closing29/r42-n3g-logs/runone.sh G2 s q` (stage, run, score,
health draw); after a stop: `python3 score/score.py s out/ATT/s`, `python3 score/score.py q
out/ATT/q`.
