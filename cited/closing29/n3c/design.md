# N3c: what in our emit stops the EDM (design note, not built, not run)

Status: a design for the lead to bring to the user as a **flagged decision**. Nothing here is
built, committed, staged or run. Tags: **[HW]** measured (a record or a kept file), **[post hoc]**
read from r37's kept files after the runs (not frozen), **[RE]** our own reading of the firmware
as the records give it, **[infer]** reasoning.

Paths: `A` = `closing29/r37-n3b-a/out/20261118-212949/own`, `B` =
`closing29/r37-n3b-b/out/20261118-213042/own` (under `/Users/jtorra/src/scratch/resgx545`),
`R` = `/Users/jtorra/src/resgx545` (main 7925c98), `F` = fork `/Volumes/linux/linux-sgx`
r37-kernel 4f35fc20ffa9, `drivers/gpu/drm/gma500/sgxfive/`. Module on the laptop:
77917296568EB311B89B0DA (`A/../../session.toml`).

## 0. What r37 A and B add (read from the kept files)

Both scorers, rerun by hand on the kept directories (`score/score.py own out/ATT/own`):

| | A (pds v1) | B (pds crumb) |
|---|---|---|
| frozen rule | A-PAST | B-1: the program never ran |
| X0 (page dword 70) | 0x5a5a3303 | 0x5a5a3303 |
| S1 (84), M4 (80), state | fill, fill, 0 | fill, fill, 0 |
| Δtick (`ticks`, window ~237 ms) | 10 | 10 |
| T = 0x0acc, snap9 / stop dump | 0x01017336 / 0x01038295 | 0x0101fc6d / 0x010585dc |
| `alive_at_stop` (`c1-a.txt`) | frozen at 2489 | frozen at 2091 |

Further, post hoc [HW, post hoc]:

- snap0 -> snap9 changed only 0x0008 (0x20 -> 0x000ccfa0), 0x0144, 0x0acc, 0x0b14 and HostCtl
  dword 12, in A and in B, as E1148. snap9 -> stop dump changed only 0x0144 and 0x0acc.
- The stop dumps read `EVENT_STATUS` 0x20000000 (the timer bit pending), `USE0_SERV_EVENT` bit 16
  set, `BIF_FAULT` 0, `BIF_INT_STAT` 0x80000, HostCtl dwords 3 and 8 = 0 and TA3DCtl dwords 56-58
  = 0: **not** the lockup path's marks (E849, `R/doc/specs/hw_spec.md:1030-1034`).
- The timer kept running and reloading after the stop in both (bit 24 set, 23:0 <= 400000, the
  two reads differ): the tick died with its timer alive.
