# R4b: a replicate of FCF's stop (Q152), round 4, decision 10 "reruns"

Prepared 2026-11-11, NOT run. Nothing here touched the laptop, cachix or a git repo; nothing is
committed. Read `PREFLIGHT.md` first.

## What and why

E817 (R3k stage f, dataset `edm-closing-r3k-events`, `out/f`) froze the verdict H-PHAS: in a plain
tick pass the `phas ... end` is what the EDM needs. The one row that refutes H-ANY and H-CFI is
FCF (ACT 3: the pass ends `cfi.global, idf, wdf, nop.end`, without the `phas`). FCF is job `fcf`,
the sixth job after the stage's arm (`e0, fc4, fc4-r2, fb, fb-r2, fcf`). It ran **once** and
stopped the tick. Its replicate `fcf-r2` was skipped by the stage's rule ("a stopped row is never
replicated"). So H-PHAS rests on one stopping job against two keeping jobs each of FB and FPH.

This session asks one question: does FCF's stop repeat, with E817's exact signature?

## Rows (stage `fr`, 21 jobs in three blocks)

The user's decision (2026-11-11): each replicate is a BLOCK that reproduces E817's stage f from its
arm to fcf, job for job. E817's `out/f/stage.json` gives that sequence: arm, then e0, fc4, fc4-r2,
fb, fb-r2, fcf, with no reset between them; fph and fph-r2 ran after fcf's stop, the recovery and
a re-arm, not between the arm and fcf. So a block is exactly that sequence, and its control after
the stop (fkN) is E817's first job after the re-arm (fph). No E817 job between the arm and fcf is
left out; the block adds nothing to it.

| block N (N = 1, 2, 3) | E817 job | ends the acted tick pass with | set | runs if |
|---|---|---|---|---|
| bNe0 (reset, then the arm) | e0 | nothing acted (idle ring) | control | N > 1: fk(N-1) kept |
| bNfc4, bNfc4-r2 | fc4, fc4-r2 | tail call to the closed exit (cont4) | control | N > 1: fk(N-1) kept |
| bNfb, bNfb-r2 | fb, fb-r2 | `cfi.global, idf, wdf, phas end, nop.end` | control | both bNfc4 kept |
| fcfN | fcf | `cfi.global, idf, wdf, nop.end` | fcf1 **held out**, fcf2, fcf3 replicates | both bNfb kept |
| (if fcfN stopped: signature x2, P3, dumps, reset, fill, triangle, health, re-arm) | (E817's stop and rearm1) | | | |
| fkN | fph | `idf, wdf, phas end, nop.end` | control | - |

The arm and the jobs of a block run with no reset between them, as in E817. A reset comes only at
a block start, after a stop, and at the end.

Hypotheses, frozen in `predictions/fr.tsv` before any run:

- **H-REP**: each FCF replicate stops the tick with E817's exact signature: the acted pass logged
  (flag 3, ACT_SEEN 3), no entry after it; both signature samples busy, CR_CLKGATESTATUS
  0x000ccfa0, USE0_SERV_EVENT empty bit clear and frozen, EVENT_TIMER counting, EVENT_STATUS
  0x20000000; CCB read offset = write offset; HostCtl dword 14 0; P3 (one miscinfo) not answered.
- **H-NOREP**: each replicate keeps the tick (next entry 25000 +- 50 after the acted pass).
- A stop with another signature refutes both (the scorer names what differs).

Replicates that disagree are "mixed", never held (scorekit `combine`).

## Stops

Only the three fcf rows may stop. Each stop is signed first (the signature twice, P3, the dumps),
then reset, gated (fill and triangle) and health-checked, and re-armed; then fkN runs. Block N+1
runs only if fkN kept the tick. The budget is 3 stops, one per block. A stop in any other row (a
control) ends the stage at once (exit 8). A watchdog line (exit 3) or a freeze (exit 6) stops all
laptop work. `PREFLIGHT.md` section 5 says how this fits R3k's rule.

Gates (the scorer): fcfN is judged only if block N's controls (bNe0, both bNfc4, both bNfb, its
arm) passed, and for N > 1 also fk(N-1) and the re-arm after fcf(N-1). The headline needs every
control.

## Layout

- `asm/ring_exit.s`, `bins/ring_exit.blob`, `bins/blobs.json`: R3k-events' frozen files byte for
  byte (`run/guard_blob_r4b.py` checks the published hashes and the landed verifier).
- `gen/r4blayout.py` (the one source: module, rows, E817's values), `gen/r3layout.py` (R3k's,
  byte for byte), `gen/gen_r4b.py` (writes `tables/fr.json`, `predictions/fr.tsv`, `TABLES.md`),
  `gen/laptop_files.py`.
- `run/r4b_run.py` (laptop runner, from R3k's `r3_run.py`), `run/r3common.py`,
  `run/health_remote.sh` (both R3k's), `run/r4b.sh` (Mac driver), `run/stage_r4b.sh`,
  `run/freeze_r4b.sh`, `run/guard_r4b.sh`, `run/guard_blob_r4b.py`, `run/guard_py.py`.
- `score/score_r4b.py` (the scorer), `score/scorekit.py` (resgx545 6421c1c
  `tools/closing/scorekit.py`, byte for byte), `score/scorelib.py` (R3k's readers, byte for byte).
- `tests/`: `run_all.sh`, `test_gen_r4b.py`, `test_score_r4b.py` (+ `worlds_r4b.py`, worlds built
  from E817's kept records in `fixtures/e817f/`), `run_mock.py` (+ `mockfw/`, `shims/`,
  `fake_tool.py`).
- `FROZEN.sha256`, `FROZEN.commits`, `PREDICTIONS.sha256`, `LAPTOP.sha256`, `TOOL.sha256`.

## Run (the lead), in the boot of the new module (fork a2788bd8)

```
cd ~/src/scratch/resgx545/closing3/r4-reruns/b-q152
export PYTHONDONTWRITEBYTECODE=1 PY=~/src/resgx545/.venv/bin/python PYTHON=~/src/resgx545/.venv/bin/python
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
tests/run_all.sh                                    # offline: RUN_ALL PASSED
run/guard_r4b.sh && run/freeze_r4b.sh verify
SGX_DRY_RUN=1 run/stage_r4b.sh; SGX_DRY_RUN=1 run/r4b.sh
run/stage_r4b.sh                                    # copy to ~/r4b and check there
run/r4b.sh                                          # load step, stage fr, copy, health, score
```

`run/r4b.sh ATTEMPT` names the attempt (default: date and time). Results: `out/ATTEMPT/` on the
Mac (`fr/`, `fr.log`, `health-load.txt`, `health-fr.txt`, `score-fr.txt` with one `SUMMARY:`
line), `~/r4b-out/ATTEMPT/fr` on the laptop. An existing attempt is never overwritten.
