# r42-n3g-g3

**NEEDS THE USER'S OK BEFORE RUNNING** (flagged; user present, reset ready). It needs the r42-kernel
module, built on cachix, installed and booted once by the lead with the user's OK first.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 c0e2dc367496 (branch r42-n3g, not
on main: the words sb402 and sb400, the blob emitsb_sb402s, the images mark and landv, the kit's arm
grammar for them, K5's per-job BIF words, the fork pin at r42-kernel) and resgx545-data
5e9c84b22ace, laptop prefix `r42g3`, HostKeyAlias `cedar`. Question Q128 (N3g): where sa13's page
comes from under sideband bit 10, bit 10 with bits 1:0 = 2, and `land` with V0/V2. Design:
`closing29/n3g/design.md` (§3 the rows, §6 risks and order, §8 the user's decisions A-F, all (a),
2026-11-21). Built offline, frozen with a placeholder srcversion, not staged, not run.

**When:** last of round 42, its own session (decision D (a)): landv with 0xc43, the timer running;
the highest risk. The round's order: G1 (C then M), G2 (S then Q), G3 (LV).

**Module.** fork r42-kernel ec6511d5de87 (`drm/gma500: let own_arm take sb402, sb400 and the mark
and landv images`; r42-red the same tests with stubs). Its KUnit suite on the Mac shim plus one
suite on the three after-read blobs armed with every row's arm line, 48 of 48
(`closing29/r42-n3g-logs/shim-r42.log`); r42-red 38 of 48 (`shim-r42-red.log`); the extra suite
fails when a blob's form is wrong (`shim-r42-neg.log`). srcversion is the placeholder
`UNBUILT-r42-kernel-ec6511d5de87` until the boot.

**Before staging** (the lead): build the module on cachix (`closing29/kernel39c/deliver-cachix.sh
send|start|fetch r42-kernel r42-red`), install and boot it once with the user's OK, check srcversion
loaded = installed, then set `srcversion` in session.toml (or rerun `stamp.py G3 SRCV` from
`closing29/r42-n3g-logs/sessgen`), `python3 kit/session.py freeze .` and `bash tests/run_all.sh`.

## Stage lv: row LV, 1 row of 3 jobs, flagged, on_stop "end", on_gate_fail "score"

**The arm.** `slots=0x1 entry=0 pds=landv pdsat=fw14 form=sbc43`; blob `emitsb_sbc43s`
(`emitsb_sbc43` with the cmd 6 branch), emit word `emitpds.tasks.taske #0, r2, r3, r4, #0xc43`
(sideband 0xc43). Image landv (`asm/fwtask/pds/landv.s`, 3 rows, control word 0x01800100).