- The arm wrote the image before the firmware boot (`B/kernel.log`: "own task armed ... emit
  image 0x30022000 ... pds=crumb", then "loaded", then "boot"; `F/sgxfive.c:218-225`): no stale
  cache line can hold the page.

What that says [infer]: the issuer goes on past the emit (X0, both); two programs whose first
instruction differs (`douta` in v1, `movs tim` in crumb) give the same stop at the same Δtick;
and, **if** a `movs tim` of an emitted program writes the host's 0x0acc, crumb's first
instruction never ran (B-1). The stop then lies between the issue and the program's first
instruction, and the tick dies about 9 passes after the emit, not at it.

## 1. Candidate variables, measured against inferred

**V0. The instrument: does an emitted `movs tim` write the host-visible 0x0acc?**
- Measured: a client PDS `movs tim` loads the counter that later PDS reads see, in every later
  job of any client, until a reset; bits 24-0 of the first word (`R/doc/isa/content/pds/probe/
  inputs.md:62-74`, `R/doc/specs/pds_isa.md:195-205`) [HW]. The name `EVENT_TIMER` = `tim` is
  the GPL DDK's [GPL].
- Not measured: a host read of 0x0acc after a PDS write. The probe made for it,
  `pds-timer-tim-host` (`R/probes/pds/timer.toml:6-14`), kept only its scratch stores
  (`resgx545-data/pds/timer/pds-timer-tim-host/raw.txt`: no register read). The crumb design
  already tags it [infer] (`closing29/n3b/design.md` §1.3).
- Supporting [RE]: no per-tick instruction of the closed handler writes 0x0acc (only boot, POWER
  and a 0 at 0x50a, `R/evidence/edm/E155-*.md:47-51`), so a T1 marker would not be masked by the
  next pass. And a stopped timer would have stopped the tick at once; B ticked ~9 more passes.
- B-1 rests on V0. Every crumb-based row below rests on it too.

**V1. The program (its instructions and data words).**
- Measured: v1 (`douta, douta, doutu, halt`, `R/asm/fwtask/pds/emit.s:24-27`) and crumb
  (`movs tim` first, `R/asm/fwtask/pds/crumb.s:24-30`) both stop at Δtick 10 with X0 [HW, §0].
- Inferred: under V0 no instruction ran, so instructions cannot be the cause; the data rows
  (U0 = TRC 8, index 0x4000 + e1, CBASE 15, `F/sgxfive_owntask.c:563-566`) are loaded, never
  executed. No instruction-free image (`halt` alone) has run [open].

**V2. Where the image is: address, page, flags, alignment.**
- Ours: 0x30022000 = KERNEL_CODE + 0x22000 (`F/sgxfive_owntask.h:53`), a page of its own mapped
  `SGX_MMU_RO` (`F/sgxfive_debug.c:83`), 4 KiB aligned; the kernel refuses an address not 16-byte
  aligned (`F/sgxfive_owntask.c:623`); `s1` = address >> 4 (`:678`).
- The firmware's: its PDS programs sit in KERNEL_CODE too, #13 at 0x30010000 with 6 rows
  (`0x0a68`/`0x0a6c` in every snap; `R/doc/specs/hw_spec.md:952-953`), every firmware buffer page
  aligned (`F/sgx_fw.c:799-833`, `sgx_fw_place`) and mapped with flags 0, read-write
  (`F/sgxfive.c:166-170`). Its emits name `ADDR_SHR4`, an absolute address >> 4
  (`R/doc/specs/fw_format.md:174, 198-206`) [RE]. So the address form and alignment are the
  firmware's; **the page and its flags are not**.
- A client emit names an offset from `PDS_EXEC_BASE` (E488: `s1` 4 ran the copy's program at
  heap base + 0x40, `R/doc/isa/content/usse/groups/emit.md:29-31`; pixel PDS pointers are
  relative, `R/doc/specs/render_uapi.md:158`). `PDS_EXEC_BASE` read 0x2e000000 at snap0 [HW]. A
  relative reading of an EDM emit would put the firmware's #14 in an unmapped page of the pixel
  PDS heap (`F/sgxfive_debug.c:66`: one page) and every render would fault; none does [infer]:
  the EDM's emit is absolute.
- A read of an `SGX_MMU_RO` page by the USSE works (our code page, `F/sgxfive_debug.c:77`) [HW];
  by the PDS, never measured. A fault in this path would show in `BIF_FAULT` (a write to a
  read-only alias did, E151) [HW]; none showed [HW, §0].

**V3. The control word: rows field and addend.**
- Ours: `(2 << 23) | 0x100` = 0x01000100 (`F/sgx_own_pds.h:20-21`). The firmware's: #14
  `(3 << 23) | 0x100` (3 rows, E146; `fw_format.md:205`), #12 `| 0x100`, #11 `| 0x1000` [RE].
  So our addend is #14's and #12's; **our rows field (2) is not #14's (3)**.
- Client emits: rows 1, 2 and 4 changed nothing seen of whether the program ran (one probe each);
  the addend matters (E520) [HW] (`emit.md:33-42`). From the EDM: one value only [HW].

**V4. The operand form and `s2`.**
- Ours: the exact word `emitpds.tasks.taske #0, r2, r3, r4, #0x0` = 0xfb20b00000008184, the
  firmware's three forms' flags (`emit.md:48-50, 60-61`; `kernel33/design.md:27-31`) [RE]; `s2`
  = 0. The firmware's #14 `s2` is not in our records; its request word reaches `ir0` by an
  operand we only infer (E146 "The start of #14", `R/evidence/edm/E146-*.md:69-76`). Client
  `s2` of 0, 1, 0xFFFFFFFF, 0xE17D0001 changed nothing seen (E488) [HW]. Low prior.

**V5. The issuing context and what follows the emit.**
- Ours: a timer pass of the slot 0 general task; after the emit X0, `idf`/`wdf`, then the tail
  call into the closed task (`R/asm/fwtask/emitsb.s:34-42`).
- The firmware's #14: also a slot 0 pass, but a kick pass; before the emit it waits for
  `MADD_CACHE_INVALCOMPLETE` and writes bit 26 to `EVENT_HOST_CLEAR` (E1130, sim, [RE, infer]),
  ORs the request into TA3DCtl dword 31 and skips the emit when nothing changed (E146) [RE]. What
  it does after the emit is not in our records. #11 and #12 are emitted by the boot task [RE].
- Not separable from V2-V4 by any row that keeps our task; see §2 rule M-NEVER.

**V6. The stop's clock: a firmware pass count or a hardware time?**
- Δtick 10 in both [HW]; the firmware's hardware-recovery sample runs every HostCtl dword 5
  passes, 10 (`F/sgxfive.c:499`), and its lockup path came after exactly 2 x dword 5 passes
  (E849, E856: the same count at a 2 ms tick) [HW]. Our stops left no lockup marks [post hoc].
- Not a cause of the emit's failure, but it says whether the tick dies at the firmware's own
  periodic check of an emitted program that never started, or at a hardware timeout.

## 2. Rows, cheapest first, with frozen predictions

Readings, as r37: page dwords X0 = 70, S1 = 84, M4 = 80-81, state = 2 (the results page, or the
stop dump's); T = 0x0acc in snap9 and in the stop dump (`running` = bit 24 set, 23:0 <= 400000,
the reads differ); Δtick = the record's `ticks`; `alive` = `alive_at_stop.advancing`. Controls in
every owntask row, as r37: PG (page dword 0 = 0x4e574f53), E0 (slot 1 = M1, run id, cmd 0), T0
(snap0's T running), B (`BIF_FAULT` 0 in snap9; else FAULT, its own outcome). Rule: every
control passes and exactly one outcome holds; else CANNOT TELL. One owntask row per stage, `#limit
0`, `on_stop = "end"`.

### 2.1 No module rebuild, no boot (module 77917296, arm words as today)

**Session S1, stage `own`: R1 `n0`, the same task without the emit** (new blob `emitsn`; arm
`slots=0x1 entry=0`). `emitsb` with the three `pds` limms and the `emitpds` removed: entry 0
stores M1, run id, cmd 0, fence, X0, fence, then done's sequence (M4 + run id in slot 4, echo,
state 2) and the tail call. One entry. Separates "the emit" from "our cmd-1 path".

| outcome | X0 | M4, state | Δtick | gate |
|---|---|---|---|---|
| N0-OK (expected): the stop needs the emit | 0x5a5a3303 | M4 + run id, 2 | >= 25 | ok |
| N0-STOP: our path stops the tick without any emit | any | any | < 25 or no done | - |

**Session S1, stage `tim` (last): R2 `th`, the instrument** (no owntask; stock firmware; t30
`probe --pds 4 --use USE` with the recorded `pds-timer-tim-host` program and harness,
`resgx545-data/pds/timer/pds-timer-tim-host/bins/`, wrapped by `regtimeline` sampling 0x0acc, the
tool bound by r33-tim2, `closing29/r33-tim2/session.toml:29-33`). The program loads `tim` with
0x00abcde0 (bit 24 clear; bits 23:0 above any running count) and stores `tim` back to scratch.

| outcome | 0x0acc in the timeline after the change, and in snap9 | scratch `tim` |
|---|---|---|
| V0-HOLDS (expected): host sees the PDS write | 0x00abcde0, every sample, constant | 0x00abcde0 |
| V0-NOT: a PDS `tim` is not the host's 0x0acc | running throughout | 0x00abcde0 |
| CANNOT TELL: scratch not 0x00abcde0 (the program did not run), or another constant | | |

Controls: the timeline's interval (E1133's bounds), samples before the change running. V0-NOT
voids B-1's reading (and every crumb row below reads by S1 only).

