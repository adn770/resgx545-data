# R4-pixel of the resgx545 question-closing pass (round 4): prepared, NOT run

Laptop session R4-pixel: Q082 (STATUS2 bits 6 and 7), Q276 (the o4 clause) and Q230 (the 1/w word),
userspace only, one session, five stages, 158 jobs, about 16 minutes of jobs. Plan:
`closing4/pixel/exp-pixel-r4.md`, section 3, decisions taken as recommended (R4-9 a, bit-7 scope a
with the 1500-vertex rows, triangles a with the t6 row and without 2x2, Q276 design a, Q230 table a,
tool a). Built offline on the Mac from round 3's framework (`closing3/r3-pixel`, the published copy
with the post-run scorer fixes), nothing here touched the laptop, cachix or a git repo.
Read `PREFLIGHT.md` first (jobs, time, controls, stops, risks, deviations).

## What runs, in this order (`stages.txt`)

| stage | jobs | question | what |
|---|---|---|---|
| p4-o4 | 36 | Q276 | which o4 word lands: 8 controls, 14 value jobs, 12 predicate jobs, 2 replicates |
| q4-v | 28 | Q082 | bit 7 against the TA-clock rule: 4 bridge controls, 3 ladders, 3 stock rows |
| q4-f | 16 | Q082 | what a load does to bit 6 in a fill: 5 bridge controls, 4 + 7 held out |
| q4-t | 54 | Q082 | bit 6 in triangles: 12 controls, H-SEG against H-N and E806's discrete reading |
| g4-rw | 24 | Q230 | a table of 60 1/w words, FIT / HELD OUT split frozen: 4 controls, 20 jobs |

Every stage starts with its bridge controls (the rgn4 module must reproduce round 3's values).
A bridge control that reads otherwise stops the SESSION (runner rc 18 or the scorer's gate, driver
exit 42): the lead decides. Any fault, hang or STATUS2 not 0x400 after a reset stops the stage.

## Layout

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|knobs|rt|command`; `#need` lines list
  the staged programs); `TABLES.md` is the readable view with every frozen prediction.
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`; hashes in
  `PREDICTIONS.sha256`. `FROZEN.sha256` pins every generator, scorer, runner script, table,
  prediction, program and template, and by absolute path the resgx545 and resgx545-data files read;
  `FROZEN.commits` names resgx545 commit `5a13042` for each resgx545 pin (`gen/frozen_commits.py`).
- `gen/`: `r4gen.py` regenerates everything (`r4_o4.py`, `r4_v.py`, `r4_f.py`, `r4_t.py`,
  `r4_rw.py`, `r4loops.py` the loop programs, `r4common.py`); `gen/pins_*.txt` list the files read.
- `score/`: `score_r4.py` (stage scorer, `gate`, `verdict`; refuses to run unless the freeze
  verifies), `score_v.py`, `score_f.py`, `score_t.py`, `score_o4.py` + `o4model.py`, `score_rw.py` +
  `rwfam.py` + `rwdesign.py`, `r4tl.py` (the timeline reader and the two frozen timing rules),
  `r4job.py`, `r4lib.py`, `r4const.py`, `scorekit.py` (a byte copy of `tools/closing/scorekit.py`).
- `templates/`: `pix_green.s`, `vtx_loop.s`, `vtx_loop2.s` (b2v), `vtx_zw.s` (w = C x + D).
- `run/`: `stage_r4.sh` (Mac: copies and checks), `r4.sh` (Mac driver), `run_stage.sh` +
  `lib_r4.sh` + `r4.env` (laptop runner), `freeze_r4.sh`, `guard_r4.sh`, `lib_check.sh`.
- `tests/`: `run_all.sh` runs everything (see PREFLIGHT.md section 8); `tests/fixtures/` holds the
  kept records used. `debug-src/simcheck` is the scratch cargo crate the loop test builds into
  `debug/` (source only, `Cargo.toml` names the pinned tree).

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy: generators,
scorers and tests only, never on the laptop). Always `export PYTHONDONTWRITEBYTECODE=1`.
Laptop directories: `~/r4p-run`, `~/r4p-stage`, `~/r4p-out` (prefix `~/r4p-`, no other session's).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing4/r4-pixel
export PYTHONDONTWRITEBYTECODE=1
export RESGX545_MAIN=~/src/resgx545      # a tree that holds commit 5a13042 (the pins verify on main
                                         # f5b3574 and on the lead worktree; see PREFLIGHT.md 1)
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                    # offline, all must pass
run/guard_r4.sh && run/freeze_r4.sh verify
SGX_DRY_RUN=1 run/stage_r4.sh            # prints the commands
run/stage_r4.sh                          # copies, compares, checks the rgn4 tool and regtimeline
run/r4.sh                                # the session (stops: PREFLIGHT.md section 5)
$PY score/score_r4.py verdict out/ATT    # one line a stage from the kept stages
```

`run/r4.sh --only STAGE...` (a new attempt directory) reruns stages; `run/r4.sh --from STAGE`
continues after a stop. There is no gate file anywhere: gates are computed from the kept stage.
