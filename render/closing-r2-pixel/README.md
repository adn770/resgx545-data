# R2-pixel of the resgx545 question-closing pass: prepared, NOT run

Part of laptop session R2: Q281 D2 (the probe's VM layout, 7 jobs) and Q286 A2 (the TA data
sufficiency, 6 jobs, plus the pre-approved slack pair as a conditional stage).  Decisions R2-7 to
R2-9 and R2-17 of `plans/resgx545-question-closing.md`, proposal `closing2/exp-pixel.md` sections
2 and 3.  Built offline from S3 (held faults, a-rows, scorer), S1b (p-d rows) and R1-pixgeo
(runner fixes).  Nothing here touched the laptop; nothing is committed.  Read `PREFLIGHT.md`
first (jobs, time, controls, decision rule, risks, what changed from the proposal).

## Layout

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|knobs|rt|command`); `TABLES.md` is the
  readable view with every frozen prediction (quantity = value [hypothesis]).
- `predictions/`: `r2-d.tsv`, `r2-a.tsv` (case, quantity, value, model, set; frozen, hashes in
  `PREDICTIONS.sha256`) and `r2-d-images.tsv` (the model's 2048 words for d-ok-64, 19, 19x, 18x).
- `gen/r2gen.py` regenerates tables, predictions, the variant program (`bins/`), `TABLES.md`,
  `stages.txt`, `conditional.txt`; `r2models.py` is the Q281 layout model (HL); `gen/data/` holds
  S1b's frozen A4 images the model reads; `templates/` the landed `tx_map.s` and the one-line
  variant `tx_map_x1.s`.
- `score/score_r2.py` (+ `r2lib.py`): one scorer per stage, `verdict` (Q281, Q286) and `gate`;
  it refuses to run unless the freeze verifies.
- `run/`: `stage_r2.sh` (Mac, copies and checks), `r2.sh` (Mac driver: gates, ssh, copy, score,
  health), `run_stage.sh` + `lib_r2.sh` + `r2.env` (laptop runner), `freeze_r2.sh`,
  `guard_r2.sh`, `lib_check.sh`; `FROZEN.sha256`, `PREDICTIONS.sha256`.
- `tests/`: `run_all.sh` runs everything: `test_models.py`, `test_gen.py`, `test_scorers_r2.py`
  (S1b/S1/S3 landed data and synthetic worlds), `mock_all.py` (every command against the landed
  tool's `--mock`), `run_mock.sh` (runner, stop rules, guard, staging and the whole driver
  against a fake tool, fake debugfs, fake ssh/scp); `tests/fixtures/` has the landed data used.

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; generator, scorers
and tests only, never on the laptop).  Always `export PYTHONDONTWRITEBYTECODE=1`.

## Order

`stages.txt`: r2-d-safe (5 jobs), r2-d-fault (2), r2-a-safe (4), r2-a-fault (2: held).  The
conditional `r2-a-slack` (3) runs after r2-a-fault only if the slack gate opens (PREFLIGHT 5).
Health after every stage (the driver) and after every fault (the runner).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing2/r2-pixel
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                       # offline, all must pass
run/freeze_r2.sh verify
SGX_DRY_RUN=1 run/stage_r2.sh               # prints the commands
run/stage_r2.sh                             # copies, compares with the Mac's, checks R1's tool
run/r2.sh                                   # the session; stops at the first non-zero status
$PY score/score_r2.py verdict out/ATT [out/EARLIER...]     # Q281 and Q286 SUMMARY lines
```

`run/r2.sh --only STAGE` (a new attempt directory) reruns one stage; `run/r2.sh --from STAGE` with
`R2_FAULTS_PRIOR=N` continues after a stop (the stop message prints both).  There is no gate
file anywhere: gates are computed from the kept stage directories (this attempt, then earlier
ones), so restaging or a new attempt never loses one.
