# R3-events: laptop session R3 of the question-closing pass, round 2

Prepared, NOT run. Nothing here touched the laptop; nothing is committed. Read `PREFLIGHT.md`
first. Decisions: `~/src/plans/resgx545-question-closing.md`, "Round 2 decisions" (R2-1, R2-2,
R2-3, R2-17). Proposal: `closing2/exp-events.md` sections 0 to 2.

It is a copy of the framework of `closing2/r1-events/` (kernel-log markers, kept-output gates,
scorer layout, preflight with the srcversion check, mock) and `closing/s2b/` (ring_hold, the
90-tick mid-period hold):

| stage | rows | what runs | gate |
|---|---|---|---|
| a | Q152 A0-A6 (A7, A8 are NOT here) | `alias.s` (one entry), 19 jobs | none |
| b | Q152 B0, B1, B2 (B3 is NOT here) | `ring_skip.s`, 8 jobs; B2 only if B1 kept the tick | a finished |
| k7 | Q290 K7, LAST, reset after | `ring_hold.blob` (S2b's), 90-tick hold, 5 jobs | b finished |

A gate is the previous stage's own kept `stage.json` (exit 0, or 8 when a second tick stop
ended it and the lead chose `--from`): derived from kept output, never from a file the staging
resets.

## Layout

- `asm/alias.s`, `asm/ring_skip.s`, `asm/ring_hold.s` and `bins/*.blob`, `bins/blobs.json`: the
  three tasks (208, 656 and 747 instructions, all accepted by the landed `tools/fwtask`;
  `ring_hold.blob` is S2b's byte for byte, sha256 `fa0f79db...`)
- `tables/{a,b,k7}.json`: one job table a stage; `TABLES.md` the readable view
- `predictions/{a,b,k7}.tsv`: frozen predictions `case quantity value model set`
- `gen/gen_r3.py` (writes all of the above), `gen/r3blobs.py` (the two new tasks and the
  scans the guard shares), `gen/r3layout.py` (the results page layout)
- `score/score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...`: the scorer; states held,
  FAILED, cannot tell, void; the stop signature (busy / idle-pending / idle-empty, scored
  against E537's); fit, held-out, replicate and control rows tallied apart
- `run/r3_run.py` (laptop runner), `run/r3.sh` (Mac driver), `run/stage_r3.sh` (copy and
  check), `run/health_remote.sh`, `run/freeze_r3.sh`, `run/guard_r3.sh`, `run/guard_py.py`,
  `run/guard_blobs.py` (the limits applied to the ASSEMBLED code and to the tables)
- `FROZEN.sha256`, `PREDICTIONS.sha256`, `LAPTOP.sha256`, `TOOL.sha256` (the pinned health
  tool, S1b's `~/sgxfive-test-s1b`)
- `tests/`: `sim_r3.py` (blobs in sgx-sim), `test_scorer.py` (fixtures and synthetic worlds),
  `test_guard.py` (every limit broken in a copy), `run_mock.py` (and its mock: `mockfw/`,
  `shims/`, `fake_tool.py`, `fake_health.sh`)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy is not needed by
anything here; the laptop needs only its python3, 3.8 or later). Always
`export PYTHONDONTWRITEBYTECODE=1`.

## Run (the lead)

The laptop must be in linux-resgx545 with the tool `~/sgxfive-test-s1b` of S1b in place.

```
cd ~/src/scratch/resgx545/closing2/r3-events
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHON=../../closing/pixel-faults/.venv/bin/python PY=../../closing/pixel-faults/.venv/bin/python
run/guard_r3.sh
run/freeze_r3.sh verify
SGX_DRY_RUN=1 run/stage_r3.sh                        # prints the commands
run/stage_r3.sh                                      # copies, checks the pinned tool, builds nothing
run/r3.sh                                            # a, b, k7; stops at the first problem
run/r3.sh --from b                                   # resume (a's kept stage.json is the gate)
```

Scores: `out/score-STAGE.txt` (one `SUMMARY:` line each; `out/STAGE/` has the kept files, the
stop dumps `stop-NAME-regs.txt` and the stop signatures inside the job records).
Refreeze (`run/freeze_r3.sh freeze` after `gen/gen_r3.py`) only before the first job.

## Tests (all offline)

```
PY=../../closing/pixel-faults/.venv/bin/python
$PY tests/sim_r3.py        # blobs in sgx-sim
$PY tests/test_scorer.py   # scorers on E536/E537/S2b/R1 fixtures and synthetic worlds
$PY tests/test_guard.py    # the guard on assembled code and tables
$PY tests/run_mock.py      # end to end on a mock laptop (a few minutes)
```
