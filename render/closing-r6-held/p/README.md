# r6-held part P: Q111's CR_DPM_TASK_STATE row on the new kernel (prepared, NOT run)

Built 2026-11-12 offline for r6-held (session B of `closing6/rank/rank-round6.md`, DECISIONS-R6.md
R6-3 (a), R6-4 (a)). Nothing here touched the laptop, cachix or a git repository. Frozen against
resgx545 main **d9b2969** (`FROZEN.pin`, `FROZEN.commits`) and resgx545-data **e5cdaf0a** (the
replay fixtures). Read `PREFLIGHT.md` before running. Base: `closing5/r5-events` (published
`edm/closing-r5-events`, E855), cut to one stage; its file names were kept where the code imports
them (`gen/r5layout.py`, `gen/gen_r5.py`, `score/r5common.py`).

Q294 has **no rows**: its pysgx oracle (rank-round6.md O3, run in `../private/o3/`, data-private)
did not separate the sa65 words, and decision 5 (a) runs Q294 only if it does.

## What runs

One stage, `p1`, on the new kernel (fork `r6-kernel` 3f0b3e74, srcversion 41E2F5C756F96D20F7109A4),
timer_clock 0, task ring_skip3p (R4's bytes, E836):

| job | set | what | predicted |
|---|---|---|---|
| b0 | control | E855's b0: the fill without the skip, hold N | tick alive, no marks |
| b1p | held out | E855's b1p: slot 3's end-of-render pass skipped, hold Y | the lockup stop (budget 1 of 2) |
| b1p-r2 | held out | the same, replicate | the lockup stop (2 of 2) |

**3 jobs, 2 predicted stops** (each signed, explained by the marks, recovered by a reset, the gate
and the health; the stage goes on). About 2 minutes of jobs (a stop job 30-35 s with its
recovery), the load step, the clock check and the copy: **about 4 minutes, 10 with staging**.

## Hypotheses (predictions/p1.tsv, frozen)

- **H-R6** (E855's [RE] row, from R-6 as E855 lands it; this session cites no data-private file):
  the lockup path writes `CR_DPM_TASK_STATE` (0x0694) = 2 before its poll, so the peek read right
  after the stop's signature reads `0x00000002` and differs from the job's arm read. Rival
  **H-IDLE**: the stop leaves 0x0694 as the arm read it. Both rows are decided only when the arm
  read is not 2 (else cannot tell, with the reason). **H-RESET** [infer]: the read after the
  recovery equals the arm's.
- Controls that can fail: every peek read prints one `reg 0x0694 0x%08x` line (`peek_format`, each
  job), B0's E855 controls (the fill exact, the tick alive, no marks), the clock, the skip flag,
  the arm dump. A B0 that stops ends the stage.
- E855's own rows again (held out, replicated): H-HWR / H-NOMARK (the marks), H-TICKS (20 passes),
  H-LEVEL / H-PULSE (bit 18), H-W / H-ALL / H-NONE (the host's clears).

What it changes: Q111's E855 row (`CR_DPM_TASK_STATE cannot tell`) gets its reading; with H-R6
held, R-6's reading of the lockup path is confirmed on the one register E855 could not read.

## Stops

A B0 stop, an unexplained stop (no marks or no readable count) or a third stop: exit 8 (the stage
ends after its reset, gate and health; the session ends: the lead decides). Exit 5 (a reset or
gate not exact): ask the user. Exit 3 (watchdog) or 6 (no return): nothing more touches the
laptop. Exit 21: less than 300 MiB free on ~. Exit 1: preflight (the module, the knobs, the
peek's line, the frozen files). Driver exits: README of r5-events, plus 36 for a knob or the peek
line at the health.

## Run (the lead)

```
cd ~/src/scratch/resgx545/closing6/r6-held/p
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python PYTHON=$PY
bash tests/run_all.sh                               # offline: RUN_ALL PASSED
run/guard_p.sh && run/freeze_p.sh verify
SGX_DRY_RUN=1 run/p.sh ATTEMPT                      # prints the commands
run/stage_p.sh                                      # copy and check on the laptop (~/scratch/r6h/p/stage)
run/p.sh ATTEMPT                                    # the session; stops at the first problem
$PY score/score_p.py replay p1 b1p DIR NAME         # read a kept job of any round as a job of this table
```

Results: `out/ATTEMPT/score-p1.txt` (the `SUMMARY:` line), `out/ATTEMPT/p1/` (records with the
peek reads in `NAME.json` key `peek`, stop dumps, `clock-back.json`); on the laptop
`~/scratch/r6h/p/out/ATTEMPT/p1`. An attempt is never overwritten.

## Tests (offline, `tests/run_all.sh`, about 4 minutes)

The static guard (`run/guard_p.sh`: round 5's rules plus: the peek only read, with `timeout -k`;
every `timeout` with `-k`; no `/tmp` or tempfile; the one delete is `rm_work`, path-checked), the
freeze verify, `test_gen_r5.py` (the table and predictions are the generator's; the peek rows; no
data-private citation), `test_scorer.py` (replays BEFORE the freeze: E855's kept b1p and b1p-r2
read as p1's hold every E855 row and give the peek rows cannot tell, no file; r4's b1p holds;
E823's b1 fails H-HWR; worlds: a stop read of 2 holds H-R6, a stop read equal to the arm read
FAILS it, an arm read of 2 is cannot tell, a bad line fails the format control), `run_mock.py`:

- the whole session through `stage_p.sh` and `p.sh` on a mock laptop; the laptop side runs under
  `env -i` with the laptop's environment only (the system `/usr/bin/python3`, the shims, the
  mock's own hooks; the mock firmware, layout and shims are copies in the mock home);
- the mock answers by what the runner wrote and the tool's argv, never by a job name; the argv
  twin against a hand transcription of the plan (`PLAN_ROWS`: clock, skip, hold, clears, the
  peek phases, the tool's argv);
- `t_laptop_tree`: the staged tree is exactly the frozen list, and `tests/laptop_check.py`, run on
  the mock laptop against it with the REAL landed `fwtask_run.py`, finds every method, layout
  name and landed function the runner calls (and catches a broken one);
- `t_scorer_reads_kept`: every file the scorer opens is a file the runner kept, byte for byte;
- `t_slow_tool`: the fake tool 3 s late changes no outcome (the mock window holds at most 4 ticks
  before the fill's kick: r5-events' 16 ms fragility is gone from the mock);
- worlds: H-IDLE, an arm read of 2, a sticky 0x0694, a bad peek line and an unreadable peek (the
  preflight refuses), no marks, no stop, sticky marks, a B0 stop, a failed fill; the refusals (old
  module, knobs incl. render_tail_room, full disk at the preflight and before a job, an existing
  attempt, changed files); a watchdog, an exception, the trap (knobs back, work directory gone).

## Layout

`asm/`, `bins/` (R4's blob), `gen/` (`r5layout.py` the one source, `gen_r5.py`, `laptop_files.py`,
R3k's `r3layout.py`, `r3blobs.py`), `tables/p1.json`, `predictions/p1.tsv`, `TABLES.md`,
`stages.txt`, `run/` (`r6hp_run.py` the laptop runner, `ops_h.py`, `r3common.py`,
`health_remote.sh`, `p.sh` the driver, `stage_p.sh`, `freeze_p.sh`, `guard_p.sh`, `guard_*.py`),
`score/` (`score_p.py`, `sc_h.py`, `r5common.py`, `scorelib.py`, `scorekit.py`), `tests/`.

## Publishable

Everything here is our own and cites landed records only (E855 for R-6's reading). **No file is
firmware-derived**; nothing goes to data-private from `p/`. (The O3 oracle beside it, `../private/`,
is data-private: the parent's README says so.)

## Deviations

1. **No `run/` laptop directory**: the staged tree (runner included) is `~/scratch/r6h/p/stage`,
   the results `~/scratch/r6h/p/out`, the work directories `~/scratch/tmp/r6hp.XXXXXX`.
2. **The job's fill is not wrapped in `timeout`** (E855's start-up timing: the kick must land within
   the 16-tick ring window); the runner bounds it (6 s, then killed). The landed gate's tool calls
   are the landed code's (no timeout), inside the driver's 600 s alarm.
3. **E855's H-HWR rows stay held-out rows** (replicates), not controls: the runner's stop rule
   already ends the stage on a stop without the marks (exit 8), which is the control's effect.
4. **H-RESET** is its own [infer] family (not a control): a 0x0694 that survives the reset must not
   void the H-R6 rows.
5. **Two B1P jobs**, not E855's three (the parent's plan: 3 jobs), stop budget 2.
