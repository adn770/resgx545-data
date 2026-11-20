# r40-n3e-l

**NEEDS THE USER'S OK BEFORE RUNNING**, and the r40-kernel module built, installed and booted first
(below). The row writes our PDS image into the slack of the firmware's PDS
#14 page (a **new** image, `land`: its exact bytes are below and need the user's approval before the run) and emits on a timer pass, as ST and D0.

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 b8528c0ceb04 (branch r40-n3e, not
on main: r40-d0 merged, the 18-word list, the `land` image, the kit's arm words, the fork pin at
r40-kernel) and resgx545-data 9fce0b9934f2, laptop prefix `r40l`, HostKeyAlias `cedar`. Question
Q128 (N3e): which bits of the emit's sideband start our emitted PDS program, and where an emitted
`douta` lands. Design: `closing29/n3e/design.md` (§3.2 the build, §3.3 row L, §4 risks). **Flagged**
(user present, reset ready). Built offline, frozen, not staged, not run.

**Row L, E1, 2nd. When it runs:** after B0-DONE (n3e §3.3 row L, the user's decision C (a));
L-NEVER: no other image in this build.

**Module.** The r40-kernel module (fork r40-kernel 423b436e7f80, red r40-red 1be09fd22de0), not
built yet. `srcversion` in session.toml is the placeholder `UNBUILT-r40-kernel-423b436e7f80` (the
preflight refuses it): **the lead writes the built module's srcversion there after the boot and
freezes again** (delete FROZEN.*, PREDICTIONS.sha256, then `python3 kit/session.py freeze .`; the
tables and predictions do not change). Delivery: `closing29/kernel39c/deliver-cachix.sh` with
TIPB=r40-kernel REDB=r40-red. The fork's KUnit suite passes on the Mac shim at the tip (40 of 40;
red 34 of 40): `closing29/r40-n3e-logs/shim-r40-kernel.log`, `shim-r40-red.log`. Its own_arm arms a
blob only at the `form=` that names its emit word (`sgx_own_regs.h`'s `sgx_own_emit_forms[]`),
before anything is written.

**The arm.** `slots=0x1 entry=0 pds=land pdsat=fw14 form=fw14`. Image `land`
(`asm/fwtask/pds/land.s`): crumb3's 3 rows and control word 0x01800100 (#14's), two `douta` of
constant markers Ma 0x5a5a3a18 to secondary attribute 24 and Mb 0x5a5a3a1a to 26, the `doutu`,
`halt`, no `tim`; the kernel fills U0 only. The blob's emit word: 0xfb20b10800c08184
(`emitpds.tasks.taske #0, r2, r3, r4, #0x843`, sideband 0x843).

Against B0 it changes one thing: the image (`pds=land` instead of crumb3). Blob (emitsb14d, so D0's
pre/post survey), word, place, rows, control word and pass are B0's.

## The firmware-page write: `land`, new bytes (**the user approves them before the run**)

