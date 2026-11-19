# r38-n3c-s3

**NEEDS THE USER'S OK BEFORE RUNNING.** This row writes our PDS image into the slack of the
firmware's PDS #14 page (the exact write is below). The user has not yet approved R4/R6.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 94a7de5eaeb0 (branch
r38-rebuild, not on main; kit/ is that commit's blobs) and resgx545-data 5fa307500702, laptop
prefix `r38c`, HostKeyAlias `cedar`. Design: `closing29/n3c/design.md` (N3c, **session S3**:
§2.2 row R4 `M`; §3 risks; §4 items 2, 3, 5-7). **Flagged** (user present, reset ready). Built
offline, frozen, not staged, not run.

**Module.** The r38-kernel module (fork r38-kernel e1cf9d2b43ab, red r38-red 82b6c2082130), not built
yet. `srcversion` in session.toml is the placeholder `UNBUILT-r38-kernel-e1cf9d2b43ab` (the preflight
refuses it): **the lead writes the built module's srcversion there after the boot and freezes
again** (delete FROZEN.*, PREDICTIONS.sha256, then `python3 kit/session.py freeze .`; the tables
and predictions do not change). Delivery scripts: `closing29/kernel38/`.

**When.** After r38-n3c-s1 (R1 N0-OK, R2 V0-HOLDS) and the r38-kernel build and one-shot boot. Run S3 and S4 on the same boot, in either order.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14`. Image: crumb3 (`asm/fwtask/pds/crumb3.s`): crumb's 8 data dwords, four zero dwords (3 rows, as PDS #14), crumb's 7 instructions; control word `(3 << 23) | 0x100` = 0x01800100, #14's own; in the slack of the firmware's PDS #14 page (`pdsat=fw14`). Changes V2 (page, flags) and V3 (rows) at once; V4 and V5 stay.

## The firmware-page write (for the user's approval)

`pdsat=fw14`: at the arm (the firmware load the kit's arm does, before the firmware boot) the
kernel writes the **crumb3** image into PDS #14's page (buffer 5, the firmware's own page in
KERNEL_CODE, the same PTE and flags, read-write, as the #14 program the firmware emits on every
kick):

- **address** = #14's buffer address (page aligned, `sgx_fw_place`) + 0x100 (past #14's 0x68
  bytes and every PATCHES word in it, rounded up to 0x100: `sgx_own_fw14_off()`); `pds1` = that
  >> 4, and the arm's kernel log line prints it (`emit image 0x...100 ... pds=crumb3
  pdsat=fw14`).
- **bytes** = 19 dwords, 76 bytes, at [0x100, 0x14c) of the page: U0 0x080401ef (TRC 8, CBASE
  15, index 0x4000 + 30, emitsb's entry 1), U1 0, U2 0, 0x000, V0 (TA3DCtl dword 0), V2
  (TA3DCtl dword 2), 0x200, 0x005a3305, four zero dwords, then crumb's 7 instruction words
  (0x07001fe7 tim, 0x07040606 douta, 0x07042ca6 douta, 0x07003547 tim, 0x07000305 doutu,
  0x07003fe7 tim, 0xaf000000 halt). The emit's control word is 0x01800100 (3 rows).
- **cleared** = the rest of the page past #14's bytes, [0x68, 0x1000), is zeroed first (fresh
  zero pages at a load anyway).
- **untouched** = #14's own 0x68 bytes [0, 0x68) and its PTE and flags, every other firmware
  buffer, and the kernel's own image page (zeroed: no program there).
- **disarm** = the kit's reset at the stage's end rebuilds the firmware's buffers (which rewrites
  #14's 0x68 bytes only) and then zeroes [0x68, 0x1000) (`sgxfive_debug_reset`): no word of ours
  is left in the page (KUnit `fw14_disarm`).

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r37-n3b-b's binding).
- The own task: `owntask/emitsb.blob` (sha256 83c25ac3cfc0..., the map's `emitsb` at 94a7de5,
  r37-n3b-b's blob): X0 0x5a5a3303 at page dword 70 right after the emit, S1 0x5a5a3304 at
  dword 84 as entry 1's first work, then pa, sa, M4 0x5a5a3302 at dword 80, state 2.

## Stage own: 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) first,
`"ticks": true`, timeout 200 ms; then the page, snap0/snap9, the record, the gate after an ok end,
the disarm (its reset restarts `tim` and zeroes #14's slack).

## Outcomes (predictions/own.tsv, frozen; score/score.py)

T is 0x0acc in snap9 and in the stop dump (about 0.3 s apart; one read after an ok end):
`running` = bit 24 set, bits 23:0 <= 400000 and two reads differ; a constant = every read equal.

| outcome | T | S1 (dw 84) | M4 (dw 80), state | Δtick |
|---|---|---|---|---|
| M-NEVER: page, flags and rows are not the cause | running | fill | fill, 0 | 9-11 |
| M-T1: started, stopped at a `douta` | 0x00000000 | fill | fill, 0 | any |
| M-T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 | any |
| M-T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 | any |
| M-E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 | any |
| M-DONE: all ran | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 | any |

X0 (dword 70) is printed as a qualifier. Cannot tell (pre-declared): snap0's T not running
(control T0), T any other value, M-NEVER's Δtick outside 9-11, two unequal reads while not
running (no outcome holds). S1 set with T 0 or 0x200 is printed as its own reading (`S1-EARLY`).
T1 stops the tick by design: whenever T1 ran, the tick says nothing about what stopped it.

Controls (r37's, every row): PG page dword 0 = 0x4e574f53; E0 slot 1 = M1 and the run id,
cmd 0; T0 snap0's 0x0acc running; B BIF_FAULT 0 in snap9 (else FAULT, its own outcome). The
scorer also prints the arm's kernel log line (the address the emit names, pds=, pdsat=), Δtick,
alive, and E1148's signature; never scored.

## Stage post: 2 jobs, flagged

As r37-n3b-b: after own's disarm, p1-tri and p2-fill on t30, `reads:diff` frozen at 0. Runs only
after an ok end of own (M-DONE).

## Stops

As r37-n3b-b: a runner stop ends the session after reset and health (rc 4); a failed reset (rc
13 or 5) means the user's ordinary reboot to the default entry. In M-DONE the row ends ok, so the kit runs the owntask gate with the timer stopped (T3):
its outcome is not scored; a failing gate is rc 16, reset and health, session end, data kept.

## Deviations from the design (builder)

- Controls are r37's (PG, E0, T0, B); the arm's log line is printed, not a control (an arm that
  cannot place the image fails the load: the kit's arm is not ok, rc 26).
- crumb3 is 19 dwords (76 bytes), more than §3's "48-60 bytes" (which counted v1 and crumb).

## The mock's worlds and commands

As r37-n3b-b (mock/world.py, tests/, gen/ and score/ are the same files in r38-n3c-s3 to -s6,
STEP = "M", "H", "P" or "W"; the arm differs). Offline: `bash tests/run_all.sh`. Laptop:
`python3 kit/session.py stage .`, then `python3 kit/session.py run .`; after the run (or a stop):
`python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
