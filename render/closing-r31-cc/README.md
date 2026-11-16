# r31-cc

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 2ffa9a93727d (data dc838e60f4bb), module srcversion
7CE8E38EDB97FC5EA4F6C90 (N1, booted), laptop prefix `r31c`. **Safe class**: no knob, no kreg, no
register write, no planned fault or hang; regtimeline only reads. Nothing assumes cachix. Record
reserved: **E1122** (provisional: r31-kreg2 is built in parallel and names none yet; the lead
settles it).

## Why

Firmware-in-sim (main 2ffa9a9) stops at the microkernel's read of CR_CACHE_CTRL right after the
kick of a TA command, before its own write: does that read already return 0x1000ffff? E1120
(r30-evst2) read 0x0000ffff after the kit's reset and one change to 0x1000ffff before every
sampled event of a plain triangle, held to the next reset, with bit 26 of CR_EVENT_STATUS 19.6
to 106.6 us later. Two readings:

- **H-CC-FW**: the change is the firmware's own write. The kick pass tests the command's cache
  control: bits 0 and 1 call a BIF routine, bit 3 writes CR_CACHE_CTRL | 0x10000000 (E013's
  dataflow, doc/specs/edm_dataflow.md, COMMAND+0x004 and 0x0804); every job kick of our kernel
  carries bit 3 (INVAL_DATA; a triangle 0xb, a fill 0x8 with the BIF bits its mapping adds). The
  read then returns 0x0000ffff after a reset, and the sim answers it with the reset word.
- **H-CC-HW**: the hardware sets bit 28 at the kick, before any firmware response. The read
  then returns 0x1000ffff.

Already known, post hoc from the kit's kept snapshots (no timeline): a plain fill after a reset
(a transfer kick, no TA) also leaves 0x1000ffff (r8-k2 and r9-faults `xf-c-fill`, r30-pde
`s0-pfill`, r14-bif `refill`, r13-flag `f3-fill-a`), so a set that only the TA kick makes is
unlikely [infer]; c5 holds it out.

## What runs

Every row: t10 (`~/sgxfive-test-t10`, sha256 9bedc2d6..., source a581c06) under regtimeline
(`rt`, sha256 079f6359..., read only), `1.5 0.5 REGS -- "$HOME/sgxfive-test-t10" ...`, after the
kit's reset. In run order:

| stage | rows | REGS | job | what it reads |
|---|---|---|---|---|
| c1 | 10 (2 controls, 8 held) | 0x0804 | `tri --width 64 --height 64` | the change alone, densest |
| c2 | 12 (2, 10) | 0x0804, 0x0b14 | as c1 | the change against the served count |
| c3 | 12 (2, 10) | 0x0804, 0x0c00 | as c1 | the change against CR_BIF_CTRL |
| c4 | 10 (2, 8) | 0x012c, 0x0804, 0x0a74, 0x0b14, 0x0c00 | as c1 | the kick's whole order |
| c5 | 8 (2, 6) | 0x012c, 0x0804, 0x0b14, 0x0c00 | `fill` (64 x 32) | a transfer kick |

52 jobs. Every register is one E258's register timelines read (tests check it), and 0x0b14,
which every kit snapshot reads (E009, E1120). Time: r30-evst2's 41 jobs took about 7 to 8
minutes, so about 9 to 10 minutes of jobs, 12 to 15 with staging [infer]. Alarms 900 s a stage.

## Hypotheses (frozen: predictions/*.tsv from gen/make.py; every row held out)

The anchor is the first sample with CR_CACHE_CTRL changed (`cct`); times are read at the sample
interval (about 0.5 us alone, 0.8 with two registers, 1.8 with five) [infer from E1120, E1121].

- Every stage: **H-CC-ONE** (one change, 0x0000ffff to 0x1000ffff, held to the end; E1120 24 of
  24). c1-c4: **H-CC-LAT** (the change 10 to 40 ms after the tool starts; E1120 18.6 to 25.1).
- c2, c4, c5: **H-CNT-LAG** (no CR_USE0_SERV_EVENT count in the 30 us before the change, the next
  count 0 to 12 us after it; E1120 post hoc: 0 in 21 rows, 5.0 to 7.3 us in 11 of 12) against
  **H-CNT-LEAD** (a count in the 30 us before it). A row where a tick the lead's cadence predicts
  may fall in a window (within 15 us) cannot tell.
- c3, c4, c5: **H-BIF-FIRST** (a CR_BIF_CTRL word other than its first shows in the 30 us before
  the change) against **H-BIF-LATER** (only in the 15 us after it). Stage: **H-BIF-HIDDEN** (no
  row decides; E258 never saw 0x0c00 move at about 15 us a sample) against **H-BIF-VISIBLE**.
