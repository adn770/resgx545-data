# r14-tex

Round 14's session r14-tex (closing14/plan/rank-round14.md sections 2 and 3, decision R14-1 (a) of
closing14/DECISIONS-R14.md), built with the session kit (resgx545 HACKING.md, "Session kit"),
scaffolded by `tools/closing/new_session.py` from resgx545 dddadbdd001b (kit/ is that commit's
blobs), data 3309b5fd9bd7. Generators: gen/make.py with gen/srgb4.py and gen/addr5.py (+
gen/forms5.py); r13-tex's gen/srgb.py, gen/addr.py, gen/tex.py and gen/texprog.py are copied
unchanged (resgx545-data `render/closing-r13-tex`), gen/pins.py with its temp prefix renamed. Every
repository file they read is read at the frozen commits (gen/pins.py) and pinned. Records E1038
(srgb4), E1039 (addr5).

## What runs

Two stages in this order, 27 jobs, laptop prefix `r14t` (files under `~/scratch/r14t/`), one
binary: `~/sgxfive-test-t10` (t10, sha256 9bedc2d6...), bound by source to resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`), recipe
`data:render/closing-r10-st1/lead/build_tool10.sh`. Every row names t10; the kit's library-mock
replay runs all 27 (each a probe of a program of ours: "program not simulated", since c12542e).
Module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is written.
Safe class: no planned fault, no expect-fault row, no held reset, `#limit 0` on both stages.

| stage | plan | question | jobs | what is frozen | record |
|---|---|---|---|---|---|
| srgb4 | srgb4 | Q282 | 13 | TRI-RNTU against TRI-G15, TRI-RNE, TRI-BF11, TRI-OUT (and -NF, QN-); B2-FTZ-OUT; A-LIN against A-SRGB, A-BYTE | E1038 |
| addr5 | addr5 | Q177 | 14 | C-LOG4 against C-SAT24, C-FLOOR16, CO-WH2, CO-12M4, CO-12W4; IN / LR / AB with M, W, H; T-MODE0 against T-OFFSET | E1039 |

- **srgb4** (`tables/srgb4.txt`, gen/srgb4.py). Controls that can fail: srgb4-ctl (E723's
  g-bl-st-a, r10-tex's published srgb2-ctl program, its kept image), srgb4-trir (r13-tex's
  srgb3-tri program and kept image: the trilinear replicate), srgb4-b2x1 (the r11 program on
  srgb3-x1's texture with byte 2 equal to byte 0: its low halves must be srgb3-x1's kept channel 0,
  h: tokens). Held out, the trilinear level lerp (T0 0x0FFC1600, smp2dreplace): srgb3-tri's
  16 x 16 counting chain at LOD 1.125, 1.5, 1.75 and 1.984375 (levels 1 and 2, f 8, 32, 48, 63),
  0.25 (levels 0 and 1, f 16), 1.2 (float32 0x3f99999a: f 12 floor, 13 nearest), and a dark
  4 x 4 chain injected (21 dwords; byte 1 from 0 to 3 on every level, byte 0 from 0 to 3 on level
  0 and 64 to 255 above) at LOD 0.125 (f 8). Frozen per pixel: TRI-RNTU (E1025's post hoc form,
  operands floored to 2^(e - 16), exact lerp, nearest ties up, the third result below 2^-14
  flushed), TRI-RNTU-NF (not flushed), TRI-G15 and TRI-G15-NF (floored to 2^(e - 15)), TRI-RNE,
  TRI-BF11, TRI-OUT; on the 1.2 row each also with f rounded (QN-). Held out, bytes 2 and 3
  (E723's published tx_map_r11.s: o0 from r11, the sample's second dword): the x stage alone
  (srgb4-ax), the y stage alone (srgb4-ay), both (srgb4-axy, fy 29/64); byte 2 pairs (0, 1 to
  3), byte 3 random pairs. B2-FTZ-OUT (the low half, h:) and A-LIN / A-SRGB / A-BYTE (the high
  half, u:).
