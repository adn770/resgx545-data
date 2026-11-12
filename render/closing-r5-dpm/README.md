# R5-dpm: laptop session r5-dpm of round 5 (Q210's c4-b3 repeat, Q211's count rows): PREPARED, NOT RUN

Built offline 2026-11-12 from the approved plan `closing5/dpm/exp-dpm-r5.md` with every decision (a)
(DECISIONS-R5.md R5-3 (a): all seven stages, 82 jobs, the 16-register list with `0x0734`, `0x0730`,
`0x012c`, `0x0a74` swapped in; R5-5 (a): the own task `oomring` reading `sa8`/`sa9`, run last).
Nothing here touched the laptop, cachix or a git repository; nothing is committed; the repository's
clean-room guard was not run (the session has its own, `run/guard_r5.sh`). Read `PREFLIGHT.md`
first (time, controls, stops, risks, deviations).

The offline folds landed on main before the freeze (main f0d5b39): the predictions cite E852 (the
step table and c4-b3 on S4: H-GREQ's fit), E853 (R-5's guard held on g-qf and s275) and E854 (the
count rule H-CNT, d = 7/4, k = 0), with 3d.md 6.4 (R-5's guard, the `sa8` bits of H-BITS), E773
(HU1), E799, E801 and E832 (the kept flips and counts the controls repeat).

## What runs (one session, laptop prefix `~/r5d-`)

| stage | jobs | what | stops |
|---|---|---|---|
| d-a0 | 8 | premise (any capture not whole: rc 13, freeze 2): calibrations 2048 (P 0x162) and 4096 (P 0x422), the four kept flips, 4096 thr0 0x35a / 0x35c | any premise off (class, knob proof, non-monotone steps): rc 10, the session stops before A1 |
| d-a1 | 9 | c4-b3 (P 0x10a) x5 interleaved with S4 - 1, S4 + 1 (read from a0-cal-2048), c4-b4, c4-b2 | any hang/fault |
| d-a2 | 16 | held out: 2048 S3-1, S3 x2, S3+1, S2-1, S2, S2+1, S5-1, S5, S5+1; 4096 S4 x2, S3-1, S3 x2, S3+1 | any hang/fault |
| d-a2b | 6 | calibration + S4 cell at 4096x2048, 2048x4096, 3072x3072 | any hang/fault |
| d-t | 8 | exploratory: 2048 thr0 S3-7..S3-4, S5-7..S5-4 | any hang/fault |
| d-b | 27 | 5 g-qf controls; scenes s119 (`--move 1:2560,0`) and s198 (`--move 1:1984,0`): calibration + 10 cells each | a scene whose U is not HU1's: its cells skipped (void) |
| d-a3 | 8 | LAST, own task armed before each job: c4-b5 x2, c4-b6 x2, P 0x10a x3, 2048 S3 | EDM stall: reset once; a second: rc 11 |

**82 jobs**, order A0, A1, A2, A2b, T, B, A3. Expected time about 22 minutes (2048 jobs about 9 s,
4096-class and B jobs 15 to 25 s, stage starts with health and copies 25 s each); plan for 35.
Stop budget: no fault planned (every row class "safe": rc 3 "scene overflowed" is the normal end);
any hang, fault, -110, kernel watchdog or failed health stops the session; one EDM stall in A3.

## Predicted outcomes (frozen in `predictions/`, readable in `TABLES.md`)

- A0: section 1's steps; c4-b5 R, c4-b6 N, 0xe2 R, 0x122 N, 4096 0x35a/0x35c N; no grow.
- A1 (H-GREQ, FIT side): grow in 5 of 5 replicates and in none of the 4 others; all 9 silent.
  H-NOISE predicts at most 1 grow.
- A2 (held out): grow at S cells only; S4/S5 silent; S2/S3 neighbours raise; the five raising-side
  S cells raise under H-PEND, are silent under H-BLOCK (the decision table of plan section 2).
- A2b: grow and silent at S4 on the three targets. T: pages left 2, 2, 1, 1; band 2 R, band 4 N.
- B: controls 9, 4, 3, 2, 1 partial renders; calibrations U = 119 and 198 (HU1) with no partial
  render; 20 held-out cells by H-CNT (d = 7/4, k = 0), the seven alternatives tallied.
- A3 (H-BITS, held out): decision-entry `sa8 & 0x380` 0x180 in c4-b5, 0 in c4-b6, 0x380 at the entry
  after the raise; P 0x10a: 0 with `sa9` bit 8 clear (H-PEND) or set (H-BLOCK); S3 cell 0x180 (PEND).

## Stage A3 is NOT blocked

`tests/test_oomring.py` builds the rgn4 fork's own verifier (`sgxfive_owntask.c`, `sgx_fw.c` at
`a2788bd86537`, the commit `tools/forkpin.py` pins and the r4 sessions name for module 99CD90DA,
read with `git archive`, never written) with the landed host shim: it ACCEPTS `bins/oomring.blob`
(sha256 5b2fcf02..., 738 words, no str, ldr only CR_TIMER) and refuses the two failing controls
with the Python verifier's reasons. No kernel build is needed.

## Layout

- `gen/r5plan.py` (+ `hu1.py`): tables, predictions, `TABLES.md`, `stages.txt`; `gen/gen_oomring.py`:
  `asm/oomring.s`, `bins/oomring.blob`, `bins/blobs.json`; `gen/frozen_commits.py`: `FROZEN.commits`.
- `run/run_stage.sh`, `run/lib_r5.sh`, `run/r5.env` (laptop runner); `run/r5read.py` (THE reader:
  runner and scorer import it; `kept_name` the one file-name function); `run/fwtask_run.py` (the
  landed one, byte for byte); `run/r5.sh` (Mac driver), `run/stage_r5.sh`, `run/freeze_r5.sh`,
  `run/guard_r5.sh`.
- `score/score_r5.py STAGE out/STAGE` (and `replay DIR`), `score/scorekit.py` (landed copy).
- `tests/run_all.sh` runs everything (see its header); `debug/` is scratch.

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2 SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"   # or .234
cd ~/src/scratch/resgx545/closing5/r5-dpm; export PYTHONDONTWRITEBYTECODE=1
bash tests/run_all.sh                       # offline, must print RUN_ALL PASSED
SGX_DRY_RUN=1 run/stage_r5.sh; run/stage_r5.sh   # copies; checks tool, regtimeline, blob, python3
R5_ATTEMPT=a2 run/r5.sh                     # attempt 2: out/a2, ~/r5d-out/a2; stops at the first non-zero stage
```

## Publication

The fold publishes this directory whole. No file here imports `closing4/p7/guard.py` or reads a
firmware image, listing or closed binary: nothing is marked for data-private. `oomring.s` is our
own source from `doc/specs/usse_isa.md`, `asm/fwtask/events_m.s` and R4-events' `ring_hold.s`; the
A3 predictions rest on R-5 as landed in 3d.md 6.4 (public text). The planner's `qf_guard*.py`
(in `closing5/dpm/`, not here) are the firmware-derived files the plan sends to data-private.

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
