# r41-n3f-h3

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready). No rebuild, no boot:
the installed module.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 e516a7aa628b (branch r41-n3f, not
on main: the after-read blobs emitsb14s, emitsb_sbc43s and emitsb_sb403s, the kit's job lists,
sleep_ms, slots, gate_order, the gate's kept outputs and devcoredumps, on_gate_fail) and
resgx545-data b5b95bff2da7, laptop prefix `r41h3`, HostKeyAlias `cedar`. Question Q128 (N3f): what
an own-task emit with sideband bit 10 leaves behind that breaks the next fill. Design:
`closing29/n3f/design.md` (§3 the rows, §4 risks, §6 the user's decisions A-F, all (a), 2026-11-20).
Built offline, frozen, not staged, not run.

**When:** after H1 and H2, its own session (decision D (a)): land with 0xc43, the timer running; the
highest risk. The round's order: H1 (C then X), H2 (Y), H3 (LC), H4 (T).

**Module.** The installed r40-kernel module, srcversion 83FBFD860D4E0D4CE691F48 (fork r40-kernel
423b436e7f80). The three blobs are accepted by its verifier unchanged and armed at their own form=
only: the fork's KUnit suite at 423b436e7f80 on the Mac shim plus one suite on them, 43 of 43
(`closing29/r41-n3f-logs/shim-r41.log`; the extra suite fails when a blob's form is wrong,
`shim-r41-neg.log`).

## Stage lc: row LC, 1 row of 3 jobs, flagged, on_stop "end", on_gate_fail "score"

**The arm.** `slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch, resgx545 r41-n3f
`test_emitsb_after_is_its_base_plus_the_cmd_6_branch_only`), emit word `emitpds.tasks.taske #0, r2,
r3, r4, #0xc43` (sideband 0xc43). Image land (`asm/fwtask/pds/land.s`, row L's).

Row lc1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 as above, no kick (the next tick
pass); job 3: command 6 as above after `"sleep_ms": 2000` (about 2000 stock passes: the heal read).
Then the page, snap0/snap9, the record, and after an ok end the gate (fill then tri; the tools'
whole outputs and the devcoredumps kept), the disarm.

### The firmware-page write of stage lc

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 16 dwords at #14's buffer address + 0x100, [0x100, 0x140) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again:

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00001800 | ds1[1]: douta control, attribute 24 |
| 0x110 | 0x5a5a3a18 | ds0[2]: Ma (the marker to sa24) |
| 0x114 | 0x5a5a3a1a | ds0[3]: Mb (the marker to sa26) |
| 0x118 | 0x00001a00 | ds1[2]: douta control, attribute 26 |
| 0x11c | 0x00000000 | ds1[3]: 0 |
| 0x120 | 0x00000000 | 0 |
| 0x124 | 0x00000000 | 0 |
| 0x128 | 0x00000000 | 0 |
| 0x12c | 0x00000000 | 0 |
| 0x130 | 0x07040606 | movs douta (Ma to sa24) |
| 0x134 | 0x07042ca6 | movs douta (Mb to sa26) |
| 0x138 | 0x07000305 | movs doutu (entry 1) |
| 0x13c | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, at its base's index:
the cmd 6 branch sits after the base's last line). **These bytes are row L's (r40-n3e-l), byte for
byte: no new firmware-page write.** The emit's s0 is 0x01800100, s1 the address >> 4, s2 0. **What
is new is the effect, not the bytes** (design §3.1): a 0xc43 emit rewrites the EDM's secondaries
until a reset (B11's survey, §0.3).

V0/V2 are not written by land (its dwords 4 and 5 are the markers): under H-REBASE the EDM's sa0 and
sa2 become stale block words too (design §3.4).

### Outcomes of stage lc (predictions/lc.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| LC-EARLY | a stop or a BIF fault (CID 15) after job 1, before the gate (early = yes) | **held** |
| LC-REBASE | job 2's after = job 1's post (early = no, after2 = REBASE) | **held if not LC-EARLY** |
| LC-HEAL | job 3's after sa13 = pre sa13 (0) (j3 = done, heal = yes) | failed |
| LC-FILL | the gate's fill faults, CID 15, at the page of job 1's post sa13 (gate1page = @post13) | **held if reached** |
| LC-FILLOK | the gate's fill exact (would say: bit 10 + stopped timer) (gate1 = exact) | failed |

Controls (all can fail): PG (page dword 0), E0 (slot 1 = M1 and job 1's run id, cmd 0), T0 (snap0's
timer running), B (BIF_FAULT 0 after the row; a fault is read by the outcomes that name it), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder, design
§3.1). The RULE line `Q128-N3F-LC RULE:` names the outcomes held; one PREDICTION line per outcome
says predicted, read and held or FAILED. Printed, never scored: the arm line, job 1's start outcome
and T, each job's Δtick, slept and kick reply, the survey (pre, post, each after-read and where they
differ), the gate's two tools, the devcoredumps, the fault page against job 1's post words.

The gate's failure is this stage's planned end (rc 16, scored: on_gate_fail "score"); its hooks
print an sa0-sa3 change or an after-read that is not the pre survey to the runner log and never stop
on it (design K4).

## Risk

**Higher** (design §4, decision D (a)): with land the tick keeps running, so stock passes run every
~1 ms on a stale sa0/sa1/sa2 until the stop: stores through stale pointers into EDM-mapped pages
(the kernel's buffers and the render node's contexts) [infer]; the reset rebuilds firmware buffers
and context images. Its own session, after H1 and H2.

## Stops

Job 1 not DONE: CANNOT TELL, stop the ladder. A runner stop (a job not done, any fault outside the
gate) ends the session after reset and health (rc 4); the lead scores it by hand (`python3
score/score.py STAGE out/ATT/STAGE`), as round 40's stopped rows. A failed reset (rc 13 or 5) is the
user's ordinary reboot to the default entry, end of the day. Any FAULT outside the gate other than
the KICKFAULT reading stops for the user. LC-EARLY: no further LC form.

## Deviations from the design (builder)

- Jobs 2 and 3 read their after-reads from result slots 40-47 in their records (K1's `slots`): both
  write dwords 224-255.
- LC-EARLY is read as a later job not done or BIF_FAULT naming list 15 after the row; the runner's
  stop (rc 4) is scored by hand, as round 40's stopped rows (K4 covers the gate's failure only).
- LC-REBASE's prediction is frozen as "held if not LC-EARLY", LC-FILL's as "held if reached" (the
  design's (a)-(c) notes); the PREDICTION line says "not reached" when LC-EARLY holds.
- No post stage.

## Replay vectors

None: every row is an own firmware task on the EDM (the after-read of its secondary attributes and
the gate's fault); sgx-sim refuses the 0xc43 emit until a fold models what X measures (design O2),
so the replay is `refused` with that reason.

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`;
after (or a stop): `python3 score/score.py lc out/ATT/lc`.
