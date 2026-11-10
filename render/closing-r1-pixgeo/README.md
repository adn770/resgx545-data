# R1-pixgeo of the resgx545 question-closing pass: prepared, NOT run

Part of laptop session R1: Q276 C2 (pixel) and geometry round 2 (U1, C1, T1, T2, T7, U2, T5, T6),
with the 0x072c trial in the first DPM job (decisions R2-11 to R2-17 in
`plans/resgx545-question-closing.md`).  Built offline in
`~/src/scratch/resgx545/closing2/r1-pixgeo/` from S1b's framework (`closing/s1b-v2/`) and the
gate ideas of S3.  Nothing here touched the laptop; nothing is committed.  Read `PREFLIGHT.md`
first (jobs, time, controls, the gate, risks, what was wrong in the proposals).

## Layout (the same pieces as S1b)

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|P|knobs|rt|command`); `TABLES.md` is
  the readable view with every frozen prediction (quantity = value [hypothesis] label)
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`; `set` is control,
  heldout, repeat (a fit of earlier data run again) or replicate
- `gen/r1gen.py` (+ `r1_q276.py`, `r1_geo.py`, `r1models.py`, `rcommon.py`): regenerate tables,
  predictions, programs (`bins/`), `TABLES.md`, `stages.txt`.  `r1models.py` holds the offline
  models (HU1/HU2, Sutherland-Hodgman + zigzag + prim words + depth, RZ/RN reciprocal words)
- `templates/`: `vtx_zab_pa1.s` (T2, one changed line), `vtx_zw.s` (T3), `vtx_wzclip.s` (T4) and
  the copy of `pix_green.s`; T3 and T4 have no rows in R1
- `score/score_r1.py STAGE out/STAGE`: the scorers (refuse unless the freeze verifies);
  `score_q276.py`, `score_geo2.py`, `gate072c.py`, `r1lib.py`
- `run/stage_r1.sh --src PATH`: copies runner, tables and programs to the laptop and rebuilds the
  tool there (one userspace rebuild for all three templates)
- `run/r1.sh [--from STAGE | --only STAGE... | --cell STAGE JOB]`: the Mac-side driver (verify,
  one ssh a stage, copy, health), every ssh/scp bounded by a perl alarm
- `run/run_stage.sh`, `run/lib_r1.sh`: the laptop-side runner (including the 0x072c gate)
- `run/freeze_r1.sh [freeze|verify]`, `FROZEN.sha256`, `PREDICTIONS.sha256`, `TOOLSRC.sha256`
- `run/guard_r1.sh`: the forbidden list, wait loops, debugfs only through `sudo -n`
- `tests/`: `run_all.sh` runs everything below: `test_models.py`, `test_gen.py`,
  `test_templates.py` (assemble + simulator + `--mock`), `test_gate.py`, `test_scorers_r1.py`
  (S1/S1b fixtures and synthetic worlds), `mock_all.py` (every command against the tool's mock),
  `run_mock.sh` (runner, gate, guard, driver, staging end to end)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; scorers,
generators and tests only, never on the laptop).  Always `export PYTHONDONTWRITEBYTECODE=1`.

## Order

`stages.txt`: p-c2 (Q276 C2, 41 jobs), g-u1 (21; its first two jobs are the 0x072c trial), g-c1
(22), g-t1 (11), g-t2 (7), g-t7 (4), g-u2 (9), g-t5 (9), g-t6 (7): 131 jobs, no pause.  `g-c1f`
(16 candidate step-1 cells, one of them runs after the C1 verdict) is a table, not a stage.

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing2/r1-pixgeo
bash tests/run_all.sh                                  # offline, all must pass
run/freeze_r1.sh verify
SGX_DRY_RUN=1 run/stage_r1.sh --src ~/src/resgx545     # prints "deploy inputs match the freeze"
run/stage_r1.sh --src ~/src/resgx545                   # stage + userspace rebuild (the one rebuild)
run/r1.sh                                              # stops at the first non-zero stage or health
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
PYTHONDONTWRITEBYTECODE=1 $PY score/score_r1.py g-u1 out/g-u1   # one SUMMARY a stage (+ the gate)
run/r1.sh --cell g-c1f f-1500-0x373                    # the step-1 cell once C1's flip is known
```
