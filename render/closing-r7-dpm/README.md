# R7-dpm: laptop session r7-dpm of round 7 (Q210's margin at new targets, Q211's count, the passes with oomring2)

Built offline 2026-11-12 from the approved plan `closing7/b/exp-dpm-r7.md` (DECISIONS-R7.md R7-2 (a), R7-4 (a), R7-6 (a); the
plan's own decisions all (a)). Nothing here touched the laptop, cachix or a git repository; nothing is committed; the repository's
clean-room guard was not run (the session has its own, `run/guard_r7.sh`). Read `PREFLIGHT.md` first (time, controls, stops, risks,
deviations).

Two sets, two freezes, both against resgx545 main 1c64f3a and resgx545-data 830641e6:

- **set A** (`FROZEN.sha256`, `PREDICTIONS.sha256`, `FROZEN.commits`): s-a0, s-m, s-b, s-v on the test module 41E2F5C7 (fork
  3f0b3e74), loaded now.
- **set B** (`FROZEN-B.sha256`, `PREDICTIONS-B.sha256`, `FROZEN-B.commits`): s-k on module 37EC97AB (fork 664fd0d0, round 7's
  own-task register list) after the lead's one-shot boot. Each stage's table names its set and module (`#set`, `#module`); the runner's
  preflight refuses a module that is not its set's (set B on 41E2F5C7 is refused, and the reverse).

Every prediction starts from the frozen offline rules on main (gen/r7model.py imports them from their published copies and refuses
one whose hash is not its FREEZE file's): E899 (H-WALK64, the 64-row strip walk order; H-REPLAY64, E875's replay in that order:
`cited/closing7/b/offline/g1_walk64.py`, `g2_replay64.py`, `olib.py`), E900 (H-SPAN, the burst end at the straddling block:
`g3_span.py`), E874's step replay (`cited/closing6/dpm/offline/f5lib.py`), F9 (exploratory), HU1 (R5-dpm). E900 froze no step rule for
larger objects (G5: H-CUM 9 of 12 at N 4), so s-v is two calibrations as exploration (plan decision 5 (a)).

## What runs (laptop prefix `~/scratch/r7d/`)

| stage | set | jobs | what | stops |
|---|---|---|---|---|
| s-a0 | A | 6 | premise: 2048 calibrations at P 0x162 (S2..S5, 2 left) and 0x422 (S2..S7, need 0x213), c4-b5 R / 2 left, c4-b6 N / 1 left, t-s3m6 1 left, g-qf P 0xa2 2 partial renders with H-REPLAY64's run peaks | any control off, WITHOUT A READING, off the model, a knob proof: rc 10, set A stops; capture not whole: rc 13 |
| s-m | A | 50 | held out: 3072x3072 (cal + bands 5, 6 B-1..A), 3072x2048, 2048x3072, 2560x2560, 1024x1024 (cal + B3-1, B3 + parting band B-1..A), 2048x2048 A-1, A at bands 5-7 (replicates) | hang/fault; a calibration off the model re-picks its cells |
| s-b | A | 29 | held out: one-triangle scenes never run: s44a, s44b (4096x4096, cal + 6), s42 (4096x2048), s22 (2048x2048, cal dumped: H-WALK64), s17 (1024x768) (cal + 4 each) | a scene's need not HU1's: its cells void |
| s-v | A | 2 | exploration: 2048x2048 `--vtx-coords 4` and `8` calibrations with dumps (R6-dpm's readings repeated) | a missing dump: rc 13 |
| s-k | B | 10 | after the boot: oomring2 armed before each job: k-b6 (premise: rungs hold page counts inside the host bracket), k-b5, k-b3, k-s3, k-s4p1, k-s3m6, 0x177, 0x178 (band 5 A-1, A), the 2048x4096 creep cell twice | premise: rc 10; second EDM stall: rc 11; arm: rc 12 |

**97 jobs**: set A 87, set B 10. Order: health, s-a0, s-m, s-b, s-v (set A, now); then the one-shot boot of 37EC97AB, health, s-k
(set B). About 25 minutes for set A (plan 45), 3 for set B plus the boot. Stop budget: no fault planned (every row "safe"; rc 3
"scene overflowed" is the normal end); any hang, fault, -110, watchdog or failed health stops the session; one EDM stall in s-k.

## Predicted outcomes (frozen in `predictions/`, readable in `TABLES.md`)

- s-a0: as R6-dpm's kept rows of the same jobs (29 of 29 controls held on them, tests/test_controls.py).
- s-m (H-SPAN, held out): 2 pages left below A_k, 1 from A_k; 19 discriminating cells where E874's B_k says 1 (3072x3072 0x32a..0x32e,
  0x3cd, 0x3ce; 3072x2048 0x225..0x228; 2048x3072 0x22a..0x22c; 2560x2560 0x2ae..0x2b0; 1024x1024 0x6b, 0x6c); R-5 raises at B3 - 1,
  silent at B3 at the four targets; every calibration's steps and U by H-STEPMODEL (3072x3072 U 0x479 > the clamp: steps only).
- s-b (H-REPLAY64): count and every run's peak per cell; row order (E875's) the rival, d = 7/4 and d = 1 tallied; HU1's U per
  calibration (157, 131, 145, 78, 22); b-cal-s22's dump: every block at its page and slot (H-WALK64), row order not.
