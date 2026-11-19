# r39-n3d-z

**NEEDS THE USER'S OK BEFORE RUNNING.** The row writes our PDS image into the slack of the
firmware's PDS #14 page (R4's write, approved and run in r38-n3c-s3; the exact write is below)
and emits from inside a host-command pass (GETMISCINFO), the design's main risk.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 7d1aa9e531e0 (branch r39-n3d, not
on main; kit/ is that commit's blobs) and resgx545-data 9fce0b9934f2, laptop prefix `r39z`,
HostKeyAlias `cedar`. Design: `closing29/n3d/design.md` (N3d, **session S3**: row Z;
§3 the common table; §4 risks and work list). **Flagged** (user present, reset ready). Built
offline, frozen, not staged, not run.

**Module.** The r39-kernel module (fork r39-kernel f9453424bf71, red r39-red e0ab1778fb4e), not built yet. `srcversion`
in session.toml is the placeholder `UNBUILT-r39-kernel-f9453424bf71` (the preflight refuses it): **the
lead writes the built module's srcversion there after the boot and freezes again** (delete
FROZEN.*, PREDICTIONS.sha256, then `python3 kit/session.py freeze .`; the tables and
predictions do not change). Delivery: `closing29/kernel39c/` (cachix, another agent).

**When.** First frozen as conditional on r39-n3d-k reading K-NEVER. K (20261119-152848) read
CANNOT TELL: its readings were K-NEVER's but the tick stopped 7 from the kick, outside the 8-11
band carried over from R4. Refrozen 2026-11-19 at the user's choice, before Z ran: Z-NEVER reads
T and S1 alone, Δtick is printed, not scored. K stays CANNOT TELL.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 pds2=req form=fw14`. Image: crumb3 (`asm/fwtask/pds/crumb3.s`), 3 rows, control word
0x01800100 (#14's own), in the slack of the firmware's PDS #14 page (`pdsat=fw14`), as R4.
The blob's emit word: 0xfb20b10800c08184 (`emitpds.tasks.taske #0, r2, r3, r4, #0x843`: ours with the 14-bit sideband 0x843 of #12's and #14's emit, N3d O1; every other field equal).
`pds2=req` makes the kernel write 0x00020000 (the request #14's emit carries in `s2`, N3d
O2a; E1130) into the blob's `pds2` limm, so the emit's `s2` is it (ours was 0).
`form=fw14` is the arm word that lets the kernel take the second emit word: the arm refuses
a blob holding it without `form=fw14`, and `form=fw14` without it.
Against K it changes the emit's sideband and `s2`; the pass (the kick), the image, its
page, rows and control word stay.

## The firmware-page write (approved for R4; the same bytes)

