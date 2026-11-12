# r6-misc (round 6 session A of the ranking: Q289, Q287, Q086): run once; q287 to rerun on freeze 2

## Attempt 1 and freeze 2 (2026-11-12)

Attempt `out/20261112-144153` (freeze 1, rc 0) gave **Q289: M-OR held** (20 of 20 held-out rows, 8
of 8 separating; M-ADD refuted) and **Q086: H-COV held** (9 of 9; H-ANY refuted, 6 of 9; 11 rows
skipped by their groups); the lead has seen both verdicts. **Q287 was cannot tell**: freeze 1's
runner made no `$JW/depth` directory, so `--depth-dump "$W/depth"` (the tool writes
DIR/depth.N.bin into an existing DIR) printed `--depth-dump: No such file or directory` on every
row; no dump was written, so none was kept (the work directory was then removed). The audit of
the kept output against every file the scorers read (`score_m.REQUIRED`): q289 23 of 23 rows
and q086 10 of 10 have their output (the only file those scorers read); q287 lacks 20 of 20
dumps. q289's and q086's verdicts stand.

Freeze 2 changes the runner only (`run/run_stage.sh`: `mkdir -p "$JW/depth"`, keep
`$JW/depth/*`, and stop rc 23 when the output or a `--depth-dump` row's dump is not kept;
`run/lib_m.sh`: `has_kept`), `score/score_m.py` (`REQUIRED`, `missing_files`; no verdict
changed) and the tests (the fake tool now needs the dump directory as the real one does;
`tests/run_mock.sh` checks every stage's kept output against `REQUIRED` and fails on freeze 1's
runner, kept in `freeze1/run/`). **Tables and predictions are unchanged byte for byte**
(PREDICTIONS.sha256 identical to freeze 1's). Freeze 1 is kept in `freeze1/` (FROZEN.sha256
3199ecac..., PREDICTIONS.sha256 839d74ea..., FROZEN.commits, its laptop runner; FREEZE.txt).
TOOL6.sha256 holds the lead's t6 97df5c0e... (unchanged). **The rerun is q287 only, a new
attempt:** `run/stage_m.sh S6` (restages the fixed runner), then `run/m.sh S6 --only q287`
(20 jobs, about 3 minutes, no fault expected).


Built 2026-11-12, offline, against resgx545 main **d9b2969** (not moved). Nothing here touched the
laptop, cachix or a git repository. Plan: session A of `closing6/rank/rank-round6.md` (R6-1, R6-2,
R6-4), user decision `closing6/DECISIONS-R6.md` R6-2 (a) with R6-5 (a) and R6-6 (a). Read
`PREFLIGHT.md` before staging: **the lead builds one tool on cachix first** (below).

## What runs, in order (`stages.txt`)

| stage | jobs | tool | what | frozen prediction | fault limit |
|---|---|---|---|---|---|
| q289 | 23 | t4 | Q289's held-out fill row: 128 x 64 x and y pokes (16), 256 x 32 x pokes (4), 2 baselines, E876's 64 x 32 x ^ 0x10 control | M-OR vs M-ADD (hash, wrong pixels, unwritten tiles); 8 rows separate them | 1 (none expected) |
| q287 | 20 | t6 (t4 for one control) | E831's depth-band row at W 34, odd heights: dry 34 x 17 first (gateodd), controls 34 x 18 (t4, t6, x ramp), fit H 19 x 2, held out H 7, 11, 23, 35 x 2 and x-ramp H 19, 23, 35, confirm H 17, 21 | rule A vs FLOOR (and ROUND, CEIL, RSTRICT) stored sets | 1 (none expected) |
| q086 | 21 | t4 | E511's 20 skipped 4x cases (U2, U2Q, FX, HS kpoked words) + the 1024 x 768 R control, `--aa4` contexts (four arrays), every pixel | H-COV (complete iff the words' grid covers the target) vs H-ANY (all complete) | 3 (session budget) |

64 jobs in the tables. Under the frozen predictions q086 runs 10 of its 21 (R, the 6 U2/U2Q,
the first FX, the first two HS) and skips 11 by its hypothesis groups (u 1 fault, fx 1, hs 2):
**53 jobs run, 3 predicted faults** (all q086, 3D side). Rival H-ANY: all 21 run, no fault.
**Expected time about 12 minutes of jobs (a reset and kernel-log slice per job, q086's pixel dumps
the largest at about 9 MB of text), about 25 minutes with staging and the health after each
stage; plan 35.**

## Hypotheses and verdicts (`score/score_m.py`, frozen)