**Session S2 (optional, V6): R3 `dose`, A's job at a 2 ms tick** (blob `emitsb`, arm
`slots=0x1 entry=0`, v1 image; debugfs `timer_clock` = 800000 (0x000c3500), present at the fork,
`F/sgxfive_debug.c:2316`, copied at the boot the arm does, E856). Needs a kit change only (W3).

| outcome | X0 | Δtick | arm rate |
|---|---|---|---|
| D-COUNT: the tick dies at a pass count after the emit | 0x5a5a3303 | 9-11 | 485-499 Hz |
| D-TIME: a fixed ~10 ms after the emit | 0x5a5a3303 | 4-6 | 485-499 Hz |

Any other Δtick, or the arm rate outside E856's band: CANNOT TELL.

### 2.2 One module build and one one-shot boot, then one session per row

One fork change gives two orthogonal arm words (W6-W7): `pds=v1|crumb|halt|crumb3` and
`pdsat=own|fw14`. `halt`: v1's 8 data dwords, then `halt` alone, control 0x01000100. `crumb3`:
crumb's 8 data dwords plus 4 zero dwords (3 rows; the bank map keeps every operand crumb names),
then crumb's 7 instructions, control `(3 << 23) | 0x100` = 0x01800100, #14's own word.
`pdsat=fw14`: the image is written in the firmware's PDS #14 buffer page, past its 104-byte
image at the next 0x100 (same PTE and flags as a program the firmware emits on every kick), and
`s1` names it. The blob is `emitsb` in every row.

