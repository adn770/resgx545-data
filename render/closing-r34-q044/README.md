# r34-q044 (round 34: Q044, CR_REG_0400 bits 11:0 and bit 25 over the pack modes)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 5745c8dc1a8d (kit/ is that commit's blobs) and
resgx545-data 8e59b150be5f. Plan: `closing29/plan/rank-round34.md` section 3.2, R34-1 (a), and
R34-4 (a) as the lead took it overnight (Q044 may retire though mode 14 faults and 22, 34 do not
repeat: 14 named from E031, 22 and 34 split to Q012 if undecided). **SAFE** class: no planned
fault, no hang, no knob, no kreg, `#limit 0` everywhere; mode 14 never runs. Records E1135 (p1 +
pw: bit 25) and E1136 (p2: the low byte and bits 11:8). Laptop prefix `r34p`. Module
7CE8E38EDB97FC5EA4F6C90; travel cable (`host_key_alias = "cedar"`). Built offline, not staged,
not run.

## Tool (none is built)

- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06 (sha256 23e1fa76...),
  recipe `data:render/closing-r10-st1/lead/build_tool10.sh`: every row and the health pair. The
  render command's word 11 is `pixelbe` (include/uapi/sgxfive_drm.h at a581c06; render.c builds
  0x80), the word that loads CR_REG_0400 (E251, E268); the fork passes it through unchecked
  (sgx_render.c `rd[SGX_RENDER_RD_PIXELBE / 4] = c->pixelbe`).

## What runs: 198 jobs, about 45 minutes (55 at most)

| # | stage | jobs | form | what | gate |
|---|---|---|---|---|---|
| 1 | s0 | 7 | colour, ramp | the controls: E268 mode 0 at 0x80, bit 25, bit 11; E031 mode 4; E385 mode 4 at 0x80 and bit 25, mode 8 at bit 25 | none; a stop ends the session |
| 2 | p1 | 118 | colour | bit 25 in modes 4-11, 15-63 (not 14): reference 0x80 then 0x02000080; 22, 26, 34 a second reference | s0 |
| 3 | p2 | 68 | ramp | mode 4 at nine low bytes equal to ramp alphas; modes 5-8 at 0x00, 0x40, 0xc0, 0xff, 0xf80; 1, 2, 9, 10, 11 at 0x40, 0xc0, 0xf80; 3, 15, 20, 24, 26, 27 at 0xf80 | s0 |
| 4 | pw | 5 | colour | bit 25 in modes 12 and 13 (they write past the target, E031) | s0 |

Forms (both kept programs, bins/ is the published bytes): **colour** is E031's and E268's (o0 =
0x80ff8040 over the background 0xff203040, `eot_plain`); **ramp** is E385's (pds_iter_xy, alpha
= bits 23:16 of x + 0.5 as a single, 47 alpha values on the triangle's columns 8 to 54,
`vtx_coords`, `--vtx-coords 2`). Each stage's first row is a control (a kept image). Every row
reads all 4096 dwords. Time: E031/E385's probes took under 2 s; with the kit's reset, snapshots
and health about 13 s a job.

## Hypotheses (frozen in predictions/, gen/q044.py)

Readings are taken against a reference row of THIS stage (r30-evst's and r33-tim's lesson): `xor`
is the one value every dword the mode's 0x80 reference wrote differs by in the row (its sentinel
dwords unchanged), "mixed" for several; for 22, 26, 34 (p1) and 26 (p2) only over the dwords the
two references repeat. Kept images are frozen only for the controls and as H-E031, the p1
references' replicate model.

