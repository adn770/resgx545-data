# N3h: who writes attribute 1, what the tick pass reads, and which pass faults
(design note, not built, not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§8). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
with its E number or, for round 42 (not folded yet), its session and stage (`G1 c`, `G1 m`, `G2 s`,
`G2 q`, `G3 lv`, read from `C/r42-n3g-logs/runone-G1-try2.out`, `runone-G2.out`, `runone-G3.out`
and the sessions' `out/*/STAGE/kernel.log`); **[infer]** everything else.

Paths: `R` = `/Users/jtorra/src/resgx545` (main cfd5d523, records to E1178), `F` = fork
`/Volumes/linux/linux-sgx-r42` at r42-kernel ec6511d5de87, `drivers/gpu/drm/gma500/sgxfive/`,
`C` = `/Users/jtorra/src/scratch/resgx545/closing29`. The laptop runs module srcversion
079DD0D13F231EEAC52FE0F (r42-kernel): forms incl. fw14, sbc43, sb403, sb402, sb400; images v1,
crumb, halt, crumb3, land, mark, landv (`F/sgx_own_regs.h:91-110`, `F/sgx_own_pds.h:3-9`).

**The short version.** Round 42's numbers fit one reading we can test without a rebuild: attributes
0-2 of the block bit 10 maps onto the EDM's bank are rewritten by the firmware's event PDS program
with each client event's (pa0, pa1, pa2), so the stock draws the kit runs at every stage boundary
overwrite attribute 1 (§0.1, H-EVT). Two small sessions test it, answer Q2 with the marker planted
instead of built, and split the kick pass from the after-read: **no fork change, no build, no
boot**; two kit changes (K6, K7) with tests. A rebuild alternative for Q2 is §4.

## 0. What round 42 left

- **M** [HW, G1 m]: post sa1 = M1 0x005d1000, sa13 = M13 0x005d3000, pa1 = M13; job 2's after-read
  = post in all 32; K5: job 2 pre BIF_FAULT 0, post 0x005d300f (BIF_INT_STAT 0x000d0400); the gate's
  fill then faulted at 0x5d300f. So sa1 is attribute 1 and sa13 attribute 13 (H-BLOCK; H-COPY
  failed), and the fault arose within job 2 (a GETMISCINFO kick plus our cmd 6).
- **S** [HW, G2 s]: post pa1 = M13 after M's resets and a session boundary (S-KEEP); the seven other
  odd pa as in nine kept rows. **R-BOOT** [HW, G1 c, printed]: 8 of 8 odd pa unchanged across the
  boot of the r42 module, so the store survives a warm reboot.
- **Q** [HW, G2 q]: 0x402 rebased as 0xc43 (Q-REBASE, Q-REP, Q-FILL held), post sa1 **0x04400000**,
  not M1; sa13 M13; K5 as M's (job 2 pre 0, post 0x005d300f).
- **LV** [HW, G3 lv]: LV-V (sa0 V0, sa2 V2) and LV-EARLY: K5 job 1 post BIF 0, job 2 **pre**
  0x0440000f (list 15, page 0x04400000 = post sa1), job 2 never served, the tick stopped (T read
  0x0105972f, 0x010180f6). LC [HW, E1176, E1178]: post sa0 0, the stop at page 0.
- Attribute 13 still holds M13 [HW, G3 lv post pa1], so every bit-10 row's sa13 is M13 until a
  writer we do not know of changes it.

### 0.1 H-EVT: attributes 0-2 hold the last client event's words [infer, offline]

The words bit 10 leaves in sa0-sa2 when our image does not write them have the shape of the event
words the firmware's PDS #13 hands each EDM pass (E746, E747) [HW]:

| row | post sa0 | post sa1 | post sa2 | source |
|---|---|---|---|---|
| LC (land) | 0 | (not printed) | 0x0104b95b | [HW, E1176] |
| LC2 (land) | 0 | 0x04400000 | 0x01030b00 | [HW, E1178] |
| X (crumb3) | V0 | **0x04000010** | V2 | [HW, E1174] |
| B11, Y, Q, LV | V0 | 0x04400000 | V2 | [HW, E1172, E1175, G2 q, G3 lv] |
| M (mark: M1 to attr. 1) | V0 | M1 | V2 | [HW, G1 m] |

- Event pa0 is 0 on every non-tick entry, pa1 carries a count K in bits 31:24 and one event bit in
  bits 23:0, pa2 an EVENT_TIMER sample counting down from 400000 (E746, E747) [HW]. LC's sa0 0, LC's
  and LC2's sa2 (0x04b95b and 0x030b00 in bits 23:0, both below 400000) and every sa1 (K = 4, bit 22
  or bit 4) fit that shape [HW values, infer reading].
