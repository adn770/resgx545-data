# r41-n3f-h2

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready). No rebuild, no boot:
the installed module.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 e516a7aa628b (branch r41-n3f, not
on main: the after-read blobs emitsb14s, emitsb_sbc43s and emitsb_sb403s, the kit's job lists,
sleep_ms, slots, gate_order, the gate's kept outputs and devcoredumps, on_gate_fail) and
resgx545-data b5b95bff2da7, laptop prefix `r41h2`, HostKeyAlias `cedar`. Question Q128 (N3f): what
an own-task emit with sideband bit 10 leaves behind that breaks the next fill. Design:
`closing29/n3f/design.md` (§3 the rows, §4 risks, §6 the user's decisions A-F, all (a), 2026-11-20).
Built offline, frozen, not staged, not run.

**When:** after H1 (decision C (a)): bit 10 without bits 6 and 11. The round's order: H1 (C then X),
H2 (Y), H3 (LC), H4 (T).

**Module.** The installed r40-kernel module, srcversion 83FBFD860D4E0D4CE691F48 (fork r40-kernel
423b436e7f80). The three blobs are accepted by its verifier unchanged and armed at their own form=
only: the fork's KUnit suite at 423b436e7f80 on the Mac shim plus one suite on them, 43 of 43
(`closing29/r41-n3f-logs/shim-r41.log`; the extra suite fails when a blob's form is wrong,
`shim-r41-neg.log`).

## Stage y: row Y, 1 row of 2 jobs, flagged, on_stop "end", on_gate_fail "score"

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sb403`; blob `emitsb_sb403s`
(`emitsb_sb403` with the cmd 6 branch, resgx545 r41-n3f
`test_emitsb_after_is_its_base_plus_the_cmd_6_branch_only`), emit word `emitpds.tasks.taske #0, r2,
r3, r4, #0x403` (sideband 0x403). Image crumb3 (`asm/fwtask/pds/crumb3.s`, 3 rows, control word
0x01800100), as B0-B11.

Row y1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 (dwords 224-255 filled with
0xdeadc0de and read as result slots 40-47, ticks, 200 ms) on a GETMISCINFO kick (`"kick":
"miscinfo"`). Then the page, snap0/snap9, the record, and after an ok end the gate (fill then tri;
the tools' whole outputs and the devcoredumps kept), the disarm.

### The firmware-page write of stage y

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 19 dwords at #14's buffer address + 0x100, [0x100, 0x14c) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again:

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 |
| 0x110 | V0 | V0 (TA3DCtl dword 0, the kernel's) |
| 0x114 | V2 | V2 (TA3DCtl dword 2, the kernel's) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 |
| 0x11c | 0x005a3305 | T3 0x005a3305 (the third breadcrumb) |
| 0x120 | 0x00000000 | 0 |
| 0x124 | 0x00000000 | 0 |
| 0x128 | 0x00000000 | 0 |
| 0x12c | 0x00000000 | 0 |
| 0x130 | 0x07001fe7 | tim breadcrumb 1 |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07003547 | tim breadcrumb 2 |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0x07003fe7 | tim breadcrumb 3 |
| 0x148 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sb403s`'s entry 1, at its base's index:
the cmd 6 branch sits after the base's last line). **These bytes are R4's, ST's, D0's and rows
B0-B11's, byte for byte: no new firmware-page write.** The emit's s0 is 0x01800100, s1 the address
>> 4, s2 0. **What is new is the effect, not the bytes**: whether a 0x403 emit (bit 10 without bits
6 and 11) rewrites the EDM's secondaries as 0xc43's does is the row's question (design §3.3).

### Outcomes of stage y (predictions/y.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| Y-REBASE | after sa0-31 = job 1's post sa0-31 (sa1 0x04400000, sa13 0x43000) (j2 = done, after2 = REBASE) | **held** |
| Y-HIGH | after sa0-11 = pre, sa12-31 = post (H-HIGH) (j2 = done, after2 = HIGH) | failed |
| Y-NONE | after = pre (H-NONE) (j2 = done, after2 = NONE) | failed |
| Y-OTHER | any other after (printed with indices) (j2 = done, after2 = OTHER) | failed |
| Y-KICKFAULT | job 2 not done, a BIF fault, CID 15 (page printed; 0x04400000 = sa1) (j2 = notdone, kick = cid15) | failed |
| Y-NOKICK | job 2 not done, no fault (j2 = notdone, kick = none) | failed |
| Y-FILL | the gate's fill faults 0xd0400 at 0x0004300f, the devcoredump's BIF words alike (gate1 = fault 0x000d0400 0x0004300f, devcd = 0x000d0400 0x0004300f) | **held** |

Controls (all can fail): PG (page dword 0), E0 (slot 1 = M1 and job 1's run id, cmd 0), T0 (snap0's
timer running), B (BIF_FAULT 0 after the row; a fault is read by the outcomes that name it), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder, design
§3.1). The RULE line `Q128-N3F-Y RULE:` names the outcomes held; one PREDICTION line per outcome
says predicted, read and held or FAILED. Printed, never scored: the arm line, job 1's start outcome
and T, each job's Δtick, slept and kick reply, the survey (pre, post, each after-read and where they
differ), the gate's two tools, the devcoredumps, the fault page against job 1's post words.

The gate's failure is this stage's planned end (rc 16, scored: on_gate_fail "score"); its hooks
print an sa0-sa3 change or an after-read that is not the pre survey to the runner log and never stop
on it (design K4).

## Risk

As H1's stage x (design §4): 0x403's emit, a sideband on the module's list never run before; the
same kick risk and the gate's planned fill fault.

## Stops

Job 1 not DONE: CANNOT TELL, stop the ladder. A runner stop (a job not done, any fault outside the
gate) ends the session after reset and health (rc 4); the lead scores it by hand (`python3
score/score.py STAGE out/ATT/STAGE`), as round 40's stopped rows. A failed reset (rc 13 or 5) is the
user's ordinary reboot to the default entry, end of the day. Any FAULT outside the gate other than
the KICKFAULT reading stops for the user.

## Deviations from the design (builder)

- As H1's stage x (job 2's slots, B read by Y-KICKFAULT first, no post stage, Y-FILL needs the
  devcoredump).

## Replay vectors

None: every row is an own firmware task on the EDM (the after-read of its secondary attributes and
the gate's fault); sgx-sim refuses the 0xc43 emit until a fold models what X measures (design O2),
so the replay is `refused` with that reason.

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`;
after (or a stop): `python3 score/score.py y out/ATT/y`.
