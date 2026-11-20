# r40-n3e-b10

**NEEDS THE USER'S OK BEFORE RUNNING**, and the r40-kernel module built, installed and booted first
(below). The row writes our PDS image into the slack of the firmware's PDS
#14 page (crumb3: R4's, ST's and D0's write, byte for byte, below) and emits on a timer pass, as ST and D0.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 b8528c0ceb04 (branch r40-n3e, not
on main: r40-d0 merged, the 18-word list, the `land` image, the kit's arm words, the fork pin at
r40-kernel) and resgx545-data 9fce0b9934f2, laptop prefix `r40b10`, HostKeyAlias `cedar`. Question
Q128 (N3e): which bits of the emit's sideband start our emitted PDS program, and where an emitted
`douta` lands. Design: `closing29/n3e/design.md` (§3.2 the build, §3.3 row B10, §4 risks).
**Flagged** (user present, reset ready). Built offline, frozen, not staged, not run.

**Row B10, conditional. When it runs:** only if B2, B3 or B4 read RUN (H-DM falsified as needed).

**Module.** The r40-kernel module (fork r40-kernel 423b436e7f80, red r40-red 1be09fd22de0), not
built yet. `srcversion` in session.toml is the placeholder `UNBUILT-r40-kernel-423b436e7f80` (the
preflight refuses it): **the lead writes the built module's srcversion there after the boot and
freezes again** (delete FROZEN.*, PREDICTIONS.sha256, then `python3 kit/session.py freeze .`; the
tables and predictions do not change). Delivery: `closing29/kernel39c/deliver-cachix.sh` with
TIPB=r40-kernel REDB=r40-red. The fork's KUnit suite passes on the Mac shim at the tip (40 of 40;
red 34 of 40): `closing29/r40-n3e-logs/shim-r40-kernel.log`, `shim-r40-red.log`. Its own_arm arms a
blob only at the `form=` that names its emit word (`sgx_own_regs.h`'s `sgx_own_emit_forms[]`),
before anything is written.

**The arm.** `slots=0x1 entry=0 pds=crumb3 pdsat=fw14 form=sb800`. Image crumb3
(`asm/fwtask/pds/crumb3.s`), 3 rows, control word 0x01800100 (#14's own), as ST and D0. The blob's
emit word: 0xfb20b10000008184 (`emitpds.tasks.taske #0, r2, r3, r4, #0x800`, sideband 0x800).

Against B0 it changes one thing: the emit's sideband (0x800 instead of 0x843). The blob
`emitsb_sb800` is emitsb14d with only the emit word changed (resgx545 r40-n3e
`test_emitsb_form_is_emitsb14d_with_that_word_and_nothing_else`), so entry 1, U0 and the
firmware-page write are B0's and D0's survey is read as well.

## The firmware-page write: crumb3, ST's and D0's byte for byte

The kernel writes crumb3 at #14's buffer + 0x100 (19 dwords, [0x100, 0x14c)): U0, U1 0, U2 0, 0x000,
V0, V2, 0x200, 0x005a3305, four zero dwords, crumb's 7 instruction words; zeroes [0x68, 0x1000)
first; #14's own 0x68 bytes, PTE and flags untouched; the disarm reset rebuilds #14's bytes and
zeroes the slack. U0 = 0x080401ef (TRC 8, CBASE 15, index 0x4000 + 30: `emitsb_sb800`'s entry 1 is
emitsb14d's), as in ST and D0. V0/V2 are the kernel's (TA3DCtl dwords 0 and 2).

## Risk

As ST and S2: our emit with a listed sideband; a NEVER stops the tick and ends the session (rc 4);
every own-task emit stop so far was recovered by the kit's reset (7 of 7).

## Stage own: 1 job, flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) and in dwords
128-223 first, `"ticks": true`, timeout 200 ms, no kick (as ST and D0). Then the page, snap0/snap9,
the record, the gate after an ok end, the disarm.

## Outcomes (predictions/own.tsv, frozen; score/score.py)

The design's common table (ST's; T is 0x0acc in snap9 and the stop dump; no tick band):

| outcome | T | S1 (dw 84) | M4 (dw 80), state |
|---|---|---|---|
| B10-NEVER | running | fill | fill, 0 |
| B10-T1: started, stopped at a `douta` | 0x00000000 | fill | fill, 0 |
| B10-T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 |
| B10-T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 |
| B10-E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 |
| B10-DONE | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 |

RUN = any of T1..DONE. Frozen predictions for sideband 0x800: **H-DM NEVER**, **H-ALL NEVER**
(§3.2's columns). The RULE line names the outcome; one H-DM and one H-ALL line then say predicted,
read and held or FAILED (cannot tell when the rule cannot).

Controls (all can fail): PG, E0 (slot 1 = M1 + run id, cmd 0), T0, B (else FAULT, its own outcome).
Cannot tell as ST. X0 printed. Printed, never scored: D0's landing lines (the SURVEY lines, D0's
label HID/PA/SHIFT/STIR, P0 and P1), the LANDING line after DONE, the arm line, Δtick, alive, the
signature.

## Stage post: 2 jobs, flagged

As D0: after own's disarm, p1-tri and p2-fill on t30, `reads:diff` frozen at 0.

## Stops

A runner stop ends the session after reset and health (rc 4); a failed reset (rc 13 or 5) means the
user's ordinary reboot to the default entry. Any FAULT stops the ladder for the user. In DONE the
row ends ok and the kit runs the owntask gate: a failing gate is rc 16, reset and health, session
end, data kept.

## Deviations from the design (builder)

- One session per row (the lead's brief), not E1's four stages in one session: each row is the only
  owntask stage of its session, so a stop of one never hides another.
- srcversion is a placeholder until the r40-kernel module is built and booted (as r39-n3d-z).
- `land` keeps its markers and the douta controls in crumb3's dwords (3-6); T3's dword 7
- B rows print D0's landing reading but score only the start table (§3.3).

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`;
after: `python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
