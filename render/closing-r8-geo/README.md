# r8-geo

Round 8's no-kernel laptop session (decision R8-2 (a) of `closing8/DECISIONS-R8.md`, plan
`closing8/rank/rank-round8.md` section 1), built with the session kit (resgx545 HACKING.md,
"Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545 d97c47393531 (r7-merge's
tip when scaffolded; kit/ is that commit's blobs), data d3afd435199f.

## What runs

Four stages in this order, 60 jobs, one tool (t4 = `~/sgxfive-test-rgn4`, sha256 e6951558..., built
from resgx545 4623753, sgxfive-test.c sha256 703cbcea..., unchanged since round 4; t7 is not used:
no row needs odd widths), module 37EC97AB0CB37213C42FCCC (fork 664fd0d0) loaded = installed:

| stage | plan | question | jobs | risk | what is frozen |
|---|---|---|---|---|---|
| cube | R8-2 | Q284 | 19 | safe | the q284 (s, t) rule per pixel; edge rivals |
| seam | R8-1 | Q141 | 24 | safe | the O8 R8-1 table (holes or stored sets) |
| addr | R8-5 | Q177 | 9 | safe | three rivals per pixel, nothing fitted |
| vdm | R8-4 | Q271 | 8 | risky | image same as / differs from the natural twin |

Expected time: about 1 minute of jobs a stage (each job under 2 s plus the runner's reset, snapshot
and health), about 25 minutes with staging, preflight and health; stage alarms 20, 25, 15, 15 min.

- **cube** (`tables/cube.txt`). Control: E726's cu-xn program (bins/cube-ctl-xn.bin is byte for byte
  the published p1141-cube__4.bin), its 2048 pixels as E726 kept them (E844 read them again).
  (a) 4 new off-axis programs at 16 x 16 (all six faces between them) and (b) 3 directions each at
  8 x 8 and 32 x 32 faces (T1 0x4c007007 / 0x4c01f01f, faces N * N dwords apart), held out against
  `gen/q284_rule.json` (sha256 52162471..., the offline freeze of `closing8/rank/q284_st.py`, fitted
  on E726, 4090/4096 on E844): every pixel's dword in `predictions/cube/NAME.txt`; face ties and
  texel ties at a |ma| that is no power of two are "cannot tell" (E844's 6 misses were such ties).
  (c) readings, no rule frozen: 2 face-tie sweeps (|w| = |u| in column 32, +x and -x against +z)
  and 4 texel-tie grids at |ma| 1.75, 1.625, 1.875, 0.90625 (up or down per tied axis). (d) bilinear
  (T0 0x07fe1400) at a face edge, 2 jobs: H-CLAMP (the G byte of an "out" pixel, the face of its
  taps, is its own face) vs H-SEAM (it is not) [infer: two rivals only], decided only when the job's
  "in" pixels show the filter blending.
- **seam** (`tables/seam.txt`). The O8 offline package's frozen R8-1 table (`closing8/offline/r8-1`,
  copied byte for byte to `gen/o8/`, checked against its own sha256 file; `predictions/seam.tsv` is
  its tsv): 14 tri-full renders at sizes never run, 2 zero-hole twins, 3 single triangles of other
  slopes at modes 1/TE 0x6 and 2/TE 0xe, each H-REGION (the landed model, msaa_model.py 1c0e8205...)
  against H-UNION (halves=False). Controls that can fail: tri-full 64 x 64 mode 1 TE 0x60000000 (64
  holes, E502's configuration as a colour job) and mode 2 TE 0x20000000 (no hole, E504's control).
- **addr** (`tables/addr.txt`). E565's 16 x 16 twiddled texture at page 12 of a 24-page named
  scratch, u then v swept over 128 positions at one texel a step, modes 4 to 7; rivals H-MASK-V,
  H-NOMASK-PAGE, H-BORDER (gen/addr.py); control mode 0 on u (the repeat image). Every read names
  its dword: the scorer prints the index per position, the reading table for a row no rival takes.