- Bit 4 in slot 3 is the fill's end of render, E747's frozen witness (3 of 3 fills); bit 22 in slot
  3 is the other slot-3 bit of client jobs (20 of 138 entries) [HW, E747]. Never seen in sa1: bit 8
  (the GETMISCINFO kick, slot 0, E746) or a tick's word (bits 23:0 = 0) [HW, nine rows], though the
  arm's own GETMISCINFO and hundreds of ticks come after the begin draws in every stage.
- Every stage begins with a reset and the health draws (fill, then triangle; "SGX stopped, 3 events
  seen" at the arm's reset after them, [HW, G1 m, G2 q, G3 lv kernel.log]), then the arm. So the
  last client events before every read of ours are the begin draws'.

**H-EVT** [infer]: the event PDS program (slot 3 at least) writes its task's pa0-pa2 as attributes
0-2 of the block our emitted program writes, so each client event overwrites attribute 1; ticks and
kicks do not. M1 was lost between M and Q because G1's end draws, G2's begin draws and S's gate and
draws ran in between. Not explained by H-EVT: X's bit 4 where the triangle ran last (an order
variation of the triangle's own events, [infer, weak]); the floats in attributes 3, 5, 7, 9 (1.0,
-0.375, 1.0, 0.75, the same in M, Q and LV [HW]); attribute 12's 0x3, rewritten between Q and LV
[HW, G2 q pa0 V0, G3 lv sa12 0x3].

Rivals, each predicting something else for row V (§3.2): **H-EMIT**, the bit-10 emit itself puts a
word into attribute 1 before the program's douta (M's douta then overwrote it); **H-BOOT**, the
reset or the arm's boot writes it (#11, the 0xc43 boot program, loads V0, V1 0x32005000, V2, E002
[HW]); **H-FAULT**, M's fault and recovery path wrote it.

### 0.2 What the tick pass and the kick pass read [infer]

- Tick pass: LC (sa0 0) stopped at page 0, LV (sa0 V0, sa1 0x04400000) at page 0x04400000 [HW]. The
  runner's tick is HostCtl dword 12 and E002 names sa1 the HostCtl pointer [HW], so a tick pass
  reads through sa0 (TA3DCtl) and then sa1 (HostCtl) and stops at the first unmapped one [infer;
  "first" holds if BIF_FAULT keeps the first fault, which no record settles].
- Kick pass: in M, sa1 was M1 (unmapped [infer], as LV's 0x04400000 was [HW]) and the kick pass
  faulted at sa13's page, not sa1's, and still answered GETMISCINFO in 288 us [HW, G1 m]. So the
  kick pass does not read through sa1 before sa13 [infer, same caveat]; our entry 0 runs first in
  the pass and tail-calls the stock code (`R/tools/fwtask/gen_blobs.py` `done`, `dispatch`), so the
  after-read stored before the stock code met sa13 [infer].
- T (E1177): one job, no kick, BIF_FAULT 0 in snap9; the gate's triangle (a TA kick) then faulted at
  sa13's page [HW]. So a non-tick pass without any after-read faults at sa13 [HW + infer]. After the
  faulting fill of M and Q the kernel's recovery reset printed "SGX stopped, 0 events seen" [HW,
  G1 m, G2 q kernel.log]: the fill raised no event, as if the EDM had stalled before serving it
  [infer].

## 1. Rows, one line each

| row | session | question | image | kit |
|---|---|---|---|---|
| W | N1 | plant M1 in attribute 1, read it back, no pass after | mark | K7 |
| V | N1 | attribute 1 kept with no draws; the tick pass stops at sa1's page | landv | K7 |
| W2 | N2 | W again | mark | K7 |
| F | N2 | does the fill alone rewrite attribute 1; kick-only pass; stall | crumb3 | K6, K7 |

Every row: blob `emitsb_sbc43s`, `form=sbc43`, `pdsat=fw14`.

