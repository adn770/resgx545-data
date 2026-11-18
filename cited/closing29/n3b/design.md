# N3b: breadcrumbs that split E1148's three causes (design note, not built, not run)

Status: a design for the lead to bring to the user as a **flagged decision**. Nothing here is
built, committed, staged or run. Tags: **[HW]** measured (a record or a kept file), **[post hoc]**
read from E1148's kept files after its run (not frozen), **[infer]** reasoning, **[RE]** our own
reading of the firmware as the records give it.

Paths: `S` = `/Users/jtorra/src/scratch/resgx545/closing29/r36-n3`,
`O` = `S/out/20261118-152130/own`,
`F` = `/Volumes/linux/linux-sgx-r33/drivers/gpu/drm/gma500/sgxfive` (r33-kernel, c78059370315),
`R` = `/Users/jtorra/src/resgx545` (main e39dafb).

## 0. What E1148 left open, and what its kept files add

Measured [HW] (E1148, `R/evidence/edm/E1148-*.md`; `O/e1-a.own_res.json.gz`):
entry 0 ran (slot 1 = 0x5a5a3301, run id 1, cmd 0), slots 2-4 kept 0xdeadc0de, state 0, echo 0,
no done in 200 ms; the arm logged `emit image 0x30022000` (`O/kernel.log`); reset recovered.