**Session S3: R4 `M`, the firmware's #14 mirror** (`pds=crumb3 pdsat=fw14`). Changes V2 (page,
flags) and V3 (rows) at once; V4 and V5 stay.

| outcome | T | S1 | M4, state | Δtick |
|---|---|---|---|---|
| M-NEVER: page, flags and rows are not the cause | running | fill | fill, 0 | 9-11 |
| M-T1: started, stopped at a `douta` | 0x00000000 | fill | fill, 0 | any |
| M-T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 | any |
| M-T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 | any |
| M-E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 | any |
| M-DONE: all ran | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 | any |

Expected [infer]: none preferred; this is the binary split. After V0-NOT the T column is not
read: M-NEVER = S1 fill, the program reached its `doutu` = S1 set.

**Session S4: R5 `H`, the program floor** (`pds=halt`, own page, 2 rows). No instruction but
`halt`, no `doutu`: the job never ends with done, so the runner always stops it (rc 4); the
reading is the tick.

| outcome | `alive` | Δtick |
|---|---|---|
| H-STOP (expected after V0-HOLDS): any program, no instruction needed | false | 9-11 |
| H-ALIVE: the stop needs an instruction of v1/crumb | true | >= 150 |

H-ALIVE with V0-HOLDS contradicts B-1 (record both, re-open the instrument). After V0-NOT run
S4 before S3: it is then the only instrument-free answer.

**Conditional (same build, one session each):**