- **vdm** (`tables/vdm.txt`). E703's capacity form with VDM word 7 set (`--vdm 7=V`): forced =
  natural rows (N = 8 V = 4, N = 2 V = 2) are the controls (same image as the natural twin run just
  before); forced = natural + 1 at N = 2 V = 2 twice (H-COUNT same image, H-LAYOUT changed); forced
  below natural at N = 8 V = 8 a reading. The render memory is kept (`--dump-render "$W"`) for the
  fold's decoder.

## Checks of the plan's [check] items (before the freeze)

1. T0 size field for 8 and 32: passes. The size is T1's width-1 / height-1 fields, E725's held-out
   type 1 and 3 jobs at 8 x 8 and 32 x 32 (0x6c007007, 0x6c01f01f; TEXTYPE 2 is bits 31:29 = 2).
2. Negative `--tri-z`: **fails**. `parse_tri_z` (sgxfive-test.c, 4623753 and 1c64f3a alike) refuses
   any depth outside 0 to 1. R8-3 (Q101, 10 jobs) is dropped, not the session.
3. The VDM word print: the tool prints only which words a `--vdm` poke touched, not their values;
   `--emit-scene` writes them. `bash lead/dryrun_vdm.sh` builds the rgn4 source (git archive
   4623753,
   hash checked) for the Mac into debug/ (never shipped) and runs the natural forms against the
   library's mock: word 7 = 0x03c00082 (N = 8), 0x02c00082 (N = 2), as render.c builds it. Passes,
   by a Mac dry run instead of the laptop's preflight; the controls fail if the word is wrong.
4. Scratch placement: passes with a change of means. `probe --scratch-pages 24` is a probe option
   (16 to 64); `--scratch-at` is `tri`'s only, so the texture base is moved by the program's T2
   immediate 0x5CAFC000 (the probe patches SCRATCH_IMM | k to the scratch address + k).

## Deviations from the plan

- R8-3 dropped (check 2): 60 jobs, not 66.
- R8-2: 19 jobs, not 15: the texel-tie readings are 4 jobs (one |ma| a job: a linear program cannot
  hold two constant major axes), and the control is counted.
- R8-1: the slopes are O8's (vertices inside the 1.25 box the TA clips to), not the ranking's.
- R8-4: N = 8 instead of N = 11 (the N = 8 and N = 2 programs are published in
  render/closing-s1/bins; N = 11's are not); forced below natural is rows 2 at N = 8 (natural 3).
  The forced-below row decides nothing (both rivals predict a changed image) and is kept as a
  reading with its render memory.

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E726, E844, E502, E504, E727,
E565 or E703's jobs); a control without its pixel rows stops the session (rc 25); the second row of
a stage without pixel rows stops that stage (rc 24, run/hooks.sh), and the driver goes on; less
than 300 MiB free on ~ (rc 22). The vdm rows are last and take the health pair after each job.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (the tables, predictions and programs are current).
- Dry run of check 3: `bash lead/dryrun_vdm.sh`.
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (`mock/world.py`): model, alt (every rival the other way), nopix (cube stops at its
second row without pixels, the rest runs), ctlnopix (premise stop), fault (vdm rc 4), hang (vdm rc
6).

## Replay vectors

- cube: `vectors/closing/r8-geo/cube.table.json`; replay: the sgx-pipe cube sampler test O2 adds
  (face select of E844 + the q284 (s, t), refusing exact ties) holds the (a) and (b) rows, ties and
  the edge rows refused; if O2's sampler has not landed at the fold, `refused` (no cube sampler).
- seam: `vectors/closing/r8-geo/seam.table.json`; replay: sgx-pipe's `isp::msaa_source` (E618's
  13 refused seam tiles) once the fold admits the seam tiles, else `refused` with E618's reason.
- addr: `vectors/closing/r8-geo/addr.table.json`; `refused`: no sampler models T0 address modes 4
  to 7.
- vdm: `vectors/closing/r8-geo/vdm.table.json`; `refused`: no simulator models a forced
  VDM_TASK1.OUTPUT_SIZE.

The replays read only kept files and the frozen predictions (session files) and the pins of
session.toml.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r8-geo`). bins/*.bin are our own probe programs (assembled from the pinned p1141
template by usse-asm; the vdm ones copied from render/closing-s1/bins), not tools.
