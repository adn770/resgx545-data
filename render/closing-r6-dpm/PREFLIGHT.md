# R6-dpm preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-12 offline from `closing6/dpm/exp-dpm-r6.md` (all decisions (a); DECISIONS-R6.md
R6-2 (a)). Nothing ran on the laptop. Frozen against resgx545 main d9b2969: `FROZEN.sha256`
(generators, runner, reader, scorer, tables, predictions, staged programs, task sources, tool
pins, the landed files and the frozen offline rules the checks import), `PREDICTIONS.sha256`,
`FROZEN.commits` (resgx545 d9b2969, linux fork a2788bd86537, resgx545-data e5cdaf0a for the
program and the offline rules). Refreeze (`run/freeze_r6.sh freeze`) only if the tables are
regenerated, never after the first job.

## 1. Laptop

- The rgn4 boot as it stands (R6-2 (a)): module srcversion 99CD90DA26E3AFF9C450517 loaded =
  installed (handover 2026-11-12-r5), checked before every stage; another module STOPS (ask).
- Tool `~/sgxfive-test-rgn4` sha256 e6951558..., `~/regtimeline` 079f6359..., python3. A
  mismatch STOPS; nothing is built.
- Every session file under `~/scratch/r6d/`: `run/` (runner, tables, FROZEN), `stage/`
  (p1139-green.bin, oomring.blob), `out/ATTEMPT/` (kept files, `state/`). One work directory a
  job, `mktemp -d ~/scratch/tmp/r6d.XXXXXX`, its files removed by name and the directory removed
  once they are kept (and by the trap on a stop). Nothing in `/tmp` (a work root under /tmp is
  refused). 600 MB free on the kept and the work filesystems at each preflight, 200 MB before
  every job (else rc 13, the job not run). Staging refuses less than 600 MB on `~/scratch`.
- Debugfs: reset, render_pb_pages, regs, buf09, render_param, render_tadata; r-k also own_code,
  own_arm, own_res, load, boot, status, miscinfo. All through `sudo -n`; markers by `sudo -n tee -a`.

## 2. Jobs and time

97 jobs (r-a0 7, r-m 15, r-n 21, r-v 6, r-b 40, r-k 8). 2048x2048 jobs about 9 s (g-c4), the
three smaller targets about 7 s, r-v about 10 s, r-b 15 to 25 s, r-k about 13 s (arm and page
read), six stage starts with health and copies 25 s each: about 25 minutes, plan 45. The driver's
stage alarm is 2400 s (r-b). Staging is a copy: 1 minute.

## 3. Controls (each can fail) and labels

| stage | control | fails |
|---|---|---|
| r-a0 | c4-b5 R, c4-b6 N (`ctl:`), t-s3m7 left 2, t-s3m6 left 1 (`ctlleft:`), g-qf P 0xa2 2 partial renders (`ctlcnt:`); knob proof on all 7; calibration steps monotone | runner STOPS (rc 10, CTLFAIL; later stages refused) |
| r-a0 (scorer) | the calibrations' steps in their brackets (H-IV; S6 0x181, S7 0x1ca), need 0x213, no grow | the premise headline FAILS; later headlines GATED |
| r-n | each calibration against the frozen model (`model:`) | off: its B cells re-picked by the timeline rule, scored for H-PHASE only; H-STEPMODEL refuted there |
| r-v | `vprem`: the calibration reaches a second global page | its cells skipped (nothing else depends on them) |
| r-b | g-qf at P 0x53, 0x54, 0xa2, 0xa3: 4, 3, 2, 1 (E832); scene calibrations U = HU1, no partial render | qf: r-b's headlines gated; a scene's U off: its 8 cells void |
| r-k | k-b5 0x180 and R, k-b6 0 and N with the task armed (E864) | r-k's headlines gated |

Every job: scene check from its own data (1500-vertex jobs reach a 2nd global page and show the
steps of their target's calibration, else the frozen model's, within 1 page; `--vtx-coords` jobs
their own calibration's; default-triangle jobs stay at 1 page), a FAILED control otherwise.
Labels: r-a0 and the r-b, r-k controls `control`; r-k's c4-b3 and second creep cell `repeat`;
r-m, r-n, r-v, r-b's 32 cells and r-k's other rows `heldout`; F9 counts and r-a0/qf peaks `explore`.

## 4. Stops

Runner: any hang (incl. -110), fault, unexpected failure (rc 4); kernel watchdog/BUG (rc 3); no
return (rc 6); failed health recovery (rc 5); a capture not whole, an r-v calibration without its
dump, or the work filesystem short (rc 13); knob read-back (rc 9); a control or premise (rc 10,
r-a0); second EDM stall (rc 11, r-k); arm or ring clear failed (rc 12). Driver: any non-zero
stage, health not exact, render_pb_pages not 0x422, hold_recovery not N, alias_skip not 0.

## 5. Risks

- r-v: `--vtx-coords` with 1500 vertices has never run on the hardware. The tool's mock accepts
  it and echoes "(N coordinates)"; the first job (the calibration) is the premise. Under
  H-BURST-PAGE at N 8 the model's U is above 0x400, so that calibration overflows once (normal).
- r-n's three targets have never run; the tool's mock and the fork's size check (the layout is
  computed the same way on both sides, 3072x3072 already ran) accept them, so no spare size is used.
