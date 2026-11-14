# r15-tex

Round 15's session r15-tex (closing15/plan/rank-round15.md sections 2 and 3, decisions R15-1 (a) and
R15-5 (a) of closing15/DECISIONS-R15.md), built with the session kit (resgx545 HACKING.md, "Session
kit"), scaffolded by `tools/closing/new_session.py` from resgx545 158bdc5455b2 (kit/ is that
commit's
blobs), data cddc7b60b8ed. Generators: gen/make.py with gen/chain.py, gen/prog.py and gen/ty.py;
r13-tex's gen/addr.py, gen/tex.py and gen/texprog.py are copied unchanged (resgx545-data
`render/closing-r14-tex/gen`), gen/pins.py with its temp prefix renamed. Every repository file they
read is read at the frozen commits (gen/pins.py) and pinned. Records E1052 (chain), E1055 (ty).

## What runs

Two stages in this order, 33 jobs, laptop prefix `r15t` (files under `~/scratch/r15t/`), one
binary: `~/sgxfive-test-t10` (t10, sha256 9bedc2d6...), bound by source to resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`), recipe
`data:render/closing-r10-st1/lead/build_tool10.sh`. Every row names t10; the kit's library-mock
replay runs all 33 (each a probe of a program of ours: "program not simulated", since c12542e).
Module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is written.
Safe class: no planned fault, no expect-fault row, no held reset, `#limit 0` on both stages.

| stage | plan | question | jobs | what is frozen | record |
|---|---|---|---|---|---|
| chain | chain | Q104 | 18 | chain=A against B and D (32 bits); A-TX against A-DW, B-TX, D-TX (u16); the u16 blend -BL8 against -BL16 | E1052 |
| ty | ty | Q177 | 15 | H-HALF, H-LIN1 against H-WHOLE, H-MODE0; H-AS-U4 (modes 5 to 7); NAME-U against NAME-WRAP; R-W / R-16, R-2W / R-32 | E1055 |

