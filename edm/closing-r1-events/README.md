# R1-events: laptop session R1 (events part) of the question-closing pass, round 2

Prepared, NOT run. Nothing here touched the laptop; nothing is committed. Read `PREFLIGHT.md`
first. Decisions: `~/src/plans/resgx545-question-closing.md`, "Round 2 decisions" (R2-3 to R2-6,
R2-17). Proposal: `closing2/exp-events.md` sections 2 to 4.

It is a copy of the framework of `closing/s2b/` (EDM ring tasks, kernel-log markers, gates, scorer,
mock, freeze) and `closing/s1b-v2/` (render jobs through the probe tool, preflight, staging):

| stage | rows | what runs | gate |
|---|---|---|---|
| k | Q290 K0-K6 | ring_e1, one arm a job, kicks, client jobs | none |
| t | Q082 T0-T4, T6 | loop programs through `probe`, stock firmware | none |
| d0 | Q033 D0, D1 | ring_e1 (12 rungs in slot 3), tri 64x64, partial render | opens d1 |
| d1 | Q033 D2-D4 (+D5) | 4096x4096, 1500 vertices, under regtimeline | none |

K7 (Q290), T5 (Q082) and everything of R2 and R3 are not here.

## Layout

- `asm/ring_e1.s`, `bins/ring_e1.blob`: S2's event ring with slot 3 at 12 rungs (692 instructions,
  verified by the landed `tools/fwtask/fwtask.py`, sha256 in `bins/blobs.json`); `asm/loop-*.s`,
  `bins/loop-*.bin`: our own loop programs (body 8, 16, 4 and 8 with a load) for Q082, assembled by
  the landed `usse-asm`; `bins/vtx-stock.bin` (the landed `asm/tri/use_vtx.s`),
  `bins/p1139-green.bin` (S1b's, for D2-D4)
- `tables/STAGE.json`: one job table a stage; `TABLES.md` the readable view
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`
- `gen/gen_r1.py` (writes all of the above), `gen/r1layout.py` (the results page layout)
- `score/score_r1.py STAGE OUTDIR [--gate]`: the scorer; states held, FAILED, cannot tell, void;
  fit, held-out, replicate and control rows tallied apart; `--gate` only for d0
- `run/r1_run.py` (laptop runner), `run/r1.sh` (Mac driver), `run/stage_r1.sh` (copy and check),
  `run/health_remote.sh` (health on the laptop), `run/freeze_r1.sh`, `run/guard_r1.sh`,
  `run/guard_py.py`
- `FROZEN.sha256`, `PREDICTIONS.sha256`, `LAPTOP.sha256`, `TOOL.sha256` (the pinned tool, S1b's
  `~/sgxfive-test-s1b`)
- `tests/`: `test_scorer.py`, `sim_r1.py`, `mock_tool_check.py`, `run_mock.py` (and its mock:
  `mockfw/`, `shims/`, `fake_tool.py`, `fake_rt.py`, `fake_health.sh`)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy is not needed by
anything here; the laptop needs only its python3, 3.8 or later). Always
`export PYTHONDONTWRITEBYTECODE=1`.

## Run (the lead)

The laptop must be in linux-resgx545 (one-shot grub-reboot, decided in R2) with the tool
`~/sgxfive-test-s1b` and `~/regtimeline` of S1b in place.

```
cd ~/src/scratch/resgx545/closing2/r1-events
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
PYTHON=../../closing/pixel-faults/.venv/bin/python run/guard_r1.sh
run/freeze_r1.sh verify
SGX_DRY_RUN=1 run/stage_r1.sh                        # prints the commands
run/stage_r1.sh                                      # copies, checks the pinned tool, builds nothing
run/r1.sh                                            # k, t, d0 (gate), d1; stops at the first problem
run/r1.sh --from d1                                  # resume after a stop (d0's gate must be OPEN)
```

Scores: `out/score-STAGE.txt` (one `SUMMARY:` line each; `out/STAGE/` has the kept files).
Refreeze (`run/freeze_r1.sh freeze` after `gen/gen_r1.py`) only before the first job.

## Tests (all offline)

```
PY=../../closing/pixel-faults/.venv/bin/python
$PY tests/test_scorer.py        # scorers: synthetic models, voids, past-run fixtures
$PY tests/sim_r1.py             # blob and loops in sgx-sim
$PY tests/mock_tool_check.py    # every client command through the landed tool's --mock
$PY tests/run_mock.py           # end to end on a mock laptop (about 100 s)
```
