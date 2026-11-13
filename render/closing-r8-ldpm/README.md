# r8-ldpm: round 8's leftover DPM session L1 (Q210, Q211)

Round 8, session L1 of `closing8/leftovers/exp-leftovers-r8.md` (DECISIONS-R8.md R8-8: round 7's
leftovers with the kit, safe class only: no held reset, no planned fault, no `expectfault` row,
`#limit 0` in every table). Built offline 2026-11-13 with the session kit, scaffolded by
`tools/closing/new_session.py` from resgx545 main 91f21da (the kit with `expect:rc3-overflow` and
`wraps = true`) and resgx545-data ca742f30e. Nothing here touched the laptop, cachix or a git
repository. Record numbers reserved for the fold: E935 to E939.

## What runs

Laptop prefix `~/scratch/r8l/`, module 37EC97AB0CB37213C42FCCC (fork 664fd0d0, loaded now), before
the round 8 kernel boot (R8-5). Tool t4 `~/sgxfive-test-rgn4` (e6951558..., source resgx545 4623753
`userspace/libsgxfive/tools/sgxfive-test.c`, R7-dpm's TOOLSRC.sha256) run under `~/regtimeline`
(079f6359..., S1's, tool `rt`, `wraps = true`) with R5-dpm's 16 registers: every row's args are
`0 0.3 REGS -- "$HOME/sgxfive-test-rgn4" ...`. Both tools are on the laptop already and are bound
by their sha256; no binary is built or shipped. The program binaries in `bins/` are ours:
`p1139-green.bin` (R7-dpm's, the pinned `data:render/closing-r7-dpm/bins/p1139-green.bin`),
`vtx_coord4.bin` (`asm/vtx_coord4.s` = the pinned `probes/tsp/templates/vtx_coord4.s`) and
`vtx_coord8.bin` (`asm/vtx_coord8.s`, new: o0 to o11 all written; assembled with
`tools/usse-asm/usse-asm`, run in `sgx-sim --task vertex` to its emit with o4 to o11 set,
tests/test_plan.py).

| stage | jobs | what | label | stops |
|---|---|---|---|---|
| a0 | 6 | R7's s-a0: two 2048x2048 calibrations, c4-b5, c4-b6, t-s3m6, g-qf at P 0xa2 | control | a control off (hook_check, rc 24) or without a reading (rc 25): no later stage opens (gate) |
| sp | 20 | steps pinned by the abort's global page count: 2048x3072 thr0 0x232..0x236 and 3 calibrations, 2048x4096 0x125..0x12e; controls 0xe8 (3 pages), 0xe9 (4) | control, held out | a control off: rc 24 |
| m6 | 69 | band 6: 3072x3072 0x3ce..0x3d8 and 2560x2560 0x2b0..0x2b5 mapped with dumps (fit); calibration and A_6 - 1 .. A_6 + 3 at seven targets; band 7 of 2560x2560, band 4 of 3072x3072 | control, fit, held out, explore | a control off: rc 24 |
| v | 14 | the N 4 control (R7's v-cal-c4), written N 8 (`vtx_coord8`) x3, written N 4 x2, plain N 8 x2, six written N 4 cells; all dumped | control, held out, explore | the control off: rc 24 |
| f9 | 18 | 1536x1536 and 1024x1024 at thr0 0x24, 0x30, 0x48, 0x60, 0x90, 3072x2048 at 0x60, 0x90, 0xc0, 0x120, 0x1a0, each with its calibration | control, held out | a calibration's need off: rc 24 |
| k | 25 | five multi-kick scenes (2048x2048 K 2, 3, 4; 4096x4096 K 2, 4), calibration (2048 ones dumped) and four cells | held out (need), explore (counts) | (gate only) |
| u | 9 | eight one-triangle shapes (`--tri-unit 12 --tri-v`) at P 0x422, s22's calibration as control | control, held out | the control off: rc 24 |

**161 jobs**, in the order a0, sp, m6, v, f9, k, u; about 30 minutes (the plan's 28; m6's 17
mapped rows dump 3072x3072 and 2560x2560 targets). Every stage after a0 is `gate = true`: it opens
only when a0's six controls passed. Stop budget: no fault planned; any fault, hang, -110, failed
health, an rc 3 without "scene overflowed the parameter buffer" (`expect:rc3-overflow` is the only
expected end of a `probe` row) or a `tri` rc 1 without its diff line stops the stage (rc 4) and the
session. `min_free_mb` 600, `job_timeout` 120 s.

## Predicted outcomes (frozen in `predictions/`, from the OL7 tables)

- a0: R7-dpm's kept readings repeated (S2 to S7 in their brackets, need 0x213, c4-b5 2 pages left,
  c4-b6 1, t-s3m6 1, g-qf 2 partial renders with peaks 0x80, 0xa0, 0x2). R-5's class (`cls`) is
  not read: the kit keeps no control block (buf09) (deviation from R7's s-a0).
- sp: H-STEPMODEL (E874: 2048x3072 S6 0x233, 2048x4096 S3 0x129) against H-R7S6 (S6 0x234) and
  H-KEPTS3 (S3 0x12c): gps_abort = 1 + steps below thr0 parts them at 0x234 and 0x12a to 0x12c.
- m6: at the A_6 cell (calibration-aligned) H-SPAN 1 page left everywhere; H-BIG6 2 where both
  sides are above 2048 (2560x3072, 3072x2560, and the mapped 3072x3072, 2560x2560); H-ANY6 2 where
  either side is; H-6LATE 2 everywhere but 2048x2048 (tallied). H-BIG6 and H-ANY6 are post hoc
  readings of E915's two misses [infer].
- v: H-DET, the three written N 8 calibrations give the same steps, need and object block sizes;
  one differing refutes it and P3 (OL7 (a), `--vtx-coords` leaves o4 on unwritten) [infer].
- f9: F9's partial-render count and run peaks (2 to 7 renders); rivals E854's d = 7/4 and d = 1
  (counts) and E625's boundary (an overflow iff thr0 < U). H-CUM (plan: tallied at v) is not
  computed (deviation: explore only).
- k: the calibrations' need = HU1 of the union (held out); counts and peaks of H-KICKS (OL7 (b))
  against H-UNION, explore: OL7 (b) did not reproduce 4 of 31 kept multi-kick cells (stacked
  scenes with a partial render in a later kick), so by the plan k runs labelled explore.
- u: HU1 against H-BBOX (a stream for every region of the bounding box): the slivers part them
  most (15 against 257 pages); every shape's U under both stays below 0x3f0.

## The offline prerequisite OL7 (run first, in `closing8/leftovers/`)

Copied into `gen/ol7/` byte for byte (tests/test_plan.py compares them with the leftovers):

- (a) `ol7_a_dumps.py`, frozen by `FREEZE-ol7a.sha256` before its run: P3-DUMP HELD, R6-dpm's
  and R7-dpm's N 4 calibration dumps hold the same 100 object blocks, their N 8 dumps none alike
  (97 and 94 objects, 47 blocks of another size).
- (b) `ol7_b_multikick.py` (H-KICKS, E875's replay with G4's reading over kicks), frozen by
  `FREEZE-ol7b.sha256`: a FIT on 31 kept cells of s1 g-e2a, g-e2b and r1-pixgeo g-u1, counts 28 and
  every peak 27 (H-UNION 28 and 25); it misses b-2s-lo, k-4a-P1, k-4a-P2 and b-4s-lo.
- (c) `ol7_c_tables.py` -> `gen/ol7_tables.json` (sha256 ba59dc3a... in `FREEZE-ol7c.sha256`):
  the models, F9's cells, the u shapes and the k scenes. Its first run was stopped for speed with
  no output; its second run's k cells (thr0 2 to 5, up to 34 partial renders) were refused at the
  build (kept as `ol7_c_tables.run2.out`); the third bounds a cell to 10 partial renders.

## Layout

- gen/plan.py (tables, predictions; `--check`), `gen/ol7_tables.json`, `gen/ol7/` (OL7).
- score/score.py (scorekit and kitscore), score/read.py (R7-dpm's reader, without buf09),
  score/pinned.py (stage v's dump readers loaded from their blobs at the pinned commits).
- run/hooks.sh: `rd_words` (the same reading in awk; tests/test_read.py holds the twin on kept
  R7-dpm jobs), `hook_reading`, `hook_check` (a `ctl:KEY=VALUE` word off stops the stage).
- `mock/world.py`: six worlds (model, ctloff, noread, fault, rc3other, f9off).
- `tests/`: test_plan.py (generator, counts, safe class, session.toml, the argv twin of R7-dpm's
  repeated rows, the strict fake takes every row, OL7 copies, bins), test_read.py, test_score.py
  (holds on R7-dpm's kept a0, sp, m6, v, u control jobs; fails on swapped or knob-off ones; H-DET
  held on one run thrice and FAILED with R6's among them).

## Commands

- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify; about 3 min).
- Freeze: `python3 kit/session.py freeze .` (done 2026-11-13; never rewritten).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .` (stop codes:
  kit/session.py), with `SGX_TARGET_HOST` set; afterwards move `~/scratch/r8l` to
  `~/scratch/archive/`.

## Replay vectors

- sp, m6, f9: measured steps, pages left and partial-render counts become `sgx545-tables`
  (`tools/usse-asm/closing_tables.py`) tables `dpm/r8-ldpm-sp`, `dpm/r8-ldpm-m6`,
  `dpm/r8-ldpm-f9`; replay: the sgx-pipe `dpm.rs` step and margin tests (E874's model, H-SPAN, F9).
  They read only the kept `out/` files and `gen/ol7_tables.json` (a session file).
- v, k, u: `refused` until a rule holds (v: no step rule for written N 8; k: H-KICKS is not a fit;
  u: HU1 on new shapes is held out here first).

## Publication

No file reads a firmware image, listing or closed binary: nothing is marked for data-private.
`asm/` and `bins/` are our own programs. `debug/` is scratch.
