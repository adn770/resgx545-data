# N3f: what an own-task emit with sideband bit 10 leaves behind that breaks the next fill
(design note, not built, not run)

Status: a design for the lead to bring to the user as **flagged decisions** (§6). Nothing here is
built, committed, staged or run; no laptop, cachix or fork was touched. Tags: **[HW]** measured,
**[RE]** our reading of the firmware as the records give it, **[infer]** reasoning, **[post hoc]**
read after a run, not frozen, **[unfolded]** measured in a kept session no E-record carries yet
(a fold agent is writing them in parallel; nothing here edits a repo).

Paths: `R` = `/Users/jtorra/src/resgx545` (main 98c924c, records up to E1161; the kit and blobs of
the n3e sessions at r40-n3e b8528c0ceb04), `F` = fork `/Volumes/linux/linux-sgx-r40` at r40-kernel
423b436e7f80, `drivers/gpu/drm/gma500/sgxfive/` (read with `git show r40-kernel:`), `C` =
`/Users/jtorra/src/scratch/resgx545/closing29`. Module on the laptop: srcversion
83FBFD860D4E0D4CE691F48 (fork 423b436e7f80), the 18-word `form=` list and `pds=land`
(`F/sgx_own_regs.h:150-169`; `F/sgxfive_owntask.c:612`). `0x402` is **not** in the list; `0x403`
is. `pds=` and `form=` are checked independently (`F/sgxfive_owntask.c:749-769`), so
`pds=land form=sbc43` arms on today's module.

## 0. What B11 left, read again

Row B11 (`C/r40-n3e-b11`, `emitsb_sbc43`, crumb3 at `pdsat=fw14`, `form=sbc43`, tick pass, one job)
[HW, unfolded]:

| attempt | job | gate fill | gate tri | kernel during the gate |
|---|---|---|---|---|
| 074024 | DONE | 2048/2048 0xdeadbeef | exact | BIF 0xd0400 at 0x4300f, PD 0, job 95 |
| 084102 | DONE | 2048/2048 0xdeadbeef | exact | BIF 0xd0400 at 0x4300f, PD 0, job 103 |

Every other DONE row passed the same gate: b0 (0x843), b1 (0x003), b3 (0x842), b8 (0x002), l
(`out/*/own/c1-a.gate.json`). b2, b4, b10 stopped before it (hang).

### 0.1 Where the gate runs and what it runs

- The owntask runner calls `gate` after a row that ended ok, **before** `hook_check`
  (`C/r40-n3e-b11/kit/run_stage.sh:354-363`, hook at :371; `R/tools/closing/kit/run_stage.sh` at
  b8528c0). A failed gate is rc 16: reset, health, session end. So B11's hook line "sa1 is not
  TA3DCtl dword 1" (`run/hooks.sh:57-60`) never got to stop the stage.
- `gate()` = `t30 fill` then `t30 tri`, output filtered to `^diff|FAIL|^tri 64x64`
  (`kit/fwtask_run.py:192-198`, `R/tools/fwtask/fwtask_run.py`). The filter drops the tool's `job:`
  line and its stderr, so the gate JSON cannot tell "job faulted" from "job ok, nothing written".
