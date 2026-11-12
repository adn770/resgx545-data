# R6-dpm: laptop session r6-dpm of round 6 (Q210's steps, margin and bursts; Q211's count): freeze 2 (attempt a1 stopped in r-a0 on a runner slip; a2 to run)

Built offline 2026-11-12 from the approved plan `closing6/dpm/exp-dpm-r6.md` (DECISIONS-R6.md R6-2 (a);
the plan's own decisions all (a): six stages, r-v run, oomring2 tried with the fallback, four r-b
scenes). Nothing here touched the laptop, cachix or a git repository; nothing is committed; the
repository's clean-room guard was not run (the session has its own, `run/guard_r6.sh`). Read
`PREFLIGHT.md` first (time, controls, stops, risks, deviations).

Frozen against resgx545 main d9b2969 (the round 6 offline folds E873 to E875 on it). Every
prediction starts from the frozen offline rules of `closing6/dpm/offline/` (FREEZE-f*.sha256),
imported from their published copy (resgx545-data `cited/closing6/dpm/offline`, e5cdaf0a) by
`gen/r6model.py`, which refuses to load a file whose hash is not the FREEZE file's:
H-STEPMODEL and H-PHASE (f5lib, f5_stepmodel: E874), the timeline burst-end rule (f4_phase),
F9's replay (exploratory), H-REPLAY's walk orders and E854's spacings (f7_replay: E875), H-IV
(f1: E873), R-5's guard (3d.md 6.4).

## What runs (one session, laptop prefix `~/scratch/r6d/`)

| stage | jobs | what | stops |
|---|---|---|---|
| r-a0 | 7 | premise: 2048 calibrations at P 0x162 and 0x422 (complete), c4-b5 R, c4-b6 N, t-s3m7 left 2, t-s3m6 left 1, g-qf P 0xa2 count 2 | any control off, knob proof, non-monotone steps: rc 10, the session stops before r-m; a capture not whole: rc 13 |
| r-m | 15 | held out: 2048x2048 thr0 B-2..B+2 around B5 0x176, B6 0x1c1, B7 0x20c | any hang/fault |
| r-n | 21 | held out: 2048x1024, 1024x2048, 1536x1536: calibration + B3-1, B3, S4-1, B4-1, B4, S5-1 | any hang/fault; a calibration off the model re-picks its B cells |
| r-v | 6 | discriminating: 2048x2048 `--vtx-coords 4` and `8`: calibration with dump, then E-1, E | the calibration not a 1500-vertex scene: its cells skipped; its dump missing: rc 13 |
| r-b | 40 | 4 g-qf controls; scenes s262, s243, s220, s179 (4096x4096 moves): calibration + 8 cells each | a scene whose U is not HU1's: its cells void |
| r-k | 8 | LAST, R5-dpm's oomring armed before each job: c4-b5, c4-b6, c4-b3, S3, S4+1, t-s3m6, 2048x4096 creep cell x2 | EDM stall: reset once; a second: rc 11 |

**97 jobs**, order r-a0, r-m, r-n, r-v, r-b, r-k. Expected about 25 minutes (2048-class jobs 9 s,
the smaller targets about 7 s, r-b 15 to 25 s a job, r-k about 13 s, six stage starts with health
and copies 25 s each); plan for 45. Stop budget: no fault planned (every row class "safe": rc 3
"scene overflowed" is the normal end); any hang, fault, -110, kernel watchdog or failed health
stops the session; one EDM stall in r-k; free space below 200 MB before a job: rc 13, the job not run.

## Predicted outcomes (frozen in `predictions/`, readable in `TABLES.md`)

- r-a0: steps in their brackets incl. S6 0x181, S7 0x1ca (E873), need 0x213 with no partial render.
- r-m (H-PHASE, held out): left 2, 2, 1, 1, 1 around each B; the timeline rule's rival (E5 0x178,
  E7 0x1cc) differs at 4 cells (band 5 two, band 7 two). F9: one partial render each (exploratory;
  so no class is predicted: the raise is decided at a second abort).