- s-v: R6-dpm's steps and needs (538, 691) repeated; no verdict.
- s-k: `sa8 & 0x380` at the decision entry: k-b5 0x180, k-b6 0, k-b3 0, S3 0x180, S4+1 0x180, t-s3m6 0x180, 0x177 0x180 (E874-B: 0),
  0x178 0, creep 0 (ISUB-REV 0x180); H-PASS: global pages the task reads at the abort = the host's (1 + steps below thr0: k-s3 2,
  creep 4) and at the decision entry = the pages left (1 at step cells, H-PENDREQ); the abort's page count inside the host bracket.

## Layout

- `gen/r7plan.py` (tables, predictions, controls with `reads:` refused when unreadable, `TABLES.md`, `stages.txt`, `stagesB.txt`),
  `gen/r7model.py` (the frozen rules, hash-checked), `gen/gen_oomring.py` (R5's, unchanged), `gen/gen_oomring2.py`,
  `gen/frozen_commits.py`.
- `run/run_stage.sh`, `run/lib_r7.sh`, `run/r7.env`, `run/lib_check.sh` (laptop runner); `run/r7read.py` (THE reader: runner and
  scorer import it; `kept_name` the one file-name function); `run/fwtask_run.py`, `run/sessioncheck.py`, `run/scorekit.py` (the landed
  files byte for byte, staged); `run/r7.sh` (Mac driver, `R7_SET=A|B`), `run/stage_r7.sh`, `run/freeze_r7.sh`, `run/guard_r7.sh`.
- `score/score_r7.py STAGE out/ATT/STAGE` (`REQUIRED` per stage; `replay-r6 R6OUT`: G8), `score/scorekit.py` (landed, byte for byte).
- `asm/oomring2.s`, `bins/oomring2.blob` (sha256 c855818e...), `asm/oomring.s` (R5's, for the test), `bins/p1139-green.bin`.
- `tests/run_all.sh` runs everything (prints RUN_ALL PASSED); `debug/` is scratch (`debug/tool4623753`, the rgn4 tool built from our
  own source for `tests/mock_all.py`).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2 SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"   # or .234
cd ~/src/scratch/resgx545/closing7/r7-dpm; export PYTHONDONTWRITEBYTECODE=1
bash tests/run_all.sh                       # offline, must print RUN_ALL PASSED
SGX_DRY_RUN=1 run/stage_r7.sh; run/stage_r7.sh   # copies to ~/scratch/r7d; checks tool, regtimeline, oomring2.blob, python3 >= 3.10, 600 MB
run/r7.sh                                   # set A on 41E2F5C7: out/a1, laptop ~/scratch/r7d/out/a1; stops at the first non-zero stage
# one-shot boot of 37EC97AB (closing7/kernel/deliver/664fd0d00765/gma500_gfx.ko, push-gma500.sh --ko, the user's OK), health, then
R7_SET=B run/r7.sh                          # set B: s-k, out/b1
```

After the copies the lead moves the laptop's `~/scratch/r7d` to `~/scratch/archive/` (HACKING.md).

## Publication

The fold publishes this directory whole. No file here reads a firmware image, listing or closed binary or imports a script that
does: nothing is marked for data-private. `oomring2.s` is our own source (R5-dpm's oomring from `doc/specs/usse_isa.md` plus two `ldr`
of registers the verifier list now names). `debug/` may be left out (scratch; the tool build is reproducible from resgx545 4623753).
