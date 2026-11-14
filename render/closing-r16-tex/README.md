# r16-tex

Round 16's session r16-tex (closing16/plan/rank-round16.md sections 2 and 3, decision R16-7 (a) of
closing16/DECISIONS-R16.md), built with the session kit (resgx545 HACKING.md, "Session kit"),
scaffolded by `tools/closing/new_session.py` from resgx545 b2b5288c82ed (kit/ is that commit's
blobs), data 62cb03b369ca. Predecessor: closing15/r15-tex (stage ty, record E1055) and its fold.
Generator: gen/make.py with gen/ty.py (this session's); gen/tex.py is r15-tex's unchanged,
gen/pins.py
has its temp prefix renamed; r15-tex's chain stage, gen/chain.py, gen/prog.py and gen/addr.py are
not carried. Every repository file the generator reads is read at the frozen commits (gen/pins.py)
and pinned. Record **E1065** (ty, Q177).

## What runs

One stage, **ty**, 15 jobs, laptop prefix `r16t` (files under `~/scratch/r16t/`), one binary:
`~/sgxfive-test-t10` (t10, sha256 9bedc2d6...), bound by source to resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`), recipe
`data:render/closing-r10-st1/lead/build_tool10.sh`. Every row is a `probe --temps 32 --coords
--pixels --scratch-pages 32` fill of a program of ours (the kit's library-mock replay runs all 15:
"program not simulated"). Module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no
debugfs knob is written. Safe class: no planned fault, no expect-fault row, no held reset, `#limit
0`.

Order: the control, then per size the mode 0 reference of a type followed by its rows:

| rows | what |
|---|---|
| ty-ty1u4r | control that can fail: E1055's ty-ty1u4r rerun (r14-tex's addr5-ty1-u4 program, its kept image) |
| ty-08-ty1-u0, -u4, -u5 | type 1 at 8 x 8: the reference, mode 4, mode 5 |
| ty-08-ty4-u0, -u4 | type 4 at 8 x 8: the reference, mode 4 |
| ty-64-ty1-u0, -u4, -u5, -u6, -u7 | type 1 at 64 x 64: the reference, modes 4, 5, 6, 7 |
| ty-64-ty4-u0, -u4 | type 4 at 64 x 64 |
| ty-6416-ty1-u0, -u4 | type 1 at 64 x 16 (W = 64, H = 16) |

Every row at base 0 of the 32-page named scratch (dword i = 0xD0000000 | i, T2 0x5CAF0000), the
programs E567's rt1-2d (type 1) and rt4-2d (type 4) with T0's u mode, T1's size and the `map` widths
changed (u maps log2 W bits of x, v log2 H bits of y; 64 x 64's texel rows 32 to 63 are never
drawn: the fill is 64 x 32). Type 3 is E1055's twin of type 1 (the same fit) and is not run.

## Frozen (gen/ty.py; per-pixel files predictions/ty/NAME.MODEL.txt, form and rel lines of ty.tsv)

E1055's post hoc fit on its two sizes (tests/test_gen.py replays it on all its kept rows): every
mode 4 pixel is a name with each byte halved, rounded up, the 32 rows alike, and
**N13 = 39 W + 52 + (x mod W)** (types 1 and 3), **N4 = 40 W + 20 + (x mod W)** (type 4); modes 6
and 7 read mode 4's last column; mode 5 one other halved name (163 at 16 x 16); the mode 0
reference reads dword stride * (y mod H) + (x mod W), stride W (types 1 and 3), 32 (type 4).
All sizes here are held out; the labels are `heldout`.

- mode 4: **N13 / N4** against **NQ13 / NQ4**, the other two-point form c0 + k W^2 (520 / 3796 at 8
  and 64, types 1 and 3; 500 / 3860, type 4), and at 64 x 16 **N13-H** (the form in H = 16: 676 +
  (x mod W)); forms H-HALF, H-LIN1 (c is free per row: it holds on any linear name map, so it does
  not part NQ), H-WHOLE; H-MODE0 (the row reads its reference of this run, `rel`).
- modes 6, 7 (64 x 64): **L13** (every pixel 39 W + 52 + W - 1 = 2611, halved) against LQ13 and
  H-AS-U4 (the mode 4 image: E1055 0 of 6 at 16 x 16).
- mode 5 (8 x 8, 64 x 64): H-FLAT (one value on every pixel: a form, no number frozen); the row's
  lowest names are printed (the fit for the constant: three sizes with 16 x 16's 163); H-AS-U4,
  H-HALF, H-MODE0.
- references: **R-W** (types 1, 3; stride W: 8, 64, 64 x 16), **R-32** (type 4) against R-16, R-32
  (types 1, 3) and R-2W, R-W, R-16 (type 4).

Expected, not frozen: both fit forms hold (the weakest guess: two points do not part W from a
second form; NQ is the rival the sizes 8 and 64 part by 156 and 1248), L13 on modes 6 and 7, H-FLAT
on mode 5, R-W (types 1, 3) and R-32 (type 4) on the references; H-MODE0 and H-WHOLE fail on every
mode 4 row. At 64 x 16 N13 (W) and N13-H (H) part (max(W, H) = W: README "Deviations" 3).

## What each verdict does

Q177 narrows (R16-7 a): the size form of the name (N13 / N4 on three more sizes, W against H at 64 x
16), modes 6 and 7 (L13 held out) and the references hold or fail as frozen; mode 5's constant gets
three sizes for a fit, held out in a later round (R16-7 b). "What the half is" and "which of the two
names" stay open. A failed frozen row is not explained away post hoc for a retirement
(DECISIONS-R16.md); post hoc fits, if any, go in the fold's NOTES as such.

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the stage and the session (rc 4 / 6; none in E1055's, E567's or E1039's
jobs; every frozen model's read is inside the 32 mapped pages, tests/test_gen.py); the control
without its pixel rows stops the session (rc 25); the second held-out row without its 32 pixel rows
stops the stage (rc 24, run/hooks.sh); less than 300 MiB free on ~ (rc 22). Stop budget: `#limit
0`, 0 faults and 0 hangs expected. A stop is not a finding (E934).

Expected time: probes under 2 s each plus the runner's reset, snapshot and health (about 6 s a
job): about 1.5 minutes of jobs, about 5 with staging and preflight; stage alarm 15 minutes.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest, numpy), which the offline
  tests use unless `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (mock/world.py): model (the tested models: the control's kept image, N13 / N4, L13,
R-W / R-32, mode 5 one flat name: stage 0), alt (the rivals NQ13 / NQ4, LQ13, R-16 / R-2W and the
mode 4 image on mode 5: stage 0, rows FAILED), nopix (no held-out row prints pixels: rc 24 at the
second), ctlnopix (the control without pixels: the premise stops the session, rc 25), fault (the
first held-out row faults: rc 4), hang (the first held-out row does not return: rc 6). A fill
program whose named reads pass the row's scratch faults in every world.

## Deviations from the plan

1. **15 jobs, not 14.** The plan's 14 lacked the mode 0 reference of the 64 x 16 row; the lead's
   prompt asks every mode 4 row for its reference at its size (the premise check of section 3).
2. **Type 3 is not run.** Types 1 and 3 share the fit (E1055: N13 on both at 16 and 32, kept rows
   replayed in tests/test_gen.py); the plan's rows name types 1 and 4.
3. **64 x 16 does not part W from max(W, H).** The plan says "W against max", but with W > H the
   two are the same number (64): the row parts {W, max} from H only. W against max needs H > W (a
   16 x 64 row, two more jobs, not added: the plan's count and R16-7 a). Reported to the lead.
4. **H-LIN1 is not selective** (one free c per row): any linear name map holds it, NQ13 included at
   8 x 8 (tests/test_score.py). It is kept as E1055's form, the verdict rows are N13 against NQ13.
5. **Added frozen forms** (not in the plan): L13 / LQ13 for modes 6 and 7 at 64 x 64, H-FLAT for
   mode
   5, NQ4 (type 4's two-point quadratic: 5 / 6 W^2), the reference strides (the plan names none).
6. **The control is one job** (the plan: ty-ty1u4r only; r15-tex's ty-ctl is not rerun).

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors table (closing_tables.py, `sgx545-tables`) | replay |
|---|---|---|
| ty | `vectors/closing/r16-tex/pixels/ty.table.json` | sgx-sim tex.rs types 1 and 4 in u mode 4 and mode 0 at 8 x 8, 64 x 64 and (type 1) 64 x 16, E1065's halved names, the table's kept pixels held by its tests, if N13 / N4 hold on every mode 4 row; modes 5 to 7 stay refused (E1055 named; E1065 added); otherwise the table is refused (digests), as r15-tex's |

The replays read only kept files, the frozen predictions (session files) and session.toml's pins.

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`render/closing-r16-tex`). bins/*.bin are our own probe programs (assembled from the pinned p1141
template by usse-asm) or published bins of earlier sessions (r15-tex's ty-ty1u4r), not tools.
`debug/` (the mocks, the pre-freeze fit debug/fit.py) is not published; the fit is replayed by
tests/test_gen.py, which is.