- **addr5** (`tables/addr5.txt`, gen/addr5.py). Controls that can fail: addr5-ctl (E1000's
  addr3-16x64-u4, its program and kept image, 32 pages) and addr5-bduv5 (E565's bd-uv5, p1132's
  program, base 0, 16 pages). Held out: u and v in mode 5, swept past both ends (every region
  holds pixels), twiddled 32-bit at page 12 of a 32-page named scratch (T2 0x5CAFC000), at 8 x 8,
  32 x 32, 128 x 32, 32 x 128, 128 x 128 and, last in the stage, 256 x 32. Corner bases (c + 0 to
  3): C-LOG4 4 log2 M (12, 20, 28, 28, 28, 32), C-SAT24 (24 above 24), C-FLOOR16 (16 at 8 x 8),
  CO-WH2, CO-12M4, CO-12W4 (E1026's failed forms). Types 1, 3, 4: E567's 16 x 16 programs (rt1-2d,
  ty3-2d, rt4-2d, rebuilt byte for byte) as the mode 0 reference (a replicate, H-E567), then the
  same program with u mode 4 (32 pages): T-MODE0 (the reference's image of this run) against
  T-OFFSET (that image + 180 on every pixel).

## Predictions and what each verdict does

Frozen before the run: `predictions/STAGE.tsv` and the per-pixel files `predictions/STAGE/`
(sha256 in the tsv; `PREDICTIONS.sha256` at the freeze). Expected, not frozen:

- srgb4: the controls pass; TRI-G15 on the seven trilinear rows (TRI-RNTU misses 7, 0, 0, 0, 0, 6
  and 137 pixels where they part, so the plan's tested form is expected to fail on 3 rows);
  either flush on the dark row (no kept row parts them); Q-FLOOR on the 1.2 row (texmodel's
  `int`); B2-FTZ-OUT and A-LIN on the three alpha rows (E723's r11 point jobs decode byte 3
  linearly, post hoc 2048 of 2048 twice: tests/test_gen.py).
- addr5: the controls pass; C-LOG4 and the M regions on all six shapes; the type rows are the
  open choice (T-MODE0 by analogy with the strided type [infer]).
- Q282 retires per R14-6 (a) if exactly one TRI form (with its flush decided by the dark row and
  its f by the 1.2 row) holds on all seven trilinear rows, B2-FTZ-OUT and exactly one alpha form
  on all three, and the three controls pass. Q177 retires per R14-6 (a) if C-LOG4 holds on all
  six shapes (C-FLOOR16 parted on 8 x 8 only, C-SAT24 on four), each type row holds exactly one
  of T-MODE0 or T-OFFSET (or reads a third form, then that type stays open), and both controls
  pass; "why these constants" is reworded [infer] (the lead confirms).

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E1025's, E1026's, E567's,
E1000's or E565's jobs; every rival's read is inside the mapped scratch, tests/test_gen.py); a
control without its pixel rows stops the session (rc 25); the second row of a stage without its
32 pixel rows stops that stage (rc 24, run/hooks.sh), and the driver goes on; less than 300 MiB
free on ~ (rc 22). Stop budget: `#limit 0` on both stages, 0 faults and 0 hangs expected. The
256 x 32 row is last in addr5 (its side is the only one the laptop has not read twiddled), so a
fault there loses no other row.

Expected time: probes under 2 s each plus the runner's reset, snapshot and health (about 6 s a
job): about 3 minutes of jobs, about 7 with staging and preflight; stage alarms 15 minutes each.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (mock/world.py): model (every stage 0, the tested models held: TRI-RNTU, A-LIN,
C-LOG4, T-OFFSET), alt (the rivals: TRI-OUT, A-SRGB, CO-WH2 with the W regions, T-MODE0; every
stage 0), nopix (no held-out addr5 row prints pixels: rc 24 at the second), ctlnopix (srgb4-ctl
without pixels: the premise stops the session, rc 25), fault (the first held-out addr5 row
faults: rc 4), hang (the first held-out srgb4 row does not return: rc 6). A fill program whose
reads pass the row's scratch faults in every world.

## Deviations from the plan

1. **TRI-G15 added beside TRI-RNTU.** The plan freezes E1025's post hoc form (2^(e - 16), 4091 of
   4096 halves). A declared family searched here on srgb3-tri only (fit/tri_fam.py: operand
   grids 2^(e - 11) to 2^(e - 40), the difference floored or not, ties up, even or toward zero)
   found the 2^(e - 15) grid exact, 4096 of 4096 (post hoc, fitted on the one kept row). Both are
   frozen; the rows part them on 150 pixels (srgb4-t1125, t12, tdark), the dark row designed for
   it (a dark level 0 under a bright level 1). TRI-RNTU stays the plan's tested form (mock
   model world), though TRI-G15 is the expected one.
2. **The third stage's flush is two forms** (-NF unflushed): the plan's TRI-RNTU names none, and
   no kept trilinear half is subnormal. The dark row parts them (224 pixels).
3. **The alpha forms' premise is kept data, not a guess.** E723's r11 point jobs fit
   half(sRGB(byte 2)) low and half(byte 3 / 255) high on every pixel of both (post hoc; the plan
   called r11 "not decoded"), so H-ALPHA-SRGB is refuted for point samples already and A-LIN is the
   expected bilinear form; A-BYTE (texmodel's byte blend) is added as a third rival.
4. **The type rows' references are E567's own jobs** (replicates, H-E567), not new programs, and
   T-OFFSET is scored on the reference's image of this run (score.py `rel`), not a per-pixel
   prediction: what types 1 and 4 read at mode 0 is not modelled (E567). E567 ran rt1 and rt4 in
   its "risky" group (no fault, no hang, the health exact): here they are safe class [check].
   The type rows are at 16 x 16 (E567's), so T-OFFSET is +180; the plan named no shape.
5. **Order.** The type rows run before the 256 x 32 corner row, which is last (plan: [check: T0
   takes a 256-wide twiddled texture]).

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors table (closing_tables.py, `sgx545-tables`) | replay |
|---|---|---|
| srgb4 | `vectors/closing/r14-tex/srgb4.table.json` (LOD, levels, f, the level halves, kept halves; alpha corners, weights, kept halves) | `crates/sgx-sim/src/tex.rs`: the third stage and the alpha decode added by the fold if decided; refused otherwise (Q282) |
| addr5 | `vectors/closing/r14-tex/addr5.table.json` (shape, pixel, s, t, kept dword less the base; type, reference dword, kept dword) | sgx-sim tex address (the mode 5 corner base, if C-LOG4 holds); the type rows refused unless one form holds on all three |

The replays read only kept files, the frozen predictions (session files) and session.toml's pins.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r14-tex`). bins/*.bin are our own probe programs (assembled from the pinned p1141
templates by usse-asm) or published bins of earlier sessions (r10-tex, r13-tex, p1132), not tools.
`fit/` holds the two post hoc fits "Deviations" 1 and 3 name (fit/tri_fam.py, fit/r11.py: kept
data read at data 3309b5fd9, run with the repo's .venv); `debug/` (the mocks, logs) is not
published.