- **chain** (`tables/chain.txt`, gen/chain.py). E562's generator: the 16-page scratch is the
  texture (dword i = 0xD0000000 | i, level 0 at dword 0, T2 0x5CAF0000), point sampling, repeat.
  Every held-out row samples u = v = (32 x + 17) / 2048 (the diagonal; 1/2 on a side of 1) with
  the LOD (y >> 2) + c down the rows (a `step` axis, gen/prog.py: rows 4k to 4k + 3 alike, k = 0
  to 7). Controls that can fail: E562's shp-32x16-l5 and shp-128x16-l7-x0 rerun (p1132's
  published programs, their kept images; B and D miss both). Held out, in run order: a side of 1
  (1 x 32 and 32 x 1 at c = 0 and 1/2; 32 x 1 with the bias field 0x33), u16 (T1 format 9: 32 x 16
  and 16 x 64 at c = 0 and 1/2; 32 x 16 with MIPFILTER at c = 1/2, f 32), long sides (64 x 32 at c
  = 0; 256 x 32 at c = 0 and 3/2) and, last, 1D (smp1dreplace on 64 x 1 at c = 0 and 1/2, and with
  the maximum field 3). Frozen per pixel: E562's chains (A both sides halve to 1, back to back; B
  stops at the short side's 1; D square-padded) under E441's level rule, E561's tile law inside a
  level; on u16 the level offsets in texels (-TX) or in dwords of a 32-bit chain (-DW), the half
  read as E1003 read it (odd texels 0xD000), and the MIPFILTER blend per byte (-BL8, texmodel's) or
  as one 16-bit lerp (-BL16).
- **ty** (`tables/ty.txt`, gen/ty.py). Every row at base 0 of a 32-page named scratch. Controls
  that can fail: ty-ctl (E1000's addr3-16x64-u4, r14-tex's addr5-ctl program, E1000's kept image)
  and ty-ty1u4r (E1039's addr5-ty1-u4, r14-tex's program and kept image). Held out: types 1 and 4
  at 16 x 16 in u modes 5, 6 and 7 (E567's programs, T0's u mode only); type 1 at 16 x 16 in u mode
  4 with U = x - 24 (ty-16-ty1-n16, H-NAME16); types 1, 3 and 4 at 32 x 32 (`map` u and v of 5
  bits) in mode 0 (the reference) then u mode 4. Frozen (score.py `form` and `rel` lines and
  per-pixel files): H-HALF (every pixel a name with its bytes halved, rounded up, the rows alike:
  E1039 post hoc), H-LIN1 (that, the name c + U with U the unwrapped column, E1039's map), H-WHOLE
  (an unhalved name), H-MODE0 (the mode 0 image: E567's kept image at 16 x 16, the reference row of
  this run at 32 x 32), H-AS-U4 (E1039's kept mode 4 image, modes 5 to 7), NAME-U (half(660 + U))
  against NAME-WRAP (half(676 + U mod 16)) on the n16 row, R-W / R-16 (types 1, 3) and R-2W / R-32
  (type 4) on the 32 x 32 references.

## Predictions and what each verdict does

Frozen before the run: `predictions/STAGE.tsv` and the per-pixel files `predictions/STAGE/`
(sha256 in the tsv; `PREDICTIONS.sha256` at the freeze). Expected, not frozen:

- chain: both controls pass; A on every 32-bit row and A-TX on the four u16 LOD rows (E1026: u16
  is addressed in texels [infer]); -BL8 on the MIPFILTER row is the weakest guess (no kept 16-bit
  blend; on 32 x 16 A-DW-BL8 and D-TX-BL8 are one image and cannot be parted).
- ty: both controls pass; H-HALF and H-LIN1 on the nine form rows, H-AS-U4 on modes 5 to 7 (the
  twiddled type reads modes 4, 6 and 7 alike and mode 5 inside the texture as 4 [infer]), NAME-U
  on n16, R-W and R-2W on the references [infer]. H-MODE0 and H-WHOLE are expected to fail.
- Q104 retires per R15-6 (a) if A (A-TX) holds on the 1D, side-1 and 16-bit rows with both
  controls passing, the maximum and bias rows read as E441's rule says on the new chains, and
  exactly one blend holds on the MIPFILTER row (or that clause is reworded to the u16 point chain
  [infer]); "1D" reads smp1dreplace on 64 x 1 (R15-6 a). Q177 narrows (R15-5 a): the 32 x 32 and
  mode 5 to 7 readings are the fit for a size form held out in a later round; H-NAME16 decides
  whether the 16 x 16 name map is linear in the unwrapped column.

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E562's, E567's, E1000's or
E1039's jobs; every frozen model's read is inside the mapped scratch, tests/test_gen.py); a control
without its pixel rows stops the session (rc 25); the second row of a stage without its 32 pixel
rows stops that stage (rc 24, run/hooks.sh), and the driver goes on; less than 300 MiB free on ~
(rc 22). Stop budget: `#limit 0` on both stages, 0 faults and 0 hangs expected. The three smp1d
rows are chain's last (the instruction never ran on this laptop): a fault there loses ty only.

Expected time: probes under 2 s each plus the runner's reset, snapshot and health (about 6 s a
job): about 3.5 minutes of jobs, about 8 with staging and preflight; stage alarms 15 minutes each.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (mock/world.py): model (every stage 0, the tested models held: A, A-TX, A-TX-BL8,
H-AS-U4, NAME-U, R-W, R-2W, H-HALF and H-LIN1), alt (the rivals: B, B-TX, B-TX-BL8, H-MODE0,
NAME-WRAP, R-16, R-32; every stage 0), nopix (no held-out ty row prints pixels: rc 24 at the
second), ctlnopix (chain-ctl32 without pixels: the premise stops the session, rc 25), fault (the
first held-out chain row faults: rc 4), hang (the first held-out ty row does not return: rc 6). A
fill program whose named reads pass the row's scratch faults in every world.

## Deviations from the plan

1. **D is not frozen on 256 x 32.** Its level 1 starts at dword 65536, past t10's 64 pages: a
   fault rival in a safe session. E562 refuted D on 43 of 49 held-out jobs; the 256 x 32 rows
   score A against B.
2. **The smp1d rows run last in chain** (the plan lists 1D first): smp1dreplace never ran on the
   laptop, so a fault there loses only ty.
3. **The row forms are this builder's.** The LOD down the rows is (y >> 2) + c (a `step` axis
   assembled by gen/prog.py, exact); u = v on the diagonal, inside the texture and more than 1/128
   texel from an edge at every level (E562's windows came to 1/128). The plan's "bias 7" is one
   row at the bias field 0x33 (-1.5, an E562 value). The plan named no 16-bit blend: -BL8 and
   -BL16 are frozen. The chain controls are E562's shp-32x16-l5 (a fit job of E562) and
   shp-128x16-l7-x0 (held out); the plan said "held-out rows".
4. **H-NAME16's map, fitted before the freeze** (debug/fit_name16.py, tests/test_gen.py): E567's
   `map` u lies in [1, 2), so E1039's names are c + U with U = 16 + (x mod 16) the unwrapped column:
   c = 660 (types 1, 3) and 644 (type 4) on every pixel, c - 256 equally (the halves cannot part
   them). NAME-U extends it linearly to U = -24 to 39, NAME-WRAP keeps U mod 16.
5. **Added frozen forms.** H-LIN1 (E1039's map at any size), H-AS-U4 (modes 5 to 7 read mode 4's
   image) and per-pixel references at 32 x 32 (R-W / R-16, R-2W / R-32): the plan froze H-HALF,
   H-WHOLE and H-MODE0 only. H-MODE0 at 32 x 32 is scored on this run's reference (score.py
   `rel`), at 16 x 16 on E567's kept image.
6. **The chain model is gen/chain.py, not texmodel.py**: E561's tile law inside a level (r13-tex's
   index()), u16 halves and the `step` axis; it equals texmodel on all 101 E562 specs whose short
   side is at most 16 and holds E562's kept images (tests/test_gen.py).

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors table (closing_tables.py, `sgx545-tables`) | replay |
|---|---|---|
| chain | `vectors/closing/r15-tex/pixels/chain.table.json` (the kit's texture kind: shape, format, T0, LOD rows, kept pixels) | sgx-sim tex.rs: CHAIN_SIZES and the chain rule extended to 1D, a side of 1, u16 and 64 x 32 / 256 x 32 by the fold if A holds, its tests holding kept pixels of every row; the table refused (digests), as r14-tex's |
| ty | `vectors/closing/r15-tex/pixels/ty.table.json` | refused: sgx-sim refuses types 1, 3 and 4 in u modes 4 to 7 (named E1039; the fold names E1055) |

The replays read only kept files, the frozen predictions (session files) and session.toml's pins.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r15-tex`). bins/*.bin are our own probe programs (assembled from the pinned p1141
template by usse-asm) or published bins of earlier sessions (p1132, r14-tex), not tools. `debug/`
(the mocks, the pre-freeze fit debug/fit_name16.py and its helper) is not published; the fit is
replayed by tests/test_gen.py, which is.