At the arm the kernel zeroes [0x68, 0x1000) of PDS #14's page, leaves #14's own 0x68 bytes, PTE and
flags untouched, and writes these 16 dwords at #14's buffer address + 0x100, i.e. [0x100, 0x140) of
the page (the emit names that address: 0x30011100 on the laptop, D0's arm line); the kit's disarm
reset rebuilds #14's bytes and zeroes the slack again:

| offset | dword | what |
|---|---|---|
| 0x100 | 0x080401ef | U0 (doutu: TRC 8, CBASE 15, index 0x4000 + entry 1) |
| 0x104 | 0x00000000 | U1 0 |
| 0x108 | 0x00000000 | U2 0 |
| 0x10c | 0x00001800 | ds1[1]: douta control, attribute 24 |
| 0x110 | 0x5a5a3a18 | ds0[2]: Ma (the marker to sa24) |
| 0x114 | 0x5a5a3a1a | ds0[3]: Mb (the marker to sa26) |
| 0x118 | 0x00001a00 | ds1[2]: douta control, attribute 26 |
| 0x11c | 0x00000000 | ds1[3]: 0 (crumb3's T3, unused) |
| 0x120 | 0x00000000 | ds0[4]: third row, 0 |
| 0x124 | 0x00000000 | ds0[5]: 0 |
| 0x128 | 0x00000000 | ds1[4]: 0 |
| 0x12c | 0x00000000 | ds1[5]: 0 |
| 0x130 | 0x07040606 | movs douta, ds0[2], ds1[1], ds0[2], ds0[2] (Ma to sa24) |
| 0x134 | 0x07042ca6 | movs douta, ds0[3], ds1[2], ds0[3], ds0[3] (Mb to sa26) |
| 0x138 | 0x07000305 | movs doutu, ds0[0], ds0[1], ds1[0], ds0[0] (start entry 1) |
| 0x13c | 0xaf000000 | halt |

U0 = 0x080401ef: TRC 8, CBASE 15, index 0x4000 + 30 (emitsb14d's entry 1, as ST's, D0's and R4's).
The emit's s0 (control) is 0x01800100, s1 the address >> 4, s2 0. The two `douta` also **write EDM
secondary attributes 24 and 26** (Ma, Mb), which stay set for every later EDM pass until the disarm
reset; D0 read sa24-sa31 zero and unchanged across an emit, and no firmware instruction reads them
(§1.2).

## Risk

New: the `land` image's two `douta` write markers into EDM secondary attributes 24 and 26, which
stay set for every later EDM pass until the disarm reset; no firmware instruction reads sa20, sa21
or sa23-sa31 (`doc/specs/edm_dataflow.md`), and D0 read sa24-sa31 zero and unchanged across an emit.
No `tim` in the image: the EDM tick is not stopped by us.

## Stage own: 1 job, flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) and in dwords
128-223 first, `"ticks": true`, timeout 200 ms, no kick (as ST and D0). Then the page, snap0/snap9,
the record, the gate after an ok end, the disarm.

## Outcomes (predictions/own.tsv, frozen; score/score.py)

`land` has no `tim`, so T (0x0acc in snap9 and the stop dump) runs in every outcome; the start table
is S1 and M4 alone, DONE split by one derived quantity `lland` (score.py `lland_of`; pre = page
dwords 128-159, post sa = 160-191, post pa = 192-207):

| outcome | T | S1 (dw 84) | M4, state | lland | prediction |
|---|---|---|---|---|---|
| L-NEVER | running | fill | fill, 0 | | failed (`land` did not reach entry 1: CANNOT TELL) |
| L-E1 | running | 0x5a5a3304 | fill, 0 | | (start; CANNOT TELL for the landing) |
| L-SA | running | 0x5a5a3304 | M4 + run id, 2 | post sa24 = Ma, sa26 = Mb, pre not | **held** |
| L-SHIFT | as SA | | | Ma at sa j, Mb at sa j+2, j != 24 | failed |
| L-PA | as SA | | | Ma and Mb in pa0-15, no sa pair | failed |
| L-ONE | as SA | | | only one marker found | failed |
| L-NONE | as SA | | | neither marker found | failed |

A DONE whose markers none of the five names (a pair with a marker already there before the emit, or
one marker in sa and the other in pa) is CANNOT TELL. Without `tim`, L-NEVER cannot tell a program
that never started from one that stopped before entry 1.

Controls (all can fail): PG, E0 (slot 1 = M1 + run id, cmd 0), T0, B (else FAULT), and D0's P0 (no
0xdeadc0de left in 128-159) and P1 (pre sa0-sa3 = V0-V3). Printed, never scored: **L-TICK** (T and
Δtick after a DONE with no `tim`: if the tick still counts, the DONE rows' tick stops were crumb3's
`tim` markers alone [HW then]), LAND-L (pre/post sa24/sa26, where each marker was found), D0's
SURVEY lines, the arm line, alive, the signature.

RULE: `Q128-L RULE: L-<landing>` when every control passed and one landing holds; a start outcome
short of DONE is CANNOT TELL for the landing; FAULT as ST.

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
- `land` keeps its markers and the douta controls in crumb3's dwords (3-6); T3's dword 7 is 0.

## Offline and laptop

`bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, `python3 kit/session.py run .`;
after: `python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
