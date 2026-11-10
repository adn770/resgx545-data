# R3x-events: laptop session L3 of the question-closing pass, round 3

Prepared, NOT run. Nothing here touched the laptop, cachix or a repo; nothing is committed.
Read `PREFLIGHT.md` first. Decisions: `~/src/plans/resgx545-question-closing.md`, "Round 3"
(R3-E1 to R3-E9). Proposal: `closing3/events/exp-events-r3.md`; the firmware readings that fix the
rows: `closing3/events/readings/readings-r3.md` (R-1 to R-4).

It is a copy of the framework of `closing2/r3-events/` (never edited): kernel-log markers,
kept-output gates, scorer states, mock laptop, guard, `bins/ring_hold.blob` (S2b's, byte for byte).

| stage | rows | blob | gate | jobs (max) |
|---|---|---|---|---|
| h | H0 (no hold), H1 (signature inside a 90-tick hold) | `ring_hold.blob` | none | 6 |
| c | C0 (reader), C1-C4 (cmd 10: sa65 = one word, left in place), C5 (cmd 12: sa64 = pa0 & ~2 x 50) | `alias2.s` | h finished | 13 |
| e | E0, X1 (slot 2), X20 (only if X1 kept 2 of 2), B3 (LAST) | `ring_end.s` | c finished | 7 |
| d | D0, D1 (E537's sa65, bit 8 clear), D2 (bit 8 only), D3 (E537's sa65, last of the expected stops), D4 (only if D3 kept the tick) | `alias2.s` | e finished | 7 |

A gate is the previous stage's own kept `stage.json` (exit 0, or 8 when a second tick stop ended it
and the lead chose `--from`): derived from kept output, never from a file the staging resets.
Stage f and the Q290 rows are NOT here: they run after the kernel batch.

## Layout

- `asm/alias2.s`, `asm/ring_end.s`, `asm/ring_hold.s`, `bins/*.blob`, `bins/blobs.json`: the three
  tasks (301, 678 and 747 instructions, all accepted by the landed `tools/fwtask`; `alias2.s` is
  `alias.s` of closing2 plus commands 10, 11, 12; `ring_end.s` is `ring_skip.s` generalised to KIND,
  ACT, COUNT with a second continue triple, `cont2`, in entry 0)
- `tables/{h,c,e,d}.json`, `TABLES.md`: the job tables, generated from `r3layout.ROW_SPEC`
- `predictions/{h,c,e,d}.tsv`: frozen predictions `case quantity value model set`
- `gen/gen_r3.py` (writes all of the above), `gen/r3blobs.py` (the two new tasks and the scans the
  guard shares), `gen/r3layout.py` (the results page layout, the rows, the E537 words, the dump readers)
- `score/score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...`: the scorer
- `run/r3_run.py` (laptop runner), `run/r3.sh` (Mac driver), `run/stage_r3.sh` (copy and check),
  `run/health_remote.sh`, `run/freeze_r3.sh`, `run/guard_r3.sh`, `run/guard_py.py`, `run/guard_blobs.py`
- `FROZEN.sha256`, `PREDICTIONS.sha256`, `LAPTOP.sha256`, `TOOL.sha256` (the pinned health tool)
- `tests/`: `run_all.sh`, `sim_r3.py`, `test_scorer.py`, `test_guard.py`, `run_mock.py` (and its
  mock: `mockfw/`, `shims/`, `fake_tool.py`, `fake_health.sh`)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (the laptop needs only its
python3, 3.8 or later). Always `export PYTHONDONTWRITEBYTECODE=1`.

## Run (the lead)

The laptop must be in linux-resgx545 (loaded module srcversion B21FDA82BD5E5CB5A627E3B) with the
tool `~/sgxfive-test-s1b` of S1b in place. The laptop directory is `~/r3xev` (results in
`~/r3xev-out`), no collision with `~/r3g` or `~/r3p-`.

```
cd ~/src/scratch/resgx545/closing3/r3x-events
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHON=../../closing/pixel-faults/.venv/bin/python PY=../../closing/pixel-faults/.venv/bin/python
run/guard_r3.sh
run/freeze_r3.sh verify
SGX_DRY_RUN=1 run/stage_r3.sh                        # prints the commands
run/stage_r3.sh                                      # copies, checks the srcversion, the files, the pinned tool
run/r3.sh                                            # h, c, e, d; stops at the first problem
run/r3.sh --from e                                   # resume (c's kept stage.json is the gate)
```

Scores: `out/score-STAGE.txt` (one `SUMMARY:` line each; `out/STAGE/` has the kept files, the stop
dumps `stop-NAME-regs.txt` / `-status.txt` and the signature, marks and P3 inside the job records).
A stage that a second stop ended (exit 8) is reset, healthy and scored; the session then ends and the
lead decides (`--from NEXT`). Refreeze (`run/freeze_r3.sh freeze` after `gen/gen_r3.py`) only before
the first job.

## Tests (all offline)

```
tests/run_all.sh              # guard, freeze verify, sim, scorer, guard test, mock (about 3 minutes)
tests/run_all.sh --prefreeze  # the same before the freeze (the freeze check is the one allowed failure)
```