`pdsat=fw14`: at the arm the kernel writes the **crumb3** image at #14's buffer address + 0x100
(19 dwords, [0x100, 0x14c) of PDS #14's page: U0 0x0804023f (TRC 8, CBASE 15, index 0x4000 +
35, emitsk14's entry 1: five words later than emitsb's, R4's U0 0x080401ef), U1 0, U2 0, 0x000,
V0, V2, 0x200, 0x005a3305, four zero dwords, crumb's 7 instruction words), zeroes [0x68,
0x1000) first, leaves #14's own 0x68
bytes, PTE and flags untouched; the kit's disarm reset rebuilds #14's bytes and zeroes the
slack (KUnit `fw14_disarm`).

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r37-n3b-b's binding).
- The own task: `owntask/emitsk14.blob` (the map's `emitsk14` at 7d1aa9e531e0): at cmd 1 it reads
  pa1 and emits only when bit 8 is set (a kick pass), else tail-calls with cmd 1 kept; on the
  kick pass M1 and the run id in slot 1, cmd 0, the fence, the emit, X0 0x5a5a3303 at page
  dword 70; entry 1: S1 0x5a5a3304 at dword 84, pa, sa, M4 0x5a5a3302 at dword 80, state 2.

## Stage own: 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) first,
`"ticks": true`, `"kick": "miscinfo"`, timeout 200 ms (counted from the kick). Right after
the command write the runner records K0 (HostCtl dword 12, cmd, slot 1), then reads debugfs
`miscinfo` once (a GETMISCINFO kick; the kernel gives up at 500 ms: its reply or error is kept
and printed, never scored), then polls; then the page, snap0/snap9, the record, the gate after
an ok end, the disarm (its reset restarts `tim` and zeroes #14's slack).

## Outcomes (predictions/own.tsv, frozen; score/score.py)

T is 0x0acc in snap9 and in the stop dump (about 0.3 s apart; one read after an ok end):
`running` = bit 24 set, bits 23:0 <= 400000 and two reads differ; a constant = every read equal.
Δtick from the kick = the record's `ticks_from_kick` (HostCtl dword 12 from K0 to 30 ms after
the window).

| outcome | T | S1 (dw 84) | M4 (dw 80), state | Δtick from the kick |
|---|---|---|---|---|
| Z-NEVER: the word, `s2`, the pass, page, rows and control are not it: V5b/c (§3.3) | running | fill | fill, 0 | any |
| Z-T1: started, stopped at a `douta` | 0x00000000 | fill | fill, 0 | any |
| Z-T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 | any |
| Z-T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 | any |
| Z-E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 | any |
| Z-DONE: all ran | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 | any |

Any of Z-T1..Z-DONE is **Z-RUN** (`s2` or the form decides, alone or with the kick pass: run S).

X0 (dword 70) is printed as a qualifier. Cannot tell (pre-declared): a control fails (K0: no
kick pass seen apart, or a tick emitted; K1; PG; T0; B is FAULT), T any other value,
two unequal reads while not running (no outcome holds). S1
set with T 0 or 0x200 is printed as its own reading (`S1-EARLY`). T1 stops the tick by design:
whenever T1 ran, the tick says nothing about what stopped it.

Controls (every row): PG page dword 0 = 0x4e574f53; **K0** the record's k0: cmd 1 and slot 1
dword 0 the fill right before the kick (the ticks did not emit); **K1** slot 1 = M1 and the
run id, cmd 0 (the gate fired: r37's E0); T0 snap0's 0x0acc running; B BIF_FAULT 0 in snap9
(else FAULT, its own outcome). Printed, never scored: the arm's kernel log line (the address
the emit names, pds=, pdsat=, pds2=, form=), the miscinfo
reply, the ticks between the command write and K0, Δtick from the command write, alive, and
E1148's signature.

## Stage post: 2 jobs, flagged

As r38-n3c-s3: after own's disarm, p1-tri and p2-fill on t30, `reads:diff` frozen at 0. Runs
only after an ok end of own (Z-DONE).

## Stops

As r38-n3c-s3: a runner stop ends the session after reset and health (rc 4); a failed reset
(rc 13 or 5) means the user's ordinary reboot to the default entry. An unanswered GETMISCINFO
stays in the kernel CCB until the reset rebuilds it [infer]. In Z-DONE the row ends ok, so the kit runs the owntask gate with the timer stopped (T3):
its outcome is not scored; a failing gate is rc 16, reset and health, session end, data kept.

## Deviations from the design (builder)

- The kick gate's mask is a limm in r8 (`and.testtanz` of two registers): the alu-test form
  has no encoding for the immediate 0x100 (design §4 item 1 named `#0x100`).
- K1 is r37's E0 (slot 1 = M1 and the run id, cmd 0), named as the design's K1.
- The NEVER band was first the design's §3 common table's, 8-11, counted from the kick (R4 froze
  9-11 from the command write); dropped at the refreeze of 2026-11-19 (see When).
- The timeout (200 ms) is counted from the kick's end, so a slow miscinfo reply does not eat
  the window.
- The second emit word is a blob of its own (`emitsk14`, `gen_blobs` variant), as the
  design's §3.2 says; the kernel takes it only with `form=fw14`.

## The mock's worlds and commands

As r38-n3c-s3 (mock/world.py, tests/, gen/ and score/ are the same files in r39-n3d-k and
r39-n3d-z, STEP = "K" or "Z"; the blob and arm differ). Offline: `bash tests/run_all.sh`.
Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`; after the run
(or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
