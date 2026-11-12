# R6-pixel of the resgx545 question-closing pass (round 6): prepared, NOT run

Laptop session R6-pixel: Q276 (is an o4..o7 write stored, does the predicate gate it; which instance's
o3 enters the OR; the walk in E406's setup) and Q230 (the 1/w word: how e varies between neighbouring
mantissas, H-FRAC, H-MANT at far exponents). Userspace only, one session, 202 jobs in five job tables,
about 18 minutes of jobs and 25 to 30 with staging and health. Plan:
`closing6/pixel/exp-pixel-r6.md`, every decision (a) (`closing6/DECISIONS-R6.md` R6-2 a: p6-rd 58,
g6-rwa + g6-rw 114, L3 8, S 22 last with `kpoke rd:9` and a restore check). Built offline on the Mac
from round 5's R5-pixel (`render/closing-r5-pixel`, the published copy). Nothing here touched the
laptop, cachix or a git repo. Read `PREFLIGHT.md` first.

Offline records this session starts from (on resgx545 main d9b2969, the freeze's commit): E871 (Q276:
the own words of o4..o7 reach no pixel of any kept image; E081's o4..o7 counts are leftovers) and E872
(Q230: 0 of 512703 declared models fit; H-FRAC read on FIT, frozen, held 13 of 13 on HELD OUT).

## What runs, in this order (`stages.txt`)

| table | jobs | question | what |
|---|---|---|---|
| p6-rd | 58 | Q276 | 14 controls (c-e709, c-u, c-all4, c-ow, c-rd-0, c-prd-0 k1/k7), rd-1..rd-7 (14), n-rd-1/4, x-rd-4/5 (8), prd-3/4 at k 0,1,2,3,7 (20), rd-4 again (2) |
| p6-l3 | 8 | Q276 | optional set L3: R5's p3-pa-k0/k3 byte for byte (determinism control), new p3-pa-k1/k2 |
| g6-rwa | 8 | Q230 | controls: R5's rw-k0..k5 and d-01, d-02 byte for byte (their words exact) |
| g6-rw | 106 | Q230 | L: 6 windows x 12 jobs (strides 1, 2^8, 2^16), B: 8 jobs at frac 0.42..0.62, 2 replicates, E: 4 R4 rows x 6 exponents (last) |
| p6-s | 22 | Q023/Q276 | optional set S, last: c-s-all4, s-0..s-7, s-n4 in E406's setup (`--blk 1=0x05d00200 --kpoke rd:9=1`), then r-u x/y (c-u with `--kpoke rd:9=0`: the restore check) |

Every row: knobs `stophang s2` (STATUS2 read after the reset and after the job; not 0x400 after the
reset stops the stage, rc 16), a GPU reset before the job, no regtimeline, no knob write, no firmware
`str`. p6-s rows add the knob `kpoke`: the tool's own `--kpoke rd:9=0|1` (render details dword 9 of
that job's render, applied once and dropped by the kernel); debugfs kpoke must read empty before and
after each such row (else rc 19, cleared) and the exit trap clears anything left. After each table the
driver scores it and runs its gate; a gate that does not pass stops the session (exit 42): p6-rd's
bridge (c-e709 G-o4, c-u G-o1, c-ow, c-rd-0), g6-rwa's control words, g6-rw's controls, p6-s's restore
check. p6-l3 never stops the session (its controls void the set only).

## Predicted outcomes (frozen; `predictions/*.tsv`, `TABLES.md`)

- p6-rd: no model favoured. H-STORE (S at rd-1..7), H-FOUR (S at 1..3, not S at 4..7), H-O0 (A0
  everywhere), H-MOD4 (S at 1..3, o_(j-4)'s word at 4..7). Predicate rows: gated / ignored / never per
  lane, scored only if rd-j reads S and c-prd-0 passes. If rd-4 is not S: decision R6-6 a (retire the
  o4-predicate clause as not observable in this command).
- p6-l3: x jobs 5:1; y jobs H-Y1 (5:0, 5:1), H-Y2 (5:1, 5:0) or H-YN (5:1, 5:1) at k = 1, 2.
- g6-rw: H-FRAC (no word with frac < 0.5 stores RZ + 1; about 117 such words); H-SMOOTH(s) per stride,
  none predicted to hold; H-MANT at -12, -6, -3, 5, 8, 12 (R4's delta; a clipped exponent is "no
  object", not a refutation).
- p6-s: H-OR (3 2 2 3 2 2 2 2, tag 5 at s-n4) vs H-OWN4 (2 2 2 2 1 2 2 2, none at s-n4).

## Stops

Any fault, hang, failure, freeze or kernel BUG stops the stage (rc 3, 4, 6); the first failed health
recovery (rc 5); STATUS2 not 0x400 after a reset (rc 16); kpoke armed before or after a kpoke row (rc
19); less than 200 MB free on `~/scratch` before a job (rc 21); a gate (42). No fault is expected: the
pixel command ran 155 kept clean jobs (R3 to R5), the 1/w command 72; `mov` from an output register
ran in E373; E406's setup ran 27 clean jobs at one data row (hangs only at 5 to 7 rows; R5's programs
have one). Stop budget: zero faults, zero hangs (the first one stops the stage; the lead decides).

## Layout

- `tables/STAGE.txt` (`name|set|risk|knobs|rt|command`; `#need` lines), `TABLES.md` (readable).
- `predictions/STAGE.tsv`; `PREDICTIONS.sha256`; `FROZEN.sha256` (every generator, scorer, runner,
  table, prediction, program, template, test, shim and fixture, and by absolute path the resgx545 and
  resgx545-data files read: `gen/pins_*.txt`); `FROZEN.commits` (resgx545 main d9b2969).
- `gen/`: `r6gen.py` writes everything (`r6_rd.py`, `r6_rw.py`); R5's `r5_o4.py`, `r5_rw.py`,
  `r5common.py` are byte copies of the published R5 files (pinned), imported for R5's program
  builder, command templates and paths.
- `score/`: `score_r6.py` (stage, `gate`, `verdict`; refuses unless the freeze verifies), `score_rd.py`
  + `rdmodel.py` (p6-rd, p6-l3, p6-s), `score_rw6.py` + `rwdesign6.py` (g6-rwa, g6-rw); R5's
  `score_o5.py`, `o5model.py`, `score_rw5.py`, `rwdesign5.py` and R4's `score_o4.py`, `score_rw.py`,
  `rwdesign.py`, `rwfam.py`, `r4lib.py` are byte copies (pinned); `scorekit.py` = `tools/closing/scorekit.py`.
- `run/`: `stage_r6.sh` (Mac: copies and checks), `r6.sh` (Mac driver), `run_stage.sh` + `lib_r6.sh` +
  `r6.env` (laptop runner), `freeze_r6.sh`, `guard_r6.sh`, `lib_check.sh`.
- `tests/`: `run_all.sh` (PREFLIGHT.md 8); `mockstage.py` (mock stages from the tables' own
  commands); `fake_tool.sh`, `fake_o4.py`, `fake_rw.py` (argv- and bytes-driven, no timing);
  `shims/` (sudo, ssh, scp, df, ...); `fixtures/` (R3/R4 kept images and dumps the fakes rewrite);
  `debug-src/simcheck` (the sgx-sim harness, now with `--list`).

Laptop directories: `~/scratch/r6p/{run,stage,out}`; work directories `mktemp -d
~/scratch/tmp/r6p.XXXXXX`, one per job, removed once its files are kept (never `/tmp`). Python:
`~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python`; numpy is not used.

## Publishing

Nothing in this directory is firmware-derived (no disassembly reading, no script importing one): the
whole directory may be published by the fold. `debug/` is scratch (build products, mock runs).

## Commands the lead runs

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing6/r6-pixel
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                    # offline, all must pass (about 4 minutes)
run/guard_r6.sh && run/freeze_r6.sh verify
SGX_DRY_RUN=1 run/stage_r6.sh            # prints the commands
run/stage_r6.sh                          # copies, compares, checks the rgn4 tool
run/r6.sh                                # the session (stops: PREFLIGHT.md 5)
$PY score/score_r6.py verdict out/ATT    # one line a table
```

`run/r6.sh --from TABLE` (a new attempt directory) continues after a stop; `--only TABLE...` reruns
tables (`--only p6-rd g6-rwa g6-rw` runs without the optional sets). g6-rw reads part a from the same
attempt, else from the newest `out/*/g6-rwa`.