Read post hoc from the same files (new here, not in E1148's text) [post hoc]:

- snap0 -> snap9 changed only `0x0008`, `0x0144`, `0x0acc`, `0x0b14` and HostCtl dword 12
  (`diff` of `O/e1-a.snap0.regs.gz` and `O/e1-a.snap9.regs.gz`). `0x0b0c`-`0x0b2c` (the other USE
  service registers, `0x0b20` = 0x00010000) did not move.
- `CR_CLKGATESTATUS` 0x20 -> 0x000ccfa0: the "busy" signature every recorded stop shows
  (`R/doc/specs/hw_spec.md:1022-1026`).
- But `USE0_SERV_EVENT` froze at 0x000109a8 **with bit 16 set** (queue empty). The 13 recorded
  stops read bit 16 *clear* (`hw_spec.md:1022-1024`); bit 16 set with 0x000ccfa0 was seen only
  while the EDM still served (E834, `hw_spec.md:1072-1075`). So E1148's stop is not the known
  "a pass that never reached the closed exit" kind [infer, one job].
- `USE0_SERV_EVENT` count minus HostCtl dword 12: 4 at the arm (`O/owntask.arm.json.gz`
  `alive`: 208-204, 237-233, 265-261), 5 at snap0 (1948-1943, after one GETMISCINFO kick), 5 at the
  freeze (2472-2467). The last served event before the freeze advanced both [infer]: the emitting
  pass seems to have finished the closed tick handler, and no event was served after it.
- The freeze came 524 ticks after snap0 (kernel mark 4528.109) and the runner's own mark was
  4528.524 (`R/tools/fwtask/fwtask_run.py:123-138` writes it at the start of `run`), so the tick
  stopped within about 0-110 ms of the command write [infer: snap0's read time is not logged].

Reading [infer]: the issuer probably got past the `emitpds`; something downstream (the PDS or
the event dispatch) stopped delivering events. That makes "the emitted program wedged the PDS
before or at its `doutu`" a live candidate beside causes (1)-(3). Nothing above decides it.

## 1. The proposed change

Two steps. **Step A** needs no new module and no boot; **step B** is the one whose single run
separates (1), (2) and (3), and needs one module build and one one-shot boot.

### 1.1 Blob `emitsb` (both steps; resgx545 only)

`emitsa` (`R/asm/fwtask/emitsa.s:9-71`, from `R/tools/fwtask/gen_blobs.py:551-600`) plus two
stores, each followed by `idf drc0, bif; wdf drc0` as the existing ones:

- **X0** in entry 0, right after `emitpds` (`emitsa.s:37`), before `br @tail` (`emitsa.s:38`):
  `mov r7, #0x5a5a3303; stad [r9,+#2], r7` (slot 1 dword 2 = page dword 70; r9 still holds
  res+272, `emitsa.s:24`). Shows the issuing EDM task continued past the emit.
- **S1** as entry 1's first work (before `emitsa.s:41`): `mov r9, #res+336; mov r7, #0x5a5a3304;
  stad [r9,+#0], r7` (slot 5 dword 0 = page dword 84). Today the first store is the 7th
  instruction of entry 1, after four `pa` reads (`emitsa.s:41-47`).

The verifier accepts both as written [infer, to be checked by a test]: `EMITPDS` changes no
tracked base (`R/tools/fwtask/fwtask.py:433-447`), so r9 stays the results page; X0's path leads
to the tail call, not back to the emit (`fwtask.py:401-406`); S1's base is a `res` patch. The
kernel's U0 follows entry 1's new index by itself (`F/sgxfive_owntask.c:556-559, 686-687`).

### 1.2 Runner: `"ticks": true` (both steps; kit only)

`one_cmd` already reads HostCtl dword 12 right before the command write and 30 ms after the
window when a job carries `ticks` (`R/tools/fwtask/fwtask_run.py:271-307`, passed at `:341`),
and the record is kept even on a stop (`:340-355`). The kit refuses the key today
(`R/tools/closing/kit/session.py:162`, `:686-706`). Allow `ticks` (a bool) and pass it through:
Δtick = ticks from the command write to the window's end.

### 1.3 Kernel: a second PDS image, `pds=crumb` (step B; fork + resgx545)

The current image is `douta, douta, doutu, halt` with 2 data rows and dword 7 unused
(`R/asm/fwtask/pds/emit.s:15-27`, `F/sgx_own_pds.h:22-35`). The crumb image keeps the same data
rows, the same control word 0x01000100 (`sgx_own_pds.h:19`), the same address rule and the same
U0/V0/V2 fills (`F/sgxfive_owntask.c:561-577`), and adds three `movs tim` breadcrumbs:

```
dword 7 = 0x005a3305                                   ; was 0 (unused)
movs tim,   ds1[1], ds1[1], ds1[1], ds1[1]   ; T1: tim <- 0x000      (the program started)
movs douta, ds0[2], ds1[1], ds0[2], ds0[2]   ; V0 to attribute 0     (as today)
movs douta, ds0[3], ds1[2], ds0[3], ds0[3]   ; V2 to attribute 2     (as today)
movs tim,   ds1[2], ds1[2], ds1[2], ds1[2]   ; T2: tim <- 0x200      (past both douta)
movs doutu, ds0[0], ds0[1], ds1[0], ds0[0]   ; start entry 1         (as today)
movs tim,   ds1[3], ds1[3], ds1[3], ds1[3]   ; T3: tim <- 0x005a3305 (past the doutu)
halt
```

Why `tim`: it is the only PDS output the host can read without a task. `tim` is
`CR_EVENT_TIMER` (0x0acc) (`R/doc/specs/pds_isa.md:195-205`), which the kernel's regs file and
every kept snap already hold. A `movs tim` keeps its first word's bits 24-0 (`pds_isa.md:268`);
**with bit 24 clear the value stays put, unchanged until a GPU reset, and the in-place reset
restarts the counter** [HW] (`R/doc/isa/content/pds/probe/inputs.md:62-72`). All three marker
words have bit 24 clear, so none is a running count (the hazard of Q057 is an *enabled* count
reaching 0, `inputs.md:72-74`). A running timer always reads bit 24 set with bits 23:0 at most
400000 (`hw_spec.md:966-984`). Reading 0x0acc back from the host after a PDS write is [infer]
(the PDS probes read it back through the PDS); the control in §1.5 catches a miss.

The image is chosen at the arm: own_arm gains `pds=v1|crumb` (default `v1`, today's image), so
the same module also keeps E1148's image (for a later landing run without the tick cost).

### 1.4 Prediction table (pre-declared)

Readings, all from files the kit keeps: the page (`own_res.json` or `stop0-own_res.json`),
`snap9.regs` and `stop0-regs.txt` (`fwtask_run.py:310-323`), the record's `ticks`.

- X0 = page dword 70; S1 = dword 84; M4 = dwords 80-81 and state (dword 2) = 2.
- T = 0x0acc in snap9 and in the stop dump (two reads ~0.3 s apart, E1148's spacing).

**Step A** (module C01FB320 as installed, `pds` v1 implied, blob `emitsb`, one row):

| outcome | X0 | S1 | M4, state | Δtick |
|---|---|---|---|---|
| A-ISSUER: the emit stops or ends the issuing task | 0xdeadc0de | fill | fill, 0 | 0-2 |
| A-PAST: issuer on; no entry-1 store: (1), (2), early (3) | 0x5a5a3303 | fill | fill, 0 | any |
| A-E1: (3) entry 1 stopped after its first store | 0x5a5a3303 | 0x5a5a3304 | fill, 0 | any |
| A-DONE: E1148 not reproduced | 0x5a5a3303 | 0x5a5a3304 | M4, 2 | >= 150 |

Expected from §0 [infer]: A-PAST with Δtick 0-2.

**Step B** (new module, `pds=crumb`, blob `emitsb`, one row): T decides the PDS side, S1/M4 the
task side, X0 the issuer.

| cause | T (both reads equal unless running) | S1 | M4, state |
|---|---|---|---|
| (1) the program never ran | running: bit 24 set, 23:0 <= 400000, reads differ | fill | fill, 0 |
| (1') started, stopped at a `douta` | 0x00000000 | fill | fill, 0 |
| (2a) stopped at the `doutu` (never issued) | 0x00000200 | fill | fill, 0 |
| (2b) `doutu` issued, our code never stored | 0x005a3305 | fill | fill, 0 |
| (3) entry 1 started, stopped after its first store | 0x005a3305 | 0x5a5a3304 | fill, 0 |
| none: all ran | 0x005a3305 | 0x5a5a3304 | M4, 2 |

X0 is read in every row as a qualifier (0x5a5a3303: the issuer went on). Pre-declared as
**cannot tell**: snap0's T not running (the timer was already stopped); T any other value; the two
post-stop reads of T unequal while T is not running; S1 set with T 0 or 0x200 (that would say a
`doutu` blocks the PDS until its task ends [infer, not expected]: recorded as its own reading).

Residual (stated, not separable by any store): entry 1 dying within its first three instructions
(two limm `mov` and the store) reads as (2b).

### 1.5 Controls (every row; all can fail)

E0: slot 1 dwords 0-1 = 0x5a5a3301 and the run id, cmd 0 (as N3). T0: snap0's 0x0acc running.
PG: page dword 0 = 0x4e574f53 (the page is ours and was read). B: `BIF_FAULT` 0 in snap9 (a fault
is its own outcome, kept, not one of the above).

## 2. The tick and the `douta` landing

- **Step A says something about the tick:** Δtick dates the stop against the command (0-2:
  the emit pass; larger: later), X0 says whether the issuer got past the emit, and the stop's
  `USE0_SERV_EVENT` bit 16 and count-minus-tick replicate or not §0's unusual signature. It does
  not name the mechanism.
- **Step B says nothing about what stopped the tick whenever T1 ran:** T1 stops the timer by
  design, so the tick stops then whatever else happened. Only in the (1) row (T running) are the
  tick readings clean, and then they read as in step A. Say so in the record.
- **The landing:** only in the "none: all ran" row (step B) or A-DONE, where entry 1 still
  stores pa0-pa3 and sa0-sa3 (`emitsa.s:43-59`): one exploratory row, not N3's rule (>= 6 of 8
  held out, `S/README.md`). In every other row: nothing about where `douta` lands.

## 3. Risk and recovery

- **What can hang** [infer]: the EDM as in E1148 (no event served); the PDS, if the image
  wedges it; entry 1, if it runs wild (it is verified code on a read-only page, design §2.3 of
  `closing29/kernel33/design.md`). In step B the tick stops by design at T1.
- **Recovery**: the kit's debugfs reset, measured on this path (E1148: reset, then t30 fill and
  triangle exact) and on 13 of 13 recorded EDM stops (`hw_spec.md:1024-1026`); the reset also
  restarts a `tim` left stopped (`inputs.md:64-67`). A runner stop (rc 4) ends the session after
  reset and health (`R/tools/closing/kit/run_stage.sh:409`); `#limit 0`, no retry. If a reset
  ever fails (rc 13 or 5), the user's ordinary reboot to the default entry.
- **A known side effect** (step B, "none: all ran"): the row ends ok, so the kit runs the
  owntask gate with the timer stopped (`run_stage.sh:354-363`). Its outcome is not scored; a
  failing gate means rc 16, reset and health, session end, data kept.
- **Within the rules.** No clock-gate write: the blob has no `str` at all and the verifier
  refuses clock-gate registers (`F/sgxfive_owntask.h:99`); the image has no store, `doutd` or
  load (`tim` is `EVENT_TIMER`, not a clock-gate register; but it *is* the tick's timer, which is
  why this is flagged for the user). No `trc_hazard`: the arm keeps the stock TRC and the started
  task's TRC stays 8 (`F/sgxfive_owntask.h:55`). No GRUB edit: step A needs no boot; step B uses
  the existing one-shot boot (`closing29/kernel33/deliver-laptop.sh:17-20`) only with the user's
  OK. Clean room: every word is our source (`emit.s`, `emitsa.s`); no closed binary is opened.
- **What the user is asked to approve** (step B): a second kernel PDS image that, beyond the
  approved `douta, douta, doutu, halt` (`kernel33/design.md` §1-2), writes `tim` three times with
  stopped values, a planned stop of the EDM tick until the next reset.

## 4. Work list

Tests first in every commit pair (red, then green), as r33 (`kernel33/design.md` §7).

**resgx545** (branch off main e39dafb):

1. `gen_blobs.py`: `gen_emitsb()` and the map entry. Tests (`R/tools/fwtask/test_emitpds.py`,
   beside `:185-191`): one emit, pds0-pds2, two entries; X0 is the first store after the emit
   and stores 0x5a5a3303 at res+280; entry 1's first store is 0x5a5a3304 at res+336, before any
   `pa`/`sa` read; `fwtask.refusal(...) is None`; lint clean.
2. `asm/fwtask/pds/crumb.s` and `gen_verify.py` rendering both images into `sgx_own_pds.h`
   (`R/tools/fwtask/gen_verify.py:235-284`: a second array, its own `WORDS`). Tests beside
   `test_emitpds.py:144-182`: pds-dis of the crumb image reads exactly the 8 data dwords, then
   `tim, douta, douta, tim, doutu, tim, halt`; the three `tim` take dwords 3, 6, 7; every `tim`
   source has bit 24 clear; dword 7 = 0x005a3305; rows and control word unchanged; v1 unchanged.
3. Kit: `OWNTASK_JOB_KEYS` gains `ticks` (bool only), passed to the job (`session.py:162,
   686-706`); `OWNTASK_ARM` (`session.py:159-160`) and `run_stage.sh:113` accept ` pds=crumb`.
   Tests in `R/tools/closing/test_kit.py`: a ticks row prepares to a job with `"ticks": true`, a
   non-bool is refused, `pds=crumb` is accepted, `pds=other` refused.
4. HACKING's own-task section: the `pds=` word, the crumb image's markers.

**Linux fork** (off r33-kernel c78059370315; red branch first, then green; generated header from
step 2):

5. KUnit (`F/sgxfive_owntask_test.c`): `sgx_own_arm_parse` takes `pds=v1|crumb` (default v1,
   `pds=2` and `pds=` refused) beside `:528-545`; `sgx_own_pds_build` with the crumb image
   (beside `:595-640`): U0, V0, V2 filled as v1, dword 7 = 0x005a3305, the instruction words the
   header's, zeros after; `sgx_own_apply` builds the image the arm names; `own_arm` shows
   `pds=crumb`.
6. Code: `struct sgx_own_arm` gains the image choice (`F/sgxfive_owntask.h:112-120`), the parse
   (`F/sgxfive_owntask.c:496-546`), `sgx_own_pds_build` takes it (`:561-577`, `:684-690`), the arm
   log line names it (`F/sgxfive_debug.c:2207-2209`), `own_arm` show (`sgxfive_debug.c:2124-2150`).
   Offline: the kunit-shim on the Mac (`closing29/kernel33/kunit-shim/run.sh`), red then green.

**Sessions** (each built with `tools/closing/new_session.py`, flagged, user present):

- r3x-n3b-a (step A, module C01FB320, no boot): stage `own` = `{ alarm = 600, class =
  "flagged", on_stop = "end", owntask = { blob = "emitsb", arm = "slots=0x1 entry=0" } }`, then
  `post` (t30 tri, fill) as r36-n3. Before staging: the kernel verifier at c78059370315 accepts
  `emitsb` through the kunit-shim (no laptop).
- r3x-n3b-b (step B, new module): the same with `arm = "slots=0x1 entry=0 pds=crumb"`.

Stage table rows (`tables/own.txt`, both steps; `F16` stands for sixteen 3735929054
(0xdeadc0de), written out in the table, covering slots 2-5):

```
#stage own
#limit 0
c1-a|fit|flagged|-|owntask|{"cmd": 1, "params": {"72": [F16]}, "timeout_ms": 200, "ticks": true}
```

One row only: a stop ends the session (rc 4), and in step B a stopped timer makes any second row
meaningless. Hooks: the row's page checks as r36-n3 (`S/run/hooks.sh`) plus a stop reason
"one row by design" after an ok end; the scorer prints the §1.4 row by the frozen table.

**Laptop time** (estimates from r33's `kernel33/deliver/status` and E1148's log):

- Step A: about 10 min attended (stage, preflight, one row, post), no build, no boot.
- Step B: module red check, series check and build on the laptop about 45 min unattended
  (r33: 11 + 14 + 16 min); install, one-shot boot and post-boot srcversion checks about 15 min;
  the session about 10 min. A new module **does** need the boot (the module is in the initramfs).

Step B alone separates (1), (2), (3); step A first is cheap, keeps the tick question clean, and
if it reads A-E1 or A-DONE it settles the case without the boot.

## 5. Alternatives rejected

- **PDS `store` breadcrumbs into memory**: a PDS store reaches only the first 1 MiB of its
  address space (`pds_isa.md:594-597`), nothing of ours is mapped there in the EDM's context, and
  stores totalling 2-4 dwords fault (`pds_isa.md:604-609`). A new low mapping in the EDM directory
  is a larger and riskier change than three `tim` words.
- **`tim` with bit 24 set** (distinct periods, keeping the tick): counts toward 0 and reload are
  not measured for other values, and an enabled count reaching 0 hung jobs (Q057).
- **V0/V2 as the `tim` words** (no new data dword): their bit 24 depends on where TA3DCtl lands;
  a set bit would arm a running count.
- **A third data row for marker constants**: changes the `emitpds` control word (rows field), a
  second variable against E1148.
- **`doutd` from an unmapped page as a fault marker**: a planned fault, and the approved design
  excludes `doutd` (`kernel33/design.md` §2.2).
- **Rows varying U1 or TRC**: each needs a live EDM after a stop (none: a stop ends the session)
  and none splits (1) from (2).
- **A register timeline during the job**: owntask rows take only `-` or `reads:K`
  (`run_stage.sh:141`); a larger kit change for what `ticks` and the stop dump already give.
- **Replacing the v1 image instead of `pds=`**: a smaller kernel diff, kept as the fallback; it
  costs a further boot to measure the landing with the v1 image later.
- **Reading `pa`/`sa` from entry 0 after the emit**: the `douta` values equal `sa0`/`sa2`'s own
  (design §1), so nothing would show.