Brief's questions: 1 = W, V and F's Q1 part; 2 = V; 3 = F's jobs 2 and 3. Every blob, image and
form is on the running module and was run in round 42 [HW, G1 m, G2 q, G3 lv]. No new firmware
bytes (§3).

## 2. Kit changes (no rebuild; tests first)

**K6, a kick-only job** (`R/tools/fwtask/fwtask_run.py` `one_cmd`, `cmd_run`; the kit's job
grammar): a job `{"kick": "miscinfo", "n": 0, "expect": "notdone", "timeout_ms": 50}` writes no
command (CMD stays 0, so entry 0 dispatches nothing and tail-calls: `dispatch`, `more:`), reads K5's
BIF pre, kicks, **reads BIF again right after the kick's reply returns (`bif.mid`, new for every
kicked job)**, polls its timeout and reads BIF post; `done` false is its expected end and the list
goes on. `expect: "notdone"` only with `n` 0 and a kick; any other job not done still stops (rc 4).
Tests: the fake runner's records carry `mid`; a mock world where the kick faults shows it in job 2's
`mid` or `post`; `n` 0 without a kick, or `expect` on a cmd job, is refused by lint.

**K7, draws per stage** (`R/tools/closing/kit/run_stage.sh`, `lib_kit.sh` `begin`, `health_ok`,
session.toml keys, the guard): `begin_draws` and `end_draws` = `"fill,tri"` (default, today's),
`"fill"`, `"tri"` or `"none"`, and for an owntask stage `own_gate = "none"` (no gate after an ok
row). `none` keeps the reset and the register health (`fwtask_run.py health()`: EVENT_STATUS2,
BIF words, faults) and the arm's checks (alive, rate, miscinfo); only the draws go. Recovery paths
(`health` after a stop, `strict_health`) keep both draws always. The guard refuses `begin_draws`
other than the default on a session's first stage unless the stage before it in the same session
ended its own draws (none here: N1's and N2's first stages keep their begin draws). Tests: the fake
laptop's marks show which draws ran; a stop in a `none` stage still draws in recovery.

Also carried: K1-K5 (job lists, `sleep_ms`, `gate_order`, devcoredumps, hooks print and never stop,
the gate's failure a scored end, the per-job BIF words).

## 3. Rows, frozen predictions

Common: arm `slots=0x1 entry=0 pds=<img> pdsat=fw14 form=sbc43`, blob `emitsb_sbc43s` (emit word
`emitpds.tasks.taske #0, r2, r3, r4, #0xc43`), `#limit 0`, flagged, on_stop "end". Job 1 = command 1
(slots 2-5 and dwords 128-223 filled with 0xdeadc0de first, `"ticks": true`, 200 ms, no kick: the
emit on the timer pass). A cmd-6 job fills dwords 224-255 first and reads slots 40-47.

Controls, all can fail:

- **row-scoped** (the row's page and registers): PG (page dword 0), T0 (snap0's timer running), B
  (BIF_FAULT 0 in snap9; where an outcome names a fault, B is read by that outcome, the rule frozen
  in X, LC2 and LV);
- **job-scoped, read in that job's own record, never on the row-end page** (the H3 slip, E1176): E0
  (job 1's slot 1 = M1 0x5a5a3301 and run id 1, `cmd_after` 0); J1 (job 1 DONE: X0, S1, M4 with its
  run id, `done`; else CANNOT TELL and stop the session); for each later job Jn its own `done`, slot
  and run id, and its after-read from its own `slots`; each job's K5 words (`pre`, `mid`, `post`)
  from its own record.

Printed, never scored: the arm line, each job's Δtick and kick reply, K5's words, the survey (pre,
post, each after-read, where they differ), attributes 3-12 as post sa3-sa12, every fault page
against job 1's post sa0, sa1, sa13, the kernel's "events seen" lines.

U0 = 0x080401ef in every row (TRC 8, CBASE 15, index 0x4000 + 30, `emitsb_sbc43s`'s entry 1), as
G1 m and G3 lv [HW]; the builder confirms it at the freeze. V0 and V2 are the kernel's TA3DCtl
dwords 0 and 2 at the arm (0x32004000, 0x32002000 in every round 42 snap0 [HW]).

### 3.1 Session N1, stage w: row W, plant M1 (first in N1)

Image **mark**, G1 m's 21 dwords byte for byte. Stage keys: `own_gate = "none"`, `end_draws =
"none"` (K7); begin draws kept (the session's first stage). One job: job 1 only, **no kick, no
cmd 6**: T3 stops the tick, so no pass runs on the rebased bank until the disarm reset (T and B11's
one-job shape, BIF_FAULT 0 in snap9 [HW, E1172, E1177]).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | TA3DCtl dword 0 at the arm |
| 0x114 | V2 | TA3DCtl dword 2 at the arm |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 |
| 0x120 | 0x005d3000 | ds0[4]: M13 |
| 0x124 | 0x005d1000 | ds0[5]: M1 |
| 0x128 | 0x00000d00 | ds1[4]: douta control 0xd00 (attribute 13) |
| 0x12c | 0x00000100 | ds1[5]: douta control 0x100 (attribute 1) |
| 0x130 | 0x07001fe7 | movs tim (T1) |
| 0x134 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x138 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x13c | 0x07084406 | movs douta, ds0[4], ds1[4] (M13 to attribute 13) |
| 0x140 | 0x07084ea6 | movs douta, ds0[5], ds1[5] (M1 to attribute 1) |
| 0x144 | 0x07003547 | movs tim (T2) |
| 0x148 | 0x07000305 | movs doutu (entry 1) |
| 0x14c | 0x07003fe7 | movs tim (T3) |
| 0x150 | 0xaf000000 | halt |

| outcome | rule | prediction |
|---|---|---|
| W-SA1 | job 1's post sa1 = M1 | **held** [HW, G1 m M-SA1] |
| W-SA13 | job 1's post sa13 = M13 and pa1 = M13 | **held** [HW, G1 m] |
| W-QUIET | snap9 BIF_FAULT 0 (control B as a scored outcome) | **held** [HW, E1172, E1177] |
| W-FAULT | a BIF fault after job 1 (snap9 or the disarm's dump) | failed |

**Cannot tell.** J1 not DONE: stop N1 (V needs the plant). W-SA1 failing: V's V-KEEP outcomes read
cannot tell (nothing was planted), V runs for Q2 only (V-EARLY1 reads job 1's post sa1, whatever it
is). W-FAULT: stop the session (a pass ran that we did not expect).

**Risk.** E1177's emit (one job, no kick) with mark's bytes (run in G1 m); the gate's planned fault
of M does not happen (no gate). New: the stage ends without draws: the disarm reset's own checks
(alive, rate, miscinfo, register health) stand in for them, and V's arm checks again [infer: low].

### 3.2 Session N1, stage v: row V, attribute 1 with no draws, and the tick pass (last in N1)

Image **landv**, G3 lv's 18 dwords byte for byte. Stage keys: `begin_draws = "none"` (K7): between
W's emit and V's emit run only W's disarm reset, V's begin reset and V's arm (boot, GETMISCINFO,
ticks). Jobs: job 1 the emit (tick running, landv has no `tim`); job 2 command 6 with no kick (the
next tick pass). LV's heal job is dropped (LV-EARLY [HW]).

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0) |
| 0x110 | V0 | TA3DCtl dword 0 at the arm |
| 0x114 | V2 | TA3DCtl dword 2 at the arm |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2) |
| 0x11c | 0x00001800 | ds1[3]: douta control 0x1800 (attribute 24) |
| 0x120 | 0x5a5a3a18 | ds0[4]: Ma |
| 0x124 | 0x5a5a3a1a | ds0[5]: Mb |
| 0x128 | 0x00001a00 | ds1[4]: douta control 0x1a00 (attribute 26) |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07040606 | movs douta (V0 to attribute 0) |
| 0x134 | 0x07042ca6 | movs douta (V2 to attribute 2) |
| 0x138 | 0x07082606 | movs douta, ds0[4], ds1[3] (Ma to attribute 24) |
| 0x13c | 0x07084ca6 | movs douta, ds0[5], ds1[4] (Mb to attribute 26) |
| 0x140 | 0x07000305 | movs doutu (entry 1) |
| 0x144 | 0xaf000000 | halt |

| outcome | rule | prediction |
|---|---|---|
| V-KEEP | job 1's post sa1 = M1 | **held** [infer, H-EVT: no client event since W] |
| V-EVT | post sa1 an event word: bits 31:24 in 1-15, bits 23:0 = 0x000010 or 0x400000 | failed |
| V-V1 | post sa1 = 0x32005000 (V1: the boot's #11 writes attribute 1, H-BOOT) | failed |
| V-OTHER | any other post sa1 (H-EMIT) | printed |
| V-V | post sa0 = V0 and sa2 = V2; post sa13 = M13 | **held** [HW, G3 lv] |
| V-EARLY1 | job 2 not done; its K5 BIF_FAULT CID 15 at job 1's post sa1 page | **held** [infer] |
| V-EARLY13 | the same at the page of post sa13 (M13) | failed |
| V-EARLY0 | the same at page 0 | failed |
| V-SERVE | job 2 done | failed |

What V settles. V-KEEP with W-SA1: attribute 1 holds a value across two resets, a boot, kicks and
ticks; the writer between M and Q was the draws or M's fault path (F splits those). V-EVT, V-V1 or
V-OTHER: something between W and V writes attribute 1 though no client job ran; H-EVT fails, and
which rival is named by the value. V-EARLY1 with V-KEEP: the tick pass's fault page follows the
word we put into attribute 1 (Q2), with sa13 a different unmapped word (M13) and sa0 valid.

**Cannot tell.** J1 not DONE: CANNOT TELL. W-SA1 failed: V-KEEP, V-EVT, V-V1 read cannot tell.
V-EARLY1 when post sa1 = 0x04400000: LV again, Q2 not advanced. No fault and V-SERVE: printed, and
the tick-pass reading of §0.2 fails.

**Risk.** LV's (the highest of round 42) [HW, G3 lv: stopped after one tick pass, the kit's reset
and health recovered it], with sa1 = M1 instead of 0x04400000, both below 0x10000000, where no REV1
heap lies (`R/doc/specs/boot_sequence.md` §4) [infer: unmapped in the EDM's list, as 0x04400000 and
0x005d3000 faulted [HW]]. If M1's page were mapped, the tick pass's HostCtl store (dword 12 at
+0x30, [infer]) would land there; the reset rebuilds the firmware's buffers. V ends in the runner's
stop (rc 4, reset, strict health with both draws): the planned end, so it is last in N1.

### 3.3 Session N2, stage w2: row W2 (first in N2)

Row W byte for byte (§3.1: bytes, table, controls, keys). Needed again because N1's recovery draws
(V's stop) overwrite attribute 1 under H-EVT. W-FAULT stops the session; W2's W-SA1 failing makes
F's Q1 outcomes cannot tell (F's Q3 jobs still run).

### 3.4 Session N2, stage f: row F, the fill alone, and the kick pass (last in N2)

Image **crumb3**, G2 q's 19 dwords byte for byte. Stage keys: `begin_draws = "fill"` (K7): between
W2's emit and F's emit run W2's disarm reset, F's begin reset, **one stock fill**, F's arm. The
gate after an ok row stays (fill, tri), `on_gate_fail = "score"`.

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00000000 | ds1[1]: douta control 0x000 (attribute 0); T1's value |
| 0x110 | V0 | TA3DCtl dword 0 at the arm |
| 0x114 | V2 | TA3DCtl dword 2 at the arm |
| 0x118 | 0x00000200 | ds1[2]: douta control 0x200 (attribute 2); T2's value |
| 0x11c | 0x005a3305 | ds1[3]: T3 |
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

Jobs: job 1 the emit (T3 stops the tick); **job 2 kick-only** (K6: GETMISCINFO, no command, 50 ms,
`expect: notdone`); **job 3** command 6 on a GETMISCINFO kick (M's job 2).

Q1 part:

| outcome | rule | prediction |
|---|---|---|
| F-FILL4 | job 1's post sa1 an event word, bits 23:0 = 0x000010 | **held** [infer, H-EVT, E747] |
| F-KEEP | post sa1 = M1 | failed (would say: the fill does not write it; the triangle does) |
| F-OTHER | any other post sa1 (0x400000 in bits 23:0 included) | printed |

Q3 part:

| outcome | rule | prediction |
|---|---|---|
| K-QUIET | job 2's K5 pre BIF_FAULT 0 | **held** [HW, G1 m, G2 q job 2 pre] |
| K-KICK | job 2's K5 mid or post: CID 15 at post sa13's page (M13) | **held** [infer, E1177] |
| K-KICKOK | job 2's K5 post BIF_FAULT 0 | failed (would say: the bare kick pass does not fault) |
| K-REPLY | job 2's kick answered (GETMISCINFO line) | **held** [HW, G1 m] |
| K-STALL | job 3 not done, its kick not answered (500 ms) | **held** [infer, weak, §0.2] |
| K-SERVE | job 3 done, its after-read = job 1's post | failed |
| F-GATE | if reached, the gate's fill faults, CID 15, at post sa13's page | **held if reached** |

What F settles. K-KICK: a GETMISCINFO pass with our task idle faults at sa13, so the after-read is
not the cause; with `mid` 0 and `post` set, the fault came after the reply in the same pass [infer].
K-STALL: no pass is served after the first fault, so the round 41-42 gate fills found an EDM
already stalled since job 2 [infer]. K-KICKOK with K-SERVE: the bare kick pass is clean and the
fault needs our cmd 6's pass; job 3's K5 then says whether it faults there. F-FILL4: one client fill
puts its slot-3 event word in attribute 1.

**Cannot tell.** J1 not DONE: CANNOT TELL, stop. W2-SA1 failed: F-FILL4, F-KEEP cannot tell. K-KICK
and K-KICKOK both unread (job 2's record missing): Q3 cannot tell. K-STALL ends the row in the
runner's stop (rc 4): F-GATE "not reached".

**Risk.** X's, M's and Q's emit (E1174, G1 m, G2 q). New: a kick on an EDM that may be stalled
(job 3): the kernel's GETMISCINFO gives up after 500 ms, the runner stops, the kit's reset recovers
it, as K's stop did (E1155) [HW]. The stray `[sa14 + 0xb0]` append stays as in X [infer].

### 3.5 What the pair of sessions says about Q1

| W, V | W2, F | reading |
|---|---|---|
| V-KEEP | F-FILL4 | H-EVT: a fill's event writes attribute 1; resets, boot, kicks, ticks do not |
| V-KEEP | F-KEEP | the triangle's events write it, not the fill's; resets and boot do not |
| V-KEEP | F-OTHER | printed: a fill writes something other than its slot-3 word |
| V-EVT / V-V1 / V-OTHER | any | something with no client job writes attribute 1: H-EVT fails |

## 4. The rebuild alternative for Q2 (decision A (b))

A new image **landm**: landv with Mb's douta turned into a marker into attribute 1: data dword 9
(ds0[5]) = **0x005e1000** (a page below 0x10000000, used nowhere before), dword 10 (ds1[4]) =
**0x00000100** (attribute 1); the program words unchanged from landv (0x07084ca6 then writes ds0[5]
with control ds1[4]); 18 dwords at [0x100, 0x148), control 0x01800100. Row LM = LV with landm,
default draws, two jobs; LM-EARLY1 predicts the fault page 0x005e1000.

Costs: a fork commit on r42-kernel (image + KUnit, red then green), the Mac shim, a cachix build
(about 45 min unattended), install, a one-shot boot with the user's OK, srcversion check, a build
control (G1 c again). It answers Q2 directly and nothing of Q1 (draws kept); N1 then reduces to W
and an X-shaped read. Not recommended: the planted marker does the same without a boot, if V-KEEP
holds; if it does not, LM is the fallback and the user's next build carries it.

## 5. Offline first (no laptop)

- **O1 (records and kept pages).** The fold agent writes round 42; this design adds nothing to it.
  Before the freeze, read from kept pages, printed in the README: post sa0-sa2 and sa3-sa12 of
  every bit-10 row since B11, and LC's post sa1 (E1176), to finish §0.1's table.
- **O2 (sim in sync).** sgx-sim refuses bit 10's douta landing (596cc74b); the sessions' replay is
  `refused` with that reason. After the fold, model only what W, V and F measure.
- **O3.** No fork change, no shim run needed. The kit's mock: worlds for K6 (kick faults in `mid`),
  K7 (no draws in `none` stages, draws in recovery), V's stop and F's stall.

## 6. Build needs, run order, laptop time

**Build.** None on the fork or cachix; no boot. resgx545 branch `r43-n3h` off main once round 42's
fold has landed (it carries r42-n3g's kit, blobs and K5): K6 and K7 with tests, scorers for W, V
and F, sessions N1 (`r43h1`, stages w, v) and N2 (`r43h2`, stages w2, f), frozen with srcversion
079DD0D13F231EEAC52FE0F, `run_all`, check. Firmware-page writes: mark, landv and crumb3 at fw14,
the bytes of G1 m, G3 lv and G2 q exactly; each still needs the user's OK before the run.

**Recovery.** Every own-task stop and gate fault so far was recovered by the watchdog or the kit's
reset (round 40: 7 of 7; round 41: 5 of 5; round 42: M, Q, LV) [HW]; a failed reset (rc 13 or 5) is
the user's ordinary reboot to the default entry.

**Stop conditions.** J1 not DONE in any row: CANNOT TELL, stop that session. W-FAULT: stop N1 for
the user. Any fault outside the ones V and F name: stop for the user. A failed reset: the user's
reboot, end of the day.

**Run order.** Offline: K6, K7, scorers, sessions, tests red then green, mock, check. Then N1 (w,
then v, ends in V's planned stop), then N2 (w2, then f, ends in K-STALL's stop or the gate's fault).
N1 first: its V-KEEP decides whether F's Q1 part means anything.

**Laptop time.** N1 about 15-20 min (w about 6, v about 10 with the stop's recovery), N2 about 20
min. About 40 min attended in all, no build time.

## 7. Rejected alternatives

- **M's marker write without bit 10 (mark at fw14), then read.** The 0x843 write of attribute 1
  cannot be seen in its own row (the view is attributes 12-27, E1163), so a failed read could not
  tell "never landed" from "overwritten". W writes with 0xc43 and reads it in the same job.
- **mark with sb403 or sb402.** 0x003-family douta land in every fourth attribute [HW, E1164,
  E1175], so M13 and M1 both land in attributes 1, 5, 9, 13: sa1 = sa13, and V could not tell the
  sa1 page from the sa13 page.
- **landv with sb402** (Ma replicated into sa0, a "distinct" sa0). Puts 0x5a5a3a18 in sa0, inside
  the General heap's range (`boot_sequence.md` §4), possibly mapped: a stray store risk for a
  question LC already answered (sa0 0 stops at page 0).
- **v1 at fw14 for V** (V0, V2, no tim). Two rows and control 0x01000100: no two-row image at fw14
  ever ran to DONE; every DONE row used three rows [HW, E1162-E1178, G1-G3]. landv ran [HW, G3 lv].
- **A no-kit kick-only job** (job 2 = command 7, which entry 0 ignores). It works with today's kit
  but ends the row in the runner's stop at job 2, so K-STALL is never read. Decision C (b).
- **sb400** (on the module, never run). With bits 1:0 = 0 the program never runs (E1167, E1171), so
  nothing is read; left out.
- **A second emit in one row.** The same image writes the same words; one form per arm.

## 8. User decisions (one at a time)

- **A. The round's route for Q1 and Q2:** (a) no rebuild: plant M1 with W and read it with V across
  a stage boundary without draws (K7), N1 and N2 as designed (recommended: no boot, Q1 and Q2 in one
  session); (b) the rebuild of §4 (image landm, fork commit, cachix, boot, a build control), Q2
  only; (c) the lower-risk N1: V with crumb3 instead of landv (reads attribute 1, no tick pass, no
  early stop), Q2 left open.
- **B. K7, stages without the health draws** (W's gate and end draws, V's and F's begin draws left
  out; register health and the arm's checks stay; recovery always draws): (a) add (recommended:
  without it every read follows two draws and Q1 cannot be split); (b) skip: then only F's Q3 part
  and an LV repeat remain.
- **C. Q3's kick-only pass:** (a) K6, a kick-only job that does not stop the list, plus K5's `mid`
  read after each kick reply, and job 3 reading the stall (recommended); (b) no kit change: job 2 =
  command 7 on a kick, the row ends in the runner's stop, K-STALL unread; (c) skip Q3 (T and M
  already place the fault in the first non-tick pass, [HW + infer]).
- **D. F's begin draws:** (a) the fill alone (recommended: names the fill's event if F-FILL4); (b)
  the triangle alone; (c) both (today's): F answers Q3 only.
- **E. Order:** (a) N1 then N2, each ending in its planned stop (recommended: V-KEEP decides what
  F's Q1 part means); (b) N2 first (lower risk), then N1.
