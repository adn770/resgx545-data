# R3k: laptop sessions K0 and K1 of the question-closing pass, round 3 (kernel batch)

Prepared, NOT run. Nothing here touched the laptop, cachix or a repo; nothing is committed; the
clean-room guard was not run; no closed source was read. Read `PREFLIGHT.md` first.
Decisions: `~/src/plans/resgx545-question-closing.md`, "Round 3" (R3-K1 to R3-K11, R3-E1 to
R3-E9 and the L3 results logged there). Designs: `closing3/kernel/exp-kernel-r3.md` and
`series-r3.md` (what was built: debugfs names, verifier rows), `closing3/events/exp-events-r3.md`,
`closing3/events/readings/readings-r3.md` (R-1 to R-4).

It is a copy of the framework of `closing3/r3x-events/` (L3: runner, gates, scorer states, mock,
guard), which was not edited. It runs on the NEW module: fork `resgx545` at `8fc748b0`, srcversion
`230E0EF50FFFD606C53AE3C` (cachix `~/src/linux-sgx-r3-deliver/drivers/gpu/drm/gma500/gma500_gfx.ko`,
sha256 `06bf58db...`), blobs built and verified with the landed `tools/fwtask` at resgx545 main
`7aaa017` (the rows for `str` #69, #77, #691, `mov` to pa2-pa4, the exit's cfi and phas words,
`cont4`).

| session | laptop dir | stage | blob | rows | jobs (max) |
|---|---|---|---|---|---|
| K0 | `~/r3k0` | k0f | none (stock firmware) | F0: every new debugfs file exists and reads its default | 1 |
| | | k0t | none | GD (L1's g-dd dd-p1, a geometry job), PX (L2's q-t t-ctl-green-16x16, a pixel job), pinned `~/sgxfive-test-r1` | 2 |
| | | k0c | `alias2` (L3's, byte for byte) | C0 (reader), C1 (= A7, kept) | 2 |
| | | k0h | `ring_hold` (S2b's) | H0 (idle), H1 (a 90-tick hold), G0 (one ordinary kick: K = 2, +1) | 3 |
| K1 | `~/r3kev` | f | `ring_exit` | E0; FC4 (tail to the real exit, cont4: the control, first); FB (own end + cfi + phas: the exact exit); FCF (own end + cfi); FPH (own end + phas); stops capped at 2 | 9 |
| | | t | `ring_timer` | E0; T1 (`str #691` then the closed task), T2 (`str #691` then our own end) | 5 |
| | | kb | `ring_hold` | Q290: Q0, Q1 (`kicker =0x42`), Q2 (+ one miscinfo), Q3 (`kick_no_bump` + one miscinfo), x3 each | 12 |
| | | e2b | `pa_write2` | Q098: R x3, S, C4 x3 (`mov pa3`), C5 x3 (`mov pa4`), C6 x3 (`mov pa2`), Z67, Z68 | 15 |
| | | e3h | none | Q166, the host: `kregnow 0x0114` x3 rounds of 5 steps | 3 |
| | | e3a | `strclr` | Q166, a task: `str #69` x3 rounds | 3 |
| | | e3b | `ring_skip3` | Q111 LAST: B0 x3, B1 once (hold_recovery Y; a stopped row is not replicated), B2 (`str #77`, only if B1 kept the tick); stop cap 3 | 5 |

Gates: each stage's own kept `stage.json` (exit 0, or 8 after the lead chose `--from`); K1's first
gate is K0's last stage, so K1 refuses to start after a failed K0. K0 failing stops everything: a
failed control of a K0 stage makes the scorer exit 9 and the driver stop.

## Layout

- `asm/*.s`, `bins/*.blob`, `bins/blobs.json`, `bins/progs/*`: the tasks (`alias2` and `ring_hold`
  as L3 froze them; `ring_exit`, `ring_timer`, `pa_write2`, `strclr`, `ring_skip3` new) and the tool
  programs (L1's `dd-p1__0.bin`, `pix_green.bin`; `loop-b16-i56.bin`)
- `tables/STAGE.json`, `TABLES.md`: the job tables, generated from `r3layout.ROW_SPEC`
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`
- `gen/gen_r3.py` (writes all of the above), `gen/r3layout.py` (the page layout, the stages, the
  rows, every constant the generator, the runner, the guard and the scorer share), `gen/r3kblobs.py`
  (the new tasks), `gen/r3blobs.py` (alias2 and the scans the guard shares), `gen/laptop_files.py`
- `score/score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...` (K0 scorers, gates, main),
  `score/scorelib.py` (readers, stop signature, tally), `sc_ring.py` (f, t, kb, G0), `sc_e2b.py`,
  `sc_e3.py` (e3h, e3a, e3b)
- `run/r3_run.py` (laptop runner, core), `run/ops_k0.py`, `ops_kicker.py`, `ops_e2b.py`, `ops_e3.py`
  (the op families), `run/r3common.py`, `run/r3.sh SESSION` (Mac driver), `run/stage_r3.sh SESSION`
  (copy and check), `run/health_remote.sh`, `run/freeze_r3.sh`, `run/guard_r3.sh`, `run/guard_py.py`,
  `run/guard_blobs.py`
- `FROZEN.sha256`, `PREDICTIONS.sha256`, `LAPTOP-k0.sha256`, `LAPTOP-kev.sha256`, `TOOL.sha256`
  (`~/sgxfive-test-s1b`), `TOOLR1.sha256` (`~/sgxfive-test-r1`, K0's k0t only)
- `tests/`: `run_all.sh`, `sim_r3.py`, `test_scorer.py`, `test_guard.py`, `run_mock.py` and its mock
  (`mockfw/fwtask_run.py`, `mockfw/kmock.py`, `shims/`, `fake_tool.py`, `fake_health.sh`,
  `fixtures/`)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (the laptop needs only its
python3, 3.8 or later). Always `export PYTHONDONTWRITEBYTECODE=1`.

## Run (the lead), after the new module is installed and the laptop rebooted

```
cd ~/src/scratch/resgx545/closing3/r3k-events
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHON=../../closing/pixel-faults/.venv/bin/python PY=../../closing/pixel-faults/.venv/bin/python
run/guard_r3.sh
run/freeze_r3.sh verify
SGX_DRY_RUN=1 run/stage_r3.sh k0                      # prints the commands
run/stage_r3.sh k0 && run/r3.sh k0                    # K0: k0f, k0t, k0c, k0h; stops at the first problem
run/stage_r3.sh kev && run/r3.sh kev                  # K1: f, t, kb, e2b, e3h, e3a, e3b
run/r3.sh kev --from t                                # resume after a stage a stop budget ended (exit 8)
```

Scores: `out/score-STAGE.txt` (one `SUMMARY:` line each; `out/STAGE/` has the kept files, the stop
dumps `stop-NAME-regs.txt` / `-status.txt`, the signature, marks and P3 inside the job records).
Results stay on the laptop in `~/r3k0-out` and `~/r3kev-out`. Refreeze (`run/freeze_r3.sh freeze`
after `gen/gen_r3.py`) only before the first job.

## Tests (all offline)

```
tests/run_all.sh              # guard, freeze verify, sim, scorer, guard test, mock
tests/run_all.sh --prefreeze  # the same before the freeze (the freeze check is the one allowed failure)
```
