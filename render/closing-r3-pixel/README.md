# R3-pixel of the resgx545 question-closing pass (round 3): prepared, NOT run

Laptop session L2 (pixel): Q082 (STATUS2 bits 6 and 7, pixel and TA side) and Q276 (the o4 gating
in a triangle's pixel program). Decisions R3-P1 to R3-P10 in `plans/resgx545-question-closing.md`
(Round 3), design `closing3/pixel/exp-pixel-r3.md`.  Built offline on the Mac as a copy of round
2's frameworks (`closing2/r1-pixgeo`, `r2-geo`, `r2-pixel`, `r1-events`); nothing here touched the
laptop, cachix or a git repo; nothing is committed.  Read `PREFLIGHT.md` first (jobs per stage,
time, controls, stops, risks, DEVIATION entries).

## Layout

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|knobs|rt|command`; `#need` lines list
  the staged programs); `TABLES.md` is the readable view with every frozen prediction (quantity =
  value [hypothesis]).
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`; `set` is control,
  heldout, repeat (CONFIRM rows of Q276 and E769's refuted rows, tallied apart) or replicate.
  Pseudo-cases (`ladder-*`, `vladder-*`, `f0-agree`) carry what belongs to a ladder or a pair.
  Hashes in `PREDICTIONS.sha256`.
- `gen/r3gen.py` (+ `r3_f.py` q-f0 / q-f1, `r3_t.py` q-t, `r3_v.py` q-v, `r3_c.py` p-c3,
  `r3loops.py` the loop programs, `r3common.py`) regenerate tables, predictions, programs
  (`bins/`), `TABLES.md`, `stages.txt`, `conditional.txt` (empty: no conditional stage).
  `score/r3const.py` holds the frozen constants and the per-N predictions shared by generator and
  scorers.
- `score/score_r3.py` (+ `score_f.py`, `score_t.py`, `score_v.py`, `score_c3.py`, `r3job.py`,
  `r3lib.py`): one scorer per stage, the loop `gate`, and the `verdict`; it refuses to run unless
  the freeze verifies.
- `templates/`: `vtx_loop.s` (the vertex loop, body as a parameter), `pix_green.s`.
- `run/`: `stage_r3.sh` (Mac: copies and checks), `r3.sh` (Mac driver: gates, ssh, copy, score,
  health), `run_stage.sh` + `lib_r3.sh` + `r3.env` (laptop runner), `freeze_r3.sh`, `guard_r3.sh`,
  `lib_check.sh`; `FROZEN.sha256`, `PREDICTIONS.sha256`; `TOOL.sha256` and `TOOLSRC.sha256` are
  R1's pins (copied).
- `tests/`: `run_all.sh` runs everything: `test_loops.py` (every loop program in sgx-sim at its
  real code index), `test_gen.py`, `test_scorers_r3.py` and `test_scorers_c3.py` (kept data and
  synthetic worlds where each hypothesis wins and loses), `mock_all.py` (every command against the
  landed tool's `--mock`), `run_mock.sh` (runner, stop rules, guard, staging and the whole driver
  against a fake tool, fake regtimeline, fake debugfs, fake ssh/scp); `tests/fixtures/` holds the
  landed data used (E431 timelines, E784 vertex runs, R1 p-c2 and S1b p-c images).
- `debug/`: scratch (`simcheck/`, a cargo crate over `crates/sgx-sim` by path, read-only, with a
  `--pixel` flag; `target/`; `tmp/`); untracked, deletable.

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; generators, scorers
and tests only, never on the laptop).  Always `export PYTHONDONTWRITEBYTECODE=1`.

## Order

`stages.txt`: p-c3 (75 jobs), q-f0 (10), q-f1a (54), q-f1b (54, the opposite order), q-t (93), q-v
(88): 374 jobs.  Laptop directories `~/r3p-run`, `~/r3p-stage`, `~/r3p-out` (no other session's).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing3/r3-pixel
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                       # offline, all must pass
run/guard_r3.sh && run/freeze_r3.sh verify
SGX_DRY_RUN=1 run/stage_r3.sh               # prints the commands
run/stage_r3.sh                             # copies, compares, checks R1's tool and regtimeline
run/r3.sh                                   # the session (stops: PREFLIGHT.md section 5)
$PY score/score_r3.py verdict out/ATT       # Q082 (pixel, TA) and Q276 lines from the kept stages
```

`run/r3.sh --only STAGE` (a new attempt directory) reruns one stage; `run/r3.sh --from STAGE`
continues after a stop.  There is no gate file anywhere: gates are computed from the kept stage
directories (this attempt, then earlier ones).