- c4: **H-CCFIRST** (the change before every CR_EVENT_STATUS event), **H-CC-26** (bit 26 15 to
  120 us after the change where it precedes the render end), **H-DMS** (CR_DMS_CTRL written 20 to
  70 us after it; E1120 e3 31.1 to 48.6), **H-WAIT** (after bit 26's first rise) against
  **H-NOWAIT** [infer: the firmware waits for the invalidation before the TA path], **H-IDLE**.
- c5: **H-CC-XFER** (a fill changes it as a triangle does) against **H-CC-TA** (no change);
  H-CNT-*, H-BIF-*, H-CCFIRST on a fill.

Controls (first and last row of each stage), all can fail: diff 0, the sample interval in the
stage's window, and the first sample's words as the kit's `snap0.regs` reads them after the reset
(r30-evst2 e2-c1, pinned): cache 0x0000ffff, idle 0x20000000, se16 1, bif0 0, dms0 0x00208200.

## What decides H-CC-FW against H-CC-HW

- **H-BIF-FIRST held** in the decided rows: a firmware response (the BIF calls the cache control
  bits 0 and 1 make) precedes the change, so the read after the kick still sees 0x0000ffff:
  **H-CC-HW refuted** (the sim's read answers the reset word, its write gives 0x1000ffff).
  **H-BIF-LATER held**: the change precedes the firmware's first visible write: H-CC-FW refuted.
  [infer] Two cautions: the gma500 host code writes BIF_CTRL bit 3 too when it flushes its own
  MMU (`mmu.c`), so a "pre" word is read beside the job's dmesg and timing before it is taken as
  the firmware's; and the firmware's BIF write may be shorter than a sample (E258 never saw one).
- **H-BIF-HIDDEN held** (likely): the session cannot decide H-CC-FW against H-CC-HW. It still
  narrows: the change's place against the served count (c2) at about 0.8 us, the whole order
  (c4), and H-CC-TA (c5). Which way H-CNT-LAG points depends on when CR_USE0_SERV_EVENT counts
  (E009: bit 16 EMPTY, bits 15:0 COUNT): counted at the task's start, a change 5 to 7 us before
  the count would precede the kick pass (H-CC-HW); counted at its end, it fits H-CC-FW. That is
  not measured [infer], so H-CNT-* narrows only.

**The decisive form no existing tool has**: a kick that carries no INVAL_DATA, sampled after a
reset. Our kernel sends one: the debugfs `miscinfo` read is a GETMISCINFO command with the
pending cache control, which after a reset is the boot's 0x2 (INVAL_BIF_PD: the fork's boot sets
it from the firmware file's meta word 30, sgxfive.c; doc/specs/boot_sequence.md; no bit 3). H-CC-FW predicts 0x0804 stays 0x0000ffff through that
served kick; H-CC-HW (any kick) predicts 0x1000ffff. The kit cannot run it: rows run declared
tools only and debugfs reads are the preflight's existence checks. The narrowest change: a kit
row word (say `pre:miscinfo`) that reads debugfs `miscinfo` once after the reset and the knobs,
before `snap0` (no timeline needed: snap0 then reads 0x0804 after a served kick without bit 3;
the triangle after it is the positive control). Safe class (the kernel's own arm path sends
GETMISCINFO, E768), one stage of about 10 rows. A tooling agent adds it to the kit with a test.

**Cannot decide**: when CR_USE0_SERV_EVENT counts; whether a BIF write shorter than a sample
happened; what the hardware does with bit 28 after the write.

## Stops

hook_check (rc 24): a row that does not draw exactly or lacks `tri: 1 renders ok` (c5: `fill:
ok`), a missing or cut timeline, regtimeline's rc not 0, and where 0x0b14 is sampled a tick stop
(bit 16 clear in the last sample, or under half a count a ms). Every stage declares `on_stop =
"end"`: a stop ends the session. A control without its reading: 25. Any fault or hang: 4.
`#limit 0` everywhere.

## Mock worlds

`model` (every stage 0), `nodiff` (c1 stops), `notl` (c1 stops), `tickstop` (c1 runs, c2 stops),
`nofillok` (c1 to c4 run, c5 stops). The kit's fake prints samples 1 us apart with start 0 end 0,
so the mock checks the flow and the hooks (its controls fail on ivl 0, as r30-evst2's did); the
scorer is tested on E1120's kept rows and on synthetic timelines.

## Replay vectors

No vectors table (closing_tables.py has no timeline kind): c1 to c5 refused as tables. The fold
changes sgx-sim's hw.rs and tools/fwsim/seeds.toml only from what the frozen rows decide: with
H-BIF-FIRST held, the CR_CACHE_CTRL read after a kick, before the run's write, answers the reset
word (cite E1122) and the write's value after it; otherwise the refusal stays and names E1122's
order. Test first, on the kept `.txt` files.

## Commands

- Offline: `bash tests/run_all.sh`. Regenerate: `python3 gen/make.py` (`--check` in the tests).
- Freeze: `python3 kit/session.py freeze .` (done). Laptop: `python3 kit/session.py stage .`,
  then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE out/ATT/STAGE`; one job: `python3 score/score.py file
  NAME.txt`.

No firmware-derived file: nothing here goes to data-private. Python is the repo's own `.venv`;
every command is run through its interpreter.