- p1/pw, bit 25: **H-INV25** (it inverts the mode's alpha field, E031's classes: 0xff000000 in the
  41 ARGB8888-like modes and in 9, 10, 12, 13; 0x80008000 mode 4; 0xf000f000 mode 5; 0xff00ff00
  modes 6 and 7; nothing in 8 (E385) and in the modes without alpha 15, 18, 20, 24, 25, 26, 27, 28)
  against **H-SUBSET** (it acts only in 0-2, 4, 5). Held out: every mode but 4, 5, 8 (fit, E385).
  References: **H-E031** (E031's kept image, a replicate on 7CE8E38E); 26's second reference
  **H-REPEAT** (all 4096 equal). 22 and 34: read, no model (Q012's formats).
- p2, the low byte: mode 4 `thr` (largest alpha stored clear, smallest stored set) **H-GE** (alpha
  >= the low byte sets the bit; fit: E031's mode 4 at 0x80 with alpha 0x80 stores 1, E385's
  background at 0xff with alpha 0xff stores 1) against **H-GT** (>), held out at 0x02, 0x08,
  0x3e, 0x42, 0x78, 0x84, 0xbc, 0xc4, 0xfc (2 to 40 pixels each at the equal alpha); the other
  modes **H-THR1** (the low byte acts only on the one-bit alpha: xor 0) against **H-THRN** (it
  changes them).
- p2, bits 11:8: **H-NULL** (0xf80 changes no pixel: xor 0) against **H-ACT**.

## Retire rule (frozen against Q044's text; `python3 score/score.py retire out/ATT`)

Q044's line asks (a) what bits 11:0 do, when none changes a pixel in modes 0 to 3, and (b) does
bit 25 act on the other pack modes; its body adds an alpha equal to the low byte, the low byte in
the other modes with alpha, bit 25 in the modes not run, bits 11:8.

RETIRE when all of: every stage ran with its controls PASS (s0's gate open); (b) every bit-25 row
of p1 and pw but 22 and 34 reads, decided, either its mode's H-INV25 mask or 0x00000000 (a mode
reading 0 against a non-zero mask is named: bit 25 does not act there, as in mode 8); (a) every
mode-4 equality row decides H-GE or H-GT, all the same one, every low-byte row of the other modes
reads xor 0 (H-THR1) and every 0xf80 row xor 0 (H-NULL). Else NARROW, with the reasons printed.

Clauses that retire: (a) bits 7:0 = the threshold of mode 4's one-bit alpha, the equality side
named, and nothing in modes 1, 2, 5-11 (0 by E268/E385); bits 11:8 nothing in every class run;
(b) bit 25 per mode for 4-63 but 14, 22, 34. Named, not run: **mode 14** from E031 (it faults in
both runs and stores nothing, so bit 25 has nothing to act on). **Split to Q012**: bit 25 in modes
22 and 34 (the reading on the dwords their two references repeat, printed as a note, goes to
Q012's body: their formats are Q012's). Bits 11:8 run together (0xf80) except in modes 0 and 4
(E385, each bit): a null on 0xf80 is read as each bit null [infer]. The lead confirms the split
and the body extras (R34-4 (a)).

## Stops

Any fault or hang (4 or 6; `#limit 0`); a control without its 64 pixel rows (25, the premise);
the second row of a stage without its 64 pixel rows (24, hook_check); s0's stop ends the session
(`on_stop = "end"`); a closed gate skips p1, p2 and pw. Never retried or rebooted.

## The mock's worlds

model (0 everywhere, RETIRE), alt (H-SUBSET, H-GT, H-THRN: 0, rows FAILED, NARROW), s0diff (E385's
mode 4 image off by one bit: gates closed, 0), s0nopix (25, ends), p1nopix (p1 24, p2 and pw run:
0), pwfault (pw 4), p2hang (p2 6). The kit's library-mock replay runs all 198 rows on t10's
pinned source.

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors table (closing_tables.py, `sgx545-tables`) | replay |
|---|---|---|
| p1, pw | `vectors/closing/r34-q044/p1.table.json` (mode, word, the kept image, xor) | `crates/sgx-pipe/src/pbe.rs` `reg0400_known` and `pack_pixel` for the modes pack_of models (0-3, 7, 8, 15, 18, 20, 24, 25, 27, 28) once the fold lands bit 25 there; the others refused (pack_of: Q044) unless the fold models them |
| p2 | `vectors/closing/r34-q044/p2.table.json` (mode, word, pixel, alpha, kept dword) | pbe.rs, once the fold lands the mode 4 threshold; refused for mode 4 until pack_of models ARGB1555 |
| s0 | none (controls, E031/E268/E385's images) | - |

The replays read only kept files, the frozen predictions and session.toml's pins.

## Deviations from the plan

- The ramp is E385's kept program, not a new one: it has no alpha 0x40, 0x80 or 0xc0 on the
  triangle, so the equality clause is tested at nine low bytes equal to alphas it has (2 to 40
  pixels each); E031's mode 4 (alpha 0x80 at 0x80, kept, s0) and E385's background (0xff at 0xff)
  are H-GE's fit points. A new shader would have needed its alpha map measured first (L3).
- p2 runs modes 1, 2, 5-11 for the low byte (the body's "other modes with alpha bits") and one mode
  of each class at 0xf80, not 4, 5, 7 only; 0x00 and 0xff only in 5-8.
- Modes 12 and 13 run last in their own stage pw (they write past the target into the scratch).
- 198 jobs, not ~170.

## Data

Every input is a kept record of resgx545-data (E031 pack-modes, E268 reg-0400-modes, E385
reg-0400-alpha) or resgx545's probe tables, pinned. Nothing here is firmware-derived: no file
goes to data-private.
