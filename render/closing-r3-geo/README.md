# R3-geo of the resgx545 question-closing pass: prepared, NOT run

Part of laptop session L1 of round 3: depth at w != 1 (Q230: g-da, g-db, g-dc, g-dd), the raise limit C
by target (Q210: g-c4, g-c6, g-c5, g-c7) and dword 36 (Q273: g-d36, plus the H-last side table in every
DPM job), decisions R3-G1 to R3-G9 in `plans/resgx545-question-closing.md`.  Built offline in
`~/src/scratch/resgx545/closing3/r3-geo/` as a copy of round 2's framework (`closing2/r2-geo/`, which
is untouched) from the design `closing3/geometry/exp-geometry-r3.md` and its scratch scripts.  Nothing
here touched the laptop; nothing is committed.  Read `PREFLIGHT.md` first (jobs, time, controls, stops,
risks, deviations from the design).

## Layout (the same pieces as R2-geo)

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|P|knobs|rt|command`); `TABLES.md` is the
  readable view with every frozen prediction (quantity = value [hypothesis] label).  P may be a cell
  the RUNNER derives from the observations it kept (`B:G` bisect, `L:G` / `F:G` last raise / first
  silent), see the header of `run/run_stage.sh`
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`; `set` is control,
  heldout, repeat or replicate; case names starting `@` are stage-level
- `gen/r3gen.py` (+ `r3_geo.py`, `r3models.py`): regenerate tables, predictions, programs (`bins/`),
  `TABLES.md`, `stages.txt`.  `r3models.py` holds the frozen models (the depth rules D1 D2 D5 T26 T27
  K23 and direction variants, the viewport candidates, LT and the affine laws of C, H-last), exact
  float32 by rationals; `r1_geo.py`, `r1models.py`, `r2models.py` (clip predictions), `rcommon.py` are
  round 2's helpers
- `templates/`: `vtx_wzclip.s` and `vtx_zw.s` (R1's, simulator-checked, unchanged), `pix_green.s`
- `score/score_r3.py STAGE out/STAGE [--ctl out/g-c4]`: the scorers (refuse unless the freeze
  verifies); `dpm3.py` the DPM readers and the bisect rules (the Python twin of the runner's awk);
  `score_r2.py`, `score_geo2.py`, `r1lib.py` are earlier readers imported unchanged
- `run/stage_r3.sh`: copies runner, awk readers, tables and programs to `~/r3g*` on the laptop and checks the
  pinned tool; NO rebuild (tool `~/sgxfive-test-r1`, sha256 `bf4f8be2...` in `TOOL.sha256`)
- `run/r3.sh [--from STAGE | --only STAGE... | --cell STAGE JOB]`: the Mac-side driver (verify, one
  ssh a stage, copy, health), every ssh/scp bounded by a perl alarm
- `run/run_stage.sh`, `run/lib_r3.sh`, `run/dpm_read.awk`, `run/bis.awk`: the laptop-side runner
- `run/freeze_r3.sh [freeze|verify]`, `FROZEN.sha256`, `PREDICTIONS.sha256`, `TOOL.sha256`,
  `TOOLSRC.sha256`; `run/guard_r3.sh`: the forbidden list (no poke of any kind, no other session's
  directory)
- `tests/`: `run_all.sh` runs everything below: `test_models_r3.py`, `test_gen_r3.py`,
  `test_templates_r3.py` (the 57 depth programs in sgx-sim), `test_scorers_r3.py` (past-run data and
  synthetic worlds), `test_awk_reader.py`, `mock_all.py` (every command against the tool's mock),
  `run_mock.sh` (the runner end to end on a synthetic world, compared with `compare_twin.py`)
- `debug/`: scratch (`tmp/` for the tests); untracked, deletable

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (generators, scorers and tests
only, never on the laptop).  Always `export PYTHONDONTWRITEBYTECODE=1`.

## Order

`stages.txt`: g-da (27 jobs), g-db (16), g-dc (10), g-dd (4), g-c4 (10), g-d36 (6), g-c6 (5), g-c5
(36), g-c7 (11, last, behind its calibration gate): 125 jobs.

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing3/r3-geo
export PYTHONDONTWRITEBYTECODE=1
bash tests/run_all.sh                                  # offline, all must pass
run/guard_r3.sh && run/freeze_r3.sh verify
SGX_DRY_RUN=1 run/stage_r3.sh                          # prints the commands, builds nothing
run/stage_r3.sh                                        # copies, checks the tool hash on the laptop
run/r3.sh                                              # stops at the first non-zero stage or health
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
$PY score/score_r3.py g-c4 out/g-c4                    # one SUMMARY a stage
$PY score/score_r3.py g-c5 out/g-c5                    # takes its controls from out/g-c4
```
