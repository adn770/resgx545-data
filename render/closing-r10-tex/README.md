# r10-tex

Round 10's session S10-tex (decision R10-2 (a) of the seeds plan
`closing10/seeds/exp-seeds-r10.md`, sections 1 to 4 and 15; the lead's
`closing10/DECISIONS-R10.md`),
built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 9849dab7540c (kit/ is that commit's blobs), data
1324301bef13. Its generators are r9-geo's (gen/addr.py, gen/cube.py, gen/texprog.py) and
r9-x's (gen/t3.py, gen/srgb.py, gen/tex.py, gen/pins.py), copied from resgx545-data
`render/closing-r9-geo` and `render/closing-r9-x` and extended; every repository file they read is
read at the frozen commits (gen/pins.py) and pinned. Records E1000 to E1004 (the tooling's
4-digit E-numbers must land before the fold).

## What runs

Four stages in this order, 48 jobs, all `probe --temps 32 --coords --pixels` of programs assembled
by gen/make.py from the pinned p1141 template (`bins/*.bin`), one tool: t4 =
`~/sgxfive-test-rgn4` (sha256 e6951558...), bound by source to resgx545 4623753
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 703cbcea..., `TOOLSRC.sha256`), recipe
`userspace/libsgxfive/Makefile` at that commit (the binary's `built` line of FROZEN.commits);
every row is replayed on that source's library mock before the worlds run (48 of 48, none refused).
Module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is written.
Laptop files under `~/scratch/r10t/`. Safe class: no planned fault, no expect-fault row, no held
reset, `#limit 0` on every stage.

| stage | plan | question | jobs | what is frozen | record |
|---|---|---|---|---|---|
| addr3 | section 2 | Q177 | 11 | the offset rivals H-W / H-H / H-SQ / H-WH, mode 5 H-B5 / H-B5H | E1000 |
| cube3 | section 3 | Q284 | 16 | ties H-HIGHAXIS / H-FMADNE / H-THIRD; edges H-SEAM-FLOAT / H-SEAM-ADJ | E1001 (ties), E1002 (edges) |
| t3b | section 4 | Q078 | 15 | R-4096 / R-4096TX / R-ROUND / H-U01 (H-UV, H-URAW on their rows) | E1003 |
| srgb2 | section 1 | Q282 | 6 | R10-BF11 (E982's rule), R10-BF11-ROUND, H-WEXACT, H-K0FLOOR | E1004 |

Expected time: each probe under 2 s plus the runner's reset, snapshot and health, about 1 minute
of jobs a stage, about 13 to 20 minutes with staging, preflight and health; stage alarms 15, 20,
20 and 10 minutes.

- **addr3** (`tables/addr3.txt`, gen/addr.py). Twiddled 32-bit textures at page 12 of a 32-page
  named scratch (T2 0x5CAFC000, `--scratch-pages 32` on every row), the swept u over 128
  positions at one texel a step, v on texel H / 2's centre. The index is E561's tile law for
  every shape (tests: it reproduces E957's kept 8 x 8, 16 x 16 and 32 x 32 rows with + 116, + 180
  and + 308, and E932's mode 5 replicate). Control: u mode 0 (r9-geo's program byte for byte).
  Replicates: 16 x 16 mode 4 (+180) and E565's 32 x 8 form, u and v in mode 4 (+308). Held out:
  8 x 32, 16 x 64, 64 x 16 (the four rivals part on 2048 of 2048 pixels each), 64 x 64 in modes 4
  and 6 and 4 x 4 (every rival agrees: the size's own check, 564 and 84), and u mode 5 at 16 x 32
  and 32 x 16 (H-B5 against H-B5H). The scorer also prints each row's read less H-MASK-V's index.
- **cube3** (`tables/cube3.txt`, gen/cube.py, the r9-geo text unchanged and r10-tex's part at
  its end). E726's probe form, 16 x 16 faces, r9-geo's frozen q284_rule.json (pinned, sha256
  checked). Control: E726's cu-xn program. Ties (point): 6 cc rows (tied coordinates movs of
  +-0.75, the third a ramp) and 6 rr rows (the bit-identical fmad ramp or its negation, the third
  0.5), the seeds' `q284/rows_a.json` specs (tests compare), 2048 two-axis tie pixels each; r8-geo's
  a2 program replayed byte for byte (78 tie pixels). Frozen: H-HIGHAXIS (every tie pixel reads a
  face of the higher tied axis, `lower` 0), H-FMADNE (cc and rr read high; the replay repeats
  r8-geo's kept image, `lower` 4), H-THIRD [infer] (`lower` > 0 on cc and rr). Edges (bilinear,
  T0 0x07fe1400): +z/+x and -y/+x, the across coordinate 15 + (x + 1/2) / 64 texels (16 in columns,
  16 out columns of outer weight 1/4 to 1/2), the along coordinate 7.75 and 8.25; H-SEAM-FLOAT
  (seeds finding 3; tests: 96 of 96 on both of E956's kept edges) against H-SEAM-ADJ, every out
  pixel's bytes within 1, gated by the in pixels (90% within 1). The rivals part on 512 of 512
  out pixels by more than 2 in a byte on both rows.
- **t3b** (`tables/t3b.txt`, gen/t3.py). E566's tx_map form on strided named memory. Controls:
  E566's s64x32-ctl and s64x32-t3b14 (their kept images; programs byte for byte). Replicate:
  E975's b14-u01 (its kept image = R-4096; program byte for byte). Six held-out pairs, each bit-14
  row followed by its bit-clear `-ref` (texmodel's image, which gates the pair in the scorer):
  S 256 x W 64 (u over [0, 1/4), so H-U01's reads fit 19 pages), S 16 x W 16 x H 64, u off the
  1/128 grid (4096 u = 64 x + 3/4: floor and round part), u from -0.5 to 1.5 (the texture at dword
  2048 so that H-URAW's negative offsets stay inside), u fixed at 5/16 with v a ramp (H-UV), and a
  16-bit format (T1 format 9, u16, the half returned) at S 64 on row 0: R-4096 (4096 dwords)
  against R-4096TX (4096 texels), scored on the low 16 bits (`h:` tokens) [infer: the 16-bit
  texel x of row 0 is the half x & 1 of dword x >> 1, which the `-ref` row checks].
- **srgb2** (`tables/srgb2.txt`, gen/srgb.py, gen/q282.py). E723's g-bl-st form. Control:
  E723's g-bl-st-a (its kept image; program byte for byte). Held out against R10-BF11 (the seeds'
  `q282/q282_r10_rule.json`, reimplemented exactly in the standard library; tests: 2048 of 2048
  on r9-x's six kept rows and on E723's g-bl-st-a and -b): offgrid (fx and fy off the 1/64 grid by
  3/4 of a step: R10-BF11 against R10-BF11-ROUND and H-WEXACT, 2046 and 2047 pixels apart), k0b
  (x stage at k = 0, B larger than A in half the columns: H-K0FLOOR [infer] parts on 664 pixels),
  sub (458 subnormal halves), rand1, rand2 (random bytes, both stage orders' geometry).

## Predictions and what each verdict does

Frozen before the run: `predictions/STAGE.tsv` and the per-pixel files `predictions/STAGE/`
(sha256 in the tsv; `PREDICTIONS.sha256` at the freeze). Expected, not frozen: addr3 H-W on the
three non-square held-out rows (then Q177's "what sets the offset" is the width, E1000) and H-B5
on mode 5; cube3 H-HIGHAXIS on the 12 tie rows with the replay either repeating r8-geo's lower
reads (H-FMADNE: the tie clause narrows to unequal fmad ramps) or not, and H-SEAM-FLOAT on both
edges (Q284's edge clause retires); t3b R-4096 on all six pairs (bit 14's constant held out:
E1003), the 16-bit pair deciding dwords against texels; srgb2 R10-BF11 on every row (Q282's rule
confirmed on hardware past the kept jobs: E1004). The seeds plan's section 14 says what each
verdict retires.

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E565, E932, E957, E726, E930,
E956, E566, E975, E723 or E976's jobs; every rival's read is inside the mapped scratch, checked by
tests/test_gen.py); a control without its 32 pixel rows stops the session (rc 25); the second row
of a stage without its 32 pixel rows stops that stage (rc 24, run/hooks.sh) and the driver goes
on; less than 300 MiB free on ~ (rc 22). No knob is written.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (mock/world.py, the probe answering with the session's own frozen predictions):
model (every stage 0), alt (the other rivals: every stage 0, the rows FAILED), nopix (cube3 stops
at its second row without pixels, rc 24; t3b and srgb2 run), ctlnopix (addr3's control without
pixels: the premise stops the session, rc 25), fault (t3b's first held-out row faults: rc 4),
hang (srgb2's first held-out row does not return: rc 6). A program whose reads pass the row's
scratch faults in every world.

## Deviations from the plan

- cube3 edges: the plan's along coordinates 7.25 and 7.75. At +z/+x, 7.25 parts the two rivals on
  0 of 512 out pixels (the along taps 6 and 7 differ by a few index units: tests/test_gen.py
  `test_the_plans_along_725_would_not_part`), so the edges sit across the 7 / 8 Morton step: 7.75
  (+z/+x) and 8.25 (-y/+x), 512 of 512 parted on each. The out pixels are those whose outer tap
  weighs 1/4 or more (r9-geo used 0.4), 16 columns; 16 in columns are the gate.
- srgb2-k0b: with B the smaller corner (the plan's words) the bypass and H-K0FLOOR both return A
  (A on its own grid is unchanged), so half the columns have B larger. srgb2-sub: bytes 1 to 3
  decode to normal halves (3.0e-4 and up); the subnormal halves come from lerps between 0 and a
  byte 1 to 3, so each pair holds a 0.
- t3b: S 256 runs u over [0, 1/4) (H-U01 at S * S = 65536 would read past 64 pages over [0, 1));
  the off-grid u is 4096 u = 64 x + 3/4 (the plan's 1/192 is no float32 value and its 4096 u
  fraction, 1/3, does not part floor from round); the clamp row puts the texture at dword 2048;
  H-URAW is added on the clamp row (the unclamped rival the clamp parts); the 16-bit format is u16
  (format 9, usse_isa.md: 7 to 11 return the half).
- Record numbers: the seeds plan's E987 to E991 became E1000 to E1004 (DECISIONS-R10.md).

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors table (closing_tables.py, `sgx545-tables`) | replay |
|---|---|---|
| addr3 | `vectors/closing/r10-tex/addr3.table.json` (pixel, swept texel, kept dword, read less H-MASK-V) | refused: no sampler models T0 address modes 4 to 7, unless the fold adds the offset |
| cube3 | `vectors/closing/r10-tex/cube3.table.json` (tie pixels: coordinates, kept face; edge pixels: kept bytes) | `crates/sgx-pipe/tests/texture_cube.rs` for the control and the replay's non-tie pixels; ties and edges refused (no tie rule, no bilinear cube sampler) unless the fold lands one |
| t3b | `vectors/closing/r10-tex/t3b.table.json` (pixel, u, v, reference dword, kept dword) | refused until the fold lands bit 14's rule in the sampler (no path models T3 bit 14) |
| srgb2 | `vectors/closing/r10-tex/srgb2.table.json` (corners, weights, kept halves) | sgx-pipe's sRGB bilinear stage once E982's rule lands there (sim in sync); refused before |

The replays read only kept files, the frozen predictions (session files) and session.toml's pins.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r10-tex`). bins/*.bin are our own probe programs (assembled from the pinned p1141
template by usse-asm), not tools.
