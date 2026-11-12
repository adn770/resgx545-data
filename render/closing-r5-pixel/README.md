# R5-pixel of the resgx545 question-closing pass (round 5): prepared, NOT run

Laptop session R5-pixel: Q276 (what the tag-5 word is) and Q230 (the 1/w word), userspace only, one
session, 106 jobs in three job tables, about 10 minutes of jobs and 15 to 20 with staging and
health. Plan: `closing5/pixel/exp-pixel-r5.md`, every decision (a) (`DECISIONS-R5.md` R5-3 a:
p5-o4 with 58 jobs, then g5-rw with the dense table, 48 jobs; no E406 setup; v-stock-4096 dropped).
Built offline on the Mac from round 4's R4-pixel (`render/closing-r4-pixel`, the published copy).
Nothing here touched the laptop, cachix or a git repo. Read `PREFLIGHT.md` first.

## What runs, in this order (`stages.txt`)

| table | jobs | question | what |
|---|---|---|---|
| p5-o4 | 58 | Q276 | 8 controls, the walk w-0..w-7 (16), 4 independent rows (8), predicate sets P4 and P3 (24), replicate of w-3 (2) |
| g5-rwa | 12 | Q230 | g5-rw part a: 6 controls (rw-k0..k5), the 6 quarter jobs q-15..q-20 scaled into the viewport |
| g5-rw | 36 | Q230 | g5-rw part b: m-01..m-14 (H-MANT, 42 words), replicates rw-07 and rw-10, the dense table d-01..d-20 |

Every row: `stophang s2` (STATUS2 read after the reset and after the job; not 0x400 after the reset
stops the stage, rc 16), a GPU reset before the job, no regtimeline, no knob write, no firmware
`str`, no kpoke. After each table the driver scores it and runs its gate: p5-o4's bridge controls
(c-e709 G-o4, c-u G-o1, c-v-a4 class A), g5-rwa's control words exact and fewer than three q jobs
FAILED shape. A gate that does not pass stops the session (exit 42): the lead decides.

## Stops

Any fault, hang, failure, freeze or kernel BUG stops the stage (rc 3, 4, 6), the first failed
health recovery stops (rc 5), STATUS2 not 0x400 after a reset (rc 16); a gate (42). No fault is
expected: 97 kept jobs of p5-o4's shape and 24 of g5-rw's ran clean in rounds 3 and 4.

## Layout

- `tables/STAGE.txt` (`name|set|risk|knobs|rt|command`; `#need` lines), `TABLES.md` (readable).
- `predictions/STAGE.tsv` (`case quantity value model set`); `PREDICTIONS.sha256`; `FROZEN.sha256`
  (every generator, scorer, runner, table, prediction, program, template, test and fixture list,
  and by absolute path the resgx545 and resgx545-data files read); `FROZEN.commits` (resgx545 main
  f0d5b39, which holds E850 and E851).
- `gen/`: `r5gen.py` writes everything (`r5_o4.py`, `r5_rw.py`, `r5common.py`); `pins_*.txt`.
- `score/`: `score_r5.py` (stage, `gate`, `verdict`; refuses unless the freeze verifies),
  `score_o5.py` + `o5model.py` (the nine models of E850), `score_rw5.py` + `rwdesign5.py`. R4's
  `score_o4.py`, `score_rw.py`, `rwdesign.py`, `rwfam.py`, `r4lib.py` are byte copies of the
  published R4 files (pinned), imported for R4's decode; `scorekit.py` = `tools/closing/scorekit.py`.
- `templates/`: `vtx_zws.s` (new: o0 = S x, o1 = S y), R4's `vtx_zw.s`, `pix_green.s`.
- `run/`: `stage_r5.sh` (Mac: copies and checks), `r5.sh` (Mac driver), `run_stage.sh` +
  `lib_r5.sh` + `r5.env` (laptop runner), `freeze_r5.sh`, `guard_r5.sh`, `lib_check.sh`.
- `tests/`: `run_all.sh` (PREFLIGHT.md 8); `fixtures/` (R3 and R4 kept files);
  `debug-src/simcheck` (the sgx-sim harness the tests and the fake tool build into `debug/`).

Laptop directories: `~/r5p-run`, `~/r5p-stage`, `~/r5p-out` (prefix `~/r5p-`, no other session's).
Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python`; numpy is not used.

## Publishing

Nothing in this directory is firmware-derived (no disassembly reading, no script importing one):
the whole directory may be published by the fold. `debug/` is scratch (build products, mock runs).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing5/r5-pixel
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                    # offline, all must pass (about 6 minutes)
run/guard_r5.sh && run/freeze_r5.sh verify
SGX_DRY_RUN=1 run/stage_r5.sh            # prints the commands
run/stage_r5.sh                          # copies, compares, checks the rgn4 tool
run/r5.sh                                # the session (stops: PREFLIGHT.md 5)
$PY score/score_r5.py verdict out/ATT    # one line a table
```

`run/r5.sh --from TABLE` (a new attempt directory) continues after a stop; `--only TABLE...`
reruns tables. g5-rw reads part a from the same attempt, else from the newest `out/*/g5-rwa`.
