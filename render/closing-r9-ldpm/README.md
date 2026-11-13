# r9-ldpm: round 9's DPM session S9-ldpm (Q210, Q211)

Round 9, session S9-ldpm of `closing9/seeds/exp-seeds-r9.md` section 7 (DECISIONS-R9.md: R9-5 (a),
safe class only: no held reset, no planned fault, no `expectfault` row, `#limit 0` in every
table). Built offline 2026-11-13 on the session kit, scaffolded by `tools/closing/new_session.py`
from resgx545 main f32dfac and resgx545-data 2d666bfaf. Nothing here touched the laptop, cachix or
a git repository. Record numbers reserved for the fold: E960 to E963.

## The offline steps, run first (`offline/`, each frozen before its scoring)

- OD-1 (`od1_wide.py`, FREEZE-od1.sha256): E874's replay gives the need of all nine kept
  calibrations of the 1500-vertex scene; HU1 of its 500 triangles gives none (0x52 against 0x213
  at 2048x2048), so HU1 is not this scene's need and stays a tally. Four wide targets never run,
  each U below 0x3f0: 4096x1024 (U 0x20f), 4096x1536 (0x302), 3584x1024 (0x1d0), 2048x512
  (0x9a), with one F9 cell each.
- OD-2 (`od2_band6.py`, FREEZE-od2.sha256, OD2-FIX.md): the "left 0x6" cells are the reader's last
  sample before the global list was trimmed (the next sample reads 2; 94 of 98 kept rows read the
  same either way, the other two are step cells). One reader fix after the first run (OD2-FIX.md).
  Frozen: H-NEXT1, band 6 keeps the second page until the object after the straddling block
  (b_6 + 1) is tiled: 2 of 2 fit (3072x3072, 2560x2560) and 8 of 8 SEMI (E936's eight other
  targets), where H-SPAN (A_6) gives 4 of 8.
- OD-3 (`od3_fit.py`, `od3_score.py`, FREEZE-od3.sha256): a closed family of six multi-kick count
  rules fitted on OL7 (b)'s 31 cells; the best, H-FLUSH (30 of 31), was frozen and gave 7 of 20 of
  E938's cells (H-KICKS 11). Below 18: **stage k2 does not run** (R9-5 (a)).
- `r9_tables.py` (FREEZE-tables.sha256, two runs: run 2 picked m6b targets where H-NEXT1 parts from
  H-SPAN, run 1 having found three of the plan's four where it does not) writes
  `r9_tables.json`; `gen/r9_tables.json` is its byte copy.

## What runs

Laptop prefix `~/scratch/r9l/`, module B60AB0B475DD1E8972419B5 (fork 2a650d74, loaded since the
one-shot boot of 03:11). Tool t4 `~/sgxfive-test-rgn4` (e6951558..., source resgx545 4623753
`userspace/libsgxfive/tools/sgxfive-test.c`, sha256 703cbcea..., replayed row by row on its library
mock) run under `~/regtimeline` (079f6359..., `wraps = true`) with R5-dpm's 16 registers; both are
on the laptop and bound by their sha256, nothing is built or shipped. The one program binary is
`bins/p1139-green.bin` (the pinned `data:render/closing-r7-dpm/bins/p1139-green.bin`).

| stage | jobs | what | label | stops |
|---|---|---|---|---|
| a0 | 6 | r8-ldpm's a0 rows token for token (E935) | control | a control off (rc 24) or unread (rc 25): no later stage opens |
| m6b | 34 | six E936 replicates (1536x1536 0x109 to 0x10b, 4096x2048 0x362 to 0x364); at 2304x2304, 2048x2304, 2304x1792 and 1792x1792 a calibration, A_6 - 1 .. A_6 + 3 and A_6 again dumped | control, held out, explore | none of its own (a replicate off gates the verdicts) |
| w | 8 | OD-1's four wide targets: calibration at P 0x422 and one F9 cell | control (need), held out | none of its own (a calibration off gates its cell) |
| f9b | 11 | 1280x1280, 1792x1792, 2560x2048: calibration, one or two cells off band 4, one band 4 cell | control, held out | a calibration's need off (rc 24) |

**59 jobs** in the order a0, m6b, w, f9b; about 11 minutes (r8-ldpm's 161 jobs took 30). Every
stage after a0 is `gate = true`. Stop budget: no fault planned; any fault, hang, -110, failed
health, an rc 3 without "scene overflowed the parameter buffer" (`expect:rc3-overflow` is a probe
row's expected end) or a `tri` rc 1 without `job: ok` and its diff line stops the stage (rc 4) and
the session. `min_free_mb` 300, `job_timeout` 120 s. No `--vtx-coords` row: OD-1 froze no need
for the 8-pair scene (E937), so none runs and E937's pairing rule holds trivially.

Deviations from the plan's section 7 table: f9b is 11 jobs, not 9 (each target has its own
calibration, and 1280x1280 has one cell off band 4); w's calibrations gate their own cell instead of
stopping the stage, since each calibration's need is OD-1's held-out reading; m6b's targets are
2304x2304 and 1792x1792 of the plan's and 2048x2304 and 2304x1792 (run 2 above); k2 is not built.

## Predicted outcomes (frozen in `predictions/`, from `gen/r9_tables.json`)

- a0: E935's readings again (S2 to S7 in their brackets, need 0x213, 2 / 1 / 1 pages left at
  c4-b5, c4-b6, t-s3m6, two partial renders with peaks 0x80, 0xa0, 0x2 at g-qf).
- m6b: `gps_next` per cell. H-NEXT1 (frozen by OD-2) against H-SPAN, H-NEXT2 and E936's three
  class rivals at the A_6 cell; they part at 2304x2304 (end A_6 + 2), 2048x2304 (A_6 + 3) and
  2304x1792 (A_6 + 1); 1792x1792 is a target where they agree (end A_6). The calibrations' steps
  and need: E874's replay (H-STEPMODEL). H-SPAN-AL (E936's alignment) tallied.