- After M-T1 .. M-DONE: R6 `P` (`pds=crumb pdsat=fw14`, rows 2 in the firmware's page). P runs:
  the page or its flags; P never (crumb's B outcome): the rows field, confirmed by R7 `W`
  (`pds=crumb3`, own page): W runs. Same table as M.
- After M-NEVER: the cause is in V4/V5 (our `s2`, or emitting from a timer pass of our task).
  Not designed here: the next step is a user decision between emitting the firmware's own #13
  (whose general-task start is our entry 0, E146) or #14 from our task, and a kick-pass emit.
  Both are riskier than anything above (a stock task started out of its protocol); a fwsim
  facts-only read of what the stock kick pass does after its #14 emit (O1) comes first.

### 2.3 What needs what

| row | session | new blob | kit change | module rebuild + boot |
|---|---|---|---|---|
| R1 n0 | S1 | `emitsn` | no | no |
| R2 th | S1 | no (t30, regtimeline, recorded bins) | session files only | no |
| R3 dose | S2 | no | owntask stage knob (W3) | no |
| R4 M, R5 H, R6 P, R7 W | S3-S6 | no | arm words (W3) | **yes, one for all** |

## 3. Risk and recovery

Every owntask stop so far was recovered by the kit's debugfs reset: E1148, r37 A, r37 B (3 of
3 emit stops), and 13 of 13 recorded EDM stops (`hw_spec.md:1024-1026`). A runner stop ends the
session after reset and health (rc 4); a failed reset (rc 13 or 5) means the user's ordinary
reboot to the default entry.

- **R1**: low. No emit; stores, fences and a tail call as the owntask blobs of 11.29-11.33. If it
  stops, the session ends as A did.
- **R2**: a planned stop of the EDM tick until the reset (a stopped timer: no more timer
  events). The client job itself completes, as the recorded `pds-timer-*` probes did (`diff: 0`
  before and after, `resgx545-data/pds/timer/env.toml`); the reset restarts the counter
  (`inputs.md:64-67`) [HW]. Last row of S1: the kit's health after it fails by design, ending
  the session. Flagged.
- **R3**: as A (one stop, reset). The knob must be back at its default before the kit's last
  reset, since the firmware copies it at boot (W3; E856's exit trap did the same).
- **R4, R6**: the kernel writes 48-60 bytes into the slack of the firmware's #14 page at the arm.
  The firmware never reads past its 104-byte image [RE: E146's sizes]; no render runs in an
  owntask stage, so #14 is not emitted by the firmware during the row [infer]. The page is
  read-write for the EDM, but no task of ours can store there (verifier base analysis) and the
  firmware has no address for it. The disarm's reload must leave no word of ours in the page
  (tested, W6). If T1 runs, the tick stops by design (B's approved image); if the `doutu` runs,
  entry 1 is verified code.
- **R5, R7**: as A and B.
- **Within the rules.** No clock-gate write (no image stores; blobs keep the verifier's lists,
  `R/tools/fwtask/regs.toml`); no `trc_hazard` (no `trc=` word); no GRUB edit beyond the existing
  one-shot boot (`closing29/kernel33/deliver-laptop.sh:17-20`) and only with the user's OK, for
  the one build of §2.2; every owntask stage `class = "flagged"`; one row per stopping stage,
  `#limit 0`, `on_stop = "end"`: one stop ends a session.
- **Main risk**: R4/R6 put our words in a firmware page (new); and any row could leave a state
  the reset does not clear (never seen).

## 4. Work list (tests first, red then green, as r33)

**resgx545** (branch off main 7925c98):

1. `tools/fwtask/gen_blobs.py`: `gen_emitsn()` and the map entry. Tests beside
   `tools/fwtask/test_emitpds.py`: no `emitpds` word and no `pds` patch; X0 0x5a5a3303 at
   res+280 after the fence; then M4 at res+320, the run id, echo, state 2, before the tail call;
   one entry; `fwtask.refusal(...) is None`; lint clean.
2. `asm/fwtask/pds/halt.s`, `asm/fwtask/pds/crumb3.s`; `tools/fwtask/gen_verify.py` renders each
   image with its own rows and control word into `sgx_own_pds.h`. Tests: pds-dis reads halt as 8
   data dwords then `halt`; crumb3 as 12 data dwords (crumb's 8, four zeros) then crumb's 7
   instructions, operands unchanged; controls 0x01000100 (v1, crumb, halt) and 0x01800100
   (crumb3); v1 and crumb byte for byte as at 7925c98.
3. Kit (`tools/closing/kit/session.py:160-164, 661-706`, `run_stage.sh:113`): the arm accepts
   `pds=(crumb|halt|crumb3)` and `pdsat=fw14`; an owntask stage may declare `knobs` (only
   `timer_clock`, from `[knobs]`) written before the arm and restored before the last reset.
   Tests in `tools/closing/test_kit.py`: accepted and refused words, the fake laptop's order
   (knob, arm, job, restore, reset), a refused knob on a row.
4. Session R2: no kit change expected (a `probe` row with `--pds`, files under `[files]`,
   `regtimeline` declared `wraps`); its argv twin test and a scorer test on E1133's kept
   timelines (running) and a fabricated constant one.
5. HACKING's own-task section: the words and images.

**Linux fork** (off r37-kernel 4f35fc20ffa9; red branch, then green):

6. KUnit (`sgxfive_owntask_test.c`): parse `pds=halt|crumb3`, `pdsat=own|fw14` (others refused;
   `pdsat` without an emitting blob refused at apply); `sgx_own_pds_build` per image; `pds0` =
   the image's control word; fw14: address = #14's + round_up(#14 size, 0x100), 16-aligned,
   image inside the page and past every #14 PATCHES offset, #14's own bytes unchanged; the
   disarm reload leaves the slack zero; `own_arm` shows both words; the arm log names the
   address and image.
7. Code: `sgxfive_owntask.[ch]` (images table with rows and control, placement), the apply's
   `pds0` value (`:678`), `sgxfive_debug.c` (arm, show, log). Offline on the Mac with
   `closing29/kernel33/kunit-shim/run.sh`, red then green; the verifier accepts `emitsn`.

**Offline, no laptop:**

- O1: fwsim (E1130's setup), facts only: the stock kick pass's instructions right after its #14
  emit (a wait, a different pass end, a register touched). Traces stay in data-private; only
  facts reach a spec (the FW trace separation rule). Feeds the M-NEVER decision.

**Sessions** (`tools/closing/new_session.py`, flagged, user present): S1 (R1, then R2), S2 (R3,
optional), build and boot, S3 (R4), S4 (R5), S5/S6 (R6, R7, conditional).

**Laptop time**: S1 about 15 min, S2 about 10 min, no build. The build: module red check, series
check and build about 45 min unattended (r33: 11 + 14 + 16 min), install, one-shot boot and
srcversion checks about 15 min (a new module needs the boot: it is in the initramfs). S3 and S4
about 10 min each; R6/R7 10 min each if needed. In all about 1 h 45 to 2 h 05, about 1 h
attended.

## 5. Alternatives rejected

- **Vary the control word, address or `s2` from a blob** (no rebuild): the verifier pins r2-r4
  to the kernel's values on every path to the emit (`F/sgxfive_owntask.c:265-270`); loosening
  it is a verifier change (a rebuild anyway) and lets a task name any address.
- **A `movs tim; halt` image** (the user's example): crumb's first instruction is exactly that,
  and B ran it (T running). Redundant once R2 holds; `halt` (R5) is the instrument-free floor.
- **The image in the pixel PDS heap, addressed as a client emit** (E488's form): the firmware's
  EDM emits are absolute (§1 V2); a session to refute that buys nothing for this question.
- **Emitting the firmware's own #13 or #14 now**: the strongest "regardless of program" test, but
  it starts a stock task outside its protocol (E146: #14's third task on an empty request). Kept
  as the decision after M-NEVER, after O1.
- **A kernel knob for HostCtl dword 5** (the recovery sample rate): sharper than R3 for V6, but a
  rebuild; `timer_clock` exists today and E856 already used it on the same question shape.
- **Register reads by the issuer after the emit** (`EVENT_STATUS`, USE state into the page): not
  on the `ldr` list (`R/tools/fwtask/regs.toml`), so a kernel change, and the host snapshots
  already show the frozen state.
- **fwsim for the stop itself**: sgx-sim starts an emitted program at once and has no PDS stall
  (`R/doc/roadmap.md:575-576`, E1133's fwsim note); it would read DONE.
- **PDS stores, `doutd` markers, `tim` with bit 24 set, a third data row in crumb as v1's
  variant**: as `closing29/n3b/design.md` §5.
- **Several emit rows in one session**: every emit row so far stopped, and a stop ends the
  session.
- **An `SGX_MMU_RO`-off own page as its own word now** (V2's flag alone): kept for after M runs;
  R6 (P) splits page from rows first, and if P runs a flag-only word needs a second build. If the
  fork diff stays small, the builder may add `pdsmap=rw` to this build to save that boot
  (flagged: the image page would be writable by the EDM).
