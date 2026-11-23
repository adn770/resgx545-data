# r42-n3g-g1

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready). It needs the r42-kernel
module, built on cachix, installed and booted once by the lead with the user's OK first.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 c0e2dc367496 (branch r42-n3g, not
on main: the words sb402 and sb400, the blob emitsb_sb402s, the images mark and landv, the kit's arm
grammar for them, K5's per-job BIF words, the fork pin at r42-kernel) and resgx545-data
5e9c84b22ace, laptop prefix `r42g1`, HostKeyAlias `cedar`. Question Q128 (N3g): where sa13's page
comes from under sideband bit 10, bit 10 with bits 1:0 = 2, and `land` with V0/V2. Design:
`closing29/n3g/design.md` (§3 the rows, §6 risks and order, §8 the user's decisions A-F, all (a),
2026-11-21). Built offline, frozen with a placeholder srcversion, not staged, not run.

**When:** first of round 42, right after the one-shot boot of the r42-kernel module (decision C
(a)): stage c, the build control, then stage m; C failing in any way stops the round. The round's
order: G1 (C then M), G2 (S then Q), G3 (LV).

**Module.** fork r42-kernel ec6511d5de87 (`drm/gma500: let own_arm take sb402, sb400 and the mark
and landv images`; r42-red the same tests with stubs). Its KUnit suite on the Mac shim plus one
suite on the three after-read blobs armed with every row's arm line, 48 of 48
(`closing29/r42-n3g-logs/shim-r42.log`); r42-red 38 of 48 (`shim-r42-red.log`); the extra suite
fails when a blob's form is wrong (`shim-r42-neg.log`). srcversion is the placeholder
`UNBUILT-r42-kernel-ec6511d5de87` until the boot.

**Before staging** (the lead): build the module on cachix (`closing29/kernel39c/deliver-cachix.sh
send|start|fetch r42-kernel r42-red`), install and boot it once with the user's OK, check srcversion
loaded = installed, then set `srcversion` in session.toml (or rerun `stamp.py G1 SRCV` from
`closing29/r42-n3g-logs/sessgen`), `python3 kit/session.py freeze .` and `bash tests/run_all.sh`.

## Stage c: row C, 1 row of 2 jobs, flagged, on_stop "end"

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=fw14`; blob `emitsb14s` (`emitsb14d` with
the cmd 6 branch), emit word `emitpds.tasks.taske #0, r2, r3, r4, #0x843` (sideband 0x843). Image
crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control word 0x01800100).

Row c1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 (dwords 224-255 filled with
0xdeadc0de and read as result slots 40-47, ticks, 200 ms) on a GETMISCINFO kick (`"kick":
"miscinfo"`). Then the page, snap0/snap9, the record (each job's K5 BIF words before and after it),
and after an ok end the gate (the fill then the triangle; the tools' whole outputs and the
devcoredumps kept), the disarm.

### The firmware-page write of stage c

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
0. The emit is B0's and H1's C (sideband 0x843): D0 read the EDM's own bank unchanged after it
(E1161, E1173), the control's premise.

### Outcomes of stage c (predictions/c.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| C-SAME | job 2 done; after sa0-31 = job 1's pre (E1173) (j2 = done, after2 = SAME) | **held** |
| C-DIFF | after differs from pre (j2 = done, after2 = DIFF) | failed |
| C-NOKICK | job 2 not done 200 ms after its kick (j2 = notdone) | failed |
| C-GATE | the gate's fill and triangle exact (E1173) (gate1 = exact, gate2 = exact) | **held** |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 after the
row; a fault is read by the outcomes that name it), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder), J2 (job
2 done, slot 6 = M6 and run id 2). The after-reads are each job's own record's slots 40-47. The RULE
line `Q128-N3G-C RULE:` names the outcomes held; one PREDICTION line per outcome says predicted,
read and held or FAILED. Printed, never scored: the arm line, each job's Δtick, kick reply and K5's
BIF words, the survey (pre, post, each after-read and where they differ), the gate's tools, the
devcoredumps, every fault page against job 1's post words, R-BOOT (job 1's post pa against the odd
words of nine kept rows).

**This stage is a control.** The hooks stop it (rc 24) when the after-read is not the pre survey or
sa0-sa3 moved (C-DIFF); a stop (C-NOKICK) or a failed gate (rc 16) ends the session: the round
stops. Its disarm reset ends the stage; the next stage arms.

## Stage m: row M, 1 row of 2 jobs, flagged, on_stop "end", on_gate_fail "score"

**The arm.** `slots=0x1 entry=0 pds=mark pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch), emit word `emitpds.tasks.taske #0, r2, r3, r4, #0xc43`
(sideband 0xc43). Image mark (`asm/fwtask/pds/mark.s`, 3 rows, control word 0x01800100).