Row lv1-a: job 1: command 1 (B11's: the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first,
`"ticks": true`, 200 ms, no kick: the timer pass); job 2: command 6 as above, no kick (the next tick
pass); job 3: command 6 as above after `"sleep_ms": 2000` (about 2000 stock passes: the heal read).
Then the page, snap0/snap9, the record (each job's K5 BIF words before and after it), and after an
ok end the gate (the fill then the triangle; the tools' whole outputs and the devcoredumps kept),
the disarm.

### The firmware-page write of stage lv

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 18 dwords at #14's buffer address + 0x100, [0x100, 0x148) of the
page; the disarm reset (or the watchdog's recovery reset) rebuilds #14's bytes and zeroes the slack
again:

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0) |
| 0x110 | V0 | the kernel's TA3DCtl dword 0 at the arm, V0 (0x32004000 in every round 41 snap0) |
| 0x114 | V2 | the kernel's TA3DCtl dword 2 at the arm, V2 (0x32002000 in every round 41 snap0) |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2) |
| 0x11c | 0x00001800 | ds1[3]: douta control 0x1800 (attribute 24) |
| 0x120 | 0x5a5a3a18 | ds0[4]: Ma 0x5a5a3a18 |
| 0x124 | 0x5a5a3a1a | ds0[5]: Mb 0x5a5a3a1a |
| 0x128 | 0x00001a00 | ds1[4]: douta control 0x1a00 (attribute 26) |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x134 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x138 | 0x07082606 | **movs douta, ds0[4], ds1[3]** (Ma to attribute 24, new operands) |
| 0x13c | 0x07084ca6 | **movs douta, ds0[5], ds1[4]** (Mb to attribute 26, new operands) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (`emitsb_sbc43s`'s entry 1, at its base's index:
the cmd 6 branch sits after the base's last line). The emit's s0 is 0x01800100, s1 the address >> 4,
s2 0. **New bytes** (design §2): land's markers from the third row and crumb3's two douta of V0 and
V2. Stock passes then run on the rewritten bank with the tick running (design §6, the highest risk).

### Outcomes of stage lv (predictions/lv.tsv, frozen; score/score.py)

| outcome | rule (the scorer's quantities) | prediction |
|---|---|---|
| LV-V | job 1's post sa0 = V0 and sa2 = V2 (H-BLOCK; LC2 read 0 and 0x01030b00) (postsa0 = @V0, postsa2 = @V2) | **held** |
| LV-EARLY0 | a stop, BIF_FAULT page 0 (CID 15), after job 1, before job 2 (early0 = yes) | failed |
| LV-EARLY | any other stop or CID-15 fault after job 1 before the gate (weak) (early = yes) | failed |
| LV-REBASE | job 2's after = job 1's post (as X, the tick running) (j2 = done, after2 = REBASE) | **held** |
| LV-HEAL | job 3's after sa13 = pre sa13 (0) (j3 = done, heal = yes) | failed |
| LV-FILL | the gate's fill faults, CID 15, at the page of job 1's post sa13 (gate1page = @post13) | **held if reached** |
| LV-FILLOK | the gate's fill exact (the stopped tick of crumb3 is needed) (gate1 = exact) | failed |

Controls (all can fail): PG (page dword 0), T0 (snap0's timer running), B (BIF_FAULT 0 after the
row; a fault is read by the outcomes that name it), and, read in each job's own record and never on
the row-end page (the H3 slip, E1176): E0 (job 1's slot 1 = M1 and its run id, cmd_after 0), J1 (job
1 DONE: X0, S1, M4 with its run id, its record done; else CANNOT TELL and stop the ladder), J2 (job
2 done, slot 6 = M6 and run id 2). The after-reads are each job's own record's slots 40-47. The RULE
line `Q128-N3G-LV RULE:` names the outcomes held; one PREDICTION line per outcome says predicted,
read and held or FAILED. Printed, never scored: the arm line, each job's Δtick, kick reply and K5's
BIF words, the survey (pre, post, each after-read and where they differ), the gate's tools, the
devcoredumps, every fault page against job 1's post words.

The gate's failure is this stage's planned end (rc 16, scored: on_gate_fail "score"); its hooks
print an sa0-sa3 change or an after-read that is not the pre survey to the runner log and never stop
on it.

## Risk

**The highest, lower than LC** (design §6, decision D (a)): stock passes every ~1 ms on the
rewritten bank until a stop or the gate, now with sa0/sa2 valid but sa1, sa13, sa14 and sa22 not
(X's and LC2's post sa22 is not the pre 0x32000000) [HW, E1174, E1178]: stores through stale
pointers into EDM-mapped pages are possible [infer]; the reset rebuilds firmware buffers and context
images. Its own session, last.

## Stops

J1 not DONE: CANNOT TELL. LV-EARLY0 or LV-EARLY: LV-REBASE, LV-HEAL and LV-FILL not reached (as
LC2), and no further LV form; then Q128's bit-10 thread is closed as far as our task can read it and
the user decides whether to ask it again. A runner stop (a job not done, any fault outside the gate)
ends the session after reset and health (rc 4); the lead scores it by hand (`python3 score/score.py
STAGE out/ATT/STAGE`). A failed reset (rc 13 or 5) is the user's ordinary reboot to the default
entry, end of the day. Any fault outside the gate other than the ones M, Q and LV name: stop for the
user.

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
- LV-EARLY reads as LC-EARLY did (a later job not done, or BIF_FAULT naming list 15 after the row)
  less LV-EARLY0's reading (job 2 not done and BIF_FAULT 0x0000000f); "before job 2 is served" would
  need K5's words, which the design keeps unscored, so they are printed per job (BIF lines) for the
  lead.
- LV-REBASE is frozen `held` (the design's table); with LV-EARLY0 or LV-EARLY held, LV-REBASE,
  LV-HEAL and LV-FILL read "not reached" (the design's cannot-tell rule).
- LV-V reads V0 and V2 from the row's snap0 (TA3DCtl dwords 0 and 2).

## Replay vectors

None: every row is an own firmware task on the EDM; sgx-sim refuses sb402 (bit 10 with bits 1:0 = 2
is unmeasured) and bit 10's douta landing (596cc74b), so the replay is `refused` with that reason
(design O2).

## Offline and laptop

`bash tests/run_all.sh`. Laptop (after the boot and the srcversion): `python3 kit/session.py stage
.`, `python3 kit/session.py run .`, or `closing29/r42-n3g-logs/runone.sh G3 lv` (stage, run, score,
health draw); after a stop: `python3 score/score.py lv out/ATT/lv`.
