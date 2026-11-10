# R3K-pixel (kernel-batch session K2, pixel and fault rows): prepared, NOT run

Round 3 of the resgx545 question-closing pass.  Runs AFTER K0 and K1, on the new gma500 module
(fork `resgx545` at 8fc748b0, srcversion 230E0EF50FFFD606C53AE3C).  Questions: Q140 (four
region-header arrays), Q285 (the cause of the empty image, by pokes into the parameter buffer),
Q003 "what clears" (pixel E2: host writes of `CR_BIF_CTRL` and `CR_BIF_INT_STAT`).  Decisions R3-K4,
R3-K6, R3-K7 in `plans/resgx545-question-closing.md` (Round 3); design
`closing3/kernel/exp-kernel-r3.md` section 2.2, what was built `closing3/kernel/series-r3.md`.
Built offline on the Mac as a copy of round 2's `closing2/r2-pixel` (held faults, fault limit) with
`closing3/r3-pixel`'s conventions (attempts, module pin, tool pins).  Nothing here touched the
laptop, cachix or a git repo; nothing is committed.  Read `PREFLIGHT.md` first.

## Layout

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|knobs|rt|command`); `TABLES.md` is the
  readable view with every frozen prediction (quantity = value [model, set]).
- `predictions/`: `k-f4.tsv`, `k-pb.tsv` (also carries the three controls of `k-pb0`), `k-bif.tsv`
  (case, quantity, value, model, set; frozen, hashes in `PREDICTIONS.sha256`).
- `gen/kgen.py` regenerates tables, predictions, `TABLES.md`, `stages.txt`; `gen/data/pb_words.tsv`
  holds the landed words of the parameter buffer (E728's own and the twin's, dwords 0-26).
- `score/score_k.py` (+ `klib.py`): one scorer per stage, `verdict` (Q140, Q285, Q003) and `gate`
  (k-pb needs k-pb0's three controls); it refuses to run unless the freeze verifies.
- `run/`: `stage_k.sh` (Mac: copies and checks), `k.sh` (Mac driver: gate, ssh, copy, score, health,
  the knob check), `run_stage.sh` + `lib_k.sh` + `k.env` (laptop runner), `freeze_k.sh`,
  `guard_k.sh`, `lib_check.sh`; `FROZEN.sha256`, `PREDICTIONS.sha256`; `TOOL.sha256` and
  `TOOLSRC.sha256` are r3-pixel's pins (copied).
- `tests/`: `run_all.sh` runs everything: `test_gen.py`, `test_scorers_k.py` (round 2's kept fault
  data, E728's landed images and synthetic worlds where each hypothesis wins and loses),
  `mock_all.py` (every command against the landed tool's `--mock`), `run_mock.sh` (runner, stop
  rules, guard, staging and the whole driver against a fake tool, fake debugfs with the new files,
  fake ssh/scp); `tests/fixtures/` has the landed data used.

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; generators,
scorers and tests only, never on the laptop).  Always `export PYTHONDONTWRITEBYTECODE=1`.

## Order

`stages.txt`: k-f4 (11 jobs), k-pb0 (3), k-pb (5), k-bif (5): 24 jobs.  Fault rows last in their
stages, the riskiest stage (k-bif) last of the session.  Laptop directories `~/r3kpx-run`,
`~/r3kpx-stage`, `~/r3kpx-out` (no other session's).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing3/r3k-pixel
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                       # offline, all must pass
run/guard_k.sh && run/freeze_k.sh verify
SGX_DRY_RUN=1 run/stage_k.sh                # prints the commands
run/stage_k.sh                              # copies, compares, checks the tool and regtimeline
run/k.sh                                    # the session (stops: PREFLIGHT.md section 6)
$PY score/score_k.py verdict out/ATT        # Q140, Q285, Q003 lines from the kept stages
```

`run/k.sh --only STAGE` (a new attempt directory) reruns one stage; `run/k.sh --from STAGE`
continues after a stop.  There is no gate file anywhere: the gate of k-pb is computed from the kept
k-pb0 directory (this attempt, then earlier ones).
