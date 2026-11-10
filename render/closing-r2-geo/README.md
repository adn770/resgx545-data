# R2-geo of the resgx545 question-closing pass: prepared, NOT run

Part of laptop session R2: geometry stages T3, T4, T5 (Q082, a looping vertex program), C3 (a
second target) and C2 (the `pb:11` descriptor poke, last), decisions R2-5, R2-12, R2-14, R2-15 and
R2-17 in `plans/resgx545-question-closing.md`.  Built offline in
`~/src/scratch/resgx545/closing2/r2-geo/` from R1-pixgeo's framework (`closing2/r1-pixgeo/`) and
its results.  Nothing here touched the laptop; nothing is committed.  Read `PREFLIGHT.md` first
(jobs, time, controls, the T5 decision, the C2 design, risks, changes from the proposal).

## Layout (the same pieces as R1-pixgeo)

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|P|knobs|rt|command`); `TABLES.md` is
  the readable view with every frozen prediction (quantity = value [hypothesis] label)
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`; `set` is control,
  heldout, repeat or replicate
- `gen/r2gen.py` (+ `r2_geo.py`, `r2models.py`): regenerate tables, predictions, programs
  (`bins/`), `TABLES.md`, `stages.txt`.  `r2models.py` holds the new offline models (homogeneous
  clipping with w != 1, the made vertices' 1/w by two candidates, six depth candidates, exact
  float32 rounding); `r1_geo.py`, `r1models.py`, `rcommon.py` are R1's files (`rcommon.py` with
  the R2 poke rules added)
- `templates/`: `vtx_loop.s` (T5, new), `vtx_zw.s` (T3) and `vtx_wzclip.s` (T4) (R1's,
  simulator-checked), `vtx_zab_pa1.s`, `pix_green.s`
- `score/score_r2.py STAGE out/STAGE`: the scorers (refuse unless the freeze verifies);
  `score_geo2.py` and `r1lib.py` are R1's readers, unchanged
- `run/stage_r2.sh`: copies runner, tables and programs to the laptop and checks the pinned tool;
  NO rebuild (the tool is R1's `~/sgxfive-test-r1`, sha256 `bf4f8be2...` in `TOOL.sha256`)
- `run/r2.sh [--from STAGE | --only STAGE... | --cell STAGE JOB]`: the Mac-side driver (verify,
  one ssh a stage, copy, health), every ssh/scp bounded by a perl alarm
- `run/run_stage.sh`, `run/lib_r2.sh`: the laptop-side runner (no 0x072c gate: R1's passed; knobs
  `s2`, `sweep:G`, `kpoke`, `wd:S`)
- `run/freeze_r2.sh [freeze|verify]`, `FROZEN.sha256`, `PREDICTIONS.sha256`, `TOOL.sha256`,
  `TOOLSRC.sha256` (R1's pins, copied)
- `run/guard_r2.sh`: the forbidden list; debugfs only through `sudo -n`; the one allowed poke
- `tests/`: `run_all.sh` runs everything below: `test_models.py` (models against S1b objects and
  numpy), `test_gen.py`, `test_templates.py` (assemble + simulator + `--mock`), `test_t5loop.py`
  (the vertex loop in sgx-sim at five code indices), `test_scorers_r2.py` (R1/S1b fixtures and
  synthetic worlds), `mock_all.py` (every command against the tool's mock), `run_mock.sh` (runner,
  sweep stop, watchdog, poke rules, guard, driver, staging end to end)
- `debug/`: scratch (`simcheck/`, a cargo crate over `crates/sgx-sim` by path, read-only;
  `target/`; `tmp/` for the tests); untracked, deletable

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; generators, scorers
and tests only, never on the laptop).  Always `export PYTHONDONTWRITEBYTECODE=1`.  The tests set
`TMPDIR` to `debug/tmp` themselves.

## Order

`stages.txt`: g-t3 (4 jobs), g-t4 (8), g-t5v (13; the ladder stops at the first length that sets
STATUS2 bit 7), g-c3 (11), g-c2 (9, the poke, last): 45 jobs.  `g-c3f` (8 fallback cells:
2048x1536 as the proposal says and 4096x3072) is a table, not in the order.

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing2/r2-geo
export PYTHONDONTWRITEBYTECODE=1
bash tests/run_all.sh                                  # offline, all must pass
run/guard_r2.sh && run/freeze_r2.sh verify
SGX_DRY_RUN=1 run/stage_r2.sh                          # prints the commands, builds nothing
run/stage_r2.sh                                        # copies, checks the tool hash on the laptop
run/r2.sh                                              # stops at the first non-zero stage or health
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
$PY score/score_r2.py g-t5v out/g-t5v                  # one SUMMARY a stage
run/r2.sh --only g-c3f                                 # only if g-c3's 2048x2048 cells were all void
```