- **Q289** (E876, post hoc on both 64 x 32 sweeps; this row is held out): reading the poked field in
  half-tile units, tile t stores at op(2t, f) >> 1, nothing outside the target. Controls that can
  fail: E876's hash 0x97334f75829dab25 for 64 x 32 x ^ 0x10, the two baselines (0xf7befd67a3c8e325,
  the tool mock's). Verdict: which of M-OR / M-ADD matches every held-out row, decided on the 8
  separating rows; a hash on neither model or any `outside` above 0 refutes the reading.
  DECISIONS-R6 R6-6 (a): Q289 retires if this row picks OR or ADD.
- **Q287** (E730, E831): rule A (y + 0.5 < 1.25 H) against FLOOR at the odd heights 7, 11, 19, 23,
  35 (where they differ by one row inside the tile area); .25 cells 17, 21 confirm
  (A = FLOOR there).
  Controls: 34 x 18 reproduces E831's 924 (rule A's set) with t4, with t6 and with the x ramp (the
  t6 build must reproduce the rgn4 tool). Replicates are combined (disagreeing runs are mixed, never
  held). gateodd: if the module refuses 34 x 17 the stage ends cleanly (rc 21), Q287 is "odd heights
  refused", and the driver goes on to q086.
- **Q086** (E507, E511, E824): H-COV [infer, post hoc 6 of 6 on E511] against H-ANY. Control R at
  1024 x 768 (E824 h8's shape) must complete with 0 wrong. A completed row must have `diff: 0 of
  W*H` and H pixel rows; a fault must be the 3D-side class (BIF_INT_STAT 0x0100,
  BIF_FAULT 0x100000xx,
  E511's words), else the stage stops (rc 18). Either verdict narrows Q086 (the closed driver's rule
  over sizes still needs the capture batch); H-COV held gives `ta.rs` a validity rule for poked
  macrotile words at 4x.

## The tool built from main (t6): exactly how the lead builds and stages it

Q287 needs odd heights, which `~/sgxfive-test-rgn4` (4623753) refuses (`render: Invalid argument`,
checked in its mock) and resgx545 a6d78db allows ("libsgxfive: allow odd target heights").
**Build commit: resgx545 d9b2969** (the freeze commit; its `userspace/libsgxfive` tree c5e09973 is
a6d78db's, its `include/uapi` 6c3a6746), **build target `build/sgxfive-test`** in
`userspace/libsgxfive`, i686, in the build host's docker image as `tools/bringup/push-tools.sh`
builds it (`make -s CC=gcc build/sgxfive-test`, image `$SGX_TOOLS_IMAGE`, default
`sgxhumation/arch32:igt`). Source pin: `TOOL6SRC.sha256` (sgxfive-test.c d30cae0e...).

1. `lead/build_tool6.sh` (Mac): `git archive d9b2969 userspace/libsgxfive include/uapi`, checks
   sgxfive-test.c against TOOL6SRC.sha256, builds in `~/sgxt-r6m` on `$SGX_BUILD_HOST` (cachix; not
   push-tools.sh's `~/sgxt`), copies the binary back to `debug/tool6-i686/sgxfive-test` and prints
   its sha256 `S6`. It never reaches the laptop (the guard checks it).
2. `run/freeze_m.sh tool6 S6` writes `TOOL6.sha256` once (the slot; it refuses to replace a hash).
   FROZEN.sha256 and PREDICTIONS.sha256 do not include it and are already frozen.
3. `run/freeze_m.sh verify S6`, then `run/stage_m.sh S6` copies the binary to
   **`~/scratch/r6m/bin/sgxfive-test`** (and the runner) and checks its sha256 there.
4. `run/m.sh S6`: every verify, the runner's preflight (a stage with a t6 row refuses a binary that
   is not S6) and the scorers take S6 as their input.

## Round 4's two slips: impossible by construction

- **The mock answers by argv** (`tests/worlds.py`): the fake tools see only their own path (t4
  refuses odd heights as the rgn4 build does) and argv; no case name reaches them.
- **The argv-twin test** (`tests/test_twin.py`) parses every row back (tool, size, stride, poke,
  ramp, depth words and pages, kpokes, 4x options, group) and compares it with plan rows typed by
  hand from the ranking; each control is its record's kept command token for token (E876's sweep,
  E831's g-z controls, round 5's s0 4x row). `tests/mock_all.py` runs every row through its OWN
  tool's mock (t4 = 4623753, t6 = d9b2969, built on the Mac from the pinned sources): every odd
  height is refused by t4 and drawn by t6, the kernel pokes the tool writes are the row's, and a
  baseline fill's hash equals the frozen prediction (the model's FNV-1a is the tool's).
- **Scorers replayed before the freeze** (`tests/test_replay.py`): q289 on E876's 1536 kept cases
  (OR and ADD hold 1534 of 1534 pokes, XOR must fail 4, and the scorer must not pick OR or ADD on
  64 x 32; a doctored hash must refute both); q287 on E831's kept g-z with its real dump names
  (controls 924, 924, 3444; A and FLOOR 10 of 10; ROUND and CEIL must fail 10 of 10, RSTRICT 6 of
  10; a renamed dump is cannot tell); q086 on E511's 6 kept jobs with E507's 128 x 64 R (H-COV 6 of
  6, H-ANY must fail 3 of 6).
- **No timing window**: no held flow; the fake answers synchronously; every sleep is 0 in the mock.

## Laptop files (round 6)

Everything under `~/scratch/r6m/`: `run/` (runner, tables, FROZEN.sha256, TOOL6.sha256), `bin/`
(t6), `stage/` (empty: no program is staged), `out/ATT/STAGE`. Work directory one
`mktemp -d ~/scratch/tmp/r6m.XXXXXX` per stage run, each job's subdirectory removed once its files
are kept, the whole directory at exit; at least 200 MB free on `~` before each job (rc 22). Never
`/tmp`. Debugfs writes: `reset 1` only (no knob). The tool writes its own kernel pokes through
debugfs kpoke (q287's --depth recipe as E831; q086's --kpoke-render words as E511); the reset
before each job and at exit disarms what a job left.

## Layout

- `tables/STAGE.txt` (`name|set|risk|knobs|tool|command`), `TABLES.md`, `predictions/STAGE.tsv`
  (`case quantity value model set`), `PREDICTIONS.sha256`, `FROZEN.sha256` (every generator,
  model, scorer, runner, table, prediction, pin file, lead script and, by absolute path, resgx545's
  scorekit.py and health.sh and the resgx545-data files the generator read: `gen/data/sources.lst`),
  `FROZEN.commits`, `TOOL.sha256` (t4), `TOOLSRC.sha256`, `TOOL6SRC.sha256`, `TOOL6.sha256` (the
  slot), `stages.txt`.
- `gen/`: `m6gen.py` (writes tables, predictions, TABLES.md), `models.py`, byte copies `r3_geo.py`
  (round 3's published model) and `rules1126.py` (E511's published rules), `frozen_commits.py`.
- `score/`: `score_m.py` (stages and `verdict`; refuses unless `freeze_m.sh verify S6` passes),
  `scorekit.py` (= main's tools/closing/scorekit.py at d9b2969).
- `run/`: `stage_m.sh`, `m.sh` (Mac), `run_stage.sh` + `lib_m.sh` + `m.env` (laptop),
  `freeze_m.sh`, `guard_m.sh`, `lib_check.sh`. `lead/build_tool6.sh` (Mac and build host only).
- `tests/`: `run_all.sh` and the tests above, `worlds.py`, `fake_tool4.sh`, `fake_tool6.sh`,
  `shims/`. `debug/` is scratch (mock builds, test runs).

## Publishing

Nothing here is firmware-derived (no disassembly reading, no script importing one): the whole
directory may be published by the fold. `debug/` is scratch and is not published.

## Deviations from the plan

1. **Q291 is not in this session (0 of its 6 jobs).** Its reworded test reads the iterated clip x
   past the target through a per-instance store to scratch at the pixels of the tile area. No
   landed pixel program stores an instance's attribute at a scratch address formed from its
   position (the E606 `--pixels` form prints the target and the changed scratch dwords; every
   existing scratch-storing template, e.g. probes/pds/templates/pa_sa_dump.s, stores at fixed
   offsets, so instances overwrite each other). Writing and checking such a program (position to
   address, assembled, replayed in sgx-sim before any run) is new tooling, not a build of this
   session. Proposed for round 7, after Q287 closes the depth side.
2. **Q086's fault budget meets H-COV.** The ranking expected the 20 cases to run; the frozen H-COV
   (post hoc 6 of 6) predicts 14 of them fault. With the decided budget of 3 the FX and HS
   families each run until their group count (fx 1, hs 2) and skip the rest; the 6 U2/U2Q rows,
   where H-COV and H-ANY both predict completion and a fault refutes H-COV, all run first. If H-ANY
   holds, all 21 run.
3. **Q287 has x-ramp rows at 19, 23, 35** (3 jobs, not in the ranking's list): the same band read
   with E831's other ramp, so a held A does not rest on one ramp. 20 depth jobs as planned.
4. **No `--dump-render` or `--regs`** (not needed by any verdict); q086 rows add `--pixels` (E511's
   form) and keep stderr apart, so a tool message cannot split a pixel row (E511's correction).