- w: each calibration's need is E874's U (H-REPLAY) against HU1; the cells' F9 count and run peaks
  against E854's d = 7/4 and d = 1, E625 and the abort's global pages (E935's rule).
- f9b: F9 off band 4 (counts and peaks, with R-5's raise); at band 4, F9 raised (1 partial render)
  against H-NORAISE (2; E938's band 4 reading); d = 7/4, d = 1, E625, H-ABORT.

## Layout

- gen/plan.py (tables and predictions; `--check`), `gen/r9_tables.json`; `offline/` (OD-1 to
  OD-3, the tables, their freezes and outputs).
- score/score.py (scorekit and kitscore), score/read.py (r8-ldpm's reader with `gps_next`).
- run/hooks.sh: `rd_words` (the same reading in awk; tests/test_read.py holds the twin),
  `hook_reading`, `hook_check` (a `ctl:KEY=VALUE` word off stops the stage).
- `mock/world.py`: seven worlds (model, ctloff, noread, fault, rc3other, m6boff, f9boff).
- `tests/`: test_plan.py (generator, counts, safe class, session.toml, a0 the argv twin of r8-ldpm's
  published a0, the strict fake takes every row, the offline freezes and outputs), test_read.py,
  test_score.py (holds on r8-ldpm's kept a0 and m6 replicate cells; fails on swapped or knob-moved
  ones, on another target's calibration in f9b and w, w's gate only on its own cell).

## Commands

- Offline: `bash tests/run_all.sh` (guard, own tests, library mock of every row, mock of every
  world, verify).
- Freeze: `python3 kit/session.py freeze .` (never rewritten).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .` (stop codes:
  kit/session.py), with `SGX_TARGET_HOST` set; afterwards move `~/scratch/r9l` to
  `~/scratch/archive/`.

## Replay vectors

- m6b, w, f9b: measured steps, pages left, needs and partial-render counts become `sgx545-tables`
  (`tools/usse-asm/closing_tables.py`) tables `dpm/r9-ldpm-m6b`, `dpm/r9-ldpm-w`,
  `dpm/r9-ldpm-f9b`; replay: the sgx-pipe `dpm.rs` step and margin tests (`tool_triangle_steps`,
  `first_partial_render_global_pages_left`; band 6 by H-NEXT1 if it holds) and the need
  (`tool_triangle_steps`' U at the wide targets). They read only the kept `out/` files and
  `gen/r9_tables.json`. f9b's counts: `refused` until a raise rule for band 4 holds (F9 against
  H-NORAISE is what the stage decides).

## Publication

No file reads a firmware image, listing or closed binary: nothing is marked for data-private.
`offline/` is publishable as it stands (`cited-scratch:closing9/r9-ldpm/offline/`); its scripts
read only resgx545-data and the scratch copy of render-closing-r8-ldpm (byte-identical to the
published one, tests/test_plan.py). `debug/` is scratch.
