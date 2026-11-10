# C3: laptop session L3b of the question-closing pass, round 3

Prepared, NOT run. Nothing here touched the laptop; nothing is committed. Read `PREFLIGHT.md`
first. Decision: R3-R1 a in `~/src/plans/resgx545-question-closing.md` (Round 3); proposal:
`closing3/rank-round3.md` section "C3" (Q158 and Q124's residual, the register start state of a
firmware task). It runs right BEFORE session L3 (events, `closing3/r3x-events/`, `~/r3xev`) as
its own session; no stop is expected, the first stop ends it.

It is a copy of the framework of `closing2/r3-events/` (kernel-log markers, kept-output scorer,
preflight with the srcversion check, mock), cut down to one stage and one task:

| stage | rows | what runs | gate |
|---|---|---|---|
| c3 | S0, N x3, F x3, L x3, R x3 (13 jobs) | `start.s` (one entry), the landed tick | none |

A job reads (rd0, the host's reader), writes (the writer sets sa63, r20, r21, i0, i1 from
markers and p0..p3 from flags, arms the reader of the next event: rdA), perturbs, and reads again
(rdB). Perturbations: S0 none (no writer, the start state as found); N 1200 ms; F one client fill
through the gate tool; L the landed `cmd_arm` again with no reset (own_arm 0, own_code, own_arm,
load, boot); R the landed `cmd_reset` and then `cmd_arm`.

## Layout

- `asm/start.s`, `bins/start.blob`, `bins/blobs.json`: the task (112 instructions, accepted by
  the landed `tools/fwtask`); the only sa register it writes is sa63, in the writer
- `tables/c3.json` (the job table), `TABLES.md` (readable view), `stages.txt`
- `predictions/c3.tsv`: frozen predictions `case quantity value model set`
- `gen/gen_c3.py` (writes all of the above), `gen/c3blobs.py` (the task and the scans the guard
  shares), `gen/c3layout.py` (the results page layout)
- `score/score_c3.py c3 OUTDIR | gate c3 ROOT | sig FILE...`: the scorer; states held, FAILED,
  cannot tell, void; the stop signature scored against E537's; fit, held-out, replicate and
  control rows tallied apart; verdict lines for Q124's p2/p3 and Q158's rows
- `run/c3_run.py` (laptop runner), `run/c3.sh` (Mac driver), `run/stage_c3.sh` (copy and check),
  `run/health_remote.sh`, `run/freeze_c3.sh`, `run/guard_c3.sh`, `run/guard_py.py`,
  `run/guard_blobs.py` (the limits applied to the ASSEMBLED code and to the table)
- `FROZEN.sha256`, `PREDICTIONS.sha256`, `LAPTOP.sha256`, `TOOL.sha256` (the pinned health tool,
  S1b's `~/sgxfive-test-s1b`)
- `tests/`: `sim_c3.py` (the blob in sgx-sim, every command path), `test_scorer.py` (fixtures and
  synthetic worlds), `test_guard.py` (every limit broken in a copy), `run_mock.py` (end to end on
  a mock laptop: `mockfw/`, `shims/`, `fake_tool.py`, `fake_health.sh`)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy is not needed; the
laptop needs only its python3, 3.8 or later). Always `export PYTHONDONTWRITEBYTECODE=1`.
Laptop directories: `~/r3xc3` (code) and `~/r3xc3-out` (results), no collision with `~/r3g`,
`~/r3gc`, `~/r3p-`, `~/r3xev`.

## Run (the lead)

The laptop must be in linux-resgx545 (srcversion B21FDA82BD5E5CB5A627E3B loaded = installed; the
preflight checks) with the tool `~/sgxfive-test-s1b` of S1b in place.

```
cd ~/src/scratch/resgx545/closing3/r3x-c3
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHON=../../closing/pixel-faults/.venv/bin/python PY=../../closing/pixel-faults/.venv/bin/python
run/guard_c3.sh
run/freeze_c3.sh verify
SGX_DRY_RUN=1 run/stage_c3.sh                        # prints the commands
run/stage_c3.sh                                      # copies, checks the pinned tool, builds nothing
run/c3.sh                                            # the stage; stops at the first problem
```

Scores: `out/score-c3.txt` (one `SUMMARY:` line; the verdict lines above it); `out/c3/` has the
kept files (a record a job, `env.json` with the uptime and boot id, the stop dumps
`stop-NAME-regs.txt`, the stop signature inside the job record). Refreeze
(`run/freeze_c3.sh freeze` after `gen/gen_c3.py`) only before the first job.

## Tests (all offline)

```
PY=../../closing/pixel-faults/.venv/bin/python
tests/run_all.sh           # all of the below
$PY tests/sim_c3.py        # the blob in sgx-sim
$PY tests/test_scorer.py   # scorer on E536/E537 fixtures and synthetic worlds
$PY tests/test_guard.py    # the guard on assembled code and the table
$PY tests/run_mock.py      # end to end on a mock laptop (about 3 minutes)
```