- r-b at 4096x4096 with thr0 2 to 6: up to 8 partial renders (g-qf ran 9 at 0x24 cleanly).
- r-k: the own task armed with the probe on rgn4 as R5-dpm's d-a3 ran it (E864, no stall).
- No clock-gate register, trc_hazard, kreg/kpoke, firmware str, reboot, GRUB or build anywhere
  (`run/guard_r6.sh`; `oomring.blob` has no str word, only `ldr #81`).

## 6. Offline checks (`tests/run_all.sh` = RUN_ALL PASSED)

guard; freeze verify; test_gen (files = generator; every written-out constant = the frozen rules
now; the rules = the offline outputs; the ARGV TWIN of all 97 rows against a hand transcription of
plan section 4 and the kept commands of the same cells); test_read (the reader = R3-geo's dpm3, the
brackets = F1's on 364 kept steps, the burst ends = F4's, the run peaks = F7's on 56 jobs, `model`
refuses c5b-cal against the 2048x4096 model); test_scorer (R5-dpm's attempt rescored = E860 to
E864, a2b-cal-4x2's S2 held under H-IV; real-record r-a0, r-b, r-k directories hold; planted ones
fail: a g-qf timeline in a 1500-vertex control, a 1500-vertex timeline in the g-qf control, a knob
not landed, c4-b6's ring under k-b5; L 67 from a real dump); test_oomring (R5's blob accepted by
both verifiers, oomring2 refused by both, its #81 twin accepted); mock_all (every command against
the rgn4 tool's own `--mock`); run_mock (the runner end to end on argv-answering worlds: CAP/row,
PAGE/column/reversed operands, a calibration off the model, the default laptop paths, every stop,
the guard's refusals, the driver and staging dry runs). The mock has no wall-clock margin (sample
times are the world's numbers, no waits); it was also run once under load (`LOAD=1`, 8 `yes`).

## 7. DEVIATIONS from the plan (and why)

1. **r-k runs R5-dpm's oomring** (the plan's own fallback): both verifiers refuse oomring2's
   `ldr` of 0x0724 and 0x072c. The count clauses are "cannot tell"; the sa8 bits stand.
2. **r-m cells** are B - 2 .. B + 2 of F5's B_k (0x176, 0x1c1, 0x20c), the rule E874 landed; the
   planner's 0x178 and 0x20d were the timeline rule's, kept as the rival E-TL. F9 gives one
   partial render at every r-m cell, so "all silent" is not predicted (no second abort).
3. **r-n cells**: B - 1 and B from the frozen model (`M:` cells, re-picked by the timeline rule
   when the calibration is off the model); S - 1 from the calibration's own step (`S:`).
4. **r-v cells** are E - 1 and E of the first band from 3 on whose burst end F4's frozen timeline
   rule finds in the calibration (`E:G:3+:off`): in the model band 3 has no creep under PAGE at
   N 4 and N 8 nor under CAP at N 8, so "band 3" alone would place nothing there. Their
   prediction is the frozen rule at the job's own thr0 and the L read from the calibration's dump
   (`rule` rows, CAP and PAGE apart). L0 = 67 + 15 N is an [infer] from 3d.md 10.1; H-BURST-PAGE's
   model (every region opens a block at b_k) is this build's formalization (`gen/r6model.py`).
5. **r-b**: H-REPLAY is scored in row order (E875's 54 of 56, post hoc there), column order (the
   frozen W*, refuted on kept data in E875) a rival with d = 7/4 and d = 1. Scenes: moves on a
   256-pixel grid where row and column differ most, U at least 10 from the kept scenes'.
6. **The creep cell** (2048x4096 thr0 0x24a): its two partial renders come from F9's replay
   (0x248 to 0x24c: 2; 0x24e up: 1), not from the kept c5b-cal (thr0 0x400, one render: it
   cannot tell). A repeat of the creep cell is r-k's "one repeat".
7. **Work directories** are one a job (the brief), not one a stage as in R5-dpm.
8. **Dumps** on every 1500-vertex row up to 2048x2048 (the new smaller targets included); only
   r-v's calibrations require theirs (rc 13 without it).
9. Stage names r-a0 .. r-k (the plan's); the attempt directory defaults to `a2` (freeze 2).

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