Row m1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 (dwords 224-255 filled with
0xdeadc0de and read as result slots 40-47, ticks, 200 ms) on a GETMISCINFO kick (`"kick":
"miscinfo"`). Then the page, snap0/snap9, the record (each job's K5 BIF words before and after it),
and after an ok end the gate (the fill then the triangle; the tools' whole outputs and the
devcoredumps kept), the disarm.

### The firmware-page write of stage m

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 21 dwords at #14's buffer address + 0x100, [0x100, 0x154) of the
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
| 0x120 | 0x005d3000 | ds0[4]: **M13** 0x005d3000 (new) |
| 0x124 | 0x005d1000 | ds0[5]: **M1** 0x005d1000 (new) |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00, attribute 13 (new) |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100, attribute 1 (new) |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | **movs douta, ds0[4], ds1[4]** (M13 to attribute 13, new) |
| 0x140 | 0x07084ea6 | **movs douta, ds0[5], ds1[5]** (M1 to attribute 1, new) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, at its base's index:
the cmd 6 branch sits after the base's last line). The emit's s0 is 0x01800100, s1 the address >> 4,
s2 0. **New bytes** (design §2): two markers and two douta more than crumb3. Through bit 10 (0xc43)
two EDM secondaries, sa1 and sa13, take values we chose until a reset [infer, H-BLOCK]; under X they
took stale values (0x04000010, 0x00043000) with the same kind of effect [HW, E1174].

### Outcomes of stage m (predictions/m.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| M-PA | job 1's post pa1 = M13 0x005d3000 (attribute 13 -> pa 13 - 12) (postpa1 = 0x005d3000) | **held** |
| M-SA13 | job 2's after sa13 = M13 (after2sa13 = 0x005d3000) | **held** |
| M-SA1 | job 2's after sa1 = M1 0x005d1000 (H-BLOCK; failed under H-COPY) (after2sa1 = 0x005d1000) | **held** |
| M-REBASE | job 2's after = job 1's post in all 32 (E1174) (j2 = done, after2 = REBASE) | **held** |
| M-FILL | the gate's fill faults, CID 15, at page 0x005d3000 (= M13) (gate1page = cid15 page 0x005d3000) | **held** |
| M-FILL43 | the fill faults at page 0x00043000 with sa13 = M13 (the page is not sa13) (gate1page = cid15 page 0x00043000, after2sa13 = 0x005d3000) | failed |
| M-FILLM1 | the fill faults at page 0x005d1000 (= M1: sa1 read first) (gate1page = cid15 page 0x005d1000) | failed |
| M-FILLOK | the gate's fill exact (gate1 = exact) | failed |
| M-NOKICK | job 2 not done 200 ms after its kick (j2 = notdone) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 after the
row; a fault is read by the outcomes that name it), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder), J2 (job
2 done, slot 6 = M6 and run id 2). The after-reads are each job's own record's slots 40-47. The RULE
line `Q128-N3G-M RULE:` names the outcomes held; one PREDICTION line per outcome says predicted,
read and held or FAILED. Printed, never scored: the arm line, each job's Δtick, kick reply and K5's
BIF words, the survey (pre, post, each after-read and where they differ), the gate's tools, the
devcoredumps, every fault page against job 1's post words.

The gate's failure is this stage's planned end (rc 16, scored: on_gate_fail "score"); its hooks
print an sa0-sa3 change or an after-read that is not the pre survey to the runner log and never stop
on it.

## Risk

Stage c: E1173's emit (0x843) and a read-only command: none new. Stage m: X's emit, kick and gate
(E1174), with sa1 and sa13 our unmapped marker pages (below 0x10000000, where no REV1 heap lies)
instead of stale unmapped ones [infer]. The stray append into [sa14 + 0xb0] stays as in X (sa14 a
stale word, an EDM-mapped page the reset rebuilds) [infer]. If a marker page were mapped (against
the map's reading), the faults would become stray reads or stores in that buffer; the reset rebuilds
the firmware's buffers (design §6).

## Stops

C not C-SAME or its gate failing (rc 16 or the hooks' rc 24): stop the round (the build, the boot or
the kit is suspect). J1 not DONE: CANNOT TELL, stop the ladder. M-MISS (the RULE says so): run G2's
s as a printed row, keep Q and LV as planned. A runner stop (a job not done, any fault outside the
gate) ends the session after reset and health (rc 4); the lead scores it by hand (`python3
score/score.py STAGE out/ATT/STAGE`). A failed reset (rc 13 or 5) is the user's ordinary reboot to
the default entry, end of the day. Any fault outside the gate other than the ones M, Q and LV name:
stop for the user.

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
- M-FILL reads the fault's list and page only (CID 15, page 0x005d3000); the devcoredump's BIF words
  are printed (X-FILL needed both).
- M-MISS is not a frozen outcome: the scorer reads it (M13 in no word of job 1's post pa0-15 and
  sa0-31) and the RULE line says the row cannot tell sa13's source.
- R-BOOT is printed (RBOOT lines: 8 odd pa against §0.1's words, the even ones as read), no outcome.

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses sb402 (bit 10 with bits 1:0 = 2
is unmeasured) and bit 10's douta landing (596cc74b), so the replay is `refused` with that reason
(design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop (after the boot and the srcversion): `python3 kit/session.py stage
.`, `python3 kit/session.py run .`, or `closing29/r42-n3g-logs/runone.sh G1 c m` (stage, run, score,
health draw); after a stop: `python3 score/score.py c out/ATT/c`, `python3 score/score.py m
out/ATT/m`.
