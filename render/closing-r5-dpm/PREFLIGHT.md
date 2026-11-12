# R5-dpm preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-12 offline from `closing5/dpm/exp-dpm-r5.md` (all decisions (a)). Nothing ran on the
laptop. Frozen against resgx545 main f0d5b39 (E852-E854 landed): `FROZEN.sha256` (generators,
runner, reader, scorer, tables, predictions, staged programs, task source, tool pins, the landed
files the checks import), `PREDICTIONS.sha256`, `FROZEN.commits` (resgx545 main, linux fork
a2788bd86537, resgx545-data). Refreeze (`run/freeze_r5.sh freeze`) only if the tables are
regenerated, never after the first job.

## 1. Laptop

- Must be the rgn4 boot: module srcversion 99CD90DA26E3AFF9C450517 loaded = installed (checked
  before every stage; a stock boot STOPS: the user's OK for a one-shot `boot-test-kernel.sh` first).
- Tool `~/sgxfive-test-rgn4` sha256 e6951558..., `~/regtimeline` 079f6359... (R4-pixel's pins),
  python3 (the reader and the landed `fwtask_run.py`); a mismatch STOPS, nothing is rebuilt.
- Directories `~/r5d-run` (runner, tables, FROZEN), `~/r5d-stage` (p1139-green.bin, oomring.blob),
  `~/r5d-out/ATTEMPT` (kept files, `state/`, the work directory). 600 MB free (4096-class dumps).
- Debugfs: reset, render_pb_pages, regs, buf09, render_param, render_tadata; A3 also own_code,
  own_arm, own_res, load, boot, status, miscinfo. All through `sudo -n`; markers by `sudo -n tee -a`.

## 2. Jobs and time

82 jobs (A0 8, A1 9, A2 16, A2b 6, T 8, B 27, A3 8). 2048 jobs about 9 s (g-c4: 10 in 81 s),
4096-class and B jobs 15 to 25 s, A3 adds an arm and a page read (about 3 s a job), seven stage
starts with health and copies 25 s each: about 22 minutes, plan 35. Staging is a copy: 1 minute.

## 3. Controls (each can fail) and labels

| stage | control | fails |
|---|---|---|
| A0 | c4-b5 R, c4-b6 N, 0xe2 R, 0x122 N, 4096 0x35a N, 0x35c N (`ctl:`); knob proof on all 8; calibration steps monotone | runner STOPS (rc 10, CTLFAIL; later stages refused) |
| A0 (scorer) | the calibrations' steps = section 1's table (E852), no grow | the premise headline FAILS; later headlines GATED |
| B | g-qf at P 0x24, 0x53, 0x54, 0xa2, 0xa3: 9, 4, 3, 2, 1 (E832); scene calibrations U = HU1 (119, 198), no partial render | qf: B's headlines gated; a scene's U off: its 10 cells skipped (void) |
| A3 | c4-b5 R and c4-b6 N with the task armed | A3's headlines gated (the task moved the decision) |

Every job: scene check from its own data (1500-vertex jobs reach a 2nd global page and show their
target's steps within 1 page; default-triangle jobs stay at 1 page), a FAILED control otherwise.
Labels: A0 and B's five controls `control`; A1's replicates and c4-b4/b2 `repeat` (FIT side, E852);
A2, A2b, B's 20 cells and A3's H-BITS rows `heldout`; T `explore`.

## 4. Stops

Runner: any hang (incl. -110), fault, unexpected failure (rc 4); kernel watchdog/BUG (rc 3); no
return (rc 6); failed health recovery (rc 5); a capture not whole or the work filesystem short (rc 13, freeze 2); knob read-back (rc 9); premise (rc 10, A0 only);
second EDM stall (rc 11, A3); arm or ring clear failed (rc 12). Driver: any non-zero stage, health
not exact, render_pb_pages not 0x422, hold_recovery not N, alias_skip not 0. `0x0734` reading 0 in
every sample: its clause is "cannot tell", the others stand (scorer).

## 5. Risks

- A2's S2 - 1 / S2 / S2 + 1 cells (thr0 0x50-0x52) are below R3's 0x60 floor: about 5 partial
  renders at 2048x2048 (E630/E706 saw hangs in long sequences); the hang stop covers it.
- A3: own task armed with the probe on the rgn4 module [infer from R4-events, which armed tasks on
  rgn4 with the s1b tool]; a stall is reset once. Each A3 job is a fresh firmware load (reset, arm).
- B at 4096x4096 with thr0 2-3: up to 7 partial renders (g-qf ran 9 at 0x24 cleanly).
- No clock-gate register, trc_hazard, kreg/kpoke, firmware str, reboot, GRUB or build anywhere
  (`run/guard_r5.sh`; `oomring.blob` has no str word, only `ldr #81`).

## 6. Offline checks (`tests/run_all.sh` = RUN_ALL PASSED)

guard; freeze verify; argv twin of all 82 rows against a hand transcription of section 4 and
against round 3's commands for the same cells; the reader = R3-geo's dpm3 on 102 kept jobs and
section 1's table from 5 kept calibrations; scorer replays: g-c4 (E799's flip, c4-b3 the only grow,
controls pass), g-c5 (E801), g-qf (E832's 22 counts) hold; planted g-c4 / d-a0 with a g-qf control
timeline FAIL; A3 pages from sgx-sim decoded rung by rung; the rgn4 fork's verifier (host build at
a2788bd86537) accepts oomring and refuses two failing controls; every command against the rgn4
tool's own `--mock`; the runner end to end on argv-answering worlds (pend, block, noise, shifted
steps, every stop, the guard's refusals).

## 7. DEVIATIONS from the plan (and why)

1. **Step rule** S_k = max(a, b - 1) for a step seen between page counts a and b: "the count before
   the step" alone reads c5b-cal's S2 as 0x99 (table 0x9a), b - 1 alone f-1350-0x36e's as 0x124
   (table 0x125); this rule gives section 1's table on all 5 kept calibrations (tested).
2. **B scenes** (the plan says "near 120 and 200"): x moves in steps of 64, HU1 nearest: (2560, 0)
   U 119 and (1984, 0) U 198. Cells frozen from HU1's U (a measured U that differs voids the scene,
   as planned). U 119 has no 5/6 step: its two missing cells are one above the 3/4 and 2/3 steps
   (thr0 0x9, 0x15).
3. **A3 rungs**: the "decision entry" is the first OOM rung (pa1 bit 20/21) after the first
   end-of-render rung (bit 4) that follows the first OOM rung (robust to c4-b3's grow entry);
   "the pass after a raise" is the next OOM rung. The ring logs pa1 bits 22, 21, 20, 10, 9, 4.
4. **A3 arming**: the plan's reset before each job disarms the task, so each A3 job is reset, arm
   (a firmware load), ring clear, job. A3's start adds a fill and triangle exact under the armed task
   and a pass count > 0.
5. **Derived floor** 0x48 (R3: 0x60), for A2's S2 cells.
6. **Premise**: steps differing from section 1's table are not a runner stop (the plan lists
   non-monotone steps, control classes and the knob proof) but fail the premise in the scorer.
7. **Grow** is not read when the threshold itself is below 0x10 (g-qf's low cells read 0x0628 below
   0x10 with no grow); no prediction uses it there.
8. The raise is dword 38 = 0x20 (R3-geo's rule); the plan's 0x0624 clause agrees on every kept job
   (tested) and is kept as `raise_tl`. 0x0730, 0x012c, 0x0a74 are sampled for the fold, unpredicted.

## Freeze 2 (2026-11-12, after attempt 1): what changed and why

Attempt 1 (freeze 1, kept in `freeze1/`: FROZEN.sha256, PREDICTIONS.sha256,
FROZEN.commits as run) ran d-a0 only and stopped at rc 10 on a0-cal-4096, "its own 0x0624 read ?".
The lead stopped there; no held-out stage ran and no reading of one was made. Its files stay as
run in `out/d-a0` (laptop `~/r5d-out/d-a0`).

Cause, from the kept files and the tool and fork sources (read only) [infer, strong]: the runner's
work directory was `mktemp` under `/tmp`, a filesystem the preflight never checked, and it filled
during a0-cal-4096. Every write into it after that failed: the TA-data dump stopped after 1044480
bytes on a short write (the tool's `dump_render()` reports a short write with no errno as EIO:
"--dump-render: Input/output error"); the job text (regtimeline's stdout, redirected there) holds
only its first 4096-byte page, cut mid-line after 23 `tl` lines; `buf09` and `regs` were not kept
(their `sudo -n cat > $W/...` failed) and the dmesg slice is 0 bytes. The kernel's debugfs read
(`sgxfive_render_dump_read`, fork a2788bd86537) returns data or an error code, never this pattern;
regtimeline flushes on exit. Why `/tmp` was that full is for the lead to check on the laptop
(`df /tmp`, leftovers of earlier runners).

Changes (the measurement path only; `predictions/` are byte for byte freeze 1's, so
PREDICTIONS.sha256 is unchanged):
1. The work directory is `~/r5d-out/ATTEMPT/work.*`, on the kept files' filesystem (600 MB checked
   at preflight), and every job first needs 200 MB free there (else rc 13, the job not run).
2. Every job's capture is checked before anything is read from it (`r5read.py check`: a timeline
   block, every `tl` line complete, a final newline; `buf09` and `regs` read; space left): a
   failure stops the stage with rc 13 "capture not whole", recorded in cases.tsv as class
   `capture`, never as a premise or a class (attempt 1 read it as a failed knob proof). The reader
   itself returns "capture cut" for a cut line (the scorer: NODATA, cannot tell).
3. `--dump-render` only on the 2048x2048 rows (round 3 and attempt 1 dumped those cleanly); the
   4096x4096, 4096x2048, 2048x4096 and 3072x3072 rows run without it. No reading uses a dump.
4. The driver keeps each attempt apart: `R5_ATTEMPT` (default `a2`), laptop `~/r5d-out/a2`, Mac
   `out/a2`; an existing stage directory is never overwritten (rc 22).
5. Tests: the runner mock reproduces attempt 1 (a fake tool printing more than 4 KiB and the
   dump error, its text cut at 4096 bytes mid-line) and must stop with rc 13 and no premise read;
   the same job with its text whole passes d-a0; the space stop; the work directory; the argv twin
   allows only the dump to differ from round 3's commands.