- **The fill is a transfer, the triangle a render.** t30 (`sgxfive-test.c` at 42c4de78,
  session.toml `[tools.t30]`) `cmd_fill` (:1074-1135) submits `sgxfive_xfer_fill`
  (`R/userspace/libsgxfive/src/xfer_job.c:368`): a transfer context's job, the register block of
  `R/doc/specs/transfer.md` §2.3, which the EDM queues in its TRANSFER handler (`0x0103`) and
  starts from its pick routine (`0x12dc`-`0x1460`) (transfer.md §0, §3.1-3.2: "every blit, fill
  and copy is a transfer, a small 3D render with no TA phase that the EDM runs from a queue").
  `cmd_tri` (:3632) builds a render context and a TA+3D render (the TA kick, handler `0x011d`).
  Our own sources settle it; the IGT fork was not needed.

### 0.2 What the kernel log says (B11's `out/*/own/kernel.log`) [HW, unfolded]

- The gate's fill faulted: `BIF fault 0xd0400 at 0x4300f (PD 0x0) stalls job N, recovering`,
  identical in both attempts. The message prints `BIF_INT_STAT`, `BIF_FAULT`, the directory
  (`F/sgxfive.c:1045-1047`). Decoded with `R/doc/specs/hw_spec.md` §5.5: `FAULT_REQ` bit 10,
  `FAULT_TYPE` 5 (the word of E764's background program fetch and E1072), `ADDR` page **0x43000**,
  `SB` 0, `CID` **15**, the EDM's list (`BIF_BANK0 = 0xf`, `R/doc/specs/boot_sequence.md:224`);
  "PD 0x0" is the kernel's own mark for the EDM's list (`F/sgxfive.c:579-586`).
- The kernel's watchdog recovered it: a full reset that rebuilds every firmware buffer and resets
  the debug state, "so the stock EDM is what boots" (`F/sgxfive.c:622-672`; the disarm is the
  same path, `F/sgxfive_owntask_test.c:1250-1272`). **The gate's tri ran after that reset, on the
  stock firmware, disarmed.** "tri exact" says nothing about the state bit 10 left; only the fill
  saw it. Then the kit's rc-16 reset (07:40:40 / 08:41:18) and health (fill2, tri ok).
- No "error state captured" line after either fault: devcoredump keeps one dump per device for five
  minutes and allocates none while one is pending (`F/sgxfive_coredump.c:14-15`); attempt 2's
  begin reset captured one 11 s before [infer: attempt 1 likewise from b10's reset].
- snap9 (after the job, before the gate) differs from b0's only in boot-specific words (`0x0144`,
  `0x0b14`, `0x0c70`, `hostctl 0x30/0x34`, `ta3dctl 0x5c`): debugfs registers and control blocks do
  not show the change.

### 0.3 What the survey shows (D0's slots, `c1-a.own_res.json`) [HW, unfolded, post hoc]

`score.py own` on attempt 1 prints the SURVEY lines; both attempts:

- pre (entry 0, the EDM's own bank, P1 passed): sa0-2 = V0, V1 0x32005000, V2; sa22 0x32000000,
  sa23 the EDM PD; the rest 0. Same as b0.
- post (entry 1): sa0 = V0, **sa1 = 0x04400000**, sa2 = V2, sa3-11 = floats (1.0, 0.75, -0.375,
  ...; attempt 2: sa11 0), and **sa(12+k) = pa(k) for k = 0..19** in both attempts. b0 (0x843):
  post = pre exactly (the sharing D0 found, E1161).
- So post sa13 = pa1 = **0x00043000** (both attempts; pa1 is 0x43000 in every DONE row since Z,
  n3e §0), sa14 = pa2 = 0x32002000 (att 1) / 0x32411000 (att 2), sa15 = pa3 = 0x01555620, sa16 =
  0x32004000, sa22 = 0x32002000.
- Firmware roles (`R/doc/specs/edm_dataflow.md:44-46, 255-261, 685-705`) [RE]: sa13/sa14 = the
  transfer run queue's head and tail (HWTRANSFERCONTEXT), sa15/sa16 = the render queue's
  (HWRENDERCONTEXT), sa3 = TRANSFERCMD; sa0-2 = TA3DCtl, HostCtl, kernel CCB control (E002).

**The fault page is post sa13 exactly, through the EDM's list** [infer, strong]: a fill finds the
transfer queue "non-empty" (head 0x43000), the pick routine reads a HWTRANSFERCONTEXT at 0x43000
and faults. The tail differed between attempts and the fault did not, as a head read predicts.
Unread: the handler's append writes the new context into `[sa14 + 0xb0]` when sa14 != 0
(`edm_dataflow.md:278-280, 700-701`): 0x320020b0 (att 1, the kernel CCB control's page) or
0x324110b0 (att 2) [infer]; both rebuilt or recovered by the reset.

## 1. Hypotheses (each [infer])

- **H-REBASE** (lead). Bit 10 makes the issuer take the emitted program's `douta` block as its
  secondary bank, for every later task of that issuer (the EDM's own included) until a reset; #11
  (the firmware's only 0xc43 user) is the program that loads the EDM's sa0-sa2 at boot (E002;
  `R/doc/specs/hw_spec.md` §11.1). Fits: post sa0/sa2 = V0/V2 = crumb3's two `douta` (to attributes
  0 and 2), the rest of the block stale; the gate's TRANSFER reached the handler because crumb3
  happens to rewrite sa0 and sa2 with the right pointers (the kernel CCB through sa2); the head
  0x43000. Predicts: the EDM's bank after the job = entry 1's post bank **including sa1 =
  0x04400000**.
- **H-HIGH**. Only the EDM's sa12 and up are overwritten (by the started task's primaries, which sit
  12 dwords above its secondaries); sa0-11 kept. Predicts EDM sa1 = 0x32005000, sa13 = 0x43000.
- **H-NONE**. The EDM's bank is untouched; post is the started task's alone; the fault has another
  cause. Predicts EDM sa = pre.
- **The timer**: crumb3 stops the tick (`tim` markers); every crumb3 DONE row's gate fill was
  served with it stopped (b0, b1, b3, b8), so a stopped timer alone does not break a fill [HW].
  Whether bit 10 needs it is LC's question (§3.4).

A note for the fold (O4): row L's dump has Ma (attribute 24) at dword 204 = pa12 and Mb
(attribute 26) at dword 206 = **pa14** (`C/r40-n3e-l/out/20261119-230429/own/c1-a.own_res.json`;
entry 1 stores pa0-15 in order, `emitsb14d.s`). "attribute n lands in pa n/2" fits 24 only;
**pa n-12** fits both, and B11's sa(12+k) = pa(k) is the same 12 [post hoc].

## 2. Offline first (no laptop)

- **O1 (records).** Fold B11 with §0's corrections: the fill faulted (BIF word, page, CID 15); the
  gate's tri ran after the watchdog's recovery reset, disarmed; the survey diff and sa13 = page.
- **O2 (sim in sync).** sgx-sim keeps refusing 0xc43 (`R/crates/sgx-sim/src/sgx.rs`, the own-task
  emit refusal); only after X it models what X measures.
- **O3 (shim).** The three new blobs (§3.1) through the fork's KUnit suite on the Mac shim (as
  `C/r40-n3e-logs/shim-r40-kernel.log`), accepted with their `form=` on 423b436e7f80.
- **O4.** Settle "pa n/2" vs "pa n-12" on L's kept page before the fold writes it.

## 3. Rows, frozen predictions

### 3.1 What every row needs: no rebuild, kit and blob changes only

**Blobs** (`R/tools/fwtask/gen_blobs.py`, one variant per form): `emitsb_<f>s` = `emitsb_<f>`
plus a **cmd 6 branch** in entry 0: store sa0-sa31 into dwords 224-255 (**after**), M6
0x5a5a3306 + run id in slot 6 (dwords 88-91), cmd 0, state 2, **no emit**. Entry 1, cmd 1's path
and the emit word unchanged. Forms: `fw14` (control), `sbc43`, `sb403`, all in the module's list.
The verifier sees one `emitpds` (`F/sgxfive_owntask.c:752-755`).

**Kit** (`R/tools/fwtask/fwtask_run.py`, `R/tools/closing/kit/`; tests with `kit/fake` and the
mock):

- **K1** an owntask row with a job list (`cmd_run` already loops over `jobs`,
  `fwtask_run.py:347-410`; the row grammar takes one object today) and `sleep_ms` before a job;
  each job's `kick` as today (`one_cmd`, :274-328).
- **K2** `gate` with an order (`fill,tri` default, `tri,fill`), a stage key `gate_order`, the full
  tool outputs kept (`NAME.gate-fill.txt`, `.gate-tri.txt`: the `job:` line and stderr).
- **K3** devcoredump: before the gate, save and free any pending
  `/sys/class/devcoredump/devcd*/data` (`NAME.devcd-pre.txt`, write to `data` frees it); after the
  gate save the new one (`NAME.devcd.txt`: BIF words, control blocks, the faulting job's command,
  `F/sgxfive_coredump.c:131-181`).
- **K4** for these sessions `hook_check` prints, never stops, on sa changes (the change is the
  reading); the gate failure of the last stage is the planned end (rc 16), scored, not void.

**Base of every row**: B11's arm with the survey blob, flagged, `#limit 0`, on_stop "end";
job 1 = cmd 1 (the emit, tick pass, `"ticks": true`, 200 ms, slots 2-5 and 128-223 filled as
B11), job 2 = cmd 6 (dwords 224-255 filled with 0xdeadc0de first). Common table and controls PG,
E0, T0, B as B11 (README "Outcomes"); job 1 must be DONE, else CANNOT TELL and stop.

**Firmware-page writes (each row needs the user's OK).** No new image, no new emit word. crumb3
rows: R4's 19 dwords [0x100, 0x14c) byte for byte (approved, run in R4, ST, D0, B0-B11); U0 =
TRC 8, CBASE 15, index 0x4000 + the new blob's entry 1 (B11's 0x080401ef if entry 1 does not move;
the builder states it). The land row: L's 16 dwords [0x100, 0x140) (decision C (a) of n3e), U0
likewise. **What is new is the effect, not the bytes**: a 0xc43 emit rewrites the EDM's
secondaries (§0.3) until a reset.

### 3.2 Session H1: control C, then row X (the after-read), crumb3

**Stage c (C, first): `emitsb14s`, `form=fw14`.** Job 2 on a GETMISCINFO kick (`"kick":
"miscinfo"`): the timer is stopped after job 1, and kicks are served then (every crumb3 DONE gate
fill; Z and SB ran on kick passes, E1156, E1157).

| outcome | rule | prediction |
|---|---|---|
| C-SAME | job 2 done; after sa0-31 = job 1's pre sa0-31 | **held** (D0: shared, unchanged) |
| C-DIFF | after differs from pre | failed |
| C-NOKICK | job 2 not done 200 ms after its kick | failed |
| gate | fill and tri exact (as B0) | **held** |

C failing in any way stops everything (the blob or K1 is suspect). Its reset disarms; stage x arms.

**Stage x (X, last): `emitsb_sbc43s`, `form=sbc43`**, job 2 as C. Then the gate (fill first, K3).

| outcome | rule | prediction |
|---|---|---|
| X-REBASE | after sa0-31 = job 1's post sa0-31 (sa1 0x04400000, sa13 0x43000) | **held** |
| X-HIGH | after sa0-11 = pre, sa12-31 = post | failed (H-HIGH) |
| X-NONE | after = pre | failed (H-NONE) |
| X-OTHER | any other after | printed with indices |
| X-KICKFAULT | job 2 not done, a BIF fault, CID 15 | failed; page printed (0x04400000 = sa1) |
| X-NOKICK | job 2 not done, no fault | failed |
| X-FILL | gate fill faults 0xd0400 at 0x0004300f, the devcd's BIF words alike | **held** (2 of 2) |

Printed, not scored: the kick's reply (under H-REBASE the GETMISCINFO reply may be lost through
sa1 [infer, weak]), job 1's survey (as B11), the devcoredump. X-REBASE and X-FILL together name
what breaks the fill: the EDM's transfer head.

### 3.3 Session H2: row Y, bit 10 without 6 and 11 (`emitsb_sb403s`, `form=sb403`, crumb3)

X's table with X replaced by Y. Frozen: **Y-REBASE and Y-FILL held** (bit 10 decides; 0x003 alone
passed the gate, b1) [infer]. Y-NONE with a passing gate says 6 or 11 is needed with 10. One
stage, last; about 10 min.

### 3.4 Session H3: row LC, `land` with 0xc43 (the timer keeps running)

Arm `slots=0x1 entry=0 pds=land pdsat=fw14 form=sbc43`, `emitsb_sbc43s`. Job 1 cmd 1 (tick pass;
L kept T counting, 39 ticks, `C/r40-n3e-l`), job 2 cmd 6 on the next tick pass (no kick), job 3
cmd 6 after `sleep_ms` 2000 (about 2000 stock passes; the heal read). land writes no V0/V2: under
H-REBASE the EDM's sa0 and sa2 become stale block words too.

| outcome | rule | prediction |
|---|---|---|
| LC-EARLY | a stop or a BIF fault (CID 15) after job 1, before the gate | **held** (a) |
| LC-REBASE | job 2's after = job 1's post | held if not EARLY |
| LC-HEAL | job 3's after sa13 = pre sa13 (0) | failed (b) |
| LC-FILL | gate fill faults at page = job 1's post sa13 | held if reached (c) |
| LC-FILLOK | gate fill exact | failed (would say: bit 10 + stopped timer) |

(a) H-REBASE: the next stock pass reads TA3DCtl and the CCB through stale sa0/sa2. (b) No stock
writer of sa13 without transfer traffic (`edm_dataflow.md:685-705`). (c) Bit 10 alone, the timer
irrelevant.

Printed: alive after job 1 (L-TICK), where Ma/Mb land, any fault page against job 1's post words.
**If X reads X-REBASE, LC-EARLY is the likely end and LC cannot answer the timer question**; then
the clean separation is a `land`-like image that also writes V0/V2 (a new image: rebuild, §6 E).

### 3.5 Session H4: row T, tri first (`emitsb_sbc43s`, crumb3, `gate_order = "tri,fill"`)

Job 1 only (job 2 optional as X). The TA kick handler appends to the render queue when sa16 != 0
(`[sa16 + run_node_next_ta]`, sa16 = 0x32004000 = TA3DCtl) and the pick reads the head sa15 =
0x01555620 (`edm_dataflow.md:255-261, 399-456`) [RE, infer].

| outcome | rule | prediction |
|---|---|---|
| T-HEAD | tri faults, CID 15, page 0x01555000 | **held** |
| T-OTHER | tri faults at another page (printed; 0x04400000 = sa1) | failed |
| T-HANG | tri times out, no fault | failed |
| T-OK | tri exact | failed (would say: the break is transfer-only) |

The fill after the tri runs on the recovered stock firmware (as B11's tri did): printed only.

### 3.6 What needs what

| row | session | new blob | kit | rebuild + boot |
|---|---|---|---|---|
| C, X | H1 (2 stages) | `emitsb14s`, `emitsb_sbc43s` | K1, K3, K4 (K2 output) | no |
| Y | H2 | `emitsb_sb403s` | as H1 | no |
| LC | H3 | `emitsb_sbc43s` | K1 (`sleep_ms`) | no |
| T | H4 | `emitsb_sbc43s` | K2 (`gate_order`) | no |
| 0x402 | cond. | `emitsb_sb402s` | as H1 | **yes** (new form, KUnit) |
| land+V | cond. | none | none | **yes** (new image) |

## 4. Risk, recovery, stop conditions, work list, time

**Recovery.** Every own-task stop so far was recovered by a reset (n3e §4: 7 of 7; B11 2 of 2 by
the watchdog, then the kit's); a failed reset (rc 13 or 5) is the user's ordinary reboot.

- **C.** B0's emit plus a read-only command; B0's risk.
- **X, Y.** B11's emit, run twice already: the fill's fault was recovered both times. New: job 2's
  kick on a rebased bank may write through sa1 (0x04400000) and fault with no job in flight; the
  kernel's watchdog polls only while jobs are in flight (`F/sgxfive.c:1025`), so the runner's
  "no done" stop and its reset end it (as K, E1155). The append into `[sa14 + 0xb0]` (§0.3) is a
  stray store into an EDM-mapped page; both seen so far were rebuilt or reset.
- **LC: higher.** Stock tick passes every ~1 ms on a stale sa0/sa1/sa2 until the stop: stores
  through stale pointers into EDM-mapped pages (the kernel's buffers and the render node's
  contexts, `F/sgxfive.c:759-761`) [infer]; the reset rebuilds firmware
  buffers and context images (`F/sgxfive.c:622-636`). Its own session, after H1 and H2.
- **T.** A stray store into TA3DCtl (rebuilt by the reset) and a fault on a render; recovered as
  the fill's. Its own session, last, only with decision D.

**Stop conditions.** C not C-SAME or its gate failing: stop everything. Job 1 not DONE in any
row: CANNOT TELL, stop the ladder. Any FAULT outside the gate other than X-KICKFAULT: stop for the
user. LC-EARLY: no further LC form. A failed reset: the user's reboot, end of the day.

**Work list (tests first, red then green), resgx545 branch off main, no fork change:**

1. `gen_blobs` `emitsb_<f>s` for fw14, sbc43, sb403; tests beside `tools/fwtask/test_emitpds.py`:
   equal to `emitsb_<f>` except the cmd-6 branch; that branch stores sa0-31 at 224-255 and M6,
   clears cmd, sets state 2, has no emit; `fwtask.refusal(...) is None`; lint clean. O3 shim.
2. K1-K4 with tests (`kit/fake` debugfs with a devcoredump file; mock runs: a two-job row, a
   `tri,fill` gate, a gate failure that keeps both outputs and the dump).
3. Scorer: C, X, Y, LC, T tables; tests on B11's kept attempts with job 2 fabricated as X-REBASE,
   X-HIGH and X-NONE.
4. Sessions H1-H4 frozen, srcversion 83FBFD860D4E0D4CE691F48.

**Laptop time.** H1 about 15 min (two stages), H2, H3, H4 about 10 min each: about 45 min, all
attended (flagged).

## 5. Rejected alternatives

- **Reading the change from debugfs registers or snaps**: snap9 is B11 = B0 (§0.2); no register
  shows the USE attribute store. Only our own task reads it.
- **`hold_recovery` around the gate** (E764's held fault): keeps the fault but stops the EDM, so no
  task of ours runs to read sa; the devcoredump (K3) gives the same BIF words and control blocks.
- **"Several fills without a reset"**: the first fill's fault is recovered by the watchdog's full
  reset, which disarms; a second fill always runs on stock. Persistence is read with sa reads (LC's
  job 3) instead.
- **A second own-task row after the gate**: the gate's failure ends the session (rc 16) and the
  watchdog's reset already disarmed; hence two jobs in one row (K1).
- **0x402 now**: needs a module build; 0x403 (H2) asks bit 10 without 6 and 11 boot-free.

## 6. User decisions (one at a time)

- **A. The kit changes K1-K4 and the three survey blobs** (no rebuild): (a) all, sessions H1-H4
  as planned (recommended); (b) K1, K3, K4 only (no tri-first row).
- **B. Row X's after-read pass** on a crumb3 arm: (a) a GETMISCINFO kick, as Z and SB
  (recommended); (b) skip X and read only on `land` (LC's tick pass).
- **C. Row Y (0x403)**: (a) run after H1 (recommended: boot-free answer for bits 6/11 with 10);
  (b) skip.
- **D. Row LC (`land` with 0xc43, the timer running; stock passes on a stale bank)**: (a) run,
  own session, after H1 and H2; (b) run only if X reads X-HIGH (H-REBASE predicts LC-EARLY);
  (c) skip.
- **E. A build for what the module lacks**: (a) add `sb402` and a `land` variant that also writes
  V0/V2 to attributes 0/2 to the next build made for other reasons; (b) a build now for them;
  (c) neither.
- **F. Row T (tri first; a stray store into TA3DCtl predicted)**: (a) run, own session, last;
  (b) only if X reads X-REBASE or X-HIGH; (c) skip.