- r-n (H-STEPMODEL + H-PHASE, held out): steps and U of the model (U 0x115, 0x120, 0x13a: each
  calibration completes); left 2, 1, 1 in bands 3 and 4; raise at B3 - 1, silent at B3 and above.
- r-v: H-BURST-CAP's steps bunch (N 4: 0x4f, 0x52, 0x9b, 0x9f ...; N 8: 0x4f, 0x50, 0x53, 0x99 ...)
  where H-BURST-PAGE's keep one step a burst (0x4f, 0x97, 0xe1, 0x12b ...); the calibration
  decides, at the L read from its dump (L0 = 67 + 15 N [infer, 3d.md 10.1]). E874's dumps read
  CAP. The cells test H-PHASE in the new scene under each hypothesis.
- r-b (H-REPLAY in row order, E875 post hoc there, now held out): counts and every run's peak per
  cell; column order (W*), d = 7/4 and d = 1 tallied; row and column differ at 3 to 5 of 8 cells a
  scene. Controls 4, 3, 2, 1 (E832); calibrations U = HU1 (262, 243, 220, 179).
- r-k: `sa8 & 0x380` at the decision entry 0x180, 0, 0, 0x180, 0, 0x180, 0, 0 (R-5); the creep
  cell (2048x4096 thr0 0x24a, dword 36 = 2, 1 page left, 2 partial renders by F9) reads 0 if
  `isub16` is source 1 minus source 2 (E864's [infer]), 0x180 the other way. The counts at the
  passes cannot be read (below).

## r-k runs R5-dpm's oomring (the plan's fallback)

`gen/gen_oomring2.py` writes `asm/oomring2.s` (oomring + `ldr` of 0x0724 and 0x072c). Both the
landed verifier and the rgn4 fork's own (host build at a2788bd86537) refuse it, "ldr of a register
not on the list" (the fork's ldr list is 7, 8, 81, 517, 670); with the two indices at #81 both
accept it (`tests/test_oomring.py`). So r-k arms `bins/oomring.blob`, R5-dpm's blob byte for byte
(sha256 5b2fcf02...), which the fork's verifier accepts; no kernel is built.

## Layout

- `gen/r6plan.py` (tables, predictions, `TABLES.md`, `stages.txt`), `gen/r6model.py` (the frozen
  rules, hash-checked, and the r-v and r-b extensions), `gen/gen_oomring.py` (R5's, unchanged),
  `gen/gen_oomring2.py`, `gen/frozen_commits.py`, `gen/hu1.py` (R5's copy).
- `run/run_stage.sh`, `run/lib_r6.sh`, `run/r6.env`, `run/lib_check.sh` (laptop runner);
  `run/r6read.py` (THE reader: runner and scorer import it; `kept_name` the one file-name
  function); `run/fwtask_run.py` (the landed one, byte for byte); `run/r6.sh` (Mac driver),
  `run/stage_r6.sh`, `run/freeze_r6.sh`, `run/guard_r6.sh`.
- `score/score_r6.py STAGE out/ATT/STAGE` (and `replay DIR`, `replay-r5 R5OUT`), `score/scorekit.py`.
- `tests/run_all.sh` runs everything; `debug/` is scratch (`debug/tool4623753` is the rgn4 tool
  built from our own source for `tests/mock_all.py`).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2 SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"   # or .234
cd ~/src/scratch/resgx545/closing6/r6-dpm; export PYTHONDONTWRITEBYTECODE=1
bash tests/run_all.sh                       # offline, must print RUN_ALL PASSED
SGX_DRY_RUN=1 run/stage_r6.sh; run/stage_r6.sh   # copies to ~/scratch/r6d; checks tool, regtimeline, blob, python3, 600 MB
R6_ATTEMPT=a2 run/r6.sh                     # out/a2, laptop ~/scratch/r6d/out/a2 (freeze 2); stops at the first non-zero stage
```

After the copy the lead moves the laptop's `~/scratch/r6d` to `~/scratch/archive/` (HACKING.md).

## Publication

The fold publishes this directory whole. No file here imports `closing4/p7/guard.py` or reads a
firmware image, listing or closed binary: nothing is marked for data-private. `oomring.s` and
`oomring2.s` are our own source (from `doc/specs/usse_isa.md`, `asm/fwtask/events_m.s` and
R4-events' `ring_hold.s`); the r-k predictions rest on R-5 as landed in 3d.md 6.4 (public text).
`debug/` may be left out of the published copy (scratch; the tool build is reproducible from
resgx545 4623753).

## Freeze 2 (2026-11-12, after attempt a1): what changed and why

Attempt a1 (freeze 1, kept in `freeze1/`: FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits as run,
`stage_r6.sh.as-run`, and `a1-tree/`, the five runner files the laptop got, each hashing to freeze
1's FROZEN.sha256) ran r-a0 only and stopped with rc 10 on a runner slip, not a premise:
`out/a1/r-a0.log` line 1 "lib_r6.sh: line 27: .../lib_check.sh: No such file or directory", lines
89-90 "STOP: control a0-t-s3m7 left 0x2 global pages, frozen 2" and "run_stage.sh: line 264:
num_eq: command not found". The lead stopped there; its files stay as run in `out/a1` (laptop
`~/scratch/r6d/out/a1`).

Jobs a1 ran, whose readings the lead has seen (all five r-a0 rows before the stop, the fifth the
one that stopped; a0-t-s3m6 and a0-qf-0xa2 did not run): a0-cal-2048 (S2..S5 0x51 0x9d 0xe8 0x132,
left 2), a0-cal-2048f (complete, need 0x213, S6 0x181, S7 0x1ca), a0-c4-b5 (R, left 2), a0-c4-b6
(N, left 1), a0-t-s3m7 (R, left 2). Each reading is the frozen prediction. These are r-a0 controls
(premise rows), not held-out cells; a2 runs r-a0 again in full.

Cause: freeze 1's `stage_r6.sh` copied five runner files by name and not `run/lib_check.sh`, which
`lib_r6.sh` sources for `num_eq` (added in this build for the ctlleft and ctlcnt controls); bash
went on after the failed `.`. The mock did not see it because `tests/run_mock.sh` ran the source
tree `run/`, where the file is, with the Mac's environment.

Changes (the staging and the runner's start only; `predictions/` and `tables/` are byte for byte
freeze 1's, so PREDICTIONS.sha256 is unchanged; main d9b2969 and data e5cdaf0a unchanged):
1. `stage_r6.sh` stages ONE file list (`RUNNER`, now with `lib_check.sh`) by scp, and `--local DIR`
   copies exactly that list into the laptop layout.
2. `lib_r6.sh` stops at once (rc 1) if a file it sources is missing, if sourcing fails, or if
   `num_eq` or `is_num` is not defined.
3. `tests/run_mock.sh` runs every stage from the `--local` staged tree under `env -i` (PATH, HOME
   and the mock's stand-ins only), and fails on any "command not found" in a stage log.
4. `tests/test_staged.sh` (in run_all): a1's tree reproduces the stop under the mock (rc 10,
   "num_eq: command not found" at a0-t-s3m7) and fails a static check (a file a laptop script
   sources or runs and is not staged; a function a laptop script calls and the staged tree does
   not define); freeze 2's staged tree passes both; a1's tree plus lib_check.sh alone passes r-a0.
5. The driver's attempt is a2 (`out/a2`, laptop `~/scratch/r6d/out/a2`); a1's directories are
   never written. Staging overwrites `~/scratch/r6d/run` (the runner tree) only.
