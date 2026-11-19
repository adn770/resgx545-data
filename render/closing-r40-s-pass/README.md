# r40-s-pass

**NEEDS THE USER'S OK BEFORE RUNNING.** The row writes our PDS image into the slack of the
firmware's PDS #14 page (R4's write, approved and run in r38-n3c-s3, r39-n3d-k and
r39-n3d-z; the exact write is below) and emits on a timer pass, as R4.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 c3f9f678ce18 (branch r40-s, not on main); kit/ is that commit's blobs, byte-equal to r39-n3d-z's) and resgx545-data 9fce0b9934f2,
laptop prefix `r40sp`, HostKeyAlias `cedar`. Question Q128: what made our own task's
emitted PDS program run (r39-n3d-z, 20261119-153429: Z-DONE). One of three sessions that
each change **one** thing against Z: r40-s-sb (`s2` 0), r40-s-s2 (our old word), r40-s-pass
(the timer pass). Design: `closing29/n3d/design.md` (§3 the common table, §3.2 rows Z and S,
§4 risks). **Flagged** (user present, reset ready). Built offline, frozen, not staged, not run.

**Module.** The one the laptop runs: srcversion 0CDFCDB73D76F39FE9E593C (r39-kernel, fork
f9453424bf71), Z's. No rebuild, no boot: its own_arm takes `pds2=0|req` and `form=own|fw14`
as independent words and arms an emitting blob only when `form=` names its emit word
(`sgxfive_owntask.c` at f9453424bf71: `emit && sgx_own_emit_form(b) != a->form` refuses);
its verifier accepts `emitsb14` unchanged (the fork's KUnit suite on the Mac shim with a
scratch copy of the test blobs header, OK_BLOBS plus emitsb14, 34 of 34:
`closing29/r40-s-logs/shim-emitsb14.log`, tree `closing29/r40-s-shim`).

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 pds2=req form=fw14`. Image: crumb3 (`asm/fwtask/pds/crumb3.s`), 3 rows, control word
0x01800100 (#14's own), in the slack of the firmware's PDS #14 page (`pdsat=fw14`), as R4 and Z.
The blob's emit word: 0xfb20b10800c08184 (`emitpds.tasks.taske #0, r2, r3, r4, #0x843`, Z's).

Against Z it changes one thing: the pass. The blob is `emitsb14` (resgx545 r40-s
c3f9f67: `emitsb` with #14's word and nothing else), which emits on the first pass that
sees cmd 1 (a timer tick, as R4's emitsb) instead of waiting for pa1 bit 8; the row has
no kick. Word, `s2` (`pds2=req form=fw14`), image, page, rows and control word stay
Z's. This is the design's row S (§3.2, S4) exactly.

## The firmware-page write (approved for R4; the same bytes as R4)

`pdsat=fw14`: at the arm the kernel writes the **crumb3** image at #14's buffer address + 0x100
(19 dwords, [0x100, 0x14c) of PDS #14's page: U0 0x080401ef (R4's, emitsb's entry 1: `emitsb14` keeps emitsb's entries),
U1 0, U2 0, 0x000, V0, V2, 0x200, 0x005a3305, four zero dwords, crumb's 7 instruction words),
zeroes [0x68, 0x1000) first, leaves #14's own 0x68 bytes, PTE and flags untouched; the kit's
disarm reset rebuilds #14's bytes and zeroes the slack (KUnit `fw14_disarm`).
Against Z's write only U0 differs (the doutu's entry 1 address, five words earlier): it
is R4's U0, the write approved and run in r38-n3c-s3.

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r37-n3b-b's binding).
- The own task: `owntask/emitsb14.blob` (the map's `emitsb14` at c3f9f678ce18):
  at cmd 1 (the first pass that sees it, a tick) M1 and the run id in slot 1, cmd 0, the
  fence, the emit,
  X0 0x5a5a3303 at page dword 70; entry 1: S1 0x5a5a3304 at dword 84, pa, sa, M4 0x5a5a3302
  at dword 80, state 2.

## Stage own: 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) first,
`"ticks": true`, timeout 200 ms, no kick (as R4's row): the runner polls; then the page,
snap0/snap9, the record, the gate after an ok end, the disarm (its reset restarts `tim` and
zeroes #14's slack).

## Outcomes (predictions/own.tsv, frozen; score/score.py)

T is 0x0acc in snap9 and in the stop dump (about 0.3 s apart; one read after an ok end):
`running` = bit 24 set, bits 23:0 <= 400000 and two reads differ; a constant = every read equal.
Z's table as refrozen: no tick band; Δtick (from the command write) is printed, not scored.

| outcome | T | S1 (dw 84) | M4 (dw 80), state | Δtick |
|---|---|---|---|---|
| SP-NEVER: with #14's word and `s2`, the kick pass is needed | running | fill | fill, 0 | any |
| SP-T1: started, stopped at a `douta` | 0x00000000 | fill | fill, 0 | any |
| SP-T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 | any |
| SP-T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 | any |
| SP-E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 | any |
| SP-DONE: all ran | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 | any |

Any of SP-T1..SP-DONE is **SP-RUN** (the kick pass is not needed: #14's word and `s2` suffice on a tick).

X0 (dword 70) is printed as a qualifier. Cannot tell (pre-declared): a control fails (E0; PG; T0; B is FAULT), T any other value, two unequal reads while not running (no
outcome holds). S1 set with T 0 or 0x200 is printed as its own reading (`S1-EARLY`). T1 stops
the tick by design: whenever T1 ran, the tick says nothing about what stopped it.

Controls (every row): PG page dword 0 = 0x4e574f53; **E0** slot 1 = M1 and the run id, cmd 0 (the gate fired: r37's E0); T0 snap0's 0x0acc running;
B BIF_FAULT 0 in snap9 (else FAULT, its own outcome). Printed, never scored: the arm's kernel
log line (the address the emit names, pds=, pdsat=, pds2=, form=), Δtick, alive, E1148's signature, and after an ok end the LANDING line (pa0-pa3, sa0-sa3
against TA3DCtl dwords 0-3; Z read pa0 = V0 no, pa2 = V2 no).

## Stage post: 2 jobs, flagged

As Z: after own's disarm, p1-tri and p2-fill on t30, `reads:diff` frozen at 0. Runs only
after an ok end of own (SP-DONE).

## Stops

As Z: a runner stop ends the session after reset and health (rc 4); a failed reset (rc 13 or
5) means the user's ordinary reboot to the default entry.
In SP-DONE the row ends ok, so the kit runs the owntask gate with the timer stopped (T3):
its outcome is not scored; a failing gate is rc 16, reset and health, session end, data kept.

## Deviations from Z (builder)

- New blob `emitsb14` (resgx545 r40-s c3f9f67, `gen_blobs.gen_emitsb14`, tests in
  `tools/fwtask/test_emitpds.py`), not in the fork's pinned KUnit list: the module's
  verifier accepts its words unchanged (the shim run above).
- No kick: the K0 control and the kick's printed lines go; K1 is named E0 (r37's).

## The mock's worlds and commands

As r39-n3d-z (mock/world.py, tests/, gen/ and score/ are the same files in r40-s-sb, r40-s-s2
and r40-s-pass, STEP = "SB", "S2" or "SP"; the blob and arm differ). Offline:
`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, then
`python3 kit/session.py run .`; after the run (or a stop): `python3 score/score.py own
out/ATT/own`, `python3 score/score.py post out/ATT/post`.
